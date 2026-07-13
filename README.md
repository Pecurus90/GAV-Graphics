# Cielo del Mese — Gruppo Astrofili Vicentini

Genera il volantino **"Cielo del Mese"**: una mappa del cielo notturno per un dato
**mese, anno e località**, con **fasi lunari**, **pianeti** e **stelle nei loro
colori reali**, più una seconda pagina di **profondo cielo** (oggetti del catalogo
di Messier). Output: **SVG** (stampa) e **PNG** (social), generati dallo stesso
motore. I colori arrivano da una **palette a token**, intercambiabile senza
toccare il codice.

> Fonte di verità del progetto: **`CLAUDE.md`**. Questo README descrive l'uso;
> le decisioni architetturali e lo stato reale stanno lì.

---

## Installazione

Richiede **Python 3.12+**. Le dipendenze sono in `requirements.txt` (l'effemeride
planetaria `de421.bsp` arriva dal pacchetto `skyfield-data`, nessun download a
runtime).

```bash
pip install -r requirements.txt
```

Un ambiente virtuale è opzionale ma consigliato:

```bash
python -m venv .venv
# Windows PowerShell:  .\.venv\Scripts\Activate.ps1
# Linux/macOS:         source .venv/bin/activate
pip install -r requirements.txt
```

## Uso da riga di comando (CLI)

Il punto d'ingresso è **`cielo.py`**. Formato e palette si scelgono **per nome**
(i nomi validi sono i file in `brand/layouts/` e `brand/palettes/`).

```bash
# A4 in SVG (default)
python cielo.py --year 2026 --month 8 --place Vicenza

# A4 in SVG + PNG
python cielo.py --year 2026 --month 8 --place Vicenza --png

# Post social quadrato 1080 (pagina 1) in SVG + PNG
python cielo.py --year 2026 --month 8 --format post --png

# Pagina 2: profondo cielo (oggetti Messier)
python cielo.py --year 2026 --month 8 --format profondo --png

# Un design social con una palette diversa
python cielo.py --year 2026 --month 8 --format dashboard --palette notte-blu --png
```

L'output finisce in `out/` (cartella usa-e-getta, non versionata).

### Formati disponibili (`--format`)

Scoperti dai file in `brand/layouts/`:

- **`a4`** — il volantino A4 (default).
- **`post`** — post quadrato 1080×1080 (pagina 1: costellazioni, Luna, pianeti).
- **`profondo`** — pagina 2 quadrata: profondo cielo, oggetti Messier.
- **`dashboard`**, **`editorial`**, **`rail`** — tre design social alternativi.

### Palette disponibili (`--palette`, default `osservatorio`)

Scoperte dai file in `brand/palettes/`:

- **`osservatorio`** (default), **`notte-blu`**, **`petrolio`**, **`luce-rossa`**.

## Web app

Web app FastAPI sottile (form → anteprima → download):

```bash
python -m uvicorn app.main:app --reload --port 8000
# poi apri http://localhost:8000
```

## Test

```bash
python -m pytest -q
```

## Licenza

- **Il codice è MIT** (vedi `LICENSE`).
- **I dati hanno licenze proprie** — non è la stessa cosa, ed è l'errore tipico
  da non fare:
  - `data/stars6.json`, `data/const_lines.json` → **BSD 2-Clause** (d3-celestial,
    Olaf Frohn) — vedi `data/stelle_FONTE.md`;
  - `data/messier.json` → **CC-BY-SA-4.0** (OpenNGC, Mattia Verga) — vedi
    `data/messier_FONTE.md`;
  - `brand/fonts/*.ttf` → **SIL Open Font License 1.1**.

  Tutti i crediti in **`CREDITI.md`**.

## Nota sulla distribuzione (D4)

La distribuzione prevista è un **`.exe`** in una Release di GitHub. L'eseguibile
**non firmato** farà scattare **SmartScreen** su Windows ("PC protetto"):
è normale, si procede da *Ulteriori informazioni → Esegui comunque*, oppure il
GAV acquista un certificato di firma. Il packaging (e l'inclusione di `CREDITI.md`
accanto all'`.exe`, richiesta dalle licenze BSD-2/OFL) è lavoro del giro D4.
