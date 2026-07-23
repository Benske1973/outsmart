import json
import re
import zipfile
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from modules.config import REPORTS_DIR
from modules.document_classifier import DocumentClassifier

ORDER_RE = re.compile(r"\b4\d{6}\b")
PO_RE = re.compile(r"\b45\d{8}\b")
EMAIL_DOMAIN_RE = re.compile(r"@([^>\s]+)")


@dataclass
class FolderSummary:
    folder_name: str
    mail_count: int = 0
    attachment_count: int = 0
    sender_counter: Counter = field(default_factory=Counter)
    domain_counter: Counter = field(default_factory=Counter)
    attachment_ext_counter: Counter = field(default_factory=Counter)
    document_type_counter: Counter = field(default_factory=Counter)
    order_counter: Counter = field(default_factory=Counter)
    po_counter: Counter = field(default_factory=Counter)
    flag_counter: Counter = field(default_factory=Counter)


class ImportPackageAnalyzer:
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
            folder_summaries = []
            for folder in manifest.get("folders", []):
                summary = self._analyze_folder(folder, archive, body_entries)
                folder_summaries.append(summary)
            return {
                "zip_path": str(zip_path),
                "created_at": manifest.get("created_at"),
                "read_only_mode": manifest.get("read_only_mode"),
                "folder_count": len(folder_summaries),
                "mail_count": sum(summary.mail_count for summary in folder_summaries),
                "attachment_count": sum(summary.attachment_count for summary in folder_summaries),
                "folders": folder_summaries,
            }

    def _find_entry(self, archive: zipfile.ZipFile, suffix: str) -> Optional[str]:
        for name in archive.namelist():
            if name.endswith(suffix):
                return name
        return None

    def _analyze_folder(self, folder: Dict[str, object], archive: zipfile.ZipFile, body_entries: Dict[str, str]) -> FolderSummary:
        summary = FolderSummary(folder_name=str(folder.get("folder_name", "")))
        mails = list(folder.get("mails", []))
        summary.mail_count = len(mails)
        for mail in mails:
            subject = str(mail.get("subject", ""))
            sender_email = str(mail.get("sender_email", "") or "onbekend")
            summary.sender_counter.update([sender_email.lower()])
            domain = sender_email.split("@", 1)[1].lower() if "@" in sender_email else "onbekend"
            summary.domain_counter.update([domain])
            text_parts = [subject]
            mail_dir = self._mail_dir_from_metadata_path(mail)
            body_name = body_entries.get(mail_dir)
            if body_name:
                try:
                    text_parts.append(archive.read(body_name).decode("utf-8-sig", errors="ignore"))
                except Exception:
                    pass
            attachments = list(mail.get("attachments", []))
            summary.attachment_count += len(attachments)
            for attachment in attachments:
                filename = str(attachment.get("filename", ""))
                text_parts.append(filename)
                ext = Path(filename).suffix.lower() or "<geen>"
                summary.attachment_ext_counter.update([ext])
                summary.document_type_counter.update([self.classifier.classify(filename)])
            combined = "\n".join(text_parts)
            summary.order_counter.update(ORDER_RE.findall(combined))
            summary.po_counter.update(PO_RE.findall(combined))
            lower = combined.lower()
            if any(word in lower for word in ["annulatie", "annuleer", "vervalt", "niet uitvoeren"]):
                summary.flag_counter.update(["ANNULATIE"])
            if any(word in lower for word in ["wijziging", "bijkomende informatie", "extra info", "planning"]):
                summary.flag_counter.update(["WIJZIGING"])
        return summary

    def _mail_dir_from_metadata_path(self, mail: Dict[str, object]) -> str:
        attachments = list(mail.get("attachments", []))
        if attachments:
            path = str(attachments[0].get("export_path", ""))
            parts = path.split("/")
            if len(parts) >= 3:
                return "/".join(parts[:2])
        return ""


def write_analysis_report(analysis: Dict[str, object]) -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = REPORTS_DIR / f"mailbox_import_analysis_{timestamp}.md"
    json_path = REPORTS_DIR / f"mailbox_import_analysis_{timestamp}.json"

    json_payload = {
        "zip_path": analysis["zip_path"],
        "created_at": analysis["created_at"],
        "read_only_mode": analysis["read_only_mode"],
        "folder_count": analysis["folder_count"],
        "mail_count": analysis["mail_count"],
        "attachment_count": analysis["attachment_count"],
        "folders": [
            {
                "folder_name": folder.folder_name,
                "mail_count": folder.mail_count,
                "attachment_count": folder.attachment_count,
                "top_domains": folder.domain_counter.most_common(10),
                "attachment_extensions": folder.attachment_ext_counter.most_common(10),
                "document_types": folder.document_type_counter.most_common(10),
                "top_orders": folder.order_counter.most_common(20),
                "top_purchase_orders": folder.po_counter.most_common(20),
                "flags": folder.flag_counter.most_common(10),
            }
            for folder in analysis["folders"]
        ],
    }
    json_path.write_text(json.dumps(json_payload, indent=4, ensure_ascii=False), encoding="utf-8")

    lines = [
        "# Mailbox Import Analysis",
        "",
        f"Package: `{analysis['zip_path']}`",
        f"Export created: {analysis['created_at']}",
        f"Read-only confirmed: {analysis['read_only_mode']}",
        f"Folders: {analysis['folder_count']}",
        f"Mails: {analysis['mail_count']}",
        f"Attachments: {analysis['attachment_count']}",
        "",
        "## Per Folder",
    ]
    for folder in analysis["folders"]:
        lines.extend([
            "",
            f"### {folder.folder_name}",
            f"- Mails: {folder.mail_count}",
            f"- Attachments: {folder.attachment_count}",
            f"- Domains: {folder.domain_counter.most_common(8)}",
            f"- Attachment types: {folder.attachment_ext_counter.most_common(8)}",
            f"- Document types: {folder.document_type_counter.most_common(8)}",
            f"- Orders found: {folder.order_counter.most_common(12)}",
            f"- Purchase orders found: {folder.po_counter.most_common(12)}",
            f"- Flags: {folder.flag_counter.most_common(8)}",
        ])
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path
