# Font del brand GAV

Qui vanno i file dei font (`.ttf`/`.otf`) che verranno **impacchettati nell'app**
e usati dal renderer (`resvg`) per disegnare i testi dei post. Servono i file
locali perche' l'app deve funzionare offline e dentro l'`.exe`, senza dipendere
dai font installati sul PC.

Entrambe le famiglie hanno licenza **SIL Open Font License 1.1**: si possono
ridistribuire nel repository e nell'`.exe` offline, citando la licenza.

## Le due famiglie (scelta del designer, usata dai mockup)

- **Barlow Semi Condensed** — testata, titoli, etichette dei pannelli,
  cardinali N/E/S/O. Geometrico, condensato: rende bene le testate.
  https://github.com/jpt/barlow (cartella `fonts/ttf`) —
  in alternativa https://fonts.google.com/specimen/Barlow+Semi+Condensed
- **Instrument Sans** — corpo del testo: nomi pianeti, orari, note, date,
  sottotitolo, crediti. Sans-serif pulito, ottimo ai piccoli corpi.
  https://github.com/Instrument/instrument-sans (cartella `fonts/ttf`) —
  in alternativa https://fonts.google.com/specimen/Instrument+Sans

## Pesi effettivamente usati negli SVG (metti almeno questi file)

```
brand/fonts/BarlowSemiCondensed-SemiBold.ttf    (600)  -> testata, etichette, cardinali
brand/fonts/BarlowSemiCondensed-ExtraBold.ttf   (800)  -> titolo "IL CIELO DI ..."
brand/fonts/InstrumentSans-Regular.ttf          (400)  -> note, sottotitolo
brand/fonts/InstrumentSans-Medium.ttf           (500)  -> orari
brand/fonts/InstrumentSans-SemiBold.ttf         (600)  -> nomi pianeti/stelle, numeri dei giorni
```

## Come funziona

- Il **testo** negli SVG resta testo (mai convertito in tracciati/outline): il
  motore lo riscrive ogni mese.
- Nei template i `font-family` sono `"Barlow Semi Condensed"` e
  `"Instrument Sans"`. I mockup li richiamano gia' per nome.
- Il renderer (`render.py`) carica automaticamente questa cartella
  (`font_dirs` → `brand/fonts/`): puntato qui, `resvg` risolve i font **senza
  rete**, quindi gira offline e dentro l'`.exe`.

> **NOTA — i `.ttf` binari non sono ancora nel repo.** Scaricali dai link OFL
> sopra e mettili in questa cartella con i nomi indicati. Finche' mancano, il
> renderer ripiega sui font di sistema (R6).

> **Storico:** una prima proposta indicava *Space Grotesk* (titoli) + *Inter*
> (testo). E' stata **superata** dalla consegna del designer (Barlow Semi
> Condensed + Instrument Sans), che e' quella usata dai mockup. `render.py`
> tiene ancora `SANS = "Inter"` come default hardcoded: e' un residuo da
> riallineare (fuori dallo scope di #6a).
