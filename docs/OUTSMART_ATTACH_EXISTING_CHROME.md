# OutSmart Discovery via bestaande Chrome

Gebruik dit wanneer de gewone Playwright-browser niet kan inloggen of reCAPTCHA blokkeert.

## Stap 1

Start Chrome met remote debugging:

```bat
start_chrome_debug_outsmart.bat
```

Log in op OutSmart in dat Chrome-venster.

## Stap 2

Start de discovery die aan Chrome koppelt:

```bat
run_outsmart_attach_discovery.bat
```

Commando's in de terminal:

- `tabs` toont alle open tabs;
- een nummer kiest een tab;
- `ENTER` scant het gekozen tabblad;
- `q` stopt.

## Read-only

De tool leest alleen de DOM, screenshots, velden, tabellen en dropdownopties. Hij mag geen werkbon opslaan of aanpassen.
