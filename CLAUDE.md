# CLAUDE.md — Cielo del Mese (Gruppo Astrofili Vicentini)

Questo file descrive **il progetto come è**, non come vorremmo fosse.
Se trovi una divergenza fra questo file e il codice, **il codice ha ragione** e
questo file va corretto. Segnalala invece di adattarti in silenzio.

> Il `README.md` è **storicamente inaffidabile** (ricognizione 2026-07-09: 8
> divergenze dal disco). Usa questo file come fonte di verità. Il README verrà
> riallineato; finché non lo è, non fidarti dei suoi comandi d'esempio.

---

## Cos'è

Genera il volantino **"Cielo del Mese"** per il Gruppo Astrofili Vicentini:
mappa del cielo notturno per un dato mese/anno/località, con fasi lunari,
pianeti e stelle nei loro colori reali. Output attuale: **SVG A4**, con
conversione PNG.

**Direzione (decisa 2026-07-09):** il valore dei prossimi mesi è la
**pubblicazione social** — post 1080×1080 e storie 1080×1920 generati ogni mese
dallo stesso motore. L'A4 resta, non è più il fuoco.

**Nessuna scadenza esterna.** Costruiamo le fondamenta prima di ristrutturare.

---

## Architettura reale (verificata, non dichiarata)

```
uvicorn ► app/main.py ─┐
python cielo.py ───────┼─► engine/generate.py ──► data/stars6.json
                       │   (motore puro: solo SVG) ├─► data/const_lines.json
                       │                            └─► de421.bsp (skyfield-data)
                       └─► render.py ──► resvg_py (SVG→PNG)
                       (leggono brand/palettes/*.json + brand/layouts/*.json)

CLI: python cielo.py --format a4|post [--png]   (compone motore + render, D1)

brand/formats.py ──► importato da NESSUNO (codice orfano)
```

| File | Ruolo |
|---|---|
| `engine/generate.py` | Il motore + compositore magro. Geometria/effemeridi → `SkyData` + disco; `generate()` cammina i blocchi di un file di layout. Libreria pura: **nessun CLI, non importa `render`**. |
| `cielo.py` | Il CLI (D1). Mappa i formati (`a4`/`post`) ai file di layout e **compone** motore + `render` (SVG, e PNG con `--png`). Vive fuori da `engine/`. |
| `brand/layouts/*.json` | La composizione come dati (canvas + blocchi). `a4.json` e `post_1080.json` esistono; altri formati sono altri file. |
| `app/main.py` | Web app FastAPI sottile: `/`, `/preview`, `/download`. |
| `render.py` | SVG→PNG via resvg. Usato dal CLI (`cielo.py`) **e** dalla web app. |
| `brand/palettes/*.json` | I temi. **Non** in `themes/` (il README mente). |
| `brand/formats.py` | Formati canvas. Orfano — ora **superato** da `brand/layouts/` (il canvas vive nel file). Candidato a rimozione. |
| `data/stars6.json` | 5044 stelle GeoJSON, tutte con `mag` e `bv`. |

---

## La regola delle case — dove vive un file

Il criterio **non** è "è roba di design?", è **"il motore lo legge a runtime?"**.

| Cartella | Cosa contiene | Criterio |
|---|---|---|
| `brand/` | palette, layout, font, logo | ciò che il **motore LEGGE a runtime** |
| `docs/`  | spec di design, mockup, riferimenti visivi | ciò che serve agli **UMANI** |
| `out/`   | SVG/PNG generati | ciò che il programma **PRODUCE**: usa e getta, **mai** in git |

Ragione operativa: `brand/` è esattamente ciò che verrà **impacchettato
nell'`.exe`** (D4). Un mockup nell'exe sarebbe peso morto; una palette no.

**Eccezione (documentazione degli asset):** un `LEGGIMI`/`README` che documenta
una cartella vive **dentro** quella cartella, anche se è per umani —
`brand/fonts/LEGGIMI.md` resta in `brand/fonts/`. La regola governa gli **asset**,
non la documentazione che li accompagna: staccare il LEGGIMI dai file che
descrive lo fa scollare al primo cambiamento.

---

## Invarianti — non violare senza chiedere

1. **Il motore non conosce la UI.** `engine/generate.py` non importa nulla di
   `app/` né di `render.py`.
2. **La palette non è mai hardcoded.** *(Sanato in #4b: `#cdd6ee` è ora il token
   di tema `moon_label`, letto con accesso diretto che spacca se manca.)*
3. **Orientamento della mappa:** N in alto, E a sinistra. Proiezione azimutale
   equidistante, zenit al centro. È identità visiva: non cambiarlo.
4. **Stile neon + glow:** identità del brand.
5. **Tutti i testi rivolti all'utente sono in italiano.** Anche gli errori.
6. **Il codice del motore è puro:** stesse coordinate + stessa data ⇒ stesso
   output. Nessuna I/O nascosta, nessun orologio di sistema.

---

## Decisioni architetturali prese

- **D1 — Il PNG si genera anche da CLI.** `render.py` resta un modulo separato
  che il CLI *compone*; non viene fuso nel motore. Un solo percorso d'uscita
  SVG→PNG, testabile headless. *(Fatto, giro #5d: `cielo.py` compone motore +
  `render`; `--png` produce il PNG accanto all'SVG, larghezza per formato.)*
- **D2 — Il tema è un contratto validato, non un dict libero.** Una palette a
  cui manca una chiave deve dare un errore leggibile, non un `KeyError`.
  Motivazione: stiamo per moltiplicare le palette. *(Da implementare.)*
- **D3 — Prima la rete di sicurezza, poi l'estrazione del layout social.** Il
  layout va estratto dal metodo `generate()` (oggi le coordinate A4 sono fuse
  nel metodo, `R5`). Quel refactor tocca la geometria: si fa **dopo** i test.
- **D4 — Distribuzione: repo pubblico su GitHub + `.exe` in Release.** I soci
  scaricano ed eseguono sul proprio PC. Niente NAS, niente server.
  Conseguenze vincolanti:
  - La build dell'`.exe` si fa in **GitHub Actions**, mai a mano. Ambiente
    pulito e riproducibile.
  - `de421.bsp` (da `skyfield-data`) e `resvg_py` (libreria nativa) vanno
    dichiarati esplicitamente al bundler e risolti a runtime: dentro un exe
    `__file__` non funziona come credi. È il punto in cui il packaging fallisce.
  - L'exe non firmato attiva **SmartScreen**. Va documentato nel README, o si
    compra un certificato.
  - **R4 (validazione input) diventa bloccante**: un HTTP 500 sul PC di un socio
    è "il programma non funziona", e non hai i log.
  - Prima di rendere pubblico il repo: `LICENSE` (senza, nessuno ha diritto di
    usarlo) e README riallineato alla realtà.
  - **Font del brand (decisi dal designer, 2026-07-12): Barlow Semi Condensed**
    (testata, titoli, etichette, cardinali) **+ Instrument Sans** (corpo: nomi,
    orari, note, date). Entrambi **SIL Open Font License**: ridistribuibili nel
    repo e nell'`.exe`. *Superano* la proposta precedente (Inter / Space
    Grotesk), che resta citata in `render.py` (`SANS = "Inter"`) e in
    `cielo-del-mese_struttura.md`: **da riallineare**. I `.ttf` non sono ancora
    nel repo — finché mancano, `resvg` ripiega sui font di sistema (R6).
- **D6 — Si mette mano all'input, mai all'output.** Un SVG generato non si
  ritocca a mano: la correzione muore alla rigenerazione successiva. Se ti
  ritrovi a voler cambiare sempre la stessa cosa, quella cosa era un parametro
  mancante. Eccezione unica e legittima: il ritocco irripetibile per un'occasione
  singola. *Claude Code non deve mai proporre di correggere l'output.*
- **D7 — Il disco è sigillato, la composizione è dati.**
  - Il **disco del cielo** (geometria, astronomia) è la parte fissa. Esce dal
    motore come frammento SVG auto-contenuto, in coordinate proprie: chi compone
    lo scala e lo posiziona, non lo ridisegna mai.
  - Il motore restituisce **disco + dati strutturati** (pianeti, fasi, data),
    distinti. Oggi i valori sono infilati direttamente nel testo dell'A4: vanno
    separati, altrimenti un file di layout non ha con cosa riempire i blocchi.
  - **Composizione, tema e contenuto sono file, non codice.** Titolo, posizioni,
    dimensioni, gerarchia tipografica: modificabili senza toccare Python.
  - `cielo-del-mese_struttura.md` è la spec di design. Non va abbassata al
    codice: è il codice che deve salire fino a lei.
  - **Niente browser headless** per comporre (HTML/CSS→PNG): impacchettare
    Chromium nell'`.exe` (D4) è insostenibile. Si resta su SVG + `resvg`.
- **D8 — L'app produce il file, non pubblica.** L'output è il PNG del post; la
  pubblicazione su Instagram è manuale, la fa Marco (o chi gestisce il profilo
  GAV). *Niente* pubblicazione automatica via API: richiederebbe account
  business, app Meta, token OAuth e revisione — incompatibile con un `.exe`
  offline distribuito ai soci (D4), che non può contenere le credenziali del
  profilo. Il confine dell'app è l'immagine pronta. Non proporre di superarlo.
- **D5 — Il golden ha una data di scadenza.** *(Corretto 2026-07-09: il
  confronto NON era byte-a-byte come credevamo. Il test legge in modalità testo,
  con newline universali: normalizzava i fine-riga su entrambi i lati. La mina
  era innescata — blob LF, output Windows CRLF — e non era esplosa per caso. Il
  `.gitattributes` ora impone LF ovunque.)* Regge finché gira solo
  su questa macchina. Su GitHub Actions (altro OS, altra numpy) l'ultima cifra
  dei `%.2f` cambierà e il test fallirà **senza che nulla sia rotto**.
  Va convertito a confronto con tolleranza numerica *quando si accende la CI*,
  non prima: adesso serve esatto, per sorvegliare il refactor del layout.
  Inoltre, per D7, andrà **ristretto al solo disco**: se sorveglia anche la
  composizione, fallirà a ogni ritocco estetico legittimo — e un test che è
  sempre rosso viene ignorato, che è il modo in cui una rete di sicurezza muore.

---

## Debito tecnico noto (ricognizione 2026-07-09)

Ordinato per rischio reale.

- **R1 — Nessun git.** Ogni modifica è irreversibile. *Prerequisito di tutto.*
- **R2 — Zero test su matematica non ispezionabile a occhio.** `altaz`,
  `project`, `sky_context` (tempo siderale), `bv2hex` producono risultati
  *plausibili* anche quando sono sbagliati. Una mappa storta di 5° non la nota
  nessuno. **È il rischio più grave del progetto.**
- **R3 — Contratto del tema implicito.** ~15 chiavi piatte + `bg[0..2]`,
  `disk[0..2]`, `status.{ok,info,warn,muted}`, `star_ramp`. Zero validazione.
- **R4 — Nessuna validazione input.** `month=13`, `lat=abc`, tema inesistente
  → HTTP 500. `fmt` non valido → 200 + JSON d'errore (incoerente).
- **R5 — RISOLTO (#5b).** Il layout A4 non è più fuso in `generate()`: vive in
  `brand/layouts/a4.json`. `generate()` è un compositore che cammina i blocchi.
  Il confine è: il **file** possiede cosa/dove/quale-dato; il **codice** possiede
  "come disegnare" per 5 primitive (background procedurale, disco sigillato,
  forma della fase lunare, colore da `bv2hex`, pallino da `status`) + la
  derivazione di presentazione (`MONTHS_IT`, `[:3]`, `{:.1f}`).
- **R6 — Font brand assenti.** `brand/fonts/` non contiene `.ttf`; l'SVG forza
  `Helvetica,Arial,sans-serif` in testa. L'identità tipografica **non** è
  applicata, benché il codice finga di sì.
- **R7 — Codice morto:** `brand/formats.py` (orfano), `render.py:DISPLAY`,
  `generate.py:NAKED_EYE`, param `obs` inutilizzato in `planet_table`, chiave
  `'Peg'` duplicata in `CONST_IT`.

**Mai verificato:** la correttezza astronomica dell'output. Sappiamo che il
codice produce un SVG. Non sappiamo che sia giusto.

---

## Metodo di lavoro

Tre ruoli. Un ciclo: `prompt → esecuzione → report → allineamento → prompt`.

- **Architetto** (Claude, altra sessione): scrive i prompt, decide, mantiene
  questo file.
- **Esecutore** (Claude Code, tu): esegue, **verifica**, riporta. Non decide
  l'architettura. Se un task richiede una scelta architetturale non coperta qui,
  **fermati e proponi 2-3 opzioni con il trade-off reale.**
- **Product owner** (Marco): arbitra le scelte irreversibili o estetiche.

### Regole di ingaggio — sempre attive

1. **Se non l'hai verificato, scrivi che non l'hai verificato.** Mai
   "dovrebbe funzionare". Distingui sempre *eseguito* da *dedotto*.
2. **Contesta le istruzioni sbagliate o ambigue** invece di eseguirle.
   Un'istruzione contraddittoria va segnalata, non aggirata in silenzio.
3. **Non compiacere.** Un report che dice "tutto a posto" quando non lo è costa
   più di una verità scomoda.
4. **Non allargare lo scope.** Se noti un bug fuori dal task, **riportalo, non
   correggerlo.** Le correzioni opportunistiche rendono i diff illeggibili.
5. **Un commit per unità di lavoro logica**, messaggio in italiano.
6. Se ritratti una tua affermazione precedente, **dillo esplicitamente.**

### Formato del report di fine task

- **Fatto** — cosa è cambiato, file per file.
- **Verificato** — comandi eseguiti e loro **output reale**. Non parafrasato.
- **Non verificato** — e perché.
- **Sorprese** — cosa hai trovato che non ti aspettavi.
- **Decisioni per l'architetto** — dove hai dovuto scegliere, o dove ti sei
  fermato.

---

## Comandi (verificati su Windows/PowerShell, 2026-07-09)

```powershell
# NB: non esiste una .venv nel repo. Oggi gira sul Python globale (3.12.2),
# che ha già le dipendenze. Un venv + lockfile diventeranno utili al packaging
# (D4, giro #9), non prima. Per crearne uno ora, se lo vuoi isolato:
#   python -m venv .venv ; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# CLI (D1): A4 in SVG (default)
python cielo.py --year 2026 --month 8 --place Vicenza
# A4 in SVG + PNG (larghezza 1800)
python cielo.py --year 2026 --month 8 --place Vicenza --png
# post quadrato 1080 in SVG + PNG (larghezza 1080)
python cielo.py --year 2026 --month 8 --format post --png

# web app
python -m uvicorn app.main:app --reload --port 8000
```

Il tema di default è già `brand/palettes/osservatorio.json`: non passare
`--theme themes/...` (quel percorso non esiste).
