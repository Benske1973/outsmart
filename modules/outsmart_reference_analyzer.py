import csv
import json
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

from modules.config import REPORTS_DIR
from modules.outsmart_csv_importer import OutSmartCsvImporter, OutSmartRecord


REFERENCE_FIELDS = [
    "debtor",
    "customer",
    "status",
    "workorder_status",
    "employee",
    "address",
    "house_number",
    "postal_code",
    "city",
    "building_code",
    "building_name",
    "unit",
]

DROPDOWN_CANDIDATES = [
    "status",
    "workorder_status",
    "employee",
    "customer",
    "debtor",
    "city",
    "building_code",
    "building_name",
    "unit",
]


@dataclass
class DebtorReferenceSummary:
    debtor: str
    record_count: int = 0
    customers: Counter = field(default_factory=Counter)
    statuses: Counter = field(default_factory=Counter)
    workorder_statuses: Counter = field(default_factory=Counter)
    employees: Counter = field(default_factory=Counter)
    addresses: Counter = field(default_factory=Counter)
    buildings: Counter = field(default_factory=Counter)
    units: Counter = field(default_factory=Counter)
    address_unit_examples: List[Dict[str, str]] = field(default_factory=list)


class OutSmartReferenceAnalyzer:
    def analyze_directory(self, directory: Path) -> Dict[str, object]:
        importer = OutSmartCsvImporter()
        records = importer.load_directory(directory)
        columns = self._collect_columns(directory)
        debtor_summaries = self._summarize_debtors(records)
        dropdowns = self._detect_dropdown_values(records)
        return {
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "source_dir": str(directory),
            "csv_count": len(list(directory.glob("*.csv"))) if directory.exists() else 0,
            "record_count": len(records),
            "columns": columns,
            "debtor_summaries": debtor_summaries,
            "dropdowns": dropdowns,
        }

    def _collect_columns(self, directory: Path) -> Dict[str, List[str]]:
        result: Dict[str, List[str]] = {}
        if not directory.exists():
            return result
        for path in sorted(directory.glob("*.csv")):
            try:
                text = path.read_text(encoding="utf-8-sig", errors="ignore")
                delimiter = ";" if text[:4096].count(";") >= text[:4096].count(",") else ","
                reader = csv.DictReader(text.splitlines(), delimiter=delimiter)
                result[path.name] = list(reader.fieldnames or [])
            except Exception as exc:
                result[path.name] = [f"ERROR: {exc}"]
        return result

    def _summarize_debtors(self, records: List[OutSmartRecord]) -> Dict[str, DebtorReferenceSummary]:
        summaries: Dict[str, DebtorReferenceSummary] = defaultdict(lambda: DebtorReferenceSummary(debtor="ONBEKEND"))
        for record in records:
            debtor = (record.debtor or "ONBEKEND").upper()
            summary = summaries[debtor]
            summary.debtor = debtor
            summary.record_count += 1
            self._count(summary.customers, record.customer)
            self._count(summary.statuses, record.status)
            self._count(summary.workorder_statuses, record.workorder_status)
            self._count(summary.employees, record.employee)
            full_address = " ".join(part for part in [record.address, record.house_number, record.postal_code, record.city] if part).strip()
            self._count(summary.addresses, full_address)
            building = " | ".join(part for part in [record.building_code, record.building_name] if part).strip()
            self._count(summary.buildings, building)
            self._count(summary.units, record.unit)
            if len(summary.address_unit_examples) < 80 and (full_address or building or record.unit):
                summary.address_unit_examples.append({
                    "outsmart_number": record.outsmart_number,
                    "order": record.order or record.external_workorder,
                    "purchase_order": record.purchase_order,
                    "address": full_address,
                    "building": building,
                    "unit": record.unit,
                    "description_sample": (record.description or record.short_description or record.memo)[:180],
                })
        return dict(summaries)

    def _detect_dropdown_values(self, records: List[OutSmartRecord]) -> Dict[str, List[Tuple[str, int]]]:
        values: Dict[str, Counter] = {field: Counter() for field in DROPDOWN_CANDIDATES}
        for record in records:
            for field in DROPDOWN_CANDIDATES:
                self._count(values[field], getattr(record, field, ""))
        return {field: counter.most_common(200) for field, counter in values.items() if counter}

    def _count(self, counter: Counter, value: str) -> None:
        cleaned = str(value or "").strip()
        if cleaned:
            counter.update([cleaned])


def write_outsmart_reference_report(analysis: Dict[str, object]) -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    md_path = REPORTS_DIR / f"outsmart_reference_analysis_{timestamp}.md"
    json_path = REPORTS_DIR / f"outsmart_reference_analysis_{timestamp}.json"
    csv_path = REPORTS_DIR / f"outsmart_address_unit_examples_{timestamp}.csv"

    jsonable = {
        "created_at": analysis["created_at"],
        "source_dir": analysis["source_dir"],
        "csv_count": analysis["csv_count"],
        "record_count": analysis["record_count"],
        "columns": analysis["columns"],
        "dropdowns": analysis["dropdowns"],
        "debtor_summaries": {
            debtor: {
                "record_count": summary.record_count,
                "customers": summary.customers.most_common(50),
                "statuses": summary.statuses.most_common(50),
                "workorder_statuses": summary.workorder_statuses.most_common(50),
                "employees": summary.employees.most_common(50),
                "addresses": summary.addresses.most_common(100),
                "buildings": summary.buildings.most_common(100),
                "units": summary.units.most_common(100),
                "address_unit_examples": summary.address_unit_examples,
            }
            for debtor, summary in analysis["debtor_summaries"].items()
        },
    }
    json_path.write_text(json.dumps(jsonable, indent=4, ensure_ascii=False), encoding="utf-8")

    with csv_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=[
            "debtor", "outsmart_number", "order", "purchase_order", "address", "building", "unit", "description_sample",
        ], delimiter=";")
        writer.writeheader()
        for debtor, summary in analysis["debtor_summaries"].items():
            for example in summary.address_unit_examples:
                row = dict(example)
                row["debtor"] = debtor
                writer.writerow(row)

    lines = [
        "# OutSmart Reference Analysis",
        "",
        f"Source: `{analysis['source_dir']}`",
        f"CSV files: {analysis['csv_count']}",
        f"Records: {analysis['record_count']}",
        "",
        "## CSV Columns",
    ]
    if not analysis["columns"]:
        lines.append("- Geen CSV-bestanden gevonden in imports/outsmart.")
    for file_name, columns in analysis["columns"].items():
        lines.append(f"- {file_name}: {columns}")
    lines.extend(["", "## Debtors"])
    for debtor, summary in sorted(analysis["debtor_summaries"].items()):
        lines.extend([
            "",
            f"### {debtor}",
            f"- Records: {summary.record_count}",
            f"- Customers: {summary.customers.most_common(10)}",
            f"- Statuses: {summary.statuses.most_common(15)}",
            f"- Workorder statuses: {summary.workorder_statuses.most_common(15)}",
            f"- Employees: {summary.employees.most_common(15)}",
            f"- Buildings: {summary.buildings.most_common(20)}",
            f"- Units: {summary.units.most_common(20)}",
            f"- Addresses: {summary.addresses.most_common(20)}",
        ])
    lines.extend(["", "## Dropdown-Like Values"])
    for field, values in analysis["dropdowns"].items():
        lines.append(f"- {field}: {values[:40]}")
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return md_path
