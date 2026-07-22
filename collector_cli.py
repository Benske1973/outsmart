import argparse
import json
from pathlib import Path

from collector.collector import ReadOnlyMailboxCollector
from modules.config import AppConfig, load_config, load_mailbox_profiles
from modules.logging_setup import configure_logging


def load_config_from_path(path: str) -> AppConfig:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return AppConfig(
        read_only_mode=bool(raw.get("READ_ONLY_MODE", True)),
        demo_mode=bool(raw.get("DEMO_MODE", True)),
        allow_real_outlook=bool(raw.get("ALLOW_REAL_OUTLOOK", False)),
        shared_mailbox_name=str(raw.get("SHARED_MAILBOX_NAME", "")),
        max_mails_per_folder=int(raw.get("MAX_MAILS_PER_FOLDER", 25)),
        mailbox_folders=list(raw.get("MAILBOX_FOLDERS", [])),
        mailbox_profiles=load_mailbox_profiles(),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="OutSmart read-only mailbox collector")
    parser.add_argument("--demo", action="store_true", help="Run safe demo mode without Outlook")
    parser.add_argument("--config", help="Use a specific collector config JSON")
    args = parser.parse_args()

    configure_logging()
    config = load_config_from_path(args.config) if args.config else load_config()
    collector = ReadOnlyMailboxCollector(config)
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
