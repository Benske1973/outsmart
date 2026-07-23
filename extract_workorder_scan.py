import argparse
from pathlib import Path

from modules.workorder_scan_extractor import WorkorderScanExtractor, write_workorder_scan_profile


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract a structured profile from an OutSmart workorder scan folder")
    parser.add_argument("folder", help="Path to one outsmart_exports scan folder")
    args = parser.parse_args()
    profile = WorkorderScanExtractor().extract(Path(args.folder))
    report = write_workorder_scan_profile(profile)
    print("Werkbon scanprofiel klaar")
    print(f"Rapport: {report}")
    print(f"OutSmart: {profile.outsmart_number or '-'}")
    print(f"Order: {profile.fields.get('job_number', '-')}")
    print(f"Klant: {profile.fields.get('customer_debtor_number', '-')} {profile.fields.get('customer_name', '')}")
    print(f"Adres: {profile.fields.get('work_address', '-')}")
    print(f"Bijlagen: {len(profile.attachments)}")
    print(f"Waarschuwingen: {len(profile.warnings)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
