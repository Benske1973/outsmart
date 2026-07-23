import argparse
from pathlib import Path

from modules.mail_outsmart_comparator import MailOutSmartComparator, write_comparison_report


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare mailbox cases with OutSmart CSV exports")
    parser.add_argument("mailbox_zip", help="Path to mailbox_export_*.zip")
    parser.add_argument("--outsmart-dir", default="imports/outsmart", help="Directory containing OutSmart CSV exports")
    args = parser.parse_args()
    result = MailOutSmartComparator().compare(Path(args.mailbox_zip), Path(args.outsmart_dir))
    report = write_comparison_report(result)
    print("Mail-OutSmart vergelijking klaar")
    print(f"Rapport: {report}")
    print(f"Mails: {result['mail_count']}")
    print(f"OutSmart records: {result['outsmart_record_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
