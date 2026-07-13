# Crediti e licenze di terze parti

Il **codice** di "Cielo del Mese" è distribuito sotto licenza **MIT** (vedi
`LICENSE`). I **dati**, i **font** e le **effemeridi** inclusi o usati a runtime
hanno licenze proprie, elencate qui. Sono cose diverse: la licenza del codice
non è la licenza dei dati.

> **⚠️ FORMA BINARIA (D4).** Alcune di queste licenze (BSD-2, OFL) obbligano a
> riprodurre la nota di copyright anche **nella distribuzione binaria**. L'`.exe`
> prodotto in D4 è forma binaria: **questo file `CREDITI.md` (o il suo contenuto)
> deve essere impacchettato con l'eseguibile** — accanto ad esso e/o in una
> schermata "Informazioni". Non è un cavillo: è la condizione a cui il GAV ha il
> diritto di usare questi dati e font. Il lavoro di packaging si fa nel giro di D4.

---

## Dati stellari — d3-celestial · BSD 2-Clause

- **File:** `data/stars6.json`, `data/const_lines.json`
- **Autore:** Olaf Frohn — <https://github.com/ofrohn/d3-celestial>
- **Copyright:** © 2015, Olaf Frohn. All rights reserved.
- **Licenza:** BSD 2-Clause. Obbliga la nota di copyright in forma **sorgente e
  binaria**. Testo completo e dettagli in **`data/stelle_FONTE.md`**.

## Catalogo Messier — OpenNGC · CC-BY-SA-4.0

- **File:** `data/messier.json`
- **Autore:** Mattia Verga — <https://github.com/mattiaverga/OpenNGC>
- **Licenza:** Creative Commons Attribuzione-Condividi allo stesso modo 4.0
  (CC-BY-SA-4.0). Richiede **attribuzione** e **share-alike sul file di dati**
  (non sul codice che lo legge). Dettagli in **`data/messier_FONTE.md`**.

## Font del brand — SIL Open Font License 1.1

- **File:** `brand/fonts/BarlowSemiCondensed-*.ttf`,
  `brand/fonts/InstrumentSans-*.ttf`
- **Barlow Semi Condensed:** Jeremy Tribby (The Barlow Project Authors).
- **Instrument Sans:** Rhys Newey, Jordan Egstad (Instrument).
- **Licenza:** SIL Open Font License 1.1. Ridistribuibili nel repo e nell'`.exe`;
  la nota va inclusa nella distribuzione. Testi completi:
  `brand/fonts/OFL-Barlow.txt`, `brand/fonts/OFL-InstrumentSans.txt`.

## Effemeridi — DE421 · pubblico dominio

- **File:** `de421.bsp` (non nel repo: scaricato via `skyfield-data`, dipendenza).
- **Fonte:** Jet Propulsion Laboratory / NASA.
- **Licenza:** pubblico dominio (opera del governo USA). Nessun obbligo, citato
  per correttezza.

---

## Riepilogo

| Componente | Cosa | Licenza | Obbligo in forma binaria (.exe) |
|---|---|---|---|
| Codice | tutto `.py`, layout, temi | MIT | nota di copyright |
| `data/stars6.json`, `data/const_lines.json` | stelle, costellazioni | BSD-2 | **sì** — nota di copyright |
| `data/messier.json` | oggetti Messier | CC-BY-SA-4.0 | attribuzione (+ share-alike sul dato) |
| `brand/fonts/*.ttf` | font | OFL 1.1 | **sì** — nota di licenza |
| `de421.bsp` | effemeridi | pubblico dominio | nessuno |
