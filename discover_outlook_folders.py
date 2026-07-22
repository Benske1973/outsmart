from modules.logging_setup import configure_logging
from modules.outlook_discovery import run_discovery


if __name__ == "__main__":
    configure_logging()
    report = run_discovery()
    print("READ-ONLY Outlook folder discovery klaar")
    print(report)
