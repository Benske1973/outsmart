import json
import shutil
import zipfile
from datetime import datetime
from typing import Dict, List

from modules.config import EXPORTS_DIR
from modules.models import CollectorRunResult, FolderScanResult, MailItemData
from modules.safety import READ_ONLY_GUARD


def safe_name(value: str) -> str:
    allowed = []
    for char in value:
        if char.isalnum() or char in ("-", "_", "."):
            allowed.append(char)
        elif char.isspace():
            allowed.append("_")
    result = "".join(allowed).strip("._")
    return result[:80] or "item"


class PortablePackageExporter:
    def create_package(self, folder_results: List[FolderScanResult], analyses: List[Dict[str, object]]) -> CollectorRunResult:
        READ_ONLY_GUARD.assert_read_only()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        export_dir = EXPORTS_DIR / f"mailbox_export_{timestamp}"
        export_dir.mkdir(parents=True, exist_ok=True)

        manifest = {
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "read_only_mode": True,
            "source": "demo_or_read_only_outlook",
            "folders": [],
            "analysis": analyses,
        }

        for folder_result in folder_results:
            folder_dir = export_dir / safe_name(folder_result.folder_name)
            folder_dir.mkdir(parents=True, exist_ok=True)
            folder_payload = {
                "folder_name": folder_result.folder_name,
                "profile": folder_result.profile,
                "mail_count": len(folder_result.mails),
                "mails": [],
            }
            for mail_index, mail in enumerate(folder_result.mails, start=1):
                mail_dir = folder_dir / f"{mail_index:04d}_{safe_name(mail.subject)}"
                attachments_dir = mail_dir / "attachments"
                attachments_dir.mkdir(parents=True, exist_ok=True)
                (mail_dir / "body.txt").write_text(mail.body or "", encoding="utf-8")
                metadata = self._mail_metadata(mail)
                metadata["attachments"] = []
                for attachment in mail.attachments:
                    target = attachments_dir / safe_name(attachment.filename)
                    if attachment.source_path and attachment.source_path.exists():
                        shutil.copy2(attachment.source_path, target)
                    else:
                        target.write_bytes(attachment.content or b"")
                    metadata["attachments"].append({
                        "filename": attachment.filename,
                        "export_path": str(target.relative_to(export_dir)),
                        "size": target.stat().st_size,
                    })
                (mail_dir / "metadata.json").write_text(json.dumps(metadata, indent=4, ensure_ascii=False), encoding="utf-8")
                folder_payload["mails"].append(metadata)
            manifest["folders"].append(folder_payload)

        manifest_path = export_dir / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=4, ensure_ascii=False), encoding="utf-8")
        report_path = export_dir / "REPORT.md"
        report_path.write_text(self._build_report(manifest), encoding="utf-8")
        zip_path = export_dir.with_suffix(".zip")
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in export_dir.rglob("*"):
                archive.write(path, path.relative_to(export_dir.parent))
        return CollectorRunResult(
            export_dir=export_dir,
            zip_path=zip_path,
            manifest_path=manifest_path,
            report_path=report_path,
            folder_results=folder_results,
        )

    def _mail_metadata(self, mail: MailItemData) -> Dict[str, object]:
        return {
            "source_folder": mail.source_folder,
            "entry_id": mail.entry_id,
            "conversation_id": mail.conversation_id,
            "subject": mail.subject,
            "sender_name": mail.sender_name,
            "sender_email": mail.sender_email,
            "received_at": mail.received_at.isoformat(timespec="seconds"),
            "unread_at_collection": mail.unread,
            "attachment_count": len(mail.attachments),
            "metadata": mail.metadata,
        }

    def _build_report(self, manifest: Dict[str, object]) -> str:
        lines = [
            "# OutSmart Read-Only Mailbox Export",
            "",
            f"Created: {manifest['created_at']}",
            "READ-ONLY: yes",
            "",
            "This export is a local copy for later analysis. The mailbox was not modified.",
            "",
            "## Folders",
        ]
        for folder in manifest["folders"]:
            lines.append(f"- {folder['folder_name']}: {folder['mail_count']} mails")
        lines.extend(["", "## Analysis"])
        for analysis in manifest["analysis"]:
            lines.append(f"### {analysis['folder']}")
            lines.append(f"- Mails: {analysis['mail_count']}")
            lines.append(f"- Attachments: {analysis['attachment_count']}")
            lines.append(f"- Document types: {analysis['document_types']}")
            lines.append("")
        return "\n".join(lines)
