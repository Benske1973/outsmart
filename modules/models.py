from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class AttachmentData:
    filename: str
    content: bytes = b""
    source_path: Optional[Path] = None
    size: int = 0

    def __post_init__(self) -> None:
        if self.source_path and self.source_path.exists():
            self.size = self.source_path.stat().st_size
        elif self.content:
            self.size = len(self.content)


@dataclass
class MailItemData:
    source_folder: str
    entry_id: str
    conversation_id: str
    subject: str
    sender_name: str
    sender_email: str
    received_at: datetime
    body: str
    unread: Optional[bool] = None
    attachments: List[AttachmentData] = field(default_factory=list)
    metadata: Dict[str, str] = field(default_factory=dict)


@dataclass
class FolderScanResult:
    folder_name: str
    profile: Dict[str, str]
    mails: List[MailItemData]


@dataclass
class CollectorRunResult:
    export_dir: Path
    zip_path: Path
    manifest_path: Path
    report_path: Path
    folder_results: List[FolderScanResult]

    @property
    def mail_count(self) -> int:
        return sum(len(folder.mails) for folder in self.folder_results)
