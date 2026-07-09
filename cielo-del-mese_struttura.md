# Cielo del Mese — Struttura grafica (specifica di replica)

Blueprint per replicare **uno a uno** il volantino in Claude Design.
Tutte le coordinate sono nel sistema del canvas originale; Claude Design può
scalarle mantenendo le proporzioni.

---

## 0. Nota importante (leggere prima)

Il volantino ha due nature diverse:

- **Cornice e impaginazione** (header, disco, pannelli, legenda, tipografia,
  colori): **100% replicabile** graficamente. È tutto qui sotto.
- **Contenuto interno del disco** (campo stellare + linee delle costellazioni):
  **non è disegnabile a mano** — nasce dalla proiezione di coordinate astronomiche
  reali. Claude Design **non** deve ridisegnare le stelle: va **inserita la mappa
  esportata** (PNG/SVG dal generatore) dentro la cornice circolare descritta al §4.
  Quello che Claude Design replica del disco è la *cornice* (sfondo, bordo neon,
  anelli, punti cardinali), non i puntini interni.

---

## 1. Canvas & griglia

| Parametro | Valore |
|---|---|
| Formato | A4 verticale |
| Canvas | 900 × 1273 px (rapporto 1 : 1.414) |
| Margine sicuro | 46 px sui lati |
| Sfondo pagina | gradiente radiale `--space-800 #0c1330` (centro, 38% dall'alto) → `#070c1e` (55%) → `--space-950 #04060f` (bordo) |
| Micro-stelle di sfondo | ~240 puntini `#aab8e0`, raggio 0.3–1.0 px, opacità 0.15–0.5, sparsi su tutta la pagina |

### Bande verticali

| Banda | Y (px) | Contenuto |
|---|---|---|
| Testata | 0 – 120 | titoli |
| Disco cielo | 116 – 884 | mappa circolare |
| Pannelli | 940 – 1055 | fasi lunari (sx) + pianeti (dx) |
| Legenda / piè | 1195 – 1240 | legenda colori + crediti |

---

## 2. Token colore

Usare i token della palette "Osservatorio" (già forniti). Richiamo dei principali:
`--neon #45c8ff` · `--gold #ffd27a` · `--text #eef3ff` · `--text-3 #8b98b8`
· sfondi `--space-*` · stelle `--star-hot/…/-red` · funzionali `--ok/--info/--warn/--muted`.

---

## 3. Tipografia

Font unico sans-serif (nel prototipo Helvetica/Arial; per il brand sostituire con
la coppia scelta). Scala usata:

| Ruolo | Size | Peso | Colore | Note |
|---|---|---|---|---|
| Nome associazione | 21 | bold | `--gold` | letter-spacing 3, centrato |
| Titolo mese | 30 | bold | `--text` | letter-spacing 1.5, centrato |
| Sottotitolo | 12.5 | regular | `--text-3` | centrato |
| Titolo sezione | 16 | bold | `--text` | letter-spacing 1 |
| Etichette costellazioni | 12.5 | regular | `--label #7fb6d8` | opacità 0.82 |
| Stelle guida (label) | 11.5 | regular | `--text` | |
| Punti cardinali | 19 | bold | `--cardinal #9fb0d8` | |
| Pianeta (nome) | 13.5 | bold | `--text` | |
| Orari / dati | 12.5 | regular | `#aeb9d6` | |
| Note e legenda | 11.5 | regular | `--text-3` | |
| Crediti (piè) | 10.5 | regular | `--text-4 #5b678a` | |

---

## 4. Testata (Y 0–120)

Tre righe centrate su X = 450:
1. `GRUPPO ASTROFILI VICENTINI` — Y 52 — `--gold`, 21 bold, spacing 3
2. `IL CIELO DI <MESE> <ANNO>` — Y 86 — `--text`, 30 bold, spacing 1.5
3. Sottotitolo — Y 108 — `--text-3`, 12.5 — es. "Cielo visibile dal Nord Italia · Vicenza · valido ~15 luglio, ore 23:00"

---

## 5. Disco cielo (cornice replicabile)

Centro **CX 450, CY 500** · raggio **R 384**.

Ordine di disegno (dal basso):
1. **Disco**: riempimento gradiente radiale `#0a1533` (centro) → `#060c22` (80%) → `#0a1236` (bordo).
2. **Bordo sottile**: stroke `--border #2b3f73`, spessore 1.5.
3. **Anello neon**: stroke `--neon`, spessore 2.4, opacità 0.55, con **glow** (blur ~3.4).
4. **Anelli di altezza** (tratteggiati): a due raggi — 256 px (alt 30°) e 128 px (alt 60°); stroke `--grid #2a3a66`, spessore 0.8, dash "2 5", opacità 0.7.
5. **[MAPPA INSERITA QUI]** — l'immagine esportata (stelle + linee) va clippata al cerchio di raggio R−1.
6. **Punti cardinali** appena fuori dal bordo (raggio R+22 = 406): `N` in alto, `E` a **sinistra**, `S` in basso, `O` a destra. `--cardinal`, 19 bold, centrati.

> Orientamento della mappa: zenit al centro, orizzonte al bordo, **Nord in alto**,
> **Est a sinistra** (vista "a naso in su", non da terra).

### Stile del contenuto interno (per riferimento, lo produce il generatore)
- Linee costellazioni: `--neon`, spessore ~1.15, opacità 0.9, estremità arrotondate, con glow.
- Stelle: colore reale per indice B‑V (da `--star-hot` blu a `--star-red` rosso); raggio proporzionale alla luminosità; alone morbido per le più brillanti.
- Stelle guida (Vega, Deneb, Altair, Arturo, Antares, Spica): alone del loro colore reale + etichetta.

---

## 6. Pannello FASI LUNARI (in basso a sinistra)

- Titolo `FASI LUNARI` — X 60, Y 960 — `--text`, 16 bold.
- **4 dischi lunari** in fila: raggio 24, primo centro X 90, passo 200, centri Y 1018.
  - Disco base: riempimento `--space-700 #0d1734`, stroke `#3a4d7d` 1.
  - Illuminazione color `#e6ecfb`:
    - **Luna Nuova** → disco scuro (nessuna).
    - **Primo Quarto** → semicerchio **destro** illuminato.
    - **Luna Piena** → disco pieno.
    - **Ultimo Quarto** → semicerchio **sinistro** illuminato.
- Sotto ogni disco: nome fase (`#cdd6ee`, 12.5) + data (`--text-3`, 12), centrati.

---

## 7. Pannello PIANETI (in basso a destra)

- Titolo `PIANETI · alzata / tramonto (<mese>)` — X 470, Y 960 — `--text`, 16 bold.
- Righe da Y 994, passo verticale 38. Struttura di ogni riga:
  - **Pallino stato** (X 476, raggio 4) col codice colore visibilità.
  - **Nome** pianeta (X 490, 13.5 bold, `--text`).
  - **Orari** `alzata / tramonto` (X 585, 12.5, `#aeb9d6`).
  - **Nota** sotto (X 490, +15, 11.5, `--text-3`).
- **Codice colore visibilità** (onesto):
  - `--ok #5fd08a` = osservabile a occhio nudo
  - `--info #4bc3ff` = solo telescopio/binocolo
  - `--warn #e8b45f` = difficile / molto basso
  - `--muted #6b7690` = non osservabile (vicino al Sole)

---

## 8. Legenda & piè (Y 1195–1240)

- Riga divisoria a Y 1195: X 60 → 840, stroke `--divider #243055`.
- "Colore stelle = temperatura reale:" (X 60, Y 1219, `--text-3`, 11.5) seguita da 5 pallini con etichetta: calde `--star-hot` · bianche `--star-white` · gialle `--star-yellow` · arancioni `--star-orange` · fredde/rosse `--star-red` (passo 100 px).
- Campione linea neon + "linee = figure delle costellazioni" (Y 1235).
- Crediti allineati a destra (X 840, Y 1239, `--text-4`, 10.5): "Effemeridi calcolate per Vicenza (45.5°N, 11.5°E)".

---

## 9. Effetti (riproduzione del "neon sfumato")

L'effetto chiave non è un colore ma **neon `#45c8ff` + glow su fondo scuro**.
In ambiente web/design:
```
elemento-neon { filter: drop-shadow(0 0 6px #45c8ff); }
testo-neon    { text-shadow: 0 0 10px #45c8ff, 0 0 22px #45c8ff66; }
```
Nel prototipo è un blur gaussiano (stdDeviation ~2–3.4) su linee e anello.

---

## 10. Elementi dinamici (cambiano ogni mese)

Da lasciare come "campi" nel template: titolo mese/anno · data e ora di validità ·
immagine della mappa · 4 fasi lunari (tipo + data) · righe pianeti (nome, orari,
stato, nota). Tutto il resto è fisso.
