import argparse
from pathlib import Path

from modules.outsmart_discovery_analyzer import OutSmartDiscoveryAnalyzer, write_discovery_analysis_report


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze an OutSmart browser discovery ZIP")
    parser.add_argument("zip", nargs="?", default="imports/20260723_114121_Werkbon_OutSmart.zip", help="Path to OutSmart discovery ZIP or folder")
    args = parser.parse_args()
    analysis = OutSmartDiscoveryAnalyzer().analyze_path(Path(args.zip))
    report = write_discovery_analysis_report(analysis)
    print("OutSmart discovery-analyse klaar")
    print(f"Rapport: {report}")
    print(f"Snapshots: {analysis['snapshot_count']}")
    print(f"Velden: {analysis['fields_total']} totaal / {analysis['fields_unique']} uniek")
    print(f"Dropdowns: {analysis['dropdowns_total']} totaal / {analysis['dropdowns_unique']} uniek")
    print(f"Tabellen: {analysis['tables_total']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
