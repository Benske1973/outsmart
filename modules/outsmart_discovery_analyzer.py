import csv
import json
import re
import zipfile
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

from modules.config import REPORTS_DIR


IMPORTANT_FIELD_WORDS = [
    "worksheet", "customer", "debtor", "project", "extern", "external", "reference",
    "workorder", "job", "employee", "status", "duration", "deadline", "date",
    "description", "comment", "address", "invoice", "form", "object", "material",
    "period", "work", "planning", "contact", "location", "building", "gebouw",
]

SCREEN_KEYWORDS = {
    "workorder_create": ["work-orders/create", "backoffice_klaarzetten", "new_worksheet", "werkbon aanmaken"],
    "workorder_detail": ["backoffice_werkbon", "work-orders/", "werkbon"],
    "projects": ["project", "projecten"],
    "relations": ["relatie", "relations", "crm"],
    "objects": ["object", "objecten"],
    "planning": ["planbord", "planning"],
    "forms": ["formulier", "forms"],
    "materials": ["materiaal", "materialen"],
    "invoices": ["factuur", "facturen"],
}

MUST_HAVE_TOPICS = {
    "Nieuwe werkbon": ["workorder_create", "worksheet[WorkDescription]", "worksheet[EmployeeNr]"],
    "Bestaande werkbon": ["workorder_detail", "Logboek", "Bestanden"],
    "Dropdowns/statussen": ["WorkStatus", "Werkbonstatus", "Type werk", "Betaalmethode"],
    "Projecten": ["ProjectNr", "project"],
    "Objecten/gebouwen": ["Object", "Gebouw", "address_code", "building"],
    "Formulieren/LMRA": ["LMRA", "forms[name][]", "Formulier"],
    "Bijlagen": ["Bestanden", "Foto", "Upload"],
}


def _clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _safe_cell(value: Any, limit: int = 220) -> str:
    text = _clean(value)
    return text[:limit]


class _HtmlOptionParser:
    def __init__(self) -> None:
        from html.parser import HTMLParser

        class Parser(HTMLParser):
            def __init__(self) -> None:
                super().__init__()
                self.in_option = False
                self.current: List[str] = []
                self.options: List[str] = []

            def handle_starttag(self, tag: str, attrs: List[Tuple[str, str]]) -> None:
                attr_map = dict(attrs)
                class_name = attr_map.get("class", "") or ""
                role = attr_map.get("role", "") or ""
                if tag.lower() in {"li", "option"} and (
                    "select2-results__option" in class_name
                    or "select2-result" in class_name
                    or role == "option"
                    or tag.lower() == "option"
                ):
                    self.in_option = True
                    self.current = []

            def handle_data(self, data: str) -> None:
                if self.in_option:
                    self.current.append(data)

            def handle_endtag(self, tag: str) -> None:
                if self.in_option and tag.lower() in {"li", "option"}:
                    text = _clean("".join(self.current))
                    if text and text not in self.options and text not in {"Selecteer uit lijst...", "Begin met typen..."}:
                        self.options.append(text)
                    self.in_option = False

        self.parser = Parser()

    def parse(self, html: str) -> List[str]:
        self.parser.feed(html)
        return self.parser.options


class OutSmartDiscoveryAnalyzer:
    def analyze_path(self, source_path: Path) -> Dict[str, Any]:
        source_path = Path(source_path)
        if source_path.is_dir():
            return self.analyze_directory(source_path)
        return self.analyze_zip(source_path)

    def analyze_zip(self, zip_path: Path) -> Dict[str, Any]:
        zip_path = Path(zip_path)
        snapshots: List[Dict[str, Any]] = []
        html_options: Dict[str, List[str]] = {}
        file_counts = Counter()
        entry_names: List[str] = []
        with zipfile.ZipFile(zip_path, "r") as archive:
            for info in archive.infolist():
                entry_names.append(info.filename)
                suffix = Path(info.filename).suffix.lower() or "<folder>"
                file_counts[suffix] += 1
                lower_name = info.filename.lower()
                if lower_name.endswith("snapshot.json"):
                    try:
                        raw = archive.read(info).decode("utf-8-sig", errors="replace")
                        snapshot = json.loads(raw)
                        snapshot["_entry"] = info.filename
                        snapshots.append(snapshot)
                    except Exception as exc:
                        snapshots.append({"_entry": info.filename, "_error": str(exc)})
                elif lower_name.endswith(".html"):
                    raw = archive.read(info).decode("utf-8-sig", errors="replace")
                    options = _HtmlOptionParser().parse(raw)
                    if options:
                        html_options[info.filename] = options
        return self._build_analysis(zip_path, entry_names, file_counts, snapshots, html_options)

    def analyze_directory(self, directory: Path) -> Dict[str, Any]:
        directory = Path(directory)
        snapshots: List[Dict[str, Any]] = []
        html_options: Dict[str, List[str]] = {}
        file_counts = Counter()
        entry_names: List[str] = []
        for path in sorted(directory.rglob("*")):
            if path.is_dir():
                continue
            rel = str(path.relative_to(directory))
            entry_names.append(rel)
            file_counts[path.suffix.lower() or "<folder>"] += 1
            if path.name.lower() == "snapshot.json":
                try:
                    snapshot = json.loads(path.read_text(encoding="utf-8-sig", errors="replace"))
                    snapshot["_entry"] = rel
                    snapshots.append(snapshot)
                except Exception as exc:
                    snapshots.append({"_entry": rel, "_error": str(exc)})
            elif path.suffix.lower() == ".html":
                options = _HtmlOptionParser().parse(path.read_text(encoding="utf-8-sig", errors="replace"))
                if options:
                    html_options[rel] = options
        return self._build_analysis(directory, entry_names, file_counts, snapshots, html_options)

    def _build_analysis(self, zip_path: Path, entry_names: List[str], file_counts: Counter, snapshots: List[Dict[str, Any]], html_options: Dict[str, List[str]] | None = None) -> Dict[str, Any]:
        screens = Counter()
        url_counter = Counter()
        title_counter = Counter()
        field_counter = Counter()
        field_rows: List[Dict[str, Any]] = []
        dropdown_counter = Counter()
        dropdown_rows: List[Dict[str, Any]] = []
        table_rows: List[Dict[str, Any]] = []
        button_counter = Counter()
        link_counter = Counter()
        option_counter = Counter()
        raw_text_index = []
        html_option_rows = []
        for entry, options in (html_options or {}).items():
            for option in options:
                option_counter[("html_select2_options", option)] += 1
            html_option_rows.append({"entry": entry, "option_count": len(options), "options": options[:1500]})

        for snapshot in snapshots:
            documents = [snapshot]
            for frame in snapshot.get("frames") or []:
                frame_copy = dict(frame)
                frame_copy["_entry"] = f"{snapshot.get('_entry', '')}::frame"
                documents.append(frame_copy)

            for document in documents:
                title = _clean(document.get("title") or snapshot.get("title"))
                url = _clean(document.get("url") or snapshot.get("url"))
                key_text = " ".join([title, url, document.get("_entry", "")]).lower()
                screen_type = self._classify_screen(key_text)
                screens[screen_type] += 1
                if url:
                    url_counter[url] += 1
                if title:
                    title_counter[title] += 1

                for field in document.get("fields") or []:
                    label = _clean(field.get("label") or field.get("name") or field.get("id") or field.get("placeholder") or field.get("selector"))
                    if not label:
                        continue
                    field_counter[label] += 1
                    row = {
                        "screen_type": screen_type,
                        "title": title,
                        "url": url,
                        "label": label,
                        "name": _clean(field.get("name")),
                        "id": _clean(field.get("id")),
                        "tag": _clean(field.get("tag")),
                        "type": _clean(field.get("type")),
                        "required": field.get("required"),
                        "disabled": field.get("disabled"),
                        "readonly": field.get("readonly"),
                        "value": _safe_cell(field.get("value")),
                        "selector": _safe_cell(field.get("selector")),
                        "entry": document.get("_entry", ""),
                    }
                    field_rows.append(row)
                    for option in field.get("options") or []:
                        option_text = _clean(option.get("text") if isinstance(option, dict) else option)
                        if option_text:
                            option_counter[(label, option_text)] += 1

                for dropdown in document.get("dropdowns") or []:
                    trigger = _clean(dropdown.get("trigger_text") or dropdown.get("label") or dropdown.get("selector") or f"dropdown {dropdown.get('index', '')}")
                    options = dropdown.get("options") or []
                    if trigger:
                        dropdown_counter[trigger] += 1
                    option_texts = []
                    for option in options:
                        text = _clean(option.get("text") if isinstance(option, dict) else option)
                        if text:
                            option_texts.append(text)
                            option_counter[(trigger, text)] += 1
                    dropdown_rows.append({
                        "screen_type": screen_type,
                        "title": title,
                        "url": url,
                        "trigger": trigger,
                        "option_count": len(option_texts),
                        "options": option_texts[:120],
                        "entry": document.get("_entry", ""),
                        "error": _clean(dropdown.get("error")),
                    })

                for table in document.get("tables") or []:
                    table_rows.append({
                        "screen_type": screen_type,
                        "title": title,
                        "url": url,
                        "headers": [_clean(x) for x in (table.get("headers") or []) if _clean(x)],
                        "rows": table.get("rows"),
                        "selector": _safe_cell(table.get("selector")),
                        "entry": document.get("_entry", ""),
                    })

                for button in document.get("buttons") or []:
                    text = _clean(button.get("text") or button.get("value") or button.get("selector"))
                    if text:
                        button_counter[text] += 1
                for link in document.get("links") or []:
                    text = _clean(link.get("text") or link.get("href"))
                    if text:
                        link_counter[text] += 1

                raw_text_index.append(" ".join([
                    title, url,
                    " ".join(field_counter.keys()),
                    " ".join(dropdown_counter.keys()),
                    " ".join(button_counter.keys()),
                ]))

        missing_topics = self._find_missing_topics(screens, field_counter, dropdown_counter, table_rows, button_counter, link_counter)
        important_fields = self._important_fields(field_rows)
        return {
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "zip_path": str(zip_path),
            "zip_size_mb": round(zip_path.stat().st_size / 1024 / 1024, 2),
            "entry_count": len(entry_names),
            "file_counts": dict(file_counts.most_common()),
            "snapshot_count": len(snapshots),
            "screens": dict(screens.most_common()),
            "urls": url_counter.most_common(80),
            "titles": title_counter.most_common(80),
            "fields_total": len(field_rows),
            "fields_unique": len(field_counter),
            "important_fields": important_fields,
            "dropdowns_total": len(dropdown_rows),
            "dropdowns_unique": len(dropdown_counter),
            "dropdown_rows": dropdown_rows,
            "tables_total": len(table_rows),
            "table_rows": table_rows,
            "buttons": button_counter.most_common(150),
            "links": link_counter.most_common(150),
            "field_rows": field_rows,
            "option_values": [
                {"field": field, "option": option, "count": count}
                for (field, option), count in option_counter.most_common(3000)
            ],
            "html_option_rows": html_option_rows,
            "missing_topics": missing_topics,
        }

    def _classify_screen(self, text: str) -> str:
        for screen, words in SCREEN_KEYWORDS.items():
            if any(word.lower() in text for word in words):
                return screen
        return "other"

    def _important_fields(self, field_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        seen = set()
        result = []
        for row in field_rows:
            haystack = " ".join([row.get("label", ""), row.get("name", ""), row.get("id", "")]).lower()
            if not any(word in haystack for word in IMPORTANT_FIELD_WORDS):
                continue
            key = (row.get("label"), row.get("name"), row.get("id"))
            if key in seen:
                continue
            seen.add(key)
            result.append(row)
        return result[:500]

    def _find_missing_topics(self, screens: Counter, fields: Counter, dropdowns: Counter, tables: List[Dict[str, Any]], buttons: Counter, links: Counter) -> Dict[str, Dict[str, Any]]:
        haystack_parts = []
        haystack_parts.extend(screens.keys())
        haystack_parts.extend(fields.keys())
        haystack_parts.extend(dropdowns.keys())
        haystack_parts.extend(buttons.keys())
        haystack_parts.extend(links.keys())
        for table in tables:
            haystack_parts.extend(table.get("headers") or [])
        haystack = "\n".join(str(x) for x in haystack_parts).lower()
        result = {}
        for topic, probes in MUST_HAVE_TOPICS.items():
            found = [probe for probe in probes if probe.lower() in haystack]
            result[topic] = {
                "found": found,
                "missing": [probe for probe in probes if probe not in found],
                "covered": bool(found),
            }
        return result


def write_discovery_analysis_report(analysis: Dict[str, Any]) -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    md_path = REPORTS_DIR / f"outsmart_discovery_analysis_{timestamp}.md"
    json_path = REPORTS_DIR / f"outsmart_discovery_analysis_{timestamp}.json"
    fields_csv = REPORTS_DIR / f"outsmart_discovery_fields_{timestamp}.csv"
    dropdowns_csv = REPORTS_DIR / f"outsmart_discovery_dropdowns_{timestamp}.csv"
    options_csv = REPORTS_DIR / f"outsmart_discovery_options_{timestamp}.csv"
    tables_csv = REPORTS_DIR / f"outsmart_discovery_tables_{timestamp}.csv"
    html_options_csv = REPORTS_DIR / f"outsmart_discovery_html_options_{timestamp}.csv"

    json_path.write_text(json.dumps(analysis, indent=4, ensure_ascii=False), encoding="utf-8")

    _write_csv(fields_csv, analysis["field_rows"], [
        "screen_type", "title", "url", "label", "name", "id", "tag", "type", "required", "disabled", "readonly", "value", "selector", "entry",
    ])
    dropdown_rows = []
    for row in analysis["dropdown_rows"]:
        dropdown_rows.append({**row, "options": " | ".join(row.get("options") or [])})
    _write_csv(dropdowns_csv, dropdown_rows, [
        "screen_type", "title", "url", "trigger", "option_count", "options", "error", "entry",
    ])
    _write_csv(options_csv, analysis["option_values"], ["field", "option", "count"])
    html_rows = []
    for row in analysis.get("html_option_rows", []):
        html_rows.append({"entry": row.get("entry", ""), "option_count": row.get("option_count", 0), "options": " | ".join(row.get("options") or [])})
    _write_csv(html_options_csv, html_rows, ["entry", "option_count", "options"])
    table_rows = []
    for row in analysis["table_rows"]:
        table_rows.append({**row, "headers": " | ".join(row.get("headers") or [])})
    _write_csv(tables_csv, table_rows, ["screen_type", "title", "url", "headers", "rows", "selector", "entry"])

    lines = [
        "# OutSmart Discovery Analysis",
        "",
        f"Source ZIP: `{analysis['zip_path']}`",
        f"Created: {analysis['created_at']}",
        f"ZIP size: {analysis['zip_size_mb']} MB",
        f"Files in ZIP: {analysis['entry_count']}",
        f"Snapshots: {analysis['snapshot_count']}",
        "",
        "## Screen Coverage",
    ]
    for screen, count in analysis["screens"].items():
        lines.append(f"- {screen}: {count}")

    lines.extend(["", "## Coverage Check"])
    for topic, info in analysis["missing_topics"].items():
        mark = "OK" if info["covered"] else "MISSING"
        lines.append(f"- {mark} - {topic}: found {info['found'] or '-'}")

    lines.extend(["", "## Totals"])
    lines.append(f"- Fields: {analysis['fields_total']} total / {analysis['fields_unique']} unique")
    lines.append(f"- Dropdown captures: {analysis['dropdowns_total']} total / {analysis['dropdowns_unique']} unique")
    lines.append(f"- Tables: {analysis['tables_total']}")
    lines.append(f"- HTML Select2 option blocks: {len(analysis.get('html_option_rows', []))}")

    lines.extend(["", "## Important Fields"])
    for row in analysis["important_fields"][:160]:
        bits = [row.get("label"), row.get("name"), row.get("id"), row.get("tag"), row.get("type")]
        lines.append("- " + " | ".join(_safe_cell(bit, 80) for bit in bits if _safe_cell(bit, 80)))

    lines.extend(["", "## HTML Select2 Options"])
    for row in analysis.get("html_option_rows", [])[:80]:
        lines.append(f"- {row.get('entry')}: {row.get('option_count')} opties -> {(row.get('options') or [])[:30]}")

    lines.extend(["", "## Dropdowns"])
    if not analysis["dropdown_rows"]:
        lines.append("- Geen dropdownopties gevonden in deze scrape.")
    for row in analysis["dropdown_rows"][:120]:
        opts = row.get("options") or []
        lines.append(f"- {row.get('trigger') or '(zonder naam)'}: {row.get('option_count')} opties -> {opts[:20]}")

    lines.extend(["", "## Tables"])
    for row in analysis["table_rows"][:120]:
        lines.append(f"- {row.get('screen_type')} | rows={row.get('rows')} | headers={row.get('headers')}")

    lines.extend(["", "## Top Buttons"])
    for text, count in analysis["buttons"][:80]:
        lines.append(f"- {text}: {count}")

    lines.extend(["", "## Output Files"])
    lines.append(f"- JSON: `{json_path}`")
    lines.append(f"- Fields CSV: `{fields_csv}`")
    lines.append(f"- Dropdowns CSV: `{dropdowns_csv}`")
    lines.append(f"- Options CSV: `{options_csv}`")
    lines.append(f"- Tables CSV: `{tables_csv}`")
    lines.append(f"- HTML options CSV: `{html_options_csv}`")
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return md_path


def _write_csv(path: Path, rows: List[Dict[str, Any]], fieldnames: List[str]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter=";")
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name, "") for name in fieldnames})
