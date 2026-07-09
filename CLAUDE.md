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
uvicorn ──► app/main.py ──┬──► engine/generate.py ──► data/stars6.json
                          │                         ├─► data/const_lines.json
                          │                         └─► de421.bsp (skyfield-data)
                          └──► render.py ──► resvg_py
                          (legge brand/palettes/*.json)

CLI: python engine/generate.py   (NON passa da render.py → solo SVG)

brand/formats.py ──► importato da NESSUNO (codice orfano)
```

| File | Ruolo |
|---|---|
| `engine/generate.py` | Il motore. Geometria, effemeridi, disegno SVG. Il cuore. |
| `app/main.py` | Web app FastAPI sottile: `/`, `/preview`, `/download`. |
| `render.py` | SVG→PNG via resvg. Usato **solo** dalla web app. |
| `brand/palettes/*.json` | I temi. **Non** in `themes/` (il README mente). |
| `brand/formats.py` | Formati canvas. Orfano: nessuno lo importa. |
| `data/stars6.json` | 5044 stelle GeoJSON, tutte con `mag` e `bv`. |

---

## Invarianti — non violare senza chiedere

1. **Il motore non conosce la UI.** `engine/generate.py` non importa nulla di
   `app/` né di `render.py`.
2. **La palette non è mai hardcoded.** *(Oggi è violato: `generate.py:285` ha un
   `fill="#cdd6ee"` nei nomi delle fasi lunari. È debito noto, da sanare.)*
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
  SVG→PNG, testabile headless. *(Da implementare.)*
- **D2 — Il tema è un contratto validato, non un dict libero.** Una palette a
  cui manca una chiave deve dare un errore leggibile, non un `KeyError`.
  Motivazione: stiamo per moltiplicare le palette. *(Da implementare.)*
- **D3 — Prima la rete di sicurezza, poi l'estrazione del layout social.** Il
  layout va estratto dal metodo `generate()` (oggi le coordinate A4 sono fuse
  nel metodo, `R5`). Quel refactor tocca la geometria: si fa **dopo** i test.

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
- **R5 — Layout A4 fuso in `generate()`.** Coordinate hardcoded (`py=960`,
  `px0=470`, `ly=1235`…). È **il** blocco all'output social.
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
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# motore (solo SVG)
python engine/generate.py --year 2026 --month 8 --place Vicenza --out cielo.svg

# web app
python -m uvicorn app.main:app --reload --port 8000
```

Il tema di default è già `brand/palettes/osservatorio.json`: non passare
`--theme themes/...` (quel percorso non esiste).
