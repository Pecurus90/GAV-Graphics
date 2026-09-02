# Font del brand GAV

I file dei font (`.ttf`) usati dal renderer (`resvg`) per disegnare i testi dei
poster, e **impacchettati nell'app** (D17). Servono i file locali perche' l'app
deve funzionare offline, senza dipendere dai font installati sul PC del socio.

Le due famiglie sono quelle del **manuale d'identita' visiva** del GAV, sez.4
(`docs/GAV-design-system.pdf`). Entrambe **SIL Open Font License 1.1**: si
ridistribuiscono nel repository e nel pacchetto, citando la licenza (i due file
`OFL-*.txt` qui accanto).

## Le due famiglie

- **Space Grotesk** — *display*: titoli, numeri, etichette. Spaziatura -0.02em.
  https://github.com/floriankarsten/space-grotesk (`fonts/ttf/static`)
- **Work Sans** — *testo corrente*: note, sottotitoli, date, crediti.
  https://github.com/weiweihuanghuang/Work-Sans (`fonts/ttf`)

Presi in **istanza statica**, non come variable font: `resvg` con gli statici e'
verificato (2026-09-02), coi variabili non lo e' — e non e' una cosa da scoprire
a meta' di un giro.

## I file presenti

```
SpaceGrotesk-Medium.ttf   (500)
SpaceGrotesk-Bold.ttf     (700)
WorkSans-Regular.ttf      (400)
WorkSans-Medium.ttf       (500)
WorkSans-SemiBold.ttf     (600)
```

**I layout chiedono anche il peso 800** (il titolo). Space Grotesk statico arriva
a 700: `resvg` prende il piu' vicino, quindi il titolo e' Bold. Verificato
rendendo: sta benissimo. Se un giorno servisse un 800 vero, non esiste in questa
famiglia — si cambia il peso nel layout, non si cerca un file che non c'e'.

## Come funziona

- Il **testo** negli SVG resta testo (mai convertito in tracciati): il motore lo
  riscrive ogni mese.
- Tutti i layout dichiarano **un solo** `font_family` sul canvas:
  `"Space Grotesk, Work Sans, Helvetica, Arial, sans-serif"`. Essendo una lista,
  **vince il primo che esiste**: oggi il poster e' quindi *interamente in Space
  Grotesk*, e Work Sans e' un fallback che non scatta mai.
  **Non e' una svista di oggi: era gia' cosi' con Barlow/Instrument.** La coppia
  display+corpo del manuale sara' davvero implementata solo quando il compositore
  accettera' un `font_family` per BLOCCO. Vedi R17.
- `render.py` carica questa cartella (`_font_dirs()`), quindi `resvg` risolve i
  font **senza rete**: offline e dentro il pacchetto.

> **Storico, e vale la pena saperlo:** la primissima proposta (2026) indicava
> *Space Grotesk* + *Inter*. Fu **superata** dalla consegna del designer (Barlow
> Semi Condensed + Instrument Sans, luglio 2026). Il manuale d'identita' del GAV
> ha poi prescritto **Space Grotesk + Work Sans**, e il 2026-09-02 Marco ha
> deciso che *il manuale ha ragione*. Barlow e Instrument sono stati rimossi.
> Il cerchio si e' chiuso sulla proposta iniziale, per la strada piu' lunga.
