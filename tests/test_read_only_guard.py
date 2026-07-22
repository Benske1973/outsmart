import unittest

from modules.safety import READ_ONLY_GUARD, ReadOnlyViolation


class ReadOnlyGuardTests(unittest.TestCase):
    def test_allows_read_operations(self):
        READ_ONLY_GUARD.check_operation("read_metadata")
        READ_ONLY_GUARD.check_operation("copy_attachments_to_export")

    def test_blocks_write_operations(self):
        for operation in ["move", "delete", "send", "reply", "mark_as_read", "alter_categories"]:
            with self.subTest(operation=operation):
                with self.assertRaises(ReadOnlyViolation):
                    READ_ONLY_GUARD.check_operation(operation)


if __name__ == "__main__":
    unittest.main()
