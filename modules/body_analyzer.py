import re
from typing import Dict, List


class BodyAnalyzer:
    ORDER_PATTERN = re.compile(r"\b4\d{6}\b")
    PO_PATTERN = re.compile(r"\b45\d{8}\b")

    def analyze(self, subject: str, body: str) -> Dict[str, object]:
        text = f"{subject}\n{body}"
        lower = text.lower()
        orders = sorted(set(self.ORDER_PATTERN.findall(text)))
        purchase_orders = sorted(set(self.PO_PATTERN.findall(text)))
        flags: List[str] = []

        if any(word in lower for word in ["annuleer", "annulatie", "vervalt", "niet uitvoeren"]):
            flags.append("ANNULATIE")
        if any(word in lower for word in ["wijziging", "extra info", "bijkomende informatie", "planning"]):
            flags.append("WIJZIGING")
        if not flags and (orders or purchase_orders):
            flags.append("REFERENTIE_GEVONDEN")

        return {
            "orders": orders,
            "purchase_orders": purchase_orders,
            "flags": flags,
        }
