import unittest

from collector.exporter import safe_attachment_name, safe_name


class ExporterPathTests(unittest.TestCase):
    def test_long_attachment_name_is_shortened(self):
        name = "httpsbatis.gentgrp.gent.bewebdavSjabloonbestandNaamloos" * 5 + ".png"
        safe = safe_attachment_name(name, 1)
        self.assertLess(len(safe), 90)
        self.assertTrue(safe.endswith(".png"))

    def test_long_subject_is_shortened(self):
        safe = safe_name("Onderwerp " * 40, max_len=38, fallback="mail")
        self.assertLess(len(safe), 55)


if __name__ == "__main__":
    unittest.main()
