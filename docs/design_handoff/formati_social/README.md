# Handoff — Nuovi formati del post quadrato (Parata · Cornice · Zenit)

*(Designer via claude.ai/design, 2026-07-15, file `Formati Social - Nuovi.dc.html`.
Consegna in risposta a `BRIEF-formati-social.md`. **Tre concept consegnati e
piaciuti** (Parata, Cornice, Zenit). **DECISIONE RIMANDATA** *(Marco,
2026-07-15)*: quali implementare e **al posto di cosa** (editoriale/colonna) si
valuta **dopo, col designer** — non è congelato. Questo handoff è il riferimento
per quando ci si torna; il giro di implementazione NON è ancora partito.)*

**Attenzione:** a differenza dell'A4, questi concept sono un **componente vivo** del
canvas del designer, non SVG estraibile. L'esecutore li costruisce dalle
descrizioni sotto + i blocchi esistenti, iterando coi render (l'architetto
confronta col concept). Tutti i blocchi citati **esistono già** (verificato).

## 1a — Parata *(costo zero, tutto esistente)*

- **Come:** quattro corsie orizzontali piene — testata · la **parata dei pianeti**
  in fila (banda a tutta larghezza) · il disco al centro affiancato dalla **legenda
  stellare a due colonne** (colori a sinistra, temperatura a destra) · la **striscia
  lunare 1→31** a piè di pagina.
- **Perché diverso:** unica lettura orizzontale; i pianeti sono una banda, non una
  lista verticale; la legenda incornicia il disco riempiendo i fianchi (niente zone
  morte).
- **Blocchi:** `planet_parade` (dall'A4) + `moon_calendar` cols=31 + `swatches` con
  `label2` (2 colonne, già supportato) + disco. **Nessun elemento nuovo.**

## 1b — Cornice *(costo zero, tutto esistente)*

- **Come:** disco dentro una **cornice neon arrotondata** nei due terzi alti
  (testata in alto a sinistra), sotto una **base a tre pannelli uguali**: pianeti ·
  fasi lunari · colori delle stelle.
- **Perché diverso:** dà al disco la cornice forte che all'editoriale mancava;
  sostituisce le due scatole gemelle con un ritmo a tre. Verticale, simmetrico, con
  più tensione.
- **Blocchi:** `moon_calendar` in **griglia 8×4** (cols=8, già supportato) +
  `planet_panel` compatto + `swatches` + disco. La cornice è **stile** (un rect
  arrotondato con lo stroke neon), nessun grafico nuovo.

## 1c — Zenit *(fattibile, MA il "vetro" diventa translucido — vedi caveat)*

- **Come:** il disco riempie l'intera tela come **sfondo** (esce dai bordi); sopra,
  pannelli negli angoli (HUD): testata in alto a sinistra, pianeti in alto a destra,
  colori in basso a sinistra, striscia lunare in una fascia in fondo coi contatti.
- **Perché diverso:** il più immersivo/da-feed; il disco è protagonista assoluto,
  opposto alla griglia del dashboard.
- **CAVEAT (deciso con Marco):** il **frosted-glass (blur dello sfondo dietro i
  pannelli) NON esiste in resvg** — `backdrop-filter` è roba da browser. I pannelli
  diventano **translucidi colorati** (fill semitrasparente sul disco), non sfocati.
  Ancora bello, ma non il vetro del mockup. *Non* si investe codice per finta-
  sfocatura (va contro il disco sigillato, D7).
- **Disco a tutto campo:** OK — è scala + posizione del frammento sigillato (D7 lo
  permette), non un ridisegno.
- **Blocchi:** `moon_calendar` cols=31 + `planet_panel`/lista + `swatches` + disco
  scalato a tutto campo + pannelli con fill translucido.
