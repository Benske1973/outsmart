# OutSmart Discovery Analysis

Deze analyse leest een ZIP die door de OutSmart Browser Discovery is gemaakt.

De analyse wijzigt niets aan OutSmart en gebruikt geen browser. Ze leest alleen de lokale ZIP in `imports`.

## Starten

Dubbelklik:

```bat
run_outsmart_discovery_analysis.bat
```

Standaard wordt deze ZIP gebruikt:

```text
imports\20260723_114121_Werkbon_OutSmart.zip
```

Of geef een andere ZIP mee:

```bat
run_outsmart_discovery_analysis.bat imports\mijn_nieuwe_scrape.zip
```

## Output

De rapporten komen in `reports`:

- `outsmart_discovery_analysis_*.md`
- `outsmart_discovery_analysis_*.json`
- `outsmart_discovery_fields_*.csv`
- `outsmart_discovery_dropdowns_*.csv`
- `outsmart_discovery_options_*.csv`
- `outsmart_discovery_tables_*.csv`

Deze output bevat interne OutSmart-data en mag niet naar GitHub gepusht worden.
