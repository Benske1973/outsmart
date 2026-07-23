import argparse
from pathlib import Path

from modules.case_analyzer import MailCaseAnalyzer, write_case_report


def main() -> int:
    parser = argparse.ArgumentParser(description="Group and classify mails from a mailbox export package")
    parser.add_argument("zip_path", help="Path to mailbox_export_*.zip")
    args = parser.parse_args()
    analysis = MailCaseAnalyzer().analyze_zip(Path(args.zip_path))
    report = write_case_report(analysis)
    print("Case analyse klaar")
    print(f"Rapport: {report}")
    print(f"Mails: {analysis['mail_count']}")
    print(f"Cases/groups: {analysis['case_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
