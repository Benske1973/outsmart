import re
from pathlib import Path


class DocumentClassifier:
    def classify(self, filename: str, text: str = "") -> str:
        value = f"{filename} {text}".lower()
        name = Path(filename).name.lower()

        if re.search(r"fag[-_ ]?45\d{8}", name) or "bestelbon" in value:
            return "BESTELBON"
        if "dienstbevel" in value:
            return "DIENSTBEVEL"
        if re.fullmatch(r"4\d{6}\.pdf", name):
            return "DIENSTBEVEL"
        if "werkorder" in value or re.search(r"\b4\d{6}\b", value):
            return "WERKORDER"
        if name.endswith((".jpg", ".jpeg", ".png", ".heic")):
            return "FOTO"
        if name.endswith(".pdf"):
            return "PDF_ONBEKEND"
        return "ONBEKEND"
