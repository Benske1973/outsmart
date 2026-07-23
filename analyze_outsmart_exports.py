import argparse
from pathlib import Path

from modules.outsmart_reference_analyzer import OutSmartReferenceAnalyzer, write_outsmart_reference_report


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze OutSmart CSV exports for reference data")
    parser.add_argument("--outsmart-dir", default="imports/outsmart", help="Directory containing OutSmart CSV exports")
    args = parser.parse_args()
    analysis = OutSmartReferenceAnalyzer().analyze_directory(Path(args.outsmart_dir))
    report = write_outsmart_reference_report(analysis)
    print("OutSmart referentieanalyse klaar")
    print(f"Rapport: {report}")
    print(f"CSV files: {analysis['csv_count']}")
    print(f"Records: {analysis['record_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
