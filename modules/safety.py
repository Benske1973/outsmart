from dataclasses import dataclass
from typing import Iterable


FORBIDDEN_OUTLOOK_OPERATIONS = {
    "mark_as_read",
    "move",
    "delete",
    "send",
    "forward",
    "reply",
    "alter_categories",
    "create_draft",
    "save_to_mailbox",
    "modify_folder",
    "save_message",
    "set_unread",
    "set_flag",
}


class ReadOnlyViolation(RuntimeError):
    pass


@dataclass(frozen=True)
class ReadOnlyGuard:
    enabled: bool = True

    def assert_read_only(self) -> None:
        if not self.enabled:
            raise ReadOnlyViolation("READ-ONLY mode must remain enabled for the mailbox collector.")

    def check_operation(self, operation: str) -> None:
        self.assert_read_only()
        normalized = operation.strip().lower()
        if normalized in FORBIDDEN_OUTLOOK_OPERATIONS:
            raise ReadOnlyViolation(f"Forbidden mailbox write operation blocked: {operation}")

    def check_operations(self, operations: Iterable[str]) -> None:
        for operation in operations:
            self.check_operation(operation)


READ_ONLY_GUARD = ReadOnlyGuard(enabled=True)
