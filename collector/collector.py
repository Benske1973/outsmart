import logging
from typing import Optional

from collector.exporter import PortablePackageExporter
from modules.config import AppConfig, load_config
from modules.demo_source import DemoMailboxSource
from modules.mailbox_analyzer import MailboxAnalyzer
from modules.models import CollectorRunResult
from modules.outlook_source import OutlookReadOnlySource
from modules.safety import READ_ONLY_GUARD, ReadOnlyViolation

LOGGER = logging.getLogger(__name__)


class ReadOnlyMailboxCollector:
    def __init__(self, config: Optional[AppConfig] = None) -> None:
        self.config = config or load_config()
        if not self.config.read_only_mode:
            raise ReadOnlyViolation("Collector refuses to start when READ_ONLY_MODE is false.")
        READ_ONLY_GUARD.assert_read_only()
        self.analyzer = MailboxAnalyzer()
        self.exporter = PortablePackageExporter()

    def run(self, demo_mode: Optional[bool] = None) -> CollectorRunResult:
        use_demo = self.config.demo_mode if demo_mode is None else demo_mode
        if use_demo:
            source = DemoMailboxSource(self.config.mailbox_profiles)
            LOGGER.info("Starting collector in DEMO mode")
        else:
            if not self.config.allow_real_outlook:
                raise ReadOnlyViolation("Real Outlook collection is disabled in config. Use demo mode or enable it on the work PC only.")
            source = OutlookReadOnlySource(self.config.mailbox_profiles, self.config.shared_mailbox_name)
            LOGGER.info("Starting collector in real Outlook READ-ONLY mode")

        folder_results = source.scan_folders(self.config.mailbox_folders, self.config.max_mails_per_folder)
        analyses = self.analyzer.analyze_all(folder_results)
        return self.exporter.create_package(folder_results, analyses)
