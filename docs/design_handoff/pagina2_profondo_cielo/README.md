# Handoff: "Cielo del Mese" — PAGINA 2 (Profondo cielo / catalogo Messier)

## Overview
Seconda immagine del **carosello Instagram 1080×1080** del Gruppo Astrofili Vicentini
("Cielo del Mese"). La pagina 1 mostra costellazioni, Luna e pianeti; **questa pagina 2**
mostra gli **oggetti del profondo cielo del catalogo Messier**. Le due escono insieme e
devono sembrare **sorelle**: stesso poster scuro, stesso disco neon, stessa testata oro col
logo a sinistra, stessi font, stesse icone social nel piè di pagina.

Il poster è prodotto dal motore che **disegna in SVG e converte in PNG con resvg**, e
**rigenera tutto ogni mese** da dati astronomici reali. Questo bundle è il **riferimento di
design** della pagina 2 (aspetto e impaginazione), non codice di produzione.

## About the Design Files
Il file `Cielo del Mese - Pagina 2.html` è un **riferimento di design creato in HTML/SVG**:
un mockup che mostra look e impaginazione voluti, **non** codice da spedire così com'è. Il
compito è **ricreare questo SVG nel generatore reale** (lo stesso motore che produce la
pagina 1), riusando i suoi pattern: template SVG con testo vivo + palette a token +
conversione resvg. I **testi e i simboli sono d'esempio**: il motore li ricalcola ogni mese.

Il file contiene DUE frame affiancati: **PAG 1** (esistente, come riferimento di
coerenza) e **PAG 2** (l'oggetto di questo handoff). Implementare solo la pagina 2; la
pagina 1 serve a verificare che restino sorelle.

## Fidelity
**High-fidelity (hifi).** Colori, tipografia, coordinate, dimensioni e convenzioni dei
simboli sono definitivi. Tutti i valori esatti sono nella sezione § Design Tokens e
§ Layout. Vincoli assoluti dal renderer:

- **Il testo deve restare TESTO** (`<text>`/`<tspan>`), mai convertito in tracciati: il
  motore lo riscrive ogni mese.
- **Niente** effetti raster, texture, blend mode esotici, HTML/CSS nel poster. **Sì** a
  gradienti, glow (sfocatura/opacità dei radialGradient) e opacità.
- **Ogni elemento è annotato con `data-token="<nome>"`**: il motore sostituisce i colori
  leggendo la palette attiva. Nel mockup i colori sono letterali (palette *osservatorio*)
  ma il valore autorevole è il token, non l'hex.

## Canvas & griglia
- **viewBox `0 0 1080 1080`**, quadrato. Margini utili: contenuto tra x≈56 e x≈1024.
- Struttura verticale: **testata** (y 40–192) · **corpo** (disco a sinistra + elenco a
  destra, y 192–~910) · **legenda** (y ~906–965) · **piè di pagina** (y 1002–1038).

## Screens / Views

### Unica vista: poster 1080×1080

#### 1. Testata (identica alla pagina 1)
- **Logo** `assets/logo.png` a **x=44, y=40, 94×94** (`data-token="logo"`).
- **Occhiello** "GRUPPO ASTROFILI VICENTINI" — x=156, baseline y=76. Barlow Semi Condensed
  600, 15px, letter-spacing 3.4px, colore `data-token="gold"`.
- **Titolo** "IL CIELO DI AGOSTO 2026" — x=154, baseline y=126. Barlow SC 800, 50px,
  letter-spacing .5px, `data-token="text"`.
- **Sottotitolo** "Profondo cielo · gli oggetti del catalogo Messier · Vicenza · valido ~15
  agosto, ore 23:00" — x=156, y=160. Instrument Sans 400, 15px, `data-token="text3"`.
  (È il sottotitolo che distingue la pagina 2 dalla 1.)
- **Divisore** linea x 56→1024 a y=192, `data-token="divider"`.

#### 2. Disco (grande, a sinistra) — SEGNAPOSTO
Il motore disegna il disco reale ogni mese; nel mockup è un **cerchio segnaposto**. I tre
numeri che il motore deve rispettare:

> **centro X = 300 · Y = 572 · raggio = 246**

- Glow azzurro: `<circle r=264 fill="url(#glowNA)">`.
- Disco: `<circle r=246 fill="url(#diskA)" stroke="#2a4a7a" stroke-width=2>` →
  `data-token="disk/border"`.
- Griglia interna: due cerchi concentrici a r≈162 e r≈81 + croce orizzontale/verticale a
  tutto diametro, `data-token="grid"`.
- Clip `diskClip` = cerchio r=244 (tutto il contenuto stellare è ritagliato dentro).
- **Cardinali** N (alto), S (basso), **E a destra, O a sinistra** — Barlow SC 600, 21px,
  `data-token="cardinal"`. ⚠️ Verificare che l'orientamento E/O combaci con la pagina 1
  attuale (la carta del cielo è specchiata rispetto a una mappa terrestre).

**Contenuto del disco (tutto d'esempio, generato dal motore):**
- **Linee delle costellazioni**: `<polyline>` neon `data-token="neon"`, opacità ~0.4, con
  piccoli vertici-stella (`data-token="text"`, r≈1.4). La pagina 2 tiene **molte meno
  stelle** della pagina 1: solo le linee + le stelle che le compongono, per far spazio ai
  simboli.
- **Simboli Messier**: da **43 (novembre) a 87 (luglio)** oggetti sopra l'orizzonte,
  disegnati come simboli. Solo **~15** portano l'etichetta "Mxx" (Instrument Sans 600, 11px,
  `data-token="gold"`); gli altri sono solo simbolo. **Rischio principale della pagina: 87
  simboli possono diventare una grattugia.** Gestire la densità con dimensione piccola +
  poche etichette (NON con colori diversi).
- **Ammasso della Vergine (caso speciale):** ~16 galassie Messier in un fazzoletto di cielo.
  Sulla mappa → **grappolo fitto di ellissi quasi sovrapposte** con **UNA SOLA etichetta**
  "Ammasso della Vergine" (+ nota "16 galassie · una sola etichetta") appoggiata al grappolo
  con una sottile linea di richiamo. In elenco → **una sola riga**.

#### 3. Elenco oggetti (colonna a destra)
Riquadro logico x≈584→1024. Il **cuore leggibile** della pagina: **15 righe**.
- Intestazione "OGGETTI MESSIER · MEGLIO PIAZZATI" (Barlow SC 600, 13px, `data-token="label"`,
  letter-spacing 2px) + nota "dati d'esempio" a destra (`data-token="text4"`) + divisore.
- Ogni riga (passo verticale **46px**, prima riga baseline y≈258):
  - **Simbolo** dell'oggetto (stesso set di forme, vedi § Simboli) a sinistra (x≈592).
  - **Nome** (x≈614): `<tspan data-token="gold">Mxx</tspan> — Nome comune`. Instrument Sans
    600, 14px, `data-token="text"`. Se non c'è nome comune, solo "Mxx".
  - **Riga secondaria** (x≈614, +16px): "Tipo · Costellazione". Instrument Sans 11.5px,
    `data-token="text3"`.
  - **Strumento** a destra: icona binocolo/telescopio (`data-token="text3"`) + parola
    "Bino./Tele." (`data-token="text2"`, 11.5px). Colonna obbligatoria per onestà: da un
    cielo suburbano quasi nessun oggetto si vede a occhio nudo.
  - Divisore sottile tra le righe (`data-token="divider"`, opacità 0.5).
- Le 15 righe d'esempio (tipo · costellazione · strumento):
  `M13 Amm. di Ercole` globulare·Ercole·binocolo · `M92` globulare·Ercole·binocolo ·
  `M57 Neb. Anello` planetaria·Lira·telescopio · `M27 Neb. Manubrio` planetaria·Volpetta·binocolo ·
  `M8 Neb. Laguna` diffusa·Sagittario·binocolo · `M20 Neb. Trifida` diffusa·Sagittario·telescopio ·
  `M11 Anatra Selvatica` aperto·Scudo·binocolo · `M22` globulare·Sagittario·binocolo ·
  `M6 Amm. Farfalla` aperto·Scorpione·binocolo · `M7 Amm. di Tolomeo` aperto·Scorpione·binocolo ·
  `M31 Andromeda` galassia·Andromeda·binocolo · `M81 Gal. di Bode` galassia·Orsa Maggiore·telescopio ·
  `M15` globulare·Pegaso·binocolo · `M2` globulare·Acquario·binocolo ·
  `Ammasso della Vergine` 16 galassie·Vergine·telescopio.

> ⚠️ **Regola di legibilità (già discussa col committente):** 15 righe su un 1080 sono il
> massimo. Se per farle stare servisse rimpicciolire il testo sotto la leggibilità su
> telefono, **NON rimpicciolire: tagliare righe.**

#### 4. Legenda (in basso, a tutta larghezza)
Senza, la mappa è indecifrabile. Divisore a y=920 + occhiello "LEGENDA · CONVENZIONE DEGLI
ATLANTI STELLARI" (`data-token="text4"`). Riga orizzontale con i **5 simboli + nome**
(`data-token="text"`, 12.5px). A destra la **chiave strumenti**: icona binocolo + "Binocolo"
e icona telescopio + "Telescopio" (`data-token="text2"`).

#### 5. Piè di pagina (identico alla pagina 1)
Divisore a y=1002. Icone social + testo (`data-token="text3"`): Instagram
`@astrofilivicentini`, Facebook `astrofilivicentini`, mail `info@astrofilivicentini.it`, e a
destra "GAV · Vicenza" (`data-token="text4"`).

## Simboli del profondo cielo — NON INVENTARLI
Convenzione universale degli atlanti stellari (ogni astrofilo la legge a colpo d'occhio). Si
può curare tratto/peso/dimensione, **mai la forma**. Tutti resi con `fill="none"`, stroke
del token colore, stroke-width ~1.15 sul disco.

| Oggetto | Forma | Resa SVG |
|---|---|---|
| Galassia | ellisse | `<ellipse>` (con `rotate`) |
| Ammasso aperto | cerchio tratteggiato | `<circle stroke-dasharray="2 2">` |
| Ammasso globulare | cerchio con croce | `<circle>` + 2 linee (croce) |
| Nebulosa diffusa | quadrato | `<rect>` |
| Nebulosa planetaria | cerchio con quattro punte | `<circle>` + 4 tacche |

Quantità reali nel catalogo: **40 galassie, 29 globulari, 26 ammassi aperti, 7 nebulose
diffuse, 4 planetarie.**

### Decisione sui token dei simboli
I simboli riusano il token esistente **`gold`** — **nessun token nuovo richiesto** (costo
zero). La densità sul disco si controlla con dimensione + poche etichette, non col colore.
*Alternativa non adottata:* colori per tipo di oggetto → richiederebbe token nuovi in tutte
e quattro le palette + validatore.

## Interactions & Behavior
Nessuna interattività: è un **poster statico** esportato in PNG (social) / SVG (stampa). Il
solo "comportamento" è la rigenerazione mensile dei dati da parte del motore.

## State Management
Nessuno stato UI. Input del motore (per la pagina): mese/anno, località, **palette attiva**
(uno dei 4 token-set), elenco calcolato di oggetti Messier sopra l'orizzonte con
tipo/costellazione/strumento e coordinate sul disco.

## Design Tokens
Palette a **nomi fissi** letti dal motore; la pagina deve funzionare con tutte e quattro
(*osservatorio, notte-blu, petrolio, luce-rossa*). Nel poster **non scrivere colori**:
annotare ogni elemento con `data-token`. Token usati in questa pagina (hex = palette
*osservatorio*, solo di riferimento):

- `bg` sfondo pagina (gradiente 3 stop, `#12203a → #0a1222 → #05070f`)
- `disk` sfondo interno disco (radiale `#0e1a33 → #0a1428 → #060c18`)
- `neon` `#45c8ff` — linee delle costellazioni
- `gold` `#e4ac4a` — testata, etichette "Mxx", **simboli del profondo cielo**
- `border` `#2a4a7a` — bordo del disco · `border2` bordi secondari
- `grid` `#1e3358` — cerchi/croce della griglia
- `divider` `#1c2c4d` — linee divisorie
- `panel` riempimento pannelli
- `bgstar` `#5f7099` — micro-stelle dello sfondo pagina
- `text` `#eef2fb` (T1) · `text2` `#b9c4dc` (T2) · `text3` `#8e9bb8` (T3) · `text4` `#6a768f` (T4)
- `label` `#a9b8d6` — occhielli/etichette · `cardinal` `#7f93c0` — N/E/S/O
- (token di pagina 1 non usati qui: `moon_lit, moon_label, status*, star_ramp, planet_colors`)

**Tipografia** (già nel progetto, **non cambiarli**):
- **Barlow Semi Condensed** (600/800) — testata, titoli, occhielli, cardinali, etichette.
- **Instrument Sans** (400/500/600) — corpo: nomi, tipi, note.

**Gradienti/effetti**: 2 linearGradient/radialGradient per sfondo+disco, 2 radialGradient di
glow (azzurro `glowNA`, oro `glowGA`). Nessun filtro raster.

## Assets
- `assets/logo.png` — logo GAV (marchio dell'associazione), in testata.
- Icone social (Instagram/Facebook/mail) e strumenti (binocolo/telescopio): **SVG inline**,
  nessun file esterno.

## Files
- `Cielo del Mese - Pagina 2.html` — mockup con i due frame (PAG 1 riferimento + **PAG 2**).
  L'SVG della pagina 2 è il secondo `<svg>` del file; contiene tutte le coordinate e i
  `data-token`.
