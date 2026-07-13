# Handoff: App "Cielo del Mese" — barra laterale + progresso a fasi reali

## Overview
Interfaccia dell'applicazione desktop del **Gruppo Astrofili Vicentini** (GAV). L'app
genera il poster "Cielo del Mese" a partire da mese, luogo, formato e palette, e mostra
l'anteprima. Questo handoff copre **la revisione strutturale** dell'app:

1. **Barra laterale di navigazione** — l'app diventa un contenitore di più strumenti. Oggi
   esiste solo "Cielo del Mese"; la barra rende ovvio aggiungere strumenti futuri.
2. **Indicatore di generazione a quattro fasi reali** — sostituisce la vecchia barra che
   avanzava a tempo (finta). Le quattro fasi corrispondono a fasi vere del motore e vanno
   pilotate dal motore, non da un timer.

Restano invariati dal design precedente: pannello controlli (Quando / Dove / Formato /
Palette), stato iniziale, stato anteprima, stato errore, toast di salvataggio.

## About the Design Files
I file in questo bundle sono **riferimenti di design realizzati in HTML/CSS/JS** — un
prototipo che mostra aspetto e comportamento voluti, **non codice di produzione da copiare
così com'è**. Il compito è **ricreare questo design nell'ambiente del codebase esistente**
dell'app (l'app gira come `.exe` offline: probabilmente una webview locale, Electron/Tauri
o simile) usando i suoi pattern. Se non esiste ancora un ambiente, scegliere il framework
più adatto e implementarvi il design. Tutta la logica di generazione (astronomia, resvg,
salvataggio file) è del motore già esistente: qui si tratta solo di UI.

## Fidelity
**Alta fedeltà (hifi).** Colori, tipografia, spaziatura e stati sono definitivi. Ricreare
la UI in modo fedele. I valori esatti sono nella sezione Design Tokens.

## Vincolo trasversale — utenti
I soci del gruppo, alcuni over-70. Conseguenze di design **da rispettare**:
- Testi e bersagli grandi e leggibili. Le voci di navigazione hanno **parola + icona**, mai
  icona muta. Altezza bersaglio voce di nav ≥ 52px.
- Una funzione futura deve **sembrare futura, non rotta**: la voce disabilitata è visibile,
  spenta, con badge "Prossimamente" e cursore `not-allowed`. Non deve dare l'impressione che
  il programma sia guasto quando ci si clicca sopra.
- L'attesa deve **dire il vero**: l'indicatore mostra a che punto è davvero il motore.

---

## Screens / Views

### Struttura generale
```
┌─ titlebar (38px, finta barra finestra) ───────────────────────────┐
├──────────┬─────────────────────┬───────────────────────────────────┤
│  NAV     │   PANNELLO          │   PALCO (stage)                    │
│  224px   │   404px             │   flex:1                           │
│  fisso   │   scroll verticale  │   4 stati sovrapposti (uno attivo) │
└──────────┴─────────────────────┴───────────────────────────────────┘
```
`.app` è `display:flex; height:calc(100% - 38px)`. Tre colonne: nav fissa, pannello fisso, palco elastico.

---

### 1. Barra laterale (`nav`) — NUOVA
Contenitore verticale a sinistra, **larghezza fissa 224px**, `display:flex; flex-direction:column`.
Sfondo: `linear-gradient(180deg, rgba(5,7,15,.6), rgba(5,7,15,.28))`, bordo destro `1px solid var(--bordo)`.
Padding `22px 16px 20px`, `gap:6px`.

Contenuti dall'alto in basso:

**a) Marca (`nav-brand`)** — `display:flex; align-items:center; gap:12px; padding:2px 8px 20px`.
- Emblema `assets/logo-emblem.png`, 40×40px, `drop-shadow(0 3px 10px rgba(0,0,0,.5))`.
- Testo: "GAV" (Barlow Semi Condensed 800, 16px, colore `--t1`) + sottotitolo "ASTROFILI
  VICENTINI" (Barlow SC 600, 9.5px, `letter-spacing:.18em`, uppercase, colore `--t4`, margin-top 3px).

**b) Etichetta sezione (`nav-cap`)** — testo "STRUMENTI", Barlow SC 600, 10.5px,
`letter-spacing:.2em`, uppercase, colore `--t4`, padding `0 10px 8px`.

**c) Voce attiva — "Cielo del Mese"** (`.nav-item.on`)
- `display:flex; align-items:center; gap:13px; padding:14px 13px; border-radius:13px`.
- Sfondo `linear-gradient(180deg,rgba(228,172,74,.14),rgba(228,172,74,.04))`, bordo
  `1px solid rgba(228,172,74,.4)`, ombra `0 8px 22px rgba(0,0,0,.28)`.
- Icona 26×26 (SVG globo/mappa) colore `--oro`. Nome: Instrument Sans 600, 16px, colore `--t1`.
- `aria-current="page"`.

**d) Voce futura — "Pillole di astronomia"** (`.nav-item.soon`)
- Stesso layout della voce attiva ma trasparente, `cursor:not-allowed`, `disabled`, `aria-disabled="true"`.
- Icona + nome a `opacity:.5`. Nessun cambiamento all'hover.
- Sotto il nome, badge "PROSSIMAMENTE": Barlow SC 600, 9.5px, `letter-spacing:.12em`, uppercase, colore `--t4`, margin-top 3px.
- **Non progettare la pagina del secondo strumento.** La voce esiste solo per rendere ovvia
  l'estensione futura. Aggiungere uno strumento domani = una nuova `.nav-item` + una nuova
  vista nel palco.

**e) Piè (`nav-foot`)** — `margin-top:auto` (spinge in fondo), bordo superiore `1px solid var(--bordo)`,
padding `14px 10px 0`. Testo "Altri strumenti arriveranno qui." — Instrument Sans, 11.5px, `--t4`.

Stati voce nav:
- hover (solo voci abilitate): sfondo `rgba(150,170,215,.07)`, bordo `--bordo`.
- attiva: come sopra (d).

---

### 2. Pannello controlli (`panel`) — invariato, solo il logo cambia
404px, scroll verticale. Marca in alto: **ora usa `assets/logo-emblem.png`** (46×46) al posto
del vecchio `logo.png` che conteneva il testo "G.A.V.". Sezioni: Quando (select mese, stepper
anno, stepper ora), Dove (località + coordinate a scomparsa), Formato (5 thumbnail),
Palette (4 chip), bottone "Genera anteprima" (oro). Vedi il file HTML per i dettagli — non
toccati in questa revisione.

---

### 3. Stato "Generazione" (`s-generating`) — RIDISEGNATO
Card centrata (`gen-card`), `display:flex; flex-direction:column; align-items:center; gap:26px`.

**a) Orbita animata (`orbit`)** — invariata. 120×120, due anelli, due satelliti che ruotano
(`@keyframes spin`), nucleo oro con glow. Puramente decorativa ("il programma sta lavorando").

**b) Titolo** — "Sto disegnando il cielo…" Barlow SC 800, 26px, colore `--t1`.

**c) Lista fasi (`phases`)** — **il cuore della modifica.** `display:flex; flex-direction:column;
gap:2px; width:330px; text-align:left`. Quattro righe, una per fase reale del motore:

| # | Testo mostrato (italiano umano)                    | Fase reale del motore        |
|---|----------------------------------------------------|------------------------------|
| 1 | Calcolo dove sono stasera i pianeti e la Luna      | calcolo delle effemeridi     |
| 2 | Metto cinquemila stelle sulla mappa                | proiezione delle stelle      |
| 3 | Compongo il poster                                 | composizione del poster      |
| 4 | Disegno l'immagine finale                          | rendering dell'immagine      |

Ogni riga (`phase`): `display:flex; align-items:center; gap:14px; padding:11px 4px`.
- Pallino (`dot`) 26×26, `border-radius:50%`. Contiene tre elementi mutuamente esclusivi
  secondo lo stato della fase:
  - **in attesa (pending)**: bordo `1.6px solid var(--bordo-forte)`, sfondo `--superficie`;
    mostra il **numero** (Barlow SC 800, 13px, colore `--t4`).
  - **in corso (active)**: bordo `--oro`, sfondo `rgba(228,172,74,.1)`, alone
    `0 0 0 4px rgba(228,172,74,.1)`; mostra uno **spinner** (cerchietto 15px, `border-top:var(--oro)`,
    `@keyframes spin .7s linear infinite`).
  - **fatta (done)**: sfondo pieno `--oro`, bordo `--oro`; mostra il **check** ✓ (colore `#05070f`, 14px, 800).
- Nome fase (`nm`): Instrument Sans, 15.5px. Colore `--t4` (pending) → `--t1` 600 (active) → `--t2` (done).

**IMPORTANTE — comportamento onesto.**
- Nel **mockup** le fasi avanzano con un `setInterval` (720ms/fase) solo per mostrarle.
- Nell'**app reale**: il motore chiama `setPhase(i)` all'**inizio** di ogni fase, quando ha
  davvero finito la precedente. Se il rendering dura sei secondi, la fase 4 resta "in corso"
  (spinner) finché non è finita davvero — non raggiunge il 100% per poi bloccarsi. È il punto
  di tutta la modifica: l'indicatore deve dire il vero.
- Rimossa la vecchia `gen-bar` (barra continua a percentuali finte) e la riga `gen-step` singola.

Al termine (`allPhasesDone()`), tutte e quattro le fasi passano a "done", breve pausa (~420ms),
poi si passa allo stato "Anteprima".

---

### 4. Stati "Iniziale", "Anteprima", "Errore" — invariati
Vedi il file HTML. Solo nota: nulla è cambiato qui in questa revisione.

---

## Interactions & Behavior
- **Nav "Cielo del Mese"**: attiva, `aria-current="page"`. In un'app multi-strumento cambierebbe
  la vista del palco; oggi è l'unica.
- **Nav "Pillole di astronomia"**: `disabled`, nessun handler, non risponde al click (per
  design — deve leggersi come futura).
- **Genera anteprima**: valida (anno 1900–2050), poi `runGenerate()` → stato Generazione →
  fasi → Anteprima. Se validazione fallisce → stato Errore.
- **`setPhase(i)`**: marca `done` le fasi `< i`, `active` la fase `i`, `pending` le successive.
- **`allPhasesDone()`**: tutte a `done`.
- Switcher stati (`#switch` in basso): **solo per la revisione del design**, da rimuovere in
  produzione.

## State Management
- `state`: mese, anno, ora, loc, fmt, fmtName, ar, pal, palName, dot (invariato).
- Stato UI del palco: uno tra `initial | generating | preview | error`.
- Stato generazione: indice fase corrente (0–3), pilotato dal motore in produzione.
- Nav: quale strumento è attivo (oggi sempre "cielo-del-mese").

## Design Tokens
Colori (CSS custom properties su `:root`):
- `--notte:#05070f` · `--blunotte:#0a1222` · `--bluprof:#12203a`
- `--superficie:#0e1626` · `--superficie2:#131d31`
- `--bordo:rgba(150,170,215,.14)` · `--bordo-forte:rgba(150,170,215,.26)`
- `--oro:#e4ac4a` · `--oro-chiaro:#f0c274` · `--petrolio:#004f6d` · `--neon:#45c8ff`
- Testo: `--t1:#eef2fb` · `--t2:#b9c4dc` · `--t3:#8e9bb8` · `--t4:#6a768f`
- Stati: `--warn:#f0b45a` · `--danger:#f08a6a` · `--ok:#6fe0a0`

Tipografia:
- Display: `'Barlow Semi Condensed'` (pesi 600, 800) — marca, titoli, etichette, badge.
- Corpo: `'Instrument Sans'` (pesi 400, 500, 600) — nomi voci, note, testo.

Raggi: nav-item 13px · dot fase 50% (cerchio). Ombre: nav attiva `0 8px 22px rgba(0,0,0,.28)`.
Nav: larghezza 224px, gap voci 6px, padding voce `14px 13px`, gap icona-testo 13px.
Fasi: larghezza lista 330px, dot 26px, gap riga 14px, padding riga `11px 4px`.

## Assets
- `assets/logo-emblem.png` — emblema GAV **senza testo**, ritagliato quadrato, 256px. Generato
  da `logo-trim.png`. **Sostituire** con l'emblema ufficiale ottimizzato (~11KB) quando disponibile.
  Il vecchio `logo.png` conteneva il testo "G.A.V. — Gruppo Astrofili Vicentini": non usarlo qui.
- `assets/preview-sample.png` — immagine di esempio dell'anteprima poster (segnaposto: in
  produzione è il PNG generato dal motore).
- Font: Barlow Semi Condensed + Instrument Sans (OFL). Vedi `fonts/README.txt` per pesi, nomi
  file e link ai repo ufficiali. Caricati localmente via `@font-face`, nessuna rete.

## Files
- `Generatore Cielo del Mese.html` — il prototipo completo (HTML+CSS+JS inline, offline, tutti
  gli stati). File di riferimento principale.
- `fonts/README.txt` — istruzioni font.
- `assets/` — logo emblema, immagine di anteprima di esempio.
