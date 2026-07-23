# Project Status v2.3.1

## Afgewerkt

[X] Lokale hoofdmap is single source of truth
[X] Startbare `main.py`
[X] Tkinter UI met duidelijke READ-ONLY banner
[X] Demo/mock mailboxbron voor prive-pc
[X] Portable exportpakket naar `exports/`
[X] Manifest en Markdown rapport
[X] Read-only guard blokkeert verboden mailboxacties
[X] Windows startscript
[X] Tests voor read-only guard en demo collector

## Bezig

[ ] Werk-pc Data Collector testen met echte Outlook-mapstructuur
[ ] Exportpakket importeren en analyseren op prive-pc
[ ] Vergelijken met bestaande OutSmart werkbonnen

## Nog te bouwen

[ ] Real Outlook collectie activeren achter expliciete config
[ ] Afzenderprofielen per map
[ ] PDF-veldextractie per map
[ ] OutSmart export importeren
[ ] Mail naar werkbon vergelijking
[ ] Automatische veldmapping

## v2.3.2 toegevoegd

[X] Read-only Outlook folder discovery
[X] Werk-pc script: run_workpc_folder_discovery.bat
[X] Rapportage naar reports/


## v2.3.3 toegevoegd

[X] Postvak IN opgenomen in werk-pc sample
[X] Read-only mail sample export met bevestiging READONLY
[X] Max 100 mails per geselecteerde map
[X] Discovery rapporten toegevoegd aan .gitignore


## v2.3.4 toegevoegd

[X] Configbestanden met UTF-8 BOM worden correct gelezen op Python 3.13
[X] Werk-pc zonder lokale .venv blijft ondersteund via gewone python


## v2.3.5 toegevoegd

[X] Exportnamen ingekort en voorzien van hash tegen Windows-padlengteproblemen
[X] Outlook-bijlagen worden read-only lokaal gekopieerd via SaveAsFile

