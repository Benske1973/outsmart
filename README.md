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

Rapporten komen in 
eports/ en mogen niet naar GitHub.


## Case analyse

Groepeer en classificeer mails lokaal met:

``bat
run_case_analysis.bat imports\mailbox_export_20260723_090753.zip
``

De CSV/JSON/Markdown rapporten komen in 
eports/.


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


## OutSmart discovery via bestaande Chrome

Als reCAPTCHA in de aparte browser blokkeert, gebruik:

``bat
start_chrome_debug_outsmart.bat
run_outsmart_attach_discovery.bat
``

Log zelf in in Chrome en scan daarna het geopende tabblad.

## OutSmart discovery ZIP analyse

Wanneer je een OutSmart scrape ZIP in `imports` plaatst, analyseer je die lokaal met:

```bat
run_outsmart_discovery_analysis.bat imports60723_114121_Werkbon_OutSmart.zip
```

De rapporten komen in `reports/`:

- schermdekking
- gevonden velden
- tabellen
- dropdowns en opties
- waarschuwingen over ontbrekende onderdelen

Let op: rapporten en exports bevatten interne OutSmart-data en blijven lokaal. Ze worden niet naar GitHub gepusht.

Voor nieuwe OutSmart-scrapes gebruikt de discovery-tool nu ook frame/iframe-captures. Dat is nodig omdat de echte werkbonvelden vaak in een interne backoffice-frame zitten.

## OutSmart Deep Discovery

Voor grote schermen zoals **Nieuwe werkbon** gebruik je de diepe read-only scan:

```bat
start_chrome_debug_outsmart.bat
run_outsmart_deep_discovery.bat
```

In het zwarte venster:

```text
tabs
0
deep
```

Gebruik `deep` op:

- Nieuwe werkbon
- Levering / Klantrelatie / Adres
- Project kiezen
- Object of gebouw kiezen
- Formulier kiezen
- Bestaande werkbon bekijken
- Bestaande werkbon bewerken

De deep scan probeert ook grote zoekdropdowns te lezen met veilige zoektermen zoals Gent, Scheldekenslaan, Botermarkt en gebouwcodes. Hij schrijft niets naar OutSmart.

