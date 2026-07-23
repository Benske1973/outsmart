# OutSmart Werkbonvelden - Huidige Kennis

We kennen de hoofdstructuur uit eerdere scrapes, maar nog niet alle dropdownopties en klant-specifieke vrije velden.

## Algemeen

- Opdrachtnummer
- Ordernummer / jobnummer
- Projectnummer
- Project
- Projectactiviteit
- Extern projectnummer
- Extern werkbonnummer
- Externe referentie / bestelbon / PO
- Type werkzaamheden
- Workflowstatus
- Werkbonstatus
- Werknemer
- Uitvoerdatum start/einde
- Duur
- Betaalmethode

## Klant, gebouw, adres en eenheid

Voor deze fase moeten we heel precies leren wat OutSmart waar bewaart:

- Debiteurnummer
- Klantnaam
- Factuurrelatie
- Werkadres
- Huisnummer of huisnummerbereik
- Postcode
- Plaats
- Gebouwcode
- Gebouwnaam
- Object
- Eenheid
- Ruimtecode
- Ruimtetype
- Invulling
- Geolocatie

Belangrijk voorbeeld:

- Gebouw/adres kan `Scheldekenslaan 6-68` zijn.
- De concrete eenheid/werkzone kan `Scheldekenslaan 58-68` zijn.
- Deze twee mogen niet samengevoegd worden. We moeten uit bestaande werkbonnen leren of OutSmart dit bewaart als adres, object, gebouw, eenheid of vrije velden.

## Werkinhoud

- Korte omschrijving
- Omschrijving
- Memo / interne omschrijving
- Commentaar

## Stad Gent referenties

- Werkorder
- Bestelbon / PO
- Taaknummer
- Raamcontract
- SLA
- Contactpersoon ter plaatse
- Telefoon contactpersoon
- Verantwoordelijke persoon
- Telefoon verantwoordelijke
- Sitecode
- Gebouwcode
- Bouwdeel
- Verdieping
- Ruimtecode
- Ruimtetype
- Invulling
- LEZ
- Asbestinfo

## Extra modules

- Formulieren, zoals LMRA
- Objecten
- Materieel
- Materialen
- Werkperiodes/uren
- Foto's
- Bestanden
- Notities
- Klantcommunicatie
- Logboek

## Nog te ontdekken

- Alle dropdownwaarden per debiteur
- Projecten per debiteur
- Gebouwen/objecten per debiteur
- Projectactiviteiten
- Vrije velden
- Exacte opslag van gebouw versus eenheid
