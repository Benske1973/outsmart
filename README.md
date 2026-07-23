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


## Werk-pc mail sample

Na folder discovery kan je op de werk-pc een beperkte read-only sample export maken:

``bat
run_workpc_mail_sample.bat
``

Deze neemt Postvak IN mee en max. 100 mails per geselecteerde map. Upload de export niet naar GitHub.


## Import analyse

Analyseer een mailbox export lokaal met:

``bat
run_import_analysis.bat imports\mailbox_export_20260723_090753.zip
``

Rapporten komen in eports/ en mogen niet naar GitHub.


## Case analyse

Groepeer en classificeer mails lokaal met:

``bat
run_case_analysis.bat imports\mailbox_export_20260723_090753.zip
``

De CSV/JSON/Markdown rapporten komen in eports/.


## Mail naar OutSmart vergelijking

Zet OutSmart CSV exports in imports\outsmart\ en draai:

``bat
run_mail_outsmart_compare.bat imports\mailbox_export_20260723_090753.zip
``

Dit vergelijkt per S.G.-debiteur mails met bestaande OutSmart-werkbonnen en legt verschillen in adres, gebouw, eenheid en referenties vast.


## OutSmart export analyse

Zet OutSmart CSV exports in imports\outsmart\ en draai:

``bat
run_outsmart_export_analysis.bat
``

Deze analyse inventariseert per S.G.-debiteur gebouwen, adressen, eenheden en dropdownachtige waarden.


## OutSmart Browser Discovery

Installeer op de werk-pc:

``bat
install_workpc_requirements.bat
``

Start daarna:

``bat
run_outsmart_browser_discovery.bat
``

Deze tool inventariseert schermen, velden, tabellen en dropdowns. Output blijft lokaal in outsmart_exports/.

