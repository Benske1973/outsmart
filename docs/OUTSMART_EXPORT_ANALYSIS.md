# OutSmart Export Analysis

Plaats lokale OutSmart CSV exports in:

```text
imports\outsmart\
```

Start daarna:

```bat
run_outsmart_export_analysis.bat
```

De analyse maakt lokaal rapporten in `reports/`:

- kolommen per CSV;
- records per debiteur;
- dropdownachtige waarden;
- statuswaarden;
- werknemers;
- klanten;
- gebouwen/objecten;
- adressen;
- eenheden/ruimtes;
- voorbeelden van adres + gebouw + eenheid.

Belangrijk voor cases zoals:

```text
Gebouw/adres: Scheldekenslaan 6-68
Eenheid/werkzone: Scheldekenslaan 58-68
```

Deze gegevens moeten apart zichtbaar worden zodat we leren waar OutSmart gebouw, adres en eenheid exact bewaart.
