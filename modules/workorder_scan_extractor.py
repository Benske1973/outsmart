import csv
import json
import re
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from modules.config import REPORTS_DIR


FIELD_MAP = {
    "worksheet[ProjectNr]": "project_number",
    "worksheet[ProjectActivityNr]": "project_activity_number",
    "worksheet[ExternProjectNr]": "external_project_number",
    "RegistrationDateField": "registration_date_display",
    "worksheet[RegistrationDate]": "registration_date",
    "worksheet[JobNr]": "job_number",
    "worksheet[WorkorderNo]": "external_workorder_number",
    "worksheet[Reference]": "reference",
    "worksheet[ExternalReference]": "external_reference",
    "worksheet[TypeOfWork]": "type_of_work",
    "worksheet[WorkStatus]": "workorder_status_code",
    "worksheet[PaymentMethod]": "payment_method",
    "worksheet[WorkDuration]": "work_duration_minutes",
    "worksheet[WorkDeadline]": "work_deadline",
    "worksheet[WorkDate]": "work_start_date",
    "worksheet[WorkEndDate]": "work_end_date",
    "CustomerDebtorNr": "customer_debtor_number",
    "adr_code": "address_code",
    "cpn_code": "contact_code",
    "client[debiteur_number]": "customer_debtor_number_display",
    "client[name]": "customer_name",
    "client[street]": "work_address",
    "client[zip]": "postal_code",
    "client[city]": "city",
    "client[country]": "country_code",
    "client[contact]": "contact_name",
    "client[phone]": "contact_phone",
    "client[werkbonmailto]": "workorder_email",
    "CustomerDebtorNrInvoice": "invoice_debtor_number",
    "cpn_code_invoice": "invoice_contact_code",
    "worksheet[WorkDescription]": "work_description",
    "worksheet[InternalWorkDescription]": "internal_work_description",
    "worksheet[ShortWorkDescription]": "short_work_description",
    "worksheet[Comment]": "comment",
    "worksheet[EmployeeNr]": "employee_number",
    "worksheet[pgp_code]": "pgp_code",
    "worksheet[accountmanager]": "account_manager",
}

TAB_NAMES = [
    "Levering / Klant relatie",
    "Terugkerende planning",
    "Omschrijving",
    "Formulier",
    "Werknemer",
    "Materialen",
    "Werk periodes",
    "Bestanden",
    "Foto's",
    "Objecten",
    "Notities",
    "Klantcommunicatie",
    "Logboek",
]


@dataclass
class WorkorderScanProfile:
    source_folder: str
    created_at: str
    page_url: str = ""
    frame_url: str = ""
    outsmart_id: str = ""
    outsmart_number: str = ""
    sheet_key: str = ""
    fields: Dict[str, str] = field(default_factory=dict)
    raw_fields: List[Dict[str, Any]] = field(default_factory=list)
    tabs_found: List[str] = field(default_factory=list)
    attachments: List[Dict[str, str]] = field(default_factory=list)
    table_headers: List[Dict[str, Any]] = field(default_factory=list)
    dropdown_options: Dict[str, List[str]] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)


class WorkorderScanExtractor:
    def extract(self, folder: Path) -> WorkorderScanProfile:
        folder = Path(folder)
        snapshot = json.loads((folder / "snapshot.json").read_text(encoding="utf-8-sig", errors="replace"))
        frame = self._best_workorder_frame(snapshot)
        html = self._best_html(folder)
        profile = WorkorderScanProfile(
            source_folder=str(folder),
            created_at=datetime.now().isoformat(timespec="seconds"),
            page_url=snapshot.get("url", ""),
            frame_url=frame.get("url", "") if frame else "",
        )
        profile.outsmart_id = self._find_outsmart_id(profile.page_url)
        profile.sheet_key = self._find_query_value(profile.frame_url, "sheet") or self._find_query_value(profile.frame_url, "sheetid")
        profile.outsmart_number = self._find_outsmart_number(html)
        self._extract_fields(profile, frame or {})
        profile.tabs_found = self._find_tabs(html)
        profile.attachments = self._find_attachments(html)
        profile.table_headers = self._find_tables(frame or {})
        profile.dropdown_options = self._find_dropdown_options(frame or {})
        self._validate(profile)
        return profile

    def _best_workorder_frame(self, snapshot: Dict[str, Any]) -> Dict[str, Any]:
        frames = snapshot.get("frames") or []
        for frame in frames:
            url = (frame.get("url") or "").lower()
            if "backoffice_werkbon" in url or "backoffice_klaarzetten" in url:
                return frame
        return max(frames, key=lambda f: len(f.get("fields") or []), default={})

    def _best_html(self, folder: Path) -> str:
        candidates = sorted(folder.glob("frame_*.html"), key=lambda p: p.stat().st_size, reverse=True)
        if candidates:
            return candidates[0].read_text(encoding="utf-8-sig", errors="replace")
        page = folder / "page.html"
        return page.read_text(encoding="utf-8-sig", errors="replace") if page.exists() else ""

    def _extract_fields(self, profile: WorkorderScanProfile, frame: Dict[str, Any]) -> None:
        for field in frame.get("fields") or []:
            key = field.get("name") or field.get("id") or field.get("label") or ""
            value = str(field.get("value") or "").strip()
            if not key:
                continue
            mapped = FIELD_MAP.get(key)
            row = {
                "key": key,
                "mapped": mapped or "",
                "value": value,
                "tag": field.get("tag", ""),
                "type": field.get("type", ""),
                "id": field.get("id", ""),
                "required": field.get("required", False),
                "readonly": field.get("readonly", False),
                "disabled": field.get("disabled", False),
            }
            profile.raw_fields.append(row)
            if mapped and value and mapped not in profile.fields:
                profile.fields[mapped] = value
            if key == "worksheet[WorkStatus]":
                selected = self._selected_option_text(field)
                if selected:
                    profile.fields["workorder_status_text"] = selected
            if key == "worksheet[EmployeeNr]":
                selected = self._selected_option_text(field)
                if selected:
                    profile.fields["employee_text"] = selected
            if key == "adr_code":
                selected = self._selected_option_text(field)
                if selected:
                    profile.fields["address_text"] = selected
            if key == "cpn_code":
                selected = self._selected_option_text(field)
                if selected:
                    profile.fields["contact_text"] = selected

    def _selected_option_text(self, field: Dict[str, Any]) -> str:
        value = str(field.get("value") or "")
        for option in field.get("options") or []:
            if str(option.get("value") or "") == value:
                return str(option.get("text") or "").strip()
        return ""

    def _find_tabs(self, html: str) -> List[str]:
        found = []
        for tab in TAB_NAMES:
            if tab.lower() in html.lower():
                found.append(tab)
        return found

    def _find_attachments(self, html: str) -> List[Dict[str, str]]:
        attachments = []
        pattern = re.compile(r'<a[^>]+href="([^"]+)"[^>]*>([^<]*(?:\.pdf|\.PDF|\.jpg|\.jpeg|\.png|\.docx|\.xlsx)[^<]*)</a>', re.I)
        for href, text in pattern.findall(html):
            name = re.sub(r"\s+", " ", text).strip()
            if name and not any(item["name"] == name for item in attachments):
                attachments.append({"name": name, "href": href})
        return attachments

    def _find_tables(self, frame: Dict[str, Any]) -> List[Dict[str, Any]]:
        result = []
        for table in frame.get("tables") or []:
            headers = [str(x).strip() for x in (table.get("headers") or []) if str(x).strip()]
            if headers:
                result.append({"rows": table.get("rows", 0), "headers": headers})
        return result

    def _find_dropdown_options(self, frame: Dict[str, Any]) -> Dict[str, List[str]]:
        result: Dict[str, List[str]] = {}
        for field in frame.get("fields") or []:
            key = field.get("name") or field.get("id") or field.get("label") or ""
            options = []
            for option in field.get("options") or []:
                text = str(option.get("text") or "").strip()
                if text and text not in options:
                    options.append(text)
            if key and options:
                result[key] = options
        for dropdown in frame.get("dropdowns") or []:
            trigger = str(dropdown.get("trigger_text") or f"dropdown_{dropdown.get('index', '')}").strip()[:80]
            options = []
            for option in dropdown.get("options") or []:
                text = str(option.get("text") or "").strip()
                if text and text not in options:
                    options.append(text)
            if trigger and options:
                result[f"captured:{trigger}"] = options
        return result

    def _validate(self, profile: WorkorderScanProfile) -> None:
        required = [
            "job_number", "external_workorder_number", "customer_debtor_number",
            "address_code", "work_address", "work_description", "workorder_status_code",
        ]
        for key in required:
            if not profile.fields.get(key):
                profile.warnings.append(f"Ontbrekend of leeg: {key}")
        for tab in ["Levering / Klant relatie", "Omschrijving", "Bestanden"]:
            if tab not in profile.tabs_found:
                profile.warnings.append(f"Tab niet gevonden in scan: {tab}")

    def _find_outsmart_id(self, url: str) -> str:
        match = re.search(r"/work-orders/(\d+)", url or "")
        return match.group(1) if match else ""

    def _find_query_value(self, url: str, key: str) -> str:
        match = re.search(rf"[?&]{re.escape(key)}=([^&]+)", url or "")
        return match.group(1) if match else ""

    def _find_outsmart_number(self, html: str) -> str:
        patterns = [
            r"Algemeen\s*-\s*(20\d{2}\.\d+)",
            r"Order nummer:\s*</label>\s*<div[^>]*>\s*<p><b>(20\d{2}\.\d+)</b>",
            r"\b(20\d{2}\.\d{3,})\b",
        ]
        for pattern in patterns:
            match = re.search(pattern, html, re.I | re.S)
            if match:
                return match.group(1)
        return ""


def write_workorder_scan_profile(profile: WorkorderScanProfile) -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = f"workorder_scan_profile_{profile.outsmart_number or stamp}_{stamp}"
    json_path = REPORTS_DIR / f"{base}.json"
    md_path = REPORTS_DIR / f"{base}.md"
    fields_csv = REPORTS_DIR / f"{base}_fields.csv"

    data = asdict(profile)
    json_path.write_text(json.dumps(data, indent=4, ensure_ascii=False), encoding="utf-8")
    with fields_csv.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=["key", "mapped", "value", "tag", "type", "id", "required", "readonly", "disabled"], delimiter=";")
        writer.writeheader()
        for row in profile.raw_fields:
            writer.writerow(row)

    lines = [
        "# Workorder Scan Profile",
        "",
        f"Source: `{profile.source_folder}`",
        f"OutSmart number: {profile.outsmart_number or '-'}",
        f"OutSmart ID: {profile.outsmart_id or '-'}",
        f"Sheet key: {profile.sheet_key or '-'}",
        f"Frame URL: `{profile.frame_url}`",
        "",
        "## Belangrijkste velden",
    ]
    for key in sorted(profile.fields):
        value = profile.fields[key]
        if len(value) > 500:
            value = value[:500] + "..."
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Tabs gevonden"])
    lines.extend([f"- {tab}" for tab in profile.tabs_found] or ["- Geen tabs gevonden"])
    lines.extend(["", "## Bijlagen"])
    lines.extend([f"- {item['name']}" for item in profile.attachments] or ["- Geen bijlagen gevonden"])
    lines.extend(["", "## Tabellen"])
    for table in profile.table_headers:
        lines.append(f"- rows={table['rows']} | {' | '.join(table['headers'])}")
    lines.extend(["", "## Dropdowns/selects"])
    for name, options in sorted(profile.dropdown_options.items()):
        lines.append(f"- {name}: {len(options)} opties -> {options[:25]}")
    if profile.warnings:
        lines.extend(["", "## Waarschuwingen"])
        lines.extend([f"- {warning}" for warning in profile.warnings])
    lines.extend(["", "## Output"])
    lines.append(f"- JSON: `{json_path}`")
    lines.append(f"- Fields CSV: `{fields_csv}`")
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return md_path
