import argparse

from collector.collector import ReadOnlyMailboxCollector
from modules.logging_setup import configure_logging


def main() -> int:
    parser = argparse.ArgumentParser(description="OutSmart read-only mailbox collector")
    parser.add_argument("--demo", action="store_true", help="Run safe demo mode without Outlook")
    args = parser.parse_args()

    configure_logging()
    collector = ReadOnlyMailboxCollector()
    result = collector.run(demo_mode=True if args.demo else None)
    print("READ-ONLY export created")
    print(f"Export folder: {result.export_dir}")
    print(f"ZIP package:   {result.zip_path}")
    print(f"Manifest:      {result.manifest_path}")
    print(f"Report:        {result.report_path}")
    print(f"Mails:         {result.mail_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
