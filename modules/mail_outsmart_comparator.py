import csv
import json
from collections import Counter, defaultdict
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

from modules.case_analyzer import MailCase, MailCaseAnalyzer
from modules.config import PROJECT_ROOT, REPORTS_DIR
from modules.outsmart_csv_importer import OutSmartCsvImporter, OutSmartRecord


def load_debtor_profiles() -> Dict[str, Dict[str, object]]:
    path = PROJECT_ROOT / "data" / "debtor_profiles.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


class MailOutSmartComparator:
    def __init__(self) -> None:
        self.profiles = load_debtor_profiles()

    def compare(self, mailbox_zip: Path, outsmart_dir: Path) -> Dict[str, object]:
        case_analysis = MailCaseAnalyzer().analyze_zip(mailbox_zip)
        records = OutSmartCsvImporter().load_directory(outsmart_dir)
        indexes = self._build_indexes(records)
        comparisons = []
        for case in case_analysis["cases"]:
            debtor = self._debtor_for_folder(case.folder_name)
            matches = self._find_matches(case, indexes)
            comparisons.append(self._compare_case(case, debtor, matches))
        return {
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "mailbox_zip": str(mailbox_zip),
            "outsmart_dir": str(outsmart_dir),
            "mail_count": len(case_analysis["cases"]),
            "outsmart_record_count": len(records),
            "comparisons": comparisons,
        }

    def _build_indexes(self, records: List[OutSmartRecord]) -> Dict[str, Dict[str, List[OutSmartRecord]]]:
        indexes: Dict[str, Dict[str, List[OutSmartRecord]]] = {
            "order": defaultdict(list),
            "purchase_order": defaultdict(list),
            "outsmart_number": defaultdict(list),
            "external_workorder": defaultdict(list),
        }
        for record in records:
            for key in indexes:
                value = getattr(record, key, "")
                if value:
                    indexes[key][value].append(record)
        return indexes

    def _find_matches(self, case: MailCase, indexes: Dict[str, Dict[str, List[OutSmartRecord]]]) -> List[Tuple[str, OutSmartRecord]]:
        matches: List[Tuple[str, OutSmartRecord]] = []
        seen = set()
        for order in case.orders:
            for record in indexes["order"].get(order, []) + indexes["external_workorder"].get(order, []):
                marker = id(record)
                if marker not in seen:
                    matches.append(("order", record))
                    seen.add(marker)
        for po in case.purchase_orders:
            for record in indexes["purchase_order"].get(po, []):
                marker = id(record)
                if marker not in seen:
                    matches.append(("purchase_order", record))
                    seen.add(marker)
        for number in case.outsmart_numbers:
            for record in indexes["outsmart_number"].get(number, []):
                marker = id(record)
                if marker not in seen:
                    matches.append(("outsmart_number", record))
                    seen.add(marker)
        return matches

    def _debtor_for_folder(self, folder_name: str) -> str:
        best = ""
        best_len = -1
        for debtor, profile in self.profiles.items():
            for folder in profile.get("folders", []):
                if folder_name.lower().startswith(str(folder).lower()) and len(str(folder)) > best_len:
                    best = debtor
                    best_len = len(str(folder))
        return best

    def _compare_case(self, case: MailCase, debtor: str, matches: List[Tuple[str, OutSmartRecord]]) -> Dict[str, object]:
        primary = matches[0][1] if matches else None
        issues = []
        learned = {}
        if primary:
            if debtor and primary.debtor and debtor.upper() != primary.debtor.upper():
                issues.append(f"Debiteur verschilt: mailbox {debtor} vs OutSmart {primary.debtor}")
            learned = {
                "outsmart_number": primary.outsmart_number,
                "outsmart_id": primary.outsmart_id,
                "debtor": primary.debtor,
                "customer": primary.customer,
                "status": primary.status,
                "workorder_status": primary.workorder_status,
                "employee": primary.employee,
                "address": primary.address,
                "house_number": primary.house_number,
                "postal_code": primary.postal_code,
                "city": primary.city,
                "building_code": primary.building_code,
                "building_name": primary.building_name,
                "unit": primary.unit,
                "description": primary.description[:500],
                "short_description": primary.short_description,
                "memo": primary.memo[:500],
                "url": primary.url(),
            }
        return {
            "case_id": case.case_id,
            "folder_name": case.folder_name,
            "mail_classification": case.classification,
            "mail_confidence": case.confidence,
            "mail_subject": case.subject,
            "mail_sender": case.sender_email,
            "mail_orders": case.orders,
            "mail_purchase_orders": case.purchase_orders,
            "mail_outsmart_numbers": case.outsmart_numbers,
            "expected_debtor": debtor,
            "match_count": len(matches),
            "match_types": [kind for kind, _ in matches],
            "action": self._action(case, matches),
            "issues": issues,
            "learned_outsmart_fields": learned,
        }

    def _action(self, case: MailCase, matches: List[Tuple[str, OutSmartRecord]]) -> str:
        if matches:
            return "BESTAANDE_WERKBON_VERGELIJKEN"
        if case.classification == "NIEUWE_OPDRACHT":
            return "NIEUWE_WERKBON_VOORBEREIDEN"
        if case.classification in {"ANNULATIE", "WIJZIGING"}:
            return "BESTAANDE_WERKBON_ZOEKEN"
        return "CONTROLE_NODIG"


def write_comparison_report(result: Dict[str, object]) -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    md_path = REPORTS_DIR / f"mail_outsmart_comparison_{timestamp}.md"
    csv_path = REPORTS_DIR / f"mail_outsmart_comparison_{timestamp}.csv"
    json_path = REPORTS_DIR / f"mail_outsmart_comparison_{timestamp}.json"
    json_path.write_text(json.dumps(result, indent=4, ensure_ascii=False), encoding="utf-8")

    comparisons = result["comparisons"]
    action_counter = Counter(item["action"] for item in comparisons)
    debtor_counter = Counter(item["expected_debtor"] or "ONBEKEND" for item in comparisons)
    lines = [
        "# Mail to OutSmart Comparison",
        "",
        f"Mailbox zip: `{result['mailbox_zip']}`",
        f"OutSmart dir: `{result['outsmart_dir']}`",
        f"Mails: {result['mail_count']}",
        f"OutSmart records: {result['outsmart_record_count']}",
        "",
        "## Actions",
    ]
    for action, count in action_counter.most_common():
        lines.append(f"- {action}: {count}")
    lines.extend(["", "## Expected Debtors"])
    for debtor, count in debtor_counter.most_common():
        lines.append(f"- {debtor}: {count}")
    lines.extend(["", "## Matched Cases"])
    for item in comparisons:
        if item["match_count"]:
            learned = item["learned_outsmart_fields"]
            lines.append(f"- {item['case_id']} | {item['expected_debtor']} | {learned.get('outsmart_number','')} | {learned.get('address','')} {learned.get('house_number','')} | gebouw: {learned.get('building_code','')} {learned.get('building_name','')} | unit: {learned.get('unit','')}")
    md_path.write_text("\n".join(lines), encoding="utf-8")

    with csv_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=[
            "case_id", "expected_debtor", "action", "match_count", "mail_classification",
            "mail_orders", "mail_purchase_orders", "outsmart_number", "outsmart_id", "outsmart_debtor",
            "customer", "status", "employee", "address", "house_number", "postal_code", "city",
            "building_code", "building_name", "unit", "url", "issues", "subject",
        ], delimiter=";")
        writer.writeheader()
        for item in comparisons:
            learned = item["learned_outsmart_fields"]
            writer.writerow({
                "case_id": item["case_id"],
                "expected_debtor": item["expected_debtor"],
                "action": item["action"],
                "match_count": item["match_count"],
                "mail_classification": item["mail_classification"],
                "mail_orders": ", ".join(item["mail_orders"]),
                "mail_purchase_orders": ", ".join(item["mail_purchase_orders"]),
                "outsmart_number": learned.get("outsmart_number", ""),
                "outsmart_id": learned.get("outsmart_id", ""),
                "outsmart_debtor": learned.get("debtor", ""),
                "customer": learned.get("customer", ""),
                "status": learned.get("status", ""),
                "employee": learned.get("employee", ""),
                "address": learned.get("address", ""),
                "house_number": learned.get("house_number", ""),
                "postal_code": learned.get("postal_code", ""),
                "city": learned.get("city", ""),
                "building_code": learned.get("building_code", ""),
                "building_name": learned.get("building_name", ""),
                "unit": learned.get("unit", ""),
                "url": learned.get("url", ""),
                "issues": " | ".join(item["issues"]),
                "subject": item["mail_subject"],
            })
    return md_path
