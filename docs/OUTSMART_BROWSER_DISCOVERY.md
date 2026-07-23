# OutSmart Browser Discovery

Doel: OutSmart-schermen, velden, tabellen en dropdownwaarden inventariseren.

## Installatie op werk-pc

```bat
install_workpc_requirements.bat
```

Dit installeert:

- pywin32
- playwright
- chromium browser voor discovery

## Start

```bat
run_outsmart_browser_discovery.bat
```

Log zelf in. Navigeer naar een relevant scherm. Druk in het terminalvenster op ENTER om het huidige scherm te scannen.

## Belangrijk

De tool is bedoeld als discovery en klikt geen bekende gevaarlijke acties aan zoals:

- Opslaan
- Verwijderen
- Aanmaken
- Versturen
- Factureren
- Status aanpassen
- Uploaden

Scan zeker:

- nieuwe werkbon;
- bestaande werkbon bekijken;
- bestaande werkbon bewerken;
- project kiezen;
- medewerker dropdown;
- type werkzaamheden;
- workflowstatus;
- werkbonstatus;
- formulieren;
- object/gebouw selectors;
- klant/relatie selectors.

## Output

Lokale output staat in:

```text
outsmart_exports\
```

Niet uploaden naar GitHub als er klantdata zichtbaar is.
