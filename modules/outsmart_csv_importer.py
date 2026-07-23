import csv
import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional

ORDER_RE = re.compile(r"\b4\d{6}\b")
PO_RE = re.compile(r"\b45\d{8}\b")
OUTSMART_NO_RE = re.compile(r"\b20\d{2}\.\d{3,5}\b")
DEBTOR_RE = re.compile(r"\bS\.G-\d\b", re.IGNORECASE)

FIELD_ALIASES = {
    "outsmart_number": ["werkbon", "werkbonnummer", "worksheetno", "worksheet_no", "bonnummer", "nummer"],
    "outsmart_id": ["id", "worksheetid", "worksheet_id", "intern id", "internal_id"],
    "debtor": ["debiteur", "debiteurnummer", "customernr", "customerdebtor", "customerdebtornr", "klantcode"],
    "customer": ["klant", "klantnaam", "customer", "customername", "relatie", "naam"],
    "order": ["order", "ordernummer", "opdrachtnummer", "jobnr", "jobnummer", "workorder", "werkorder"],
    "external_workorder": ["extern werkbonnummer", "externwerkbonnummer", "workorderno", "externalworkorder", "external workorder"],
    "purchase_order": ["bestelbon", "po", "po nummer", "ponummer", "externe referentie", "externalreference", "external reference"],
    "status": ["status", "werkstatus", "workflowstatus", "workstatus"],
    "workorder_status": ["werkbonstatus", "worksheetstatus"],
    "employee": ["werknemer", "medewerker", "employee"],
    "address": ["adres", "werkadres", "address", "straat"],
    "house_number": ["huisnummer", "nummer adres", "number"],
    "postal_code": ["postcode", "zip", "zipcode"],
    "city": ["plaats", "gemeente", "city"],
    "building_code": ["gebouwcode", "buildingcode", "objectcode", "object code"],
    "building_name": ["gebouw", "gebouwnaam", "object", "objectnaam", "building"],
    "unit": ["eenheid", "unit", "ruimte", "ruimtecode", "ruimtetype", "invulling"],
    "description": ["omschrijving", "workdescription", "werkbeschrijving", "description"],
    "short_description": ["korte omschrijving", "shortworkdescription", "short description"],
    "memo": ["memo", "internalworkdescription", "interne omschrijving"],
}


@dataclass
class OutSmartRecord:
    source_file: str
    raw: Dict[str, str]
    outsmart_number: str = ""
    outsmart_id: str = ""
    debtor: str = ""
    customer: str = ""
    order: str = ""
    external_workorder: str = ""
    purchase_order: str = ""
    status: str = ""
    workorder_status: str = ""
    employee: str = ""
    address: str = ""
    house_number: str = ""
    postal_code: str = ""
    city: str = ""
    building_code: str = ""
    building_name: str = ""
    unit: str = ""
    description: str = ""
    short_description: str = ""
    memo: str = ""

    def search_blob(self) -> str:
        return "\n".join(str(value or "") for value in self.raw.values())

    def url(self) -> str:
        key = self.outsmart_id or self.outsmart_number
        return f"https://app.out-smart.com/next/work-orders/{key}/" if key else ""


class OutSmartCsvImporter:
    def load_directory(self, directory: Path) -> List[OutSmartRecord]:
        records: List[OutSmartRecord] = []
        if not directory.exists():
            return records
        for path in sorted(directory.glob("*.csv")):
            records.extend(self.load_csv(path))
        return records

    def load_csv(self, path: Path) -> List[OutSmartRecord]:
        text = path.read_text(encoding="utf-8-sig", errors="ignore")
        sample = text[:4096]
        delimiter = self._detect_delimiter(sample)
        rows = csv.DictReader(text.splitlines(), delimiter=delimiter)
        records = []
        for row in rows:
            clean_row = {str(k or "").strip(): str(v or "").strip() for k, v in row.items()}
            records.append(self._row_to_record(path.name, clean_row))
        return records

    def _detect_delimiter(self, sample: str) -> str:
        candidates = [";", ",", "\t"]
        return max(candidates, key=lambda item: sample.count(item))

    def _row_to_record(self, source_file: str, row: Dict[str, str]) -> OutSmartRecord:
        lower_map = {self._normalize(key): value for key, value in row.items()}
        values = {field: self._pick(lower_map, aliases) for field, aliases in FIELD_ALIASES.items()}
        record = OutSmartRecord(source_file=source_file, raw=row, **values)
        blob = record.search_blob()
        if not record.order:
            match = ORDER_RE.search(blob)
            record.order = match.group(0) if match else ""
        if not record.purchase_order:
            match = PO_RE.search(blob)
            record.purchase_order = match.group(0) if match else ""
        if not record.outsmart_number:
            match = OUTSMART_NO_RE.search(blob)
            record.outsmart_number = match.group(0) if match else ""
        if not record.debtor:
            match = DEBTOR_RE.search(blob)
            record.debtor = match.group(0).upper() if match else ""
        return record

    def _normalize(self, value: str) -> str:
        return re.sub(r"[^a-z0-9]+", "", value.lower())

    def _pick(self, row: Dict[str, str], aliases: Iterable[str]) -> str:
        for alias in aliases:
            value = row.get(self._normalize(alias), "")
            if value:
                return value
        return ""


def records_to_jsonable(records: List[OutSmartRecord]) -> List[Dict[str, object]]:
    return [asdict(record) for record in records]
