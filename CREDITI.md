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

- **File:** `brand/fonts/SpaceGrotesk-*.ttf`, `brand/fonts/WorkSans-*.ttf`
- **Space Grotesk:** Copyright 2020 The Space Grotesk Project Authors
  (Florian Karsten) — https://github.com/floriankarsten/space-grotesk
- **Work Sans:** Copyright 2019 The Work Sans Project Authors
  (Wei Huang) — https://github.com/weiweihuanghuang/Work-Sans
- **Licenza:** SIL Open Font License 1.1. Ridistribuibili nel repo e nel
  pacchetto; la nota va inclusa nella distribuzione. Testi completi:
  `brand/fonts/OFL-SpaceGrotesk.txt`, `brand/fonts/OFL-WorkSans.txt`.

> *Fino al 2026-09-02 il brand usava **Barlow Semi Condensed** (Jeremy Tribby) e
> **Instrument Sans** (Rhys Newey, Jordan Egstad), anch'essi OFL 1.1. Sostituiti
> dai font prescritti dal manuale d'identità del GAV; i loro file non sono più
> distribuiti, quindi la nota di licenza non è più dovuta.*

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
