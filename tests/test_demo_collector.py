import unittest

from collector.collector import ReadOnlyMailboxCollector
from modules.config import load_config


class DemoCollectorTests(unittest.TestCase):
    def test_demo_collector_creates_package(self):
        config = load_config()
        collector = ReadOnlyMailboxCollector(config)
        result = collector.run(demo_mode=True)
        self.assertTrue(result.zip_path.exists())
        self.assertTrue(result.manifest_path.exists())
        self.assertGreater(result.mail_count, 0)


if __name__ == "__main__":
    unittest.main()
