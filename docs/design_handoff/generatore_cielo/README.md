# Handoff: Generatore "Cielo del Mese" — GAV

## Overview
Pagina dell'applicazione desktop del **Gruppo Astrofili Vicentini**. Il socio scarica un
`.exe` da GitHub, fa doppio clic e si apre una finestra del browser con questa pagina.
Da qui genera il **"Cielo del Mese"**: il poster astronomico che il gruppo pubblica su
Instagram e stampa per la bacheca.

Il flusso è: l'utente sceglie **mese/anno**, **località**, **formato** e **palette**, preme
**Genera anteprima**, attende un paio di secondi la generazione, vede l'anteprima e
**salva** il file (PNG per i social, SVG per la stampa).

**Utenza reale:** appassionati di astronomia, NON di informatica. Diversi soci hanno
settant'anni. Priorità assolute: bersagli grandi, testo mai piccolo, linguaggio umano in
italiano, nessun gergo tecnico. "Se non è ovvio, non lo usano."

## About the Design Files
Il file `Generatore Cielo del Mese.html` in questo bundle è un **riferimento di design**
— un prototipo HTML/CSS/JS che mostra aspetto e comportamento voluti, **non** codice di
produzione da copiare così com'è. Il compito è **ricreare questo design nell'ambiente
reale dell'applicazione**.

⚠️ **Vincolo di prodotto che condiziona le scelte tecniche:** l'app gira **offline** dentro
un `.exe` sul PC del socio, senza internet. Quindi:
- **Niente CDN, niente Google Fonts, niente risorse dalla rete.** Tutto locale.
- **Niente framework / niente build step** (no React, Tailwind, npm…): il file finisce
  impacchettato nell'eseguibile. HTML + CSS + JavaScript semplice scritto a mano.
- I font del brand vanno inclusi come file locali (vedi § Assets).

Per questi motivi il prototipo **è già** vanilla HTML/CSS/JS e **può essere usato quasi
direttamente** come base della UI, sostituendo le parti simulate (vedi § "Parti simulate")
con le chiamate al motore reale. Se invece si reimplementa in un layer di templating/UI
già presente nel progetto, mantenere gli stessi vincoli offline.

## Fidelity
**High-fidelity (hifi).** Colori, tipografia, spaziature, stati e micro-interazioni sono
definitivi. Ricreare la UI in modo fedele. Tutti i valori esatti sono nella sezione
§ Design Tokens.

---

## Screens / Views
La pagina è una **finestra desktop a due colonne** a tutta altezza:
- Barra titolo finta in alto (38px) — semaforo macOS + nome app.
- **Pannello controlli** a sinistra: larghezza fissa **404px**, scrollabile in verticale.
- **Palco anteprima** a destra: riempie lo spazio restante, centra il contenuto.

Il palco ospita **quattro stati mutuamente esclusivi** (un solo `.state.active` alla volta).

### Pannello controlli (sinistra)
`background: linear-gradient(180deg, rgba(19,29,49,.55), rgba(10,18,34,.35))`,
bordo destro `1px solid rgba(150,170,215,.14)`, `padding: 26px 26px 30px`.

1. **Brand** — logo 46×46px + occhiello oro "GRUPPO ASTROFILI VICENTINI" (Barlow SC 600,
   11px, letter-spacing .24em, maiuscolo) + titolo "Cielo del Mese" (Barlow SC 800, 27px).
   Sottotitolo grigio (Instrument 12.5px, `#6a768f`).
2. **Sezione "Quando"** — intestazione di sezione (occhiello + linea oro sfumata).
   - **Mese**: menù a tendina (`<select class="sel-field">`) a tutta larghezza, con nome per
     esteso ("08 · Agosto") — scelta più leggibile e a prova di errore.
   - Sotto, in griglia 1fr/1fr, due **stepper** `−`/`+` (pulsanti 46px, campo Barlow SC 800
     23px, tabular-nums; niente più didascalia in "ovale" sotto il numero):
     - **Anno**: digitabile, clamp 1900..2050.
     - **Ora**: readonly, passo 30 minuti, wrap 00:00↔23:30, default **23:00** (l'orario
       tipico del poster).
3. **Sezione "Dove"** — input testo "Località" (default `Vicenza`). Toggle testuale
   "› Inserisci coordinate precise" che apre (max-height transition) due input
   Latitudine/Longitudine (default `45.5455` / `11.5354`).
4. **Sezione "Formato"** — griglia 2 colonne con i **4 formati quadrati** (Dashboard,
   Editoriale, Colonna, Post) come card verticali uguali (mini-diagramma SVG in alto, nome
   Barlow SC 800 15px, tag 11px), più il **Volantino A4** come 5ª card a tutta larghezza in
   fondo, con la stessa impaginazione verticale (thumb con proporzione verticale) — è l'unico
   formato di stampa, distinto ma coerente. Selezionata → bordo oro + glow + spunta `✓`.
   Vedi § Formati.
5. **Sezione "Palette"** — **una colonna** di 4 pastiglie grandi (flex row: swatch a sinistra
   106×62px + testo a destra). Lo swatch mostra il mini-cielo di quella palette: gradiente
   reale + disco + stelline + pallino "neon" del colore giusto — così le 4 palette si
   distinguono a colpo d'occhio. Selezionata → bordo oro + glow + spunta. La card **Luce
   Rossa** ha un badge sempre visibile "◑ si guarda stando al telescopio". Vedi § Palette.
6. **Bottone "Genera anteprima"** — pieno oro, largo tutto il pannello, Barlow SC 800 19px,
   `border-radius:13px`, ombra oro. Disabilitato durante la generazione (testo →
   "Generazione in corso…", opacità .5).

### Stato 1 · INIZIALE (`#s-initial`)
Palco vuoto invitante. Cornice tratteggiata in proporzione poster (aspect 1/1, dashed
`rgba(150,170,215,.26)`) contenente: icona telescopio SVG (88px), titolo "L'anteprima
comparirà qui" (Barlow SC 800, 24px, `#b9c4dc`), testo guida (14.5px, `#6a768f`, max 340px)
e freccia oro "← Comincia da 'Quando'".

### Stato 2 · GENERAZIONE (`#s-generating`)
Non è istantanea (calcolo effemeridi + migliaia di stelle, ~2s). **Deve rassicurare** per
evitare i tripli click. Contenuto centrato:
- **Orbita animata**: due anelli + due satelliti che ruotano (`@keyframes spin`, 1.5s e 2.4s
  in reverse) attorno a un nucleo oro con glow.
- Titolo "Sto disegnando il cielo…" (Barlow SC 800, 26px).
- **Riga di passo** che avanza (`#gen-step`): "Calcolo le effemeridi del mese" →
  "Individuo stelle, pianeti e fasi lunari" → "Disegno la volta celeste" → "Compongo il
  poster".
- **Barra di avanzamento** oro (larghezza animata per passo: 8→22→48→74→92→100%).
- Frase rassicurante: "…Ci vogliono un paio di secondi: **è normale, aspetta senza
  chiudere**."

### Stato 3 · ANTEPRIMA PRONTA (`#s-preview`)
- **Barra di riepilogo** (pill): "Agosto 2026" · "📍 Vicenza" · "Dashboard" · pallino colore
  palette + "Osservatorio". Pill: `background rgba(19,29,49,.7)`, bordo, `border-radius:99px`.
- **Cornice poster** (`#poster-frame`): `border-radius:20px`, ombra `0 30px 70px rgba(0,0,0,.6)`,
  `aspect-ratio:1/1` per i formati quadrati, `1/1.414` quando è A4 (classe `.a4`), altezza
  `min(100%,760px)`, immagine `object-fit:cover`.
- **Riga salvataggi**: bottone oro **"Salva PNG · per i social"**, bottone ghost
  **"Salva SVG · per la stampa"**, link testo **"↻ Rigenera"**.

### Stato 4 · ERRORE (`#s-error`)
Messaggi del motore mostrati in modo **umano**, non come riga di codice rossa. Card
centrata su fondo rosso tenue (`linear-gradient(180deg,rgba(46,20,16,.7),rgba(24,10,10,.55))`,
bordo `rgba(240,138,106,.4)`):
- Icona `!` in cerchio.
- Titolo "Controlla un dato" (Barlow SC 800, 24px, `#f7d9cc`).
- **Messaggio esatto** in box (`#err-msg`, 16.5px, `#f6c6b3`), es.
  `Mese fuori intervallo: 13. Ammessi 1-12.` / `Anno fuori intervallo: 3000. Ammessi 1900-2050.`
- Suggerimento contestuale (`#err-hint`) che spiega il campo giusto.
- Bottone "Torna alle impostazioni".
- In parallelo, lo **stepper colpevole** nel pannello prende la classe `.bad` (bordo rosso).

### Toast salvataggio (`#toast`)
Comparsa in basso al centro del palco alla pressione di Salva: spunta verde + "File salvato
`cielo_2026-08_vicenza_dashboard.png`". Auto-scompare dopo 2.6s.

### Switcher stati (`#switch`) — SOLO REVISIONE
Pillola in basso al centro con "Stati: Iniziale · Generazione · Anteprima · Errore" per
navigare le schermate durante la revisione del design. **RIMUOVERE nell'app di
produzione** (o tenere dietro un flag di debug).

---

## Formati (5) — assi indipendenti dalla palette (5 × 4 = 20 combinazioni)
| chiave (`data-fmt`) | nome UI | proporzione | descrizione |
|---|---|---|---|
| `dashboard` | Dashboard | 1:1 | quadrato · mappa + pannelli (default) |
| `editorial` | Editoriale | 1:1 | quadrato · mappa grande |
| `rail` | Colonna | 1:1 | quadrato · mappa + lista laterale |
| `post` | Post | 1:1 | quadrato semplice |
| `a4` | Volantino A4 | 1:1.414 verticale | stampabile, per la bacheca |

Ogni miniatura è un **piccolo SVG** che schematizza il layout (disco della volta + pannelli/
colonna/righe). Ricrearli o sostituirli con anteprime reali del motore se disponibili.

## Palette (4)
| chiave (`data-pal`) | nome UI | gradiente swatch | neon (`data-dot`) |
|---|---|---|---|
| `osservatorio` | Osservatorio | `linear-gradient(160deg,#14243f,#0a1424 55%,#05070f)` | `#6db8ff` |
| `notte-blu` | Notte Blu | `linear-gradient(160deg,#12305a,#0a1c3a 55%,#050b18)` | `#45c8ff` |
| `petrolio` | Petrolio | `linear-gradient(160deg,#0a5e7e,#023649 55%,#011e2b)` | `#39e0d0` |
| `luce-rossa` | Luce Rossa | `linear-gradient(160deg,#2a0e12,#160608 55%,#0a0304)` | `#ff5a52` |

**Luce Rossa** è rossa perché il rosso non rovina la visione notturna (si può guardare
stando al telescopio): la nota `#pal-note` deve renderlo esplicito quando è selezionata.
I valori completi delle palette (per il motore) sono in `engine/palettes/*.json` nel
progetto sorgente (`notte-blu`, `petrolio`, `luce-rossa`); `osservatorio` è il default
classico del poster.

---

## Interactions & Behavior
- **Stepper +/−**: `anno` clampa a 1900..2050 (digitabile); `ora` passo 30 min con wrap
  00:00↔23:30. Il **mese** è un menù a tendina (sempre valido). Ogni modifica pulisce `.bad`.
- **Toggle coordinate**: apre/chiude i campi lat/lon con transizione `max-height`, e cambia
  la label in "Nascondi coordinate".
- **Selezione formato/palette**: click → togglia `.sel`, aggiorna lo stato interno.
- **Genera** (`#genera`):
  1. `clearBad()` → `validate()`.
  2. Se errore → riempi `#err-msg` con il messaggio del motore, `#err-hint` contestuale,
     marca lo stepper `.bad`, mostra stato ERRORE.
  3. Se valido → disabilita il bottone, mostra GENERAZIONE, avanza i passi ogni 620ms
     (`setInterval`), poi (dopo ~380ms extra) riempi i metadati e mostra ANTEPRIMA.
- **Rigenera** (`#regen`): rilancia la generazione.
- **Torna alle impostazioni** (`#err-back`): torna a INIZIALE.
- **Salva PNG/SVG**: mostra il toast col nome file calcolato
  (`cielo_<anno>-<mese2cifre>_<localita-slug>_<fmt>.png|svg`).

### Regole di validazione (messaggi identici al motore)
Il **mese** è un menù, quindi non può essere fuori intervallo; la validazione runtime
controlla l'**anno**. I messaggi del mese restano documentati/riutilizzabili se in futuro il
campo tornasse libero, e lo switcher li mostra come esempio nello stato Errore.
```
anno vuoto/NaN  → 'Anno non valido: "<x>". Inserisci un numero da 1900 a 2050.'
anno <1900/>2050→ 'Anno fuori intervallo: <a>. Ammessi 1900-2050.'
(mese, se input libero) → 'Mese fuori intervallo: <m>. Ammessi 1-12.'
```

## State Management
Stato applicativo minimo (oggetto `state`):
`{ mese, anno, ora, loc, fmt, fmtName, ar, pal, palName, dot }`.
Stati UI del palco: `initial | generating | preview | error` (uno solo attivo).
Transizioni: initial → (Genera, valido) → generating → preview; qualunque → (Genera,
invalido) → error → (Torna) → initial.

### Parti SIMULATE nel prototipo (da sostituire col motore reale)
- **Generazione**: nel prototipo è un `setInterval` a passi finti. Sostituire con la
  chiamata reale al motore (calcolo effemeridi + rendering) — idealmente **asincrona / in
  worker** così la UI non si blocca; aggiornare `#gen-step`/barra dai progressi reali.
- **Anteprima**: mostra un'immagine segnaposto (`assets/preview-sample.png`). Sostituire con
  l'immagine/SVG effettivamente prodotto.
- **Salvataggio**: mostra solo un toast. Agganciare alla scrittura file reale (PNG social /
  SVG stampa) e usare il nome file calcolato.
- **Switcher stati**: rimuovere in produzione.

## Design Tokens
**Colori**
- Notte `#05070f` · Blu notte `#0a1222` · Blu profondo `#12203a`
- Superficie `#0e1626` · Superficie2 `#131d31`
- Bordo `rgba(150,170,215,.14)` · Bordo forte `rgba(150,170,215,.26)`
- Oro `#e4ac4a` · Oro chiaro (hover) `#f0c274` · Petrolio `#004f6d` · Neon azzurro `#45c8ff`
- Testo: T1 `#eef2fb` · T2 `#b9c4dc` · T3 `#8e9bb8` · T4 `#6a768f`
- Stato: warn `#f0b45a` · danger `#f08a6a` · ok `#6fe0a0`
- Sfondo body: `radial-gradient(135% 75% at 50% -12%, #12203a 0%, #0a1222 42%, #05070f 100%)`

**Tipografia**
- Display: **Barlow Semi Condensed** (600, 800) — testata, titoli, occhielli, cardinali.
- Testo: **Instrument Sans** (400, 500, 600) — corpo, dati, didascalie.
- Occhielli: maiuscolo, letter-spacing .2–.24em, colore oro.

**Raggi / ombre**
- Raggi: input/stepper 12px · card/frame 20px · miniature 14px · pill 99px.
- Ombra poster `0 30px 70px rgba(0,0,0,.6)` · ombra bottone oro `0 12px 30px rgba(228,172,74,.22)`.

**Spaziature**: pannello padding 26px; gap sezioni 26px; gap griglie 11px; stepper button 46px.

**Timing**: transizioni UI .13–.15s; generazione ~620ms/passo (×4) + 380ms; toast 2600ms.

## Assets
- `assets/logo.png` — logo GAV (luna + telescopio). Marchio dell'associazione.
- `assets/preview-sample.png` — poster campione (dashboard, Agosto 2026, Vicenza), usato solo
  come **segnaposto** dell'anteprima. Da sostituire con l'output reale del motore.
- `fonts/README.txt` — istruzioni per i font. **I .ttf del brand NON sono inclusi** (binari):
  scaricare da repo OFL (Barlow Semi Condensed, Instrument Sans) e metterli in `fonts/` con
  i nomi indicati. Il CSS li richiama via `@font-face` locale (già presente nell'HTML). Le
  emoji usate (📍, ↻, ✓) sono glifi di sistema; se servono in un ambiente senza emoji,
  sostituirle con icone SVG.

## Files
- `Generatore Cielo del Mese.html` — prototipo completo (HTML + CSS + JS inline). Fonte di
  verità del design; contiene tutti i valori e la logica dei quattro stati.
