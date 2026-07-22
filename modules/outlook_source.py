import logging
from datetime import datetime
from typing import Dict, Iterable, List

from modules.models import AttachmentData, FolderScanResult, MailItemData
from modules.safety import READ_ONLY_GUARD

LOGGER = logging.getLogger(__name__)


class OutlookUnavailable(RuntimeError):
    pass


class OutlookReadOnlySource:
    """Read-only Outlook enumerator.

    No write actions are present: no Move, Delete, Send, Reply, Forward,
    category changes, draft creation, folder edits, or message Save.
    Attachment SaveAsFile is used only to copy attachments into the local
    export package.
    """

    def __init__(self, profiles: Dict[str, Dict[str, str]], shared_mailbox_name: str = "") -> None:
        READ_ONLY_GUARD.assert_read_only()
        self.profiles = profiles
        self.shared_mailbox_name = shared_mailbox_name

    def scan_folders(self, folder_names: Iterable[str], max_mails_per_folder: int) -> List[FolderScanResult]:
        READ_ONLY_GUARD.check_operations([
            "enumerate_folders",
            "read_metadata",
            "read_body",
            "copy_attachments_to_export",
        ])
        try:
            import win32com.client  # type: ignore
        except Exception as exc:
            raise OutlookUnavailable("pywin32 is required on the work PC for real Outlook collection.") from exc

        outlook = win32com.client.Dispatch("Outlook.Application").GetNamespace("MAPI")
        root = self._resolve_root(outlook)
        results: List[FolderScanResult] = []
        for folder_name in folder_names:
            folder = self._find_folder_by_path(root, folder_name)
            if folder is None:
                LOGGER.warning("Outlook folder not found, skipped: %s", folder_name)
                results.append(FolderScanResult(folder_name=folder_name, profile=self.profiles.get(folder_name, {}), mails=[]))
                continue
            mails = self._read_folder_items(folder, folder_name, max_mails_per_folder)
            results.append(FolderScanResult(folder_name=folder_name, profile=self.profiles.get(folder_name, {}), mails=mails))
        return results

    def _resolve_root(self, outlook):
        if not self.shared_mailbox_name:
            return outlook.GetDefaultFolder(6).Parent
        for store in outlook.Folders:
            if str(store.Name).lower() == self.shared_mailbox_name.lower():
                return store
        raise OutlookUnavailable(f"Shared mailbox not found: {self.shared_mailbox_name}")

    def _find_folder_by_path(self, root, folder_path: str):
        parts = [part.strip() for part in folder_path.replace("\\", "/").split("/") if part.strip()]
        if len(parts) <= 1:
            return self._find_folder(root, folder_path)
        current = self._find_folder(root, parts[0])
        for part in parts[1:]:
            if current is None:
                return None
            current = self._find_direct_child(current, part)
        return current

    def _find_direct_child(self, folder, wanted_name: str):
        wanted = wanted_name.lower()
        try:
            for child in folder.Folders:
                if str(child.Name).lower() == wanted:
                    return child
        except Exception:
            return None
        return None

    def _find_folder(self, root, wanted_name: str):
        queue = [root]
        wanted = wanted_name.lower()
        while queue:
            folder = queue.pop(0)
            try:
                if str(folder.Name).lower() == wanted:
                    return folder
                for child in folder.Folders:
                    queue.append(child)
            except Exception:
                continue
        return None

    def _read_folder_items(self, folder, folder_name: str, max_mails: int) -> List[MailItemData]:
        items = folder.Items
        try:
            items.Sort("[ReceivedTime]", True)
        except Exception:
            pass
        mails: List[MailItemData] = []
        count = min(int(items.Count), max_mails)
        for index in range(1, count + 1):
            item = items.Item(index)
            if getattr(item, "Class", None) != 43:
                continue
            received_at = getattr(item, "ReceivedTime", None) or datetime.now()
            attachments = []
            for att_index in range(1, int(item.Attachments.Count) + 1):
                att = item.Attachments.Item(att_index)
                attachment = AttachmentData(filename=str(att.FileName), content=b"")
                setattr(attachment, "outlook_attachment", att)
                attachments.append(attachment)
            mails.append(MailItemData(
                source_folder=folder_name,
                entry_id=str(getattr(item, "EntryID", "")),
                conversation_id=str(getattr(item, "ConversationID", "")),
                subject=str(getattr(item, "Subject", "")),
                sender_name=str(getattr(item, "SenderName", "")),
                sender_email=self._sender_email(item),
                received_at=received_at,
                body=str(getattr(item, "Body", "")),
                unread=bool(getattr(item, "UnRead", False)),
                attachments=attachments,
                metadata={"outlook_class": str(getattr(item, "Class", ""))},
            ))
        return mails

    def _sender_email(self, item) -> str:
        try:
            sender = item.Sender
            if sender and sender.GetExchangeUser():
                return str(sender.GetExchangeUser().PrimarySmtpAddress)
        except Exception:
            pass
        return str(getattr(item, "SenderEmailAddress", ""))
