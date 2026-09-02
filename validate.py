#!/usr/bin/env python3
"""
Validazione degli input e CONTRATTO DEL TEMA — condivisi da CLI e web app.

Perche' un modulo a se':
- NON nel motore (invariante #1: il motore non conosce la UI; validare l'input
  dell'utente e' una preoccupazione del confine, non della geometria);
- NON duplicato fra cielo.py e app/main.py (due validazioni divergerebbero): una
  sola verita', importata da entrambi gli entry point.
Il modulo dipende solo da os/re (piu' i file in brand/): non importa engine ne'
la UI. Gli entry point traducono `InputError` nel loro linguaggio — uscita con
messaggio + exit 1 per il CLI, HTTP 4xx per il web.

Tutti i messaggi sono in ITALIANO (invariante #5): mai un traceback, mai un 500.
"""
import json
import os
import re

BASE = os.path.dirname(os.path.abspath(__file__))
LAYOUTS_DIR = os.path.join(BASE, "brand", "layouts")
PALETTES_DIR = os.path.join(BASE, "brand", "palettes")


# Copertura delle effemeridi de421.bsp: fuori da qui skyfield fallirebbe con un
# errore oscuro. Meglio un messaggio chiaro.
ANNO_MIN, ANNO_MAX = 1900, 2050

_HEX = re.compile(r"#[0-9a-fA-F]{6}$")


class InputError(Exception):
    """Input dell'utente non valido. Porta un messaggio leggibile in italiano."""


# ---------------------------------------------------------------------------
# Vocabolari: la cartella E' l'elenco (come gia' fanno CLI e web).
# ---------------------------------------------------------------------------
def formati_disponibili():
    return sorted(f[:-5] for f in os.listdir(LAYOUTS_DIR) if f.endswith(".json"))


def palette_disponibili():
    """Le palette in brand/palettes/: la cartella E' l'elenco."""
    return sorted(f[:-5] for f in os.listdir(PALETTES_DIR) if f.endswith(".json"))


def carica_palette(name):
    """Legge una palette per nome. Alza InputError in italiano se il nome non esiste
    (mai un traceback: invariante #5)."""
    f = os.path.join(PALETTES_DIR, f"{name}.json")
    if not os.path.exists(f):
        disp = palette_disponibili()
        raise InputError(f"Palette sconosciuta: '{name}'. Disponibili: {', '.join(disp)}.")
    with open(f, encoding="utf-8") as fh:
        return json.load(fh)


# ---------------------------------------------------------------------------
# R4 — input della richiesta. Ogni funzione converte E controlla il range, e
# restituisce il valore pulito; al primo errore alza InputError.
# ---------------------------------------------------------------------------
def _intero(val, nome):
    try:
        return int(str(val).strip())
    except (TypeError, ValueError):
        raise InputError(f"{nome} non valido: '{val}'. Serve un numero intero.")


def _numero(val, nome):
    try:
        return float(str(val).strip())
    except (TypeError, ValueError):
        raise InputError(f"{nome} non valida: '{val}'. Serve un numero.")


def valida_anno(year):
    y = _intero(year, "Anno")
    if not (ANNO_MIN <= y <= ANNO_MAX):
        raise InputError(f"Anno fuori intervallo: {y}. Ammessi {ANNO_MIN}-{ANNO_MAX} "
                         f"(copertura delle effemeridi).")
    return y


def valida_mese(month):
    m = _intero(month, "Mese")
    if not (1 <= m <= 12):
        raise InputError(f"Mese fuori intervallo: {m}. Ammessi 1-12.")
    return m


def valida_ora(hour):
    h = _intero(hour, "Ora")
    if not (0 <= h <= 23):
        raise InputError(f"Ora fuori intervallo: {h}. Ammesse 0-23.")
    return h


def valida_lat(lat):
    v = _numero(lat, "Latitudine")
    if not (-90.0 <= v <= 90.0):
        raise InputError(f"Latitudine fuori intervallo: {v}. Ammessa fra -90 e 90.")
    return v


def valida_lon(lon):
    v = _numero(lon, "Longitudine")
    if not (-180.0 <= v <= 180.0):
        raise InputError(f"Longitudine fuori intervallo: {v}. Ammessa fra -180 e 180.")
    return v


def valida_formato(fmt):
    disp = formati_disponibili()
    if fmt not in disp:
        raise InputError(f"Formato sconosciuto: '{fmt}'. Disponibili: {', '.join(disp)}.")
    return fmt


def valida_palette(name):
    disp = palette_disponibili()
    if name not in disp:
        raise InputError(f"Palette sconosciuta: '{name}'. Disponibili: {', '.join(disp)}.")
    return name


# ---------------------------------------------------------------------------
# D2/D13 — CONTRATTO DEL TEMA, per-strumento. Una palette ha ~20 chiavi DI MARCA
# (bg, text, panel, neon, gold, border, status...) che vuole QUALUNQUE strumento,
# e 3 che sono ASTRONOMIA PURA (disk = il gradiente del disco cielo, star_ramp,
# planet_colors) che vuole SOLO chi disegna il cielo. La palette resta UN FILE
# SOLO (non si spezza: duplicare il marchio vorrebbe dire cambiare l'oro del GAV
# in quattro posti); e' lo STRUMENTO a dichiarare di quali chiavi ha bisogno, e
# validate valida contro quella dichiarazione. L'errore dice QUALE chiave, in
# QUALE file, e — se e' una chiave d'astronomia — PER QUALE strumento.
#
# I contratti (D13): oggi ne esiste UNO che disegna il cielo. Il secondo,
# generico (es. Pillole, D12), e' SIMULATO nei test con CONTRATTO_MARCA finche'
# non nasce davvero: niente file di Pillole in anticipo.
CONTRATTO_CIELO = "Cielo del Mese"   # marca + onesta' astronomica
CONTRATTO_MARCA = "generico"         # solo marca (chi non disegna il cielo)

# MARCA: colori liberi, basta che ci siano e siano hex validi.
STYLE_TOKENS = ["neon", "gold", "border", "border2", "grid", "divider", "panel",
                "moon_lit", "moon_label", "bgstar", "text", "text2", "text3",
                "text4", "label", "cardinal"]
STATUS_KEYS = ["ok", "info", "warn", "muted"]
# ASTRONOMIA: le vuole solo il contratto del cielo.
PIANETI = ["Mercurio", "Venere", "Marte", "Giove", "Saturno", "Urano", "Nettuno"]


def _hex_ok(v):
    return isinstance(v, str) and _HEX.match(v) is not None


def _valida_stop3(theme, k, err):
    """Un gradiente a 3 stop hex (bg, disk)."""
    v = theme.get(k)
    if not isinstance(v, list) or len(v) != 3:
        err(f"'{k}' deve essere una lista di 3 colori.")
    for c in v:
        if not _hex_ok(c):
            err(f"'{k}' contiene un colore non valido: {c!r}.")


def valida_tema(theme, file, contratto=CONTRATTO_CIELO):
    """Verifica il contratto del tema per lo strumento `contratto`. Alza InputError
    con file + chiave al primo problema. Le chiavi DI MARCA si controllano sempre;
    quelle di ASTRONOMIA (disk/star_ramp/planet_colors) solo per il Cielo del Mese
    (D13): uno strumento che non disegna il cielo non deve rifiutare una palette a
    cui manca star_ramp."""
    astro = (contratto == CONTRATTO_CIELO)

    def err(msg):
        raise InputError(f"Palette non valida ({file}): {msg}")

    def err_astro(msg):
        raise InputError(f"Palette non valida ({file}) per {contratto}: {msg}")

    if not isinstance(theme, dict):
        err("il file non contiene un oggetto JSON.")

    # --- MARCA (qualunque strumento) ---
    for k in STYLE_TOKENS:
        if k not in theme:
            err(f"manca la chiave di stile '{k}'.")
        if not _hex_ok(theme[k]):
            err(f"'{k}' non e' un colore hex #rrggbb valido: {theme[k]!r}.")

    _valida_stop3(theme, "bg", err)  # sfondo pagina: di marca

    st = theme.get("status")
    if not isinstance(st, dict):
        err("manca 'status' (oggetto con ok/info/warn/muted).")
    for k in STATUS_KEYS:
        if k not in st:
            err(f"manca 'status.{k}'.")
        if not _hex_ok(st[k]):
            err(f"'status.{k}' non e' un colore hex valido: {st[k]!r}.")

    # --- ASTRONOMIA (solo il cielo) ---
    if astro:
        _valida_stop3(theme, "disk", err_astro)  # gradiente del disco cielo
        _valida_star_ramp(theme.get("star_ramp"), err_astro)
        _valida_planet_colors(theme.get("planet_colors"), err_astro)


def _valida_star_ramp(ramp, err):
    """star_ramp e' FISICA: mappa l'indice B-V al colore reale della stella. Al
    crescere di B-V (stella piu' fredda) il colore va da blu a rosso, quindi il
    canale ROSSO non deve calare e il BLU non deve salire. Monotonia DEBOLE (>= e
    <=): i canali saturano a 255, una monotonia STRETTA fallirebbe su una rampa
    fisicamente corretta."""
    if not isinstance(ramp, list) or len(ramp) < 2:
        err("'star_ramp' deve essere una lista di almeno 2 stop.")
    bvs = []
    for stop in ramp:
        if not (isinstance(stop, list) and len(stop) == 2 and _hex_ok(stop[1])):
            err(f"stop di 'star_ramp' malformato (atteso [bv, \"#rrggbb\"]): {stop!r}.")
        bvs.append(stop[0])
    if any(bvs[i + 1] <= bvs[i] for i in range(len(bvs) - 1)):
        err("l'asse B-V di 'star_ramp' deve essere strettamente crescente.")
    R = [int(c[1][1:3], 16) for c in ramp]
    B = [int(c[1][5:7], 16) for c in ramp]
    if any(R[i + 1] < R[i] for i in range(len(R) - 1)):
        err("'star_ramp' non fisica: il canale ROSSO deve crescere (o restare) "
            "al crescere di B-V (blu = caldo, rosso = freddo).")
    if any(B[i + 1] > B[i] for i in range(len(B) - 1)):
        err("'star_ramp' non fisica: il canale BLU deve calare (o restare) "
            "al crescere di B-V.")


def _valida_planet_colors(pc, err):
    """planet_colors e' FISICA: i colori reali dei pianeti. Oltre alla presenza
    dei 7, un controllo minimo di sensatezza (Marte rossastro, Nettuno bluastro)
    prende un'assegnazione scambiata senza vincolare la tinta esatta."""
    if not isinstance(pc, dict):
        err("manca 'planet_colors' (oggetto coi 7 pianeti).")
    for p in PIANETI:
        if p not in pc:
            err(f"manca 'planet_colors.{p}'.")
        if not _hex_ok(pc[p]):
            err(f"'planet_colors.{p}' non e' un colore hex valido: {pc[p]!r}.")
    def rb(h):
        return int(h[1:3], 16), int(h[5:7], 16)
    mr, mb = rb(pc["Marte"])
    nr, nb = rb(pc["Nettuno"])
    if mr <= mb:
        err("'planet_colors' non fisico: Marte deve essere rossastro (R > B).")
    if nb <= nr:
        err("'planet_colors' non fisico: Nettuno deve essere bluastro (B > R).")
