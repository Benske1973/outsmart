from collections import Counter
from typing import Dict, Iterable, List

from modules.body_analyzer import BodyAnalyzer
from modules.document_classifier import DocumentClassifier
from modules.models import MailItemData


class MailboxAnalyzer:
    def __init__(self) -> None:
        self.body_analyzer = BodyAnalyzer()
        self.document_classifier = DocumentClassifier()

    def analyze_folder(self, folder_name: str, mails: Iterable[MailItemData]) -> Dict[str, object]:
        mails = list(mails)
        senders = Counter(mail.sender_email.lower() or mail.sender_name for mail in mails)
        domains = Counter(sender.split("@", 1)[1] for sender in senders if "@" in sender)
        document_types = Counter()
        orders = Counter()
        purchase_orders = Counter()
        flags = Counter()

        for mail in mails:
            body_result = self.body_analyzer.analyze(mail.subject, mail.body)
            orders.update(body_result["orders"])
            purchase_orders.update(body_result["purchase_orders"])
            flags.update(body_result["flags"])
            for attachment in mail.attachments:
                document_types.update([self.document_classifier.classify(attachment.filename)])

        return {
            "folder": folder_name,
            "mail_count": len(mails),
            "attachment_count": sum(len(mail.attachments) for mail in mails),
            "top_senders": senders.most_common(10),
            "domains": domains.most_common(10),
            "document_types": document_types.most_common(),
            "orders": orders.most_common(20),
            "purchase_orders": purchase_orders.most_common(20),
            "flags": flags.most_common(),
        }

    def analyze_all(self, folder_results) -> List[Dict[str, object]]:
        return [self.analyze_folder(result.folder_name, result.mails) for result in folder_results]
