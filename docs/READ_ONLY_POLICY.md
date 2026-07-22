# Read-Only Mailbox Policy

The Data Collector is strictly read-only.

Allowed:
- enumerate folders;
- read mail metadata;
- read mail body for local export;
- copy attachments into a local export package;
- generate manifests and reports.

Forbidden:
- mark messages read or unread;
- move or delete messages;
- send, forward, reply, or create drafts;
- alter categories, flags, or folders;
- save changes back to Outlook;
- modify shared mailbox structure.

Real Outlook collection is disabled by default in `config/collector_config.json`.
Demo mode is safe and does not connect to Outlook.
