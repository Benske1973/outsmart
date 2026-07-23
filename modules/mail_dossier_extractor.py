import csv
import json
import zipfile
from collections import defaultdict
from dataclasses import dataclass, asdict, field
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set

from modules.config import REPORTS_DIR

try:
    from pypdf import PdfReader
except Exception:  # pragma: no cover - handled at runtime
    PdfReader = None


TEXT_SUFFIXES = {".json", ".txt", ".md", ".csv", ".eml", ".html"}
PDF_SUFFIXES = {".pdf"}


@dataclass
class DossierAttachment:
    path: str
    filename: str
    size: int = 0
    matched_terms: List[str] = field(default_factory=list)
    text_sample: str = ""


@dataclass
class DossierMail:
    mail_folder: str
    source_folder: str = ""
    subject: str = ""
    sender_name: str = ""
    sender_email: str = ""
    received_at: str = ""
    conversation_id: str = ""
    entry_id: str = ""
    matched_terms: List[str] = field(default_factory=list)
    matched_in: List[str] = field(default_factory=list)
    body_sample: str = ""
    attachments: List[DossierAttachment] = field(default_factory=list)


class MailDossierExtractor:
    def extract(self, zip_path: Path, references: Iterable[str]) -> Dict[str, Any]:
        zip_path = Path(zip_path)
        refs = [str(ref).strip() for ref in references if str(ref).strip()]
        if not refs:
            raise ValueError("Geen referenties opgegeven")
        mail_hits: Dict[str, DossierMail] = {}
        with zipfile.ZipFile(zip_path, "r") as archive:
            names = archive.namelist()
            name_set = set(names)
            for name in names:
                lower_name = name.lower()
                name_terms = self._matches(name, refs)
                text_terms: List[str] = []
                text_sample = ""
                suffix = Path(name).suffix.lower()
                if suffix in TEXT_SUFFIXES:
                    text = self._read_text(archive, name)
                    text_terms = self._matches(text, refs)
                    if text_terms and name.endswith("body.txt"):
                        text_sample = self._sample_around(text, text_terms[0])
                elif suffix in PDF_SUFFIXES:
                    text = self._read_pdf_text(archive, name)
                    text_terms = self._matches(text, refs)
                    if text_terms:
                        text_sample = self._sample_around(text, text_terms[0])
                terms = sorted(set(name_terms + text_terms), key=refs.index)
                if not terms:
                    continue
                mail_folder = self._mail_folder_for(name)
                if not mail_folder:
                    continue
                mail = mail_hits.get(mail_folder)
                if not mail:
                    mail = self._load_mail(archive, name_set, mail_folder)
                    mail_hits[mail_folder] = mail
                for term in terms:
                    if term not in mail.matched_terms:
                        mail.matched_terms.append(term)
                where = self._where(name, mail_folder)
                if where not in mail.matched_in:
                    mail.matched_in.append(where)
                if name.endswith("body.txt") and text_sample and not mail.body_sample:
                    mail.body_sample = text_sample
                if suffix in PDF_SUFFIXES:
                    attachment = DossierAttachment(
                        path=name,
                        filename=Path(name).name,
                        size=self._entry_size(archive, name),
                        matched_terms=terms,
                        text_sample=text_sample,
                    )
                    if not any(existing.path == attachment.path for existing in mail.attachments):
                        mail.attachments.append(attachment)
            # enrich attachments for every matched mail, even when only metadata/body matched.
            for mail_folder, mail in mail_hits.items():
                self._add_declared_attachments(archive, name_set, mail_folder, mail)
        mails = sorted(mail_hits.values(), key=lambda m: (m.received_at or "", m.subject, m.mail_folder))
        return {
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "zip_path": str(zip_path),
            "references": refs,
            "mail_count": len(mails),
            "mails": [asdict(mail) for mail in mails],
            "missing_references": [ref for ref in refs if not any(ref in mail.matched_terms for mail in mails)],
        }

    def _load_mail(self, archive: zipfile.ZipFile, name_set: Set[str], mail_folder: str) -> DossierMail:
        meta_name = mail_folder.rstrip("/") + "/metadata.json"
        body_name = mail_folder.rstrip("/") + "/body.txt"
        meta: Dict[str, Any] = {}
        if meta_name in name_set:
            try:
                meta = json.loads(archive.read(meta_name).decode("utf-8-sig", errors="replace"))
            except Exception:
                meta = {}
        body_sample = ""
        if body_name in name_set:
            body = self._read_text(archive, body_name)
            body_sample = self._clean(body[:1200])
        return DossierMail(
            mail_folder=mail_folder,
            source_folder=str(meta.get("source_folder") or ""),
            subject=str(meta.get("subject") or ""),
            sender_name=str(meta.get("sender_name") or ""),
            sender_email=str(meta.get("sender_email") or ""),
            received_at=str(meta.get("received_at") or ""),
            conversation_id=str(meta.get("conversation_id") or ""),
            entry_id=str(meta.get("entry_id") or ""),
            body_sample=body_sample,
        )

    def _add_declared_attachments(self, archive: zipfile.ZipFile, name_set: Set[str], mail_folder: str, mail: DossierMail) -> None:
        meta_name = mail_folder.rstrip("/") + "/metadata.json"
        if meta_name not in name_set:
            return
        try:
            meta = json.loads(archive.read(meta_name).decode("utf-8-sig", errors="replace"))
        except Exception:
            return
        prefix_root = "/".join(meta_name.split("/")[:-2])
        for item in meta.get("attachments") or []:
            export_path = str(item.get("export_path") or "").replace("\\", "/")
            candidates = [export_path]
            if prefix_root and not export_path.startswith(prefix_root):
                candidates.append(prefix_root.rstrip("/") + "/" + export_path.lstrip("/"))
            path = next((candidate for candidate in candidates if candidate in name_set), "")
            if not path:
                continue
            if any(existing.path == path for existing in mail.attachments):
                continue
            mail.attachments.append(DossierAttachment(
                path=path,
                filename=str(item.get("filename") or Path(path).name),
                size=int(item.get("size") or self._entry_size(archive, path)),
            ))

    def _read_text(self, archive: zipfile.ZipFile, name: str) -> str:
        try:
            return archive.read(name).decode("utf-8-sig", errors="replace")
        except Exception:
            return ""

    def _read_pdf_text(self, archive: zipfile.ZipFile, name: str) -> str:
        if PdfReader is None:
            return ""
        try:
            reader = PdfReader(BytesIO(archive.read(name)))
            chunks = []
            for page in reader.pages[:10]:
                chunks.append(page.extract_text() or "")
            return "\n".join(chunks)
        except Exception:
            return ""

    def _matches(self, text: str, refs: List[str]) -> List[str]:
        lower = (text or "").lower()
        return [ref for ref in refs if ref.lower() in lower]

    def _mail_folder_for(self, name: str) -> str:
        parts = name.split("/")
        if "attachments" in parts:
            idx = parts.index("attachments")
            return "/".join(parts[:idx])
        if parts and parts[-1] in {"metadata.json", "body.txt"}:
            return "/".join(parts[:-1])
        if len(parts) >= 3 and parts[-1] == "":
            return "/".join(parts[:-1])
        if len(parts) >= 3 and parts[-2].startswith("mail_"):
            return "/".join(parts[:-1])
        return ""

    def _where(self, name: str, mail_folder: str) -> str:
        if name.endswith("metadata.json"):
            return "metadata"
        if name.endswith("body.txt"):
            return "body"
        if "/attachments/" in name:
            return "attachment:" + Path(name).name
        return name.replace(mail_folder, "").strip("/") or "mail_folder"

    def _entry_size(self, archive: zipfile.ZipFile, name: str) -> int:
        try:
            return archive.getinfo(name).file_size
        except Exception:
            return 0

    def _sample_around(self, text: str, term: str, radius: int = 450) -> str:
        lower = text.lower()
        idx = lower.find(term.lower())
        if idx < 0:
            return self._clean(text[: radius * 2])
        start = max(0, idx - radius)
        end = min(len(text), idx + len(term) + radius)
        return self._clean(text[start:end])

    def _clean(self, text: str) -> str:
        return " ".join(str(text or "").replace("\r", " ").replace("\n", " ").split())


def write_mail_dossier_report(dossier: Dict[str, Any]) -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    label = "_".join(dossier["references"][:4]) or "mail_dossier"
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = f"mail_dossier_{label}_{stamp}"
    json_path = REPORTS_DIR / f"{base}.json"
    md_path = REPORTS_DIR / f"{base}.md"
    csv_path = REPORTS_DIR / f"{base}.csv"
    json_path.write_text(json.dumps(dossier, indent=4, ensure_ascii=False), encoding="utf-8")
    with csv_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=[
            "source_folder", "subject", "sender_name", "sender_email", "received_at", "conversation_id", "matched_terms", "matched_in", "attachment_count", "mail_folder",
        ], delimiter=";")
        writer.writeheader()
        for mail in dossier["mails"]:
            writer.writerow({
                "source_folder": mail.get("source_folder", ""),
                "subject": mail.get("subject", ""),
                "sender_name": mail.get("sender_name", ""),
                "sender_email": mail.get("sender_email", ""),
                "received_at": mail.get("received_at", ""),
                "conversation_id": mail.get("conversation_id", ""),
                "matched_terms": ", ".join(mail.get("matched_terms", [])),
                "matched_in": ", ".join(mail.get("matched_in", [])),
                "attachment_count": len(mail.get("attachments", [])),
                "mail_folder": mail.get("mail_folder", ""),
            })
    lines = [
        "# Mail Dossier",
        "",
        f"Source ZIP: `{dossier['zip_path']}`",
        f"References: {', '.join(dossier['references'])}",
        f"Mails found: {dossier['mail_count']}",
    ]
    if dossier.get("missing_references"):
        lines.append(f"Missing references: {', '.join(dossier['missing_references'])}")
    for idx, mail in enumerate(dossier["mails"], start=1):
        lines.extend([
            "",
            f"## Mail {idx}: {mail.get('subject') or '(zonder onderwerp)'}",
            f"- Folder: {mail.get('source_folder')}",
            f"- Sender: {mail.get('sender_name')} <{mail.get('sender_email')}>",
            f"- Received: {mail.get('received_at')}",
            f"- Conversation: {mail.get('conversation_id')}",
            f"- Matched terms: {', '.join(mail.get('matched_terms', []))}",
            f"- Matched in: {', '.join(mail.get('matched_in', []))}",
            f"- Export folder: `{mail.get('mail_folder')}`",
            "",
            "### Attachments",
        ])
        for att in mail.get("attachments", []):
            lines.append(f"- {att.get('filename')} ({att.get('size', 0)} bytes) matches: {', '.join(att.get('matched_terms', [])) or '-'}")
            if att.get("text_sample"):
                lines.append(f"  - sample: {att['text_sample'][:500]}")
        if mail.get("body_sample"):
            lines.extend(["", "### Body sample", mail["body_sample"][:900]])
    lines.extend(["", "## Output", f"- JSON: `{json_path}`", f"- CSV: `{csv_path}`"])
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return md_path
