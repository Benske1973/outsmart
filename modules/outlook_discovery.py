import json
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from modules.config import REPORTS_DIR, load_config
from modules.safety import READ_ONLY_GUARD


@dataclass
class OutlookFolderInfo:
    name: str
    path: str
    item_count: Optional[int]
    unread_count: Optional[int]
    depth: int


class OutlookFolderDiscoveryUnavailable(RuntimeError):
    pass


class OutlookFolderDiscovery:
    """Lists Outlook folders in strict read-only mode."""

    def __init__(self, shared_mailbox_name: str = "") -> None:
        READ_ONLY_GUARD.assert_read_only()
        self.shared_mailbox_name = shared_mailbox_name

    def discover(self, max_depth: int = 5) -> List[OutlookFolderInfo]:
        READ_ONLY_GUARD.check_operation("enumerate_folders")
        try:
            import win32com.client  # type: ignore
        except Exception as exc:
            raise OutlookFolderDiscoveryUnavailable(
                "pywin32 is nodig op de werk-pc om Outlook-mappen te detecteren."
            ) from exc

        outlook = win32com.client.Dispatch("Outlook.Application").GetNamespace("MAPI")
        roots = self._get_roots(outlook)
        folders: List[OutlookFolderInfo] = []
        for root in roots:
            self._walk_folder(root, folders, depth=0, max_depth=max_depth, parent_path="")
        return folders

    def _get_roots(self, outlook):
        if self.shared_mailbox_name:
            wanted = self.shared_mailbox_name.lower()
            return [store for store in outlook.Folders if str(store.Name).lower() == wanted]
        return [store for store in outlook.Folders]

    def _walk_folder(self, folder, folders: List[OutlookFolderInfo], depth: int, max_depth: int, parent_path: str) -> None:
        if depth > max_depth:
            return
        try:
            name = str(folder.Name)
        except Exception:
            name = "<onbekend>"
        path = f"{parent_path}/{name}" if parent_path else name
        folders.append(OutlookFolderInfo(
            name=name,
            path=path,
            item_count=self._safe_int(lambda: folder.Items.Count),
            unread_count=self._safe_int(lambda: folder.UnReadItemCount),
            depth=depth,
        ))
        try:
            children = list(folder.Folders)
        except Exception:
            children = []
        for child in children:
            self._walk_folder(child, folders, depth + 1, max_depth, path)

    def _safe_int(self, getter):
        try:
            return int(getter())
        except Exception:
            return None


def write_discovery_report(folders: List[OutlookFolderInfo]) -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = REPORTS_DIR / f"outlook_folder_discovery_{timestamp}.json"
    md_path = REPORTS_DIR / f"outlook_folder_discovery_{timestamp}.md"
    payload = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "read_only_mode": True,
        "folder_count": len(folders),
        "folders": [asdict(folder) for folder in folders],
    }
    json_path.write_text(json.dumps(payload, indent=4, ensure_ascii=False), encoding="utf-8")
    lines = [
        "# Outlook Folder Discovery",
        "",
        "READ-ONLY: yes",
        f"Folders found: {len(folders)}",
        "",
        "## Folder tree",
    ]
    for folder in folders:
        indent = "  " * folder.depth
        lines.append(f"- {indent}{folder.name} | items: {folder.item_count} | unread: {folder.unread_count} | path: {folder.path}")
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return md_path


def run_discovery() -> Path:
    config = load_config()
    discovery = OutlookFolderDiscovery(shared_mailbox_name=config.shared_mailbox_name)
    folders = discovery.discover(max_depth=6)
    return write_discovery_report(folders)
