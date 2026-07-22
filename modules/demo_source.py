from datetime import datetime, timedelta
from typing import Dict, Iterable, List

from modules.models import AttachmentData, FolderScanResult, MailItemData


class DemoMailboxSource:
    def __init__(self, profiles: Dict[str, Dict[str, str]]) -> None:
        self.profiles = profiles

    def scan_folders(self, folder_names: Iterable[str], max_mails_per_folder: int) -> List[FolderScanResult]:
        results: List[FolderScanResult] = []
        for index, folder_name in enumerate(folder_names):
            profile = self.profiles.get(folder_name, {})
            mails = self._build_demo_mails(folder_name, index)[:max_mails_per_folder]
            results.append(FolderScanResult(folder_name=folder_name, profile=profile, mails=mails))
        return results

    def _build_demo_mails(self, folder_name: str, folder_index: int) -> List[MailItemData]:
        base_order = 4008151 + folder_index
        po_number = 4526006069 + folder_index
        received = datetime.now() - timedelta(days=folder_index + 1)
        return [
            MailItemData(
                source_folder=folder_name,
                entry_id=f"DEMO-{folder_name}-{base_order}",
                conversation_id=f"DEMO-CONV-{base_order}",
                subject=f"[DEMO] FAG-{po_number}-- GENT",
                sender_name="Stad Gent Demo",
                sender_email="demo@stad.gent",
                received_at=received,
                body=(
                    "Demo mail voor veilige test zonder Outlook.\n"
                    f"Werkorder {base_order}\n"
                    f"Bestelbon {po_number}\n"
                    "Deze mail mag alleen lokaal worden geexporteerd."
                ),
                unread=True,
                attachments=[
                    AttachmentData(filename=f"{base_order}.pdf", content=b"DEMO Dienstbevel PDF"),
                    AttachmentData(filename=f"FAG-{po_number}--.PDF", content=b"DEMO Bestelbon PDF"),
                ],
                metadata={"mode": "demo"},
            ),
            MailItemData(
                source_folder=folder_name,
                entry_id=f"DEMO-{folder_name}-INFO",
                conversation_id=f"DEMO-CONV-{base_order}-INFO",
                subject=f"[DEMO] Extra informatie werkorder {base_order}",
                sender_name="Stad Gent Demo",
                sender_email="noreply@stad.gent",
                received_at=received + timedelta(hours=2),
                body="Bijkomende informatie voor bestaande werkbon. Geen mailboxwijziging uitvoeren.",
                unread=False,
                attachments=[],
                metadata={"mode": "demo"},
            ),
        ]
