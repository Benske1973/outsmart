import argparse
from pathlib import Path

from modules.import_package_analyzer import ImportPackageAnalyzer, write_analysis_report


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze a read-only mailbox export package")
    parser.add_argument("zip_path", help="Path to mailbox_export_*.zip")
    args = parser.parse_args()

    zip_path = Path(args.zip_path)
    analyzer = ImportPackageAnalyzer()
    analysis = analyzer.analyze_zip(zip_path)
    report = write_analysis_report(analysis)
    print("Import analyse klaar")
    print(f"Rapport: {report}")
    print(f"Mails: {analysis['mail_count']}")
    print(f"Bijlagen: {analysis['attachment_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
