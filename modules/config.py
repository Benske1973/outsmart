import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
EXPORTS_DIR = PROJECT_ROOT / "exports"
LOGS_DIR = PROJECT_ROOT / "logs"
CONFIG_DIR = PROJECT_ROOT / "config"

DEFAULT_MAILBOX_FOLDERS = [
    "AANVRAAG WERKOPDRACHT",
    "THUIS.GENT",
    "BRANDWEER",
    "MOBILITEIT",
    "FEESTELIJKHEDEN",
]


@dataclass(frozen=True)
class AppConfig:
    read_only_mode: bool
    demo_mode: bool
    allow_real_outlook: bool
    shared_mailbox_name: str
    max_mails_per_folder: int
    mailbox_folders: List[str]
    mailbox_profiles: Dict[str, Dict[str, str]]


def load_mailbox_profiles() -> Dict[str, Dict[str, str]]:
    path = DATA_DIR / "mailbox_profiles.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def ensure_default_config() -> Path:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    path = CONFIG_DIR / "collector_config.json"
    if path.exists():
        return path
    payload = {
        "READ_ONLY_MODE": True,
        "DEMO_MODE": True,
        "ALLOW_REAL_OUTLOOK": False,
        "SHARED_MAILBOX_NAME": "",
        "MAX_MAILS_PER_FOLDER": 25,
        "MAILBOX_FOLDERS": DEFAULT_MAILBOX_FOLDERS,
        "NOTE": "Real Outlook collection is disabled by default. Enable only on the work PC after testing demo mode.",
    }
    path.write_text(json.dumps(payload, indent=4), encoding="utf-8")
    return path


def load_config() -> AppConfig:
    path = ensure_default_config()
    raw = json.loads(path.read_text(encoding="utf-8"))
    profiles = load_mailbox_profiles()
    return AppConfig(
        read_only_mode=bool(raw.get("READ_ONLY_MODE", True)),
        demo_mode=bool(raw.get("DEMO_MODE", True)),
        allow_real_outlook=bool(raw.get("ALLOW_REAL_OUTLOOK", False)),
        shared_mailbox_name=str(raw.get("SHARED_MAILBOX_NAME", "")),
        max_mails_per_folder=int(raw.get("MAX_MAILS_PER_FOLDER", 25)),
        mailbox_folders=list(raw.get("MAILBOX_FOLDERS", DEFAULT_MAILBOX_FOLDERS)),
        mailbox_profiles=profiles,
    )
