import csv
import json
import re
import zipfile
from collections import Counter, defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from modules.config import REPORTS_DIR
from modules.document_classifier import DocumentClassifier

ORDER_RE = re.compile(r"\b4\d{6}\b")
PO_RE = re.compile(r"\b45\d{8}\b")
OUTSMART_NO_RE = re.compile(r"\b20\d{2}\.\d{3,5}\b")


@dataclass
class MailCase:
    case_id: str
    classification: str
    confidence: int
    folder_name: str
    subject: str
    sender_email: str
    sender_name: str
    received_at: str
    orders: List[str] = field(default_factory=list)
    purchase_orders: List[str] = field(default_factory=list)
    outsmart_numbers: List[str] = field(default_factory=list)
    attachment_count: int = 0
    document_types: List[str] = field(default_factory=list)
    reasons: List[str] = field(default_factory=list)


class MailCaseAnalyzer:
    def __init__(self) -> None:
        self.classifier = DocumentClassifier()

    def analyze_zip(self, zip_path: Path) -> Dict[str, object]:
        with zipfile.ZipFile(zip_path, "r") as archive:
            manifest_entry = self._find_entry(archive, "manifest.json")
            if manifest_entry is None:
                raise FileNotFoundError("manifest.json not found in export package")
            manifest = json.loads(archive.read(manifest_entry).decode("utf-8-sig"))
            body_entries = {
                name.rsplit("/", 1)[0]: name
                for name in archive.namelist()
                if name.endswith("/body.txt")
            }
            cases: List[MailCase] = []
            for folder in manifest.get("folders", []):
                folder_name = str(folder.get("folder_name", ""))
                for mail in folder.get("mails", []):
                    cases.append(self._analyze_mail(folder_name, mail, archive, body_entries))
            groups = self._group_cases(cases)
            return {
                "zip_path": str(zip_path),
                "created_at": manifest.get("created_at"),
                "read_only_mode": manifest.get("read_only_mode"),
                "mail_count": len(cases),
                "case_count": len(groups),
                "cases": cases,
                "groups": groups,
            }

    def _find_entry(self, archive: zipfile.ZipFile, suffix: str) -> Optional[str]:
        for name in archive.namelist():
            if name.endswith(suffix):
                return name
        return None

    def _analyze_mail(self, folder_name: str, mail: Dict[str, object], archive: zipfile.ZipFile, body_entries: Dict[str, str]) -> MailCase:
        subject = str(mail.get("subject", ""))
        sender_email = str(mail.get("sender_email", "") or "")
        sender_name = str(mail.get("sender_name", "") or "")
        received_at = str(mail.get("received_at", "") or "")
        text_parts = [subject]
        mail_dir = self._mail_dir_from_metadata_path(mail)
        body_name = body_entries.get(mail_dir)
        if body_name:
            try:
                text_parts.append(archive.read(body_name).decode("utf-8-sig", errors="ignore"))
            except Exception:
                pass
        attachments = list(mail.get("attachments", []))
        document_types = []
        for attachment in attachments:
            filename = str(attachment.get("filename", ""))
            text_parts.append(filename)
            document_types.append(self.classifier.classify(filename))
        combined = "\n".join(text_parts)
        orders = sorted(set(ORDER_RE.findall(combined)))
        purchase_orders = sorted(set(PO_RE.findall(combined)))
        outsmart_numbers = sorted(set(OUTSMART_NO_RE.findall(combined)))
        classification, confidence, reasons = self._classify(folder_name, combined, orders, purchase_orders, outsmart_numbers, document_types, attachments)
        case_id = self._case_id(folder_name, subject, orders, purchase_orders, outsmart_numbers)
        return MailCase(
            case_id=case_id,
            classification=classification,
            confidence=confidence,
            folder_name=folder_name,
            subject=subject,
            sender_email=sender_email,
            sender_name=sender_name,
            received_at=received_at,
            orders=orders,
            purchase_orders=purchase_orders,
            outsmart_numbers=outsmart_numbers,
            attachment_count=len(attachments),
            document_types=sorted(set(document_types)),
            reasons=reasons,
        )

    def _classify(self, folder_name: str, text: str, orders: List[str], purchase_orders: List[str], outsmart_numbers: List[str], document_types: List[str], attachments: List[Dict[str, object]]):
        lower = text.lower()
        reasons: List[str] = []
        doc_counter = Counter(document_types)
        if any(word in lower for word in ["annulatie", "annuleer", "geannuleerd", "vervalt", "niet uitvoeren"]):
            reasons.append("Annulatie-woorden gevonden")
            return "ANNULATIE", 90, reasons
        if any(word in lower for word in ["wijziging", "bijkomende informatie", "extra info", "planning", "nieuwe datum", "aanpassing"]):
            reasons.append("Wijziging/planning-woorden gevonden")
            return "WIJZIGING", 78, reasons
        if outsmart_numbers:
            reasons.append("OutSmart werkbonnummer gevonden")
            return "BESTAANDE_WERKBON", 85, reasons
        if doc_counter.get("DIENSTBEVEL", 0) or (orders and purchase_orders):
            reasons.append("Dienstbevel of order+bestelbon gevonden")
            return "NIEUWE_OPDRACHT", 86, reasons
        if doc_counter.get("BESTELBON", 0) and purchase_orders:
            reasons.append("Bestelbon gevonden zonder duidelijk dienstbevel")
            return "CONTROLE_NODIG", 70, reasons
        if "facturatie" in folder_name.lower():
            reasons.append("Facturatiemap")
            return "BESTAANDE_WERKBON", 60, reasons
        if attachments and not orders and not purchase_orders:
            reasons.append("Bijlagen zonder klassieke referenties")
            return "CONTROLE_NODIG", 55, reasons
        if any(domain in lower for domain in ["out-smart.com", "equans-apps"]):
            reasons.append("Systeemmail")
            return "GEEN_ACTIE", 60, reasons
        reasons.append("Geen duidelijke werkbonreferentie")
        return "GEEN_ACTIE", 45, reasons

    def _case_id(self, folder_name: str, subject: str, orders: List[str], purchase_orders: List[str], outsmart_numbers: List[str]) -> str:
        if orders:
            return f"ORDER-{orders[0]}"
        if purchase_orders:
            return f"PO-{purchase_orders[0]}"
        if outsmart_numbers:
            return f"OUTSMART-{outsmart_numbers[0]}"
        cleaned = re.sub(r"[^A-Za-z0-9]+", "-", subject).strip("-")[:60] or folder_name
        return f"SUBJECT-{cleaned}"

    def _mail_dir_from_metadata_path(self, mail: Dict[str, object]) -> str:
        attachments = list(mail.get("attachments", []))
        if attachments:
            path = str(attachments[0].get("export_path", ""))
            parts = path.split("/")
            if len(parts) >= 3:
                return "/".join(parts[:2])
        return ""

    def _group_cases(self, cases: List[MailCase]) -> List[Dict[str, object]]:
        grouped: Dict[str, List[MailCase]] = defaultdict(list)
        for case in cases:
            grouped[case.case_id].append(case)
        result = []
        for case_id, items in sorted(grouped.items(), key=lambda pair: (pair[0])):
            classifications = Counter(item.classification for item in items)
            folders = Counter(item.folder_name for item in items)
            result.append({
                "case_id": case_id,
                "mail_count": len(items),
                "primary_classification": classifications.most_common(1)[0][0],
                "classifications": classifications.most_common(),
                "folders": folders.most_common(),
                "orders": sorted(set(value for item in items for value in item.orders)),
                "purchase_orders": sorted(set(value for item in items for value in item.purchase_orders)),
                "outsmart_numbers": sorted(set(value for item in items for value in item.outsmart_numbers)),
                "subjects": [item.subject for item in items[:5]],
            })
        return result


def write_case_report(analysis: Dict[str, object]) -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = REPORTS_DIR / f"mail_case_analysis_{timestamp}.md"
    csv_path = REPORTS_DIR / f"mail_case_analysis_{timestamp}.csv"
    json_path = REPORTS_DIR / f"mail_case_analysis_{timestamp}.json"

    payload = {
        "zip_path": analysis["zip_path"],
        "created_at": analysis["created_at"],
        "read_only_mode": analysis["read_only_mode"],
        "mail_count": analysis["mail_count"],
        "case_count": analysis["case_count"],
        "cases": [asdict(case) for case in analysis["cases"]],
        "groups": analysis["groups"],
    }
    json_path.write_text(json.dumps(payload, indent=4, ensure_ascii=False), encoding="utf-8")

    with csv_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=[
            "case_id", "classification", "confidence", "folder_name", "received_at",
            "sender_email", "subject", "orders", "purchase_orders", "outsmart_numbers",
            "attachment_count", "document_types", "reasons",
        ], delimiter=";")
        writer.writeheader()
        for case in analysis["cases"]:
            writer.writerow({
                "case_id": case.case_id,
                "classification": case.classification,
                "confidence": case.confidence,
                "folder_name": case.folder_name,
                "received_at": case.received_at,
                "sender_email": case.sender_email,
                "subject": case.subject,
                "orders": ", ".join(case.orders),
                "purchase_orders": ", ".join(case.purchase_orders),
                "outsmart_numbers": ", ".join(case.outsmart_numbers),
                "attachment_count": case.attachment_count,
                "document_types": ", ".join(case.document_types),
                "reasons": " | ".join(case.reasons),
            })

    class_counter = Counter(case.classification for case in analysis["cases"])
    folder_class_counter: Dict[str, Counter] = defaultdict(Counter)
    for case in analysis["cases"]:
        folder_class_counter[case.folder_name].update([case.classification])

    lines = [
        "# Mail Case Analysis",
        "",
        f"Package: `{analysis['zip_path']}`",
        f"Read-only confirmed: {analysis['read_only_mode']}",
        f"Mails: {analysis['mail_count']}",
        f"Cases/groups: {analysis['case_count']}",
        "",
        "## Classifications",
    ]
    for name, count in class_counter.most_common():
        lines.append(f"- {name}: {count}")
    lines.extend(["", "## Per Folder"])
    for folder, counter in sorted(folder_class_counter.items()):
        lines.append(f"- {folder}: {counter.most_common()}")
    lines.extend(["", "## Top Case Groups"])
    for group in analysis["groups"][:80]:
        lines.append(f"- {group['case_id']} | mails: {group['mail_count']} | class: {group['primary_classification']} | folders: {group['folders']} | subjects: {group['subjects'][:2]}")
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path
