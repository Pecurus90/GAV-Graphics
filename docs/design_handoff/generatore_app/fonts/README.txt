FONT — GAV · Cielo del Mese
============================

Il post usa DUE famiglie, entrambe con licenza SIL Open Font License 1.1
(ridistribuibili nel repository e nell'.exe offline):

  1. Barlow Semi Condensed  — testata, titoli, etichette dei pannelli, cardinali N/E/S/O
  2. Instrument Sans        — corpo del testo: nomi pianeti, orari, note, date, sottotitolo, crediti

Pesi effettivamente usati negli SVG (metti almeno questi file):
  BarlowSemiCondensed-SemiBold.ttf   (600)  -> testata, etichette, cardinali
  BarlowSemiCondensed-ExtraBold.ttf  (800)  -> titolo "IL CIELO DI ..."
  InstrumentSans-Regular.ttf         (400)  -> note, sottotitolo
  InstrumentSans-Medium.ttf          (500)  -> orari
  InstrumentSans-SemiBold.ttf        (600)  -> nomi pianeti/stelle, numeri dei giorni

Come richiamarli in resvg:
  - Il TESTO negli SVG resta testo (mai outline): il motore lo riscrive ogni mese.
  - font-family negli <text> = "Barlow Semi Condensed" / "Instrument Sans".
  - Punta resvg alla cartella dei font (usvg options.fontdb load_fonts_dir /
    resvg-cli --use-font-file / --use-fonts-dir) così NON serve rete: gira offline.

DOVE PRENDERE I .TTF (OFL, download diretto dai repo ufficiali):
  Barlow Semi Condensed : https://github.com/jpt/barlow  (cartella fonts/ttf)
  Instrument Sans       : https://github.com/Instrument/instrument-sans (fonts/ttf)
  In alternativa Google Fonts -> "Get font" -> scarica lo ZIP con i .ttf.

NOTA: i .ttf binari non li ho potuti allegare da qui. Scaricali dai link OFL
sopra e mettili in questa cartella con i nomi indicati; i mockup li richiamano
gia' per nome.
