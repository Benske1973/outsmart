import argparse
from pathlib import Path

from modules.mail_dossier_extractor import MailDossierExtractor, write_mail_dossier_report


def main() -> int:
    parser = argparse.ArgumentParser(description="Find all mails in a mailbox export that belong to a workorder/order/PO")
    parser.add_argument("zip", help="Mailbox export ZIP")
    parser.add_argument("references", nargs="+", help="Order, PO, OutSmart number or text references")
    args = parser.parse_args()
    dossier = MailDossierExtractor().extract(Path(args.zip), args.references)
    report = write_mail_dossier_report(dossier)
    print("Maildossier klaar")
    print(f"Rapport: {report}")
    print(f"Mails gevonden: {dossier['mail_count']}")
    if dossier.get("missing_references"):
        print("Niet gevonden: " + ", ".join(dossier["missing_references"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
