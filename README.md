# OutSmart Werkbon Assistent v2.3.1

Nieuwe hoofdversie met een strikt read-only Data Collector.

## Belangrijk

De collector mag de gedeelde mailbox nooit wijzigen. Hij leest alleen metadata, bodytekst en bijlagen, en maakt lokale exportpakketten voor latere analyse.

Standaard staat de app in demo/mock-modus. Op de privé-pc wordt dus geen Outlook gebruikt.

## Starten

```bat
start_app.bat
```

Of via de terminal:

```bat
.venv\Scripts\python.exe main.py
```

## Veilige demo-export

```bat
run_demo_export.bat
```

De export komt in `exports/` en bevat:

- `manifest.json`
- `REPORT.md`
- per mailboxmap metadata, bodytekst en kopieën van demo-bijlagen
- een ZIP-pakket om later te analyseren

## Mailboxprofielen

- AANVRAAG WERKOPDRACHT -> S.G-1 STAD.GENT (Thema)
- THUIS.GENT -> S.G-2 THUISPUNTGENT
- BRANDWEER -> S.G-3 HVZ Zone
- MOBILITEIT -> S.G-4 STAD.GENT (Mobiliteit)
- FEESTELIJKHEDEN -> S.G-5 STAD-GENT (FEE)

## Tests

```bat
run_tests.bat
```

## Werk-pc

Later kan dezelfde collector naar de werk-pc gekopieerd worden. Echte Outlook-collectie blijft standaard uitgeschakeld en mag alleen read-only geactiveerd worden in de configuratie.

## Werk-pc folder discovery

Gebruik op de werk-pc eerst:

``bat
run_workpc_folder_discovery.bat
``

Deze stap lijst alleen Outlook-mappen op en wijzigt geen mailboxdata.

