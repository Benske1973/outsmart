# Werk-pc Read-Only Mail Sample Export

Deze stap exporteert lokale kopieën van een beperkt aantal mails per geselecteerde map.

Belangrijk:
- `Postvak IN` zit expliciet in de selectie.
- Maximaal 100 mails per geselecteerde map.
- Strict read-only.
- De mailbox wordt niet gewijzigd.

## Start

```bat
run_workpc_mail_sample.bat
```

Je moet bewust `READONLY` typen voordat de export start.

## Output

De ZIP komt in:

```text
exports\mailbox_export_YYYYMMDD_HHMMSS.zip
```

Deze export bevat mogelijk echte maildata en mag niet naar GitHub.
