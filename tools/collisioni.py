#!/usr/bin/env python3
"""
tools/collisioni.py - STRUMENTO D'INDAGINE (non un test).

Legge i layout (brand/layouts/*.json) e gli SVG del sweep (out/sweep/<fmt>_<mm>.svg)
ed estrae, per 12 mesi x 5 formati, cinque categorie di collisione. NON corregge
nulla: e' una diagnosi. Le correzioni si decidono dopo, coi numeri davanti.

Le cinque categorie (tutte gia' viste il 2026-07-19):
  1. ETICHETTA SOTTO UN PANNELLO  - il disco sigillato (D7) non sa dov'e' il pannello.
  2. ETICHETTA IN UN'ALTRA BANDA   - banda delimitata da 'line' (non 'panel'): il buco
                                     che fece passare N/S su Parata.
  3. ETICHETTA CONTRO ETICHETTA    - due etichette del disco troppo vicine.
  4. CARDINALE SOPRA CONTENUTO     - N/E/S/O sopra pannello / altra banda / testo.
  5. TACCA CHE ATTRAVERSA UN TESTO - la tacca dei gradi taglia una scritta.

--------------------------------------------------------------------------------
IL PUNTO DURO - LA LARGHEZZA DEL TESTO NON STA NELL'SVG.
La stimo:  width = n_char * corpo * FATTORE.
FATTORE calibrato RENDENDO stringhe isolate su fondo piatto (stesso font_family e
stesso motore resvg dei poster) e misurandone la larghezza in pixel dal raster:
    Capella .493  Auriga .504  Cassiopea .539  Orsa Maggiore .525  Betelgeuse .532
  -> etichette maiuscole/minuscole MISTE: FATTORE = 0.52 +/- 0.02 (~5%)
  -> testi TUTTO-MAIUSCOLO / con cifre ("TEMPERATURA", "7.000 K"): ~0.50
  RICALIBRATI il 2026-09-02 col passaggio ai font del MANUALE (Space Grotesk +
  Work Sans, R16). Con Barlow Semi Condensed erano 0.40 e 0.50: le minuscole di
  Space Grotesk sono ~29% piu' larghe (0.400 -> 0.516 misurato sul raster), le
  MAIUSCOLE quasi identiche (0.500 -> 0.498) - Barlow e' condensato ma ha
  maiuscole relativamente larghe. Misura rifatta con la tecnica originale:
  stringhe VERE del poster rese isolate e misurate sul raster, non stimate.
Space Grotesk non e' condensato. L'anti-collisione del
MOTORE usa 0.55 (sovrastima prudente): con quel modello impacchetta le etichette
"senza sovrapporsi", ma la larghezza VERA (0.40) e' minore -> restano dei vuoti.
Conseguenza: sui formati con anti-collisione (dashboard/parata/zenit) due etichette
non si SOVRAPPONGONO quasi mai davvero; sono QUASI-contatti (distanza piccola). Per
questo cat.3 riporta la DISTANZA NUMERICA fra i bordi: cosi' il margine d'errore
della stima (+/- ~1px su un'etichetta di ~20px) e' sotto gli occhi, non nascosto.
Margine d'errore pratico: su una soglia di 3-4px, +/-1px. Le collisioni "grosse"
(etichetta a meta' sotto un pannello, tacca in mezzo a una scritta) sono robuste;
i quasi-contatti a 2-4px vanno confermati a occhio (ed e' cio' che si fa, sui peggiori).
--------------------------------------------------------------------------------

Uso:
  python tools/collisioni.py                 # tutti i 60, tabella riassuntiva
  python tools/collisioni.py --dettaglio zenit 11   # elenco per un (fmt,mese)
  python tools/collisioni.py --layout-alt <file.json> <fmt> <mm>  # usa un layout diverso
                                             # (per calibrare su una geometria pre-fix)
"""
import json
import math
import os
import re
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
LAYOUTS = os.path.join(ROOT, "brand", "layouts")
SWEEP = os.path.join(ROOT, "out", "sweep")

FORMATI = ["dashboard", "parata", "zenit", "a4", "deep-space"]
MESI = list(range(1, 13))
MESI_IT = ["", "gen", "feb", "mar", "apr", "mag", "giu",
           "lug", "ago", "set", "ott", "nov", "dic"]

# Larghezza testo (vedi intestazione). Etichette miste 0.40; per prudenza sul
# tick-vs-testo (che tocca testi con cifre/maiuscole, ~0.50) uso un fattore per tipo.
F_MISTO = 0.52      # etichette del disco (maiuscole/minuscole)
F_MAIUSC = 0.50     # testi tutto-maiuscolo o con cifre
CAP = 0.72          # altezza del glifo sopra la baseline, in unita' di corpo
DESC = 0.10         # discesa sotto la baseline (g, p, ...)
R_RIF = 384.0       # raggio del disco A4 di riferimento (k = rad / R_RIF)

# Soglie
GAP_VICINE = 4.0    # cat.3: due etichette a meno di questo (bordo-bordo) = quasi-contatto
FRAZIONE_SOTTO = 0.25  # cat.1/4: quota di bbox dentro un pannello per contare


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------
_TEXT = re.compile(r'<text\s+x="(-?[\d.]+)"\s+y="(-?[\d.]+)"([^>]*)>([^<]*)</text>')


def _attr(attrs, nome, default=None):
    m = re.search(nome + r'="([^"]*)"', attrs)
    return m.group(1) if m else default


def leggi_testi(svg):
    """Tutti i <text> semplici con posizione, corpo, ancora, peso, opacita',
    letter-spacing e contenuto. Salta i <text> con figli <tspan> (rari)."""
    out = []
    for m in _TEXT.finditer(svg):
        x, y, attrs, cont = float(m.group(1)), float(m.group(2)), m.group(3), m.group(4)
        if not cont.strip():
            continue
        size = float(_attr(attrs, "font-size", "12"))
        anchor = _attr(attrs, "text-anchor", "start")
        weight = _attr(attrs, "font-weight", "")
        op = _attr(attrs, "opacity")
        ls = float(_attr(attrs, "letter-spacing", "0"))
        out.append(dict(x=x, y=y, size=size, anchor=anchor, weight=weight,
                        opacity=op, ls=ls, text=cont))
    return out


def bbox(t):
    """Riquadro stimato del testo (x0,y0,x1,y1). y0 sopra, y1 sotto la baseline."""
    caps = t["text"].isupper() or any(c.isdigit() for c in t["text"])
    f = F_MAIUSC if caps else F_MISTO
    w = len(t["text"]) * t["size"] * f + t["ls"] * max(0, len(t["text"]) - 1)
    y0, y1 = t["y"] - CAP * t["size"], t["y"] + DESC * t["size"]
    if t["anchor"] == "middle":
        return (t["x"] - w / 2, y0, t["x"] + w / 2, y1)
    if t["anchor"] == "end":
        return (t["x"] - w, y0, t["x"], y1)
    return (t["x"], y0, t["x"] + w, y1)


def e_cardinale(t):
    return (t["weight"] == "bold" and t["anchor"] == "middle"
            and t["text"] in ("N", "E", "S", "O"))


def e_etichetta_disco(t):
    # le etichette del disco (stelle/costellazioni) portano opacity 0.7/0.82/0.95;
    # i testi dei pannelli no. I cardinali (bold, senza opacity) sono a parte.
    return t["opacity"] in ("0.7", "0.82", "0.95")


# ---------------------------------------------------------------------------
# Geometria dal layout
# ---------------------------------------------------------------------------
def pannelli(layout):
    return [(b["x"], b["y"], b["x"] + b["w"], b["y"] + b["h"])
            for b in layout["blocks"] if b.get("type") == "panel"]


def divisori_tutta_larghezza(layout):
    w = layout["canvas"]["w"]
    out = []
    for b in layout["blocks"]:
        if b.get("type") != "line":
            continue
        x1, y1, x2, y2 = b.get("x1"), b.get("y1"), b.get("x2"), b.get("y2")
        if None in (x1, y1, x2, y2) or abs(y1 - y2) > 1:
            continue
        if abs(x2 - x1) < 0.7 * w:
            continue
        out.append((min(x1, x2), max(x1, x2), y1))
    return out


def disco(layout):
    for b in layout["blocks"]:
        if b.get("type") == "disc":
            return b
    return None


def tacche(layout):
    """Ricalcola i segmenti delle tacche (come strumenti/cielo/disc._disc_ticks).
    Ritorna [(x1,y1,x2,y2), ...] o [] se il disco non ha 'ticks'."""
    d = disco(layout)
    if not d or "ticks" not in d:
        return []
    cx, cy, rad = d["cx"], d["cy"], d["rad"]
    k = rad / R_RIF
    tk = d["ticks"]
    minor, major = tk.get("minor", 10), tk.get("major", 30)
    minl, majl = tk.get("minor_len", 9.0) * k, tk.get("major_len", 17.0) * k
    out = []
    for az in range(0, 360, minor):
        t = majl if az % major == 0 else minl
        ar = math.radians(az)
        x1 = cx - rad * math.sin(ar); y1 = cy - rad * math.cos(ar)
        x2 = cx - (rad + t) * math.sin(ar); y2 = cy - (rad + t) * math.cos(ar)
        out.append((x1, y1, x2, y2))
    return out


# ---------------------------------------------------------------------------
# Primitive geometriche
# ---------------------------------------------------------------------------
def _overlap_1d(a0, a1, b0, b1):
    return max(0.0, min(a1, b1) - max(a0, b0))


def frazione_dentro(bb, rect):
    """Quota dell'area di bb dentro rect (0..1)."""
    ax0, ay0, ax1, ay1 = bb
    ox = _overlap_1d(ax0, ax1, rect[0], rect[2])
    oy = _overlap_1d(ay0, ay1, rect[1], rect[3])
    area = (ax1 - ax0) * (ay1 - ay0)
    return (ox * oy / area) if area > 0 else 0.0


def gap_bbox(a, b):
    """Distanza minima fra due bbox; <0 se si sovrappongono (profondita' negativa)."""
    dx = max(b[0] - a[2], a[0] - b[2])   # >0 se separati in x
    dy = max(b[1] - a[3], a[1] - b[3])
    if dx > 0 and dy > 0:
        return math.hypot(dx, dy)
    if dx > 0:
        return dx
    if dy > 0:
        return dy
    return max(dx, dy)   # entrambi <=0: sovrapposti (valore <=0)


def _seg_interseca_rect(p, q, rect):
    """Un segmento p->q interseca il rettangolo rect? (Cohen-Sutherland leggero:
    estremo dentro, oppure il segmento taglia un lato.)"""
    x0, y0, x1, y1 = rect
    def dentro(pt):
        return x0 <= pt[0] <= x1 and y0 <= pt[1] <= y1
    if dentro(p) or dentro(q):
        return True
    lati = [((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)),
            ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))]
    return any(_seg_seg(p, q, a, b) for a, b in lati)


def _seg_seg(p1, p2, p3, p4):
    def ccw(a, b, c):
        return (c[1] - a[1]) * (b[0] - a[0]) - (b[1] - a[1]) * (c[0] - a[0])
    d1 = ccw(p3, p4, p1); d2 = ccw(p3, p4, p2)
    d3 = ccw(p1, p2, p3); d4 = ccw(p1, p2, p4)
    return ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0))


# ---------------------------------------------------------------------------
# I cinque rilevatori
# ---------------------------------------------------------------------------
def analizza(layout, svg):
    testi = leggi_testi(svg)
    etich = [t for t in testi if e_etichetta_disco(t)]
    cardin = [t for t in testi if e_cardinale(t)]
    pans = pannelli(layout)
    divs = divisori_tutta_larghezza(layout)
    d = disco(layout)
    cy = d["cy"] if d else None
    tk = tacche(layout)

    trovate = []   # (categoria, descrizione, gravita')

    # -- cat.1: etichetta del disco sotto un pannello --
    for t in etich:
        bb = bbox(t)
        for r in pans:
            fr = frazione_dentro(bb, r)
            if fr >= FRAZIONE_SOTTO:
                trovate.append(("1_pannello",
                                f"«{t['text']}» {int(fr*100)}% sotto pannello "
                                f"({r[0]:.0f},{r[1]:.0f})-({r[2]:.0f},{r[3]:.0f})", fr))

    # -- cat.2: etichetta del disco in un'altra banda (oltre un divisore) --
    if cy is not None:
        for t in etich:
            cxl = (bbox(t)[0] + bbox(t)[2]) / 2
            for (dx0, dx1, dy) in divs:
                if dx0 <= cxl <= dx1 and (dy - t["y"]) * (dy - cy) < 0:
                    trovate.append(("2_banda",
                                    f"«{t['text']}» (y{t['y']:.0f}) oltre il divisore "
                                    f"y{dy:.0f} - banda diversa dal disco (cy{cy:.0f})", 1.0))
                    break

    # -- cat.3: etichetta contro etichetta (quasi-contatto o sovrapposizione) --
    for i in range(len(etich)):
        for j in range(i + 1, len(etich)):
            g = gap_bbox(bbox(etich[i]), bbox(etich[j]))
            if g < GAP_VICINE:
                trovate.append(("3_etichette",
                                f"«{etich[i]['text']}» e «{etich[j]['text']}» a "
                                f"{g:.1f}px" + (" (SOVRAPPOSTE)" if g <= 0 else ""),
                                -g))

    # -- cat.4: cardinale sopra contenuto (pannello / altra banda / testo) --
    for c in cardin:
        bb = bbox(c)
        for r in pans:
            if frazione_dentro(bb, r) >= FRAZIONE_SOTTO:
                trovate.append(("4_cardinale",
                                f"«{c['text']}» ({c['x']:.0f},{c['y']:.0f}) sotto pannello "
                                f"({r[0]:.0f},{r[1]:.0f})-({r[2]:.0f},{r[3]:.0f})", 1.0))
        if cy is not None:
            cxl = c["x"]
            for (dx0, dx1, dy) in divs:
                if dx0 <= cxl <= dx1 and (dy - c["y"]) * (dy - cy) < 0:
                    trovate.append(("4_cardinale",
                                    f"«{c['text']}» ({c['x']:.0f},{c['y']:.0f}) oltre il "
                                    f"divisore y{dy:.0f} - altra banda", 1.0))
                    break
        # cardinale sopra un'ALTRA etichetta o testo (qualsiasi)
        for t in testi:
            if t is c:
                continue
            if gap_bbox(bb, bbox(t)) <= 0 and abs(t["y"] - c["y"]) < 2 * c["size"]:
                trovate.append(("4_cardinale",
                                f"«{c['text']}» sovrapposto a «{t['text'][:20]}»", 1.0))

    # -- cat.5: tacca che attraversa un testo --
    # I CARDINALI sono ESCLUSI: tacca e cardinale stanno allo STESSO azimut per
    # costruzione (la tacca "punta" verso N/E/S/O), non e' un difetto. Il difetto
    # e' la tacca che taglia una scritta di CONTENUTO (legenda, pannello, o
    # etichetta del disco) - es. la Sud che tagliava «≈ 7.000 K» sull'A4.
    for (x1, y1, x2, y2) in tk:
        for t in testi:
            if e_cardinale(t):
                continue
            if _seg_interseca_rect((x1, y1), (x2, y2), bbox(t)):
                trovate.append(("5_tacca",
                                f"una tacca attraversa «{t['text'][:24]}»", 1.0))
    # dedup cat.5 (piu' tacche sullo stesso testo)
    return _dedup(trovate)


def _dedup(trovate):
    visti = set(); out = []
    for cat, desc, g in trovate:
        key = (cat, desc)
        if key in visti:
            continue
        visti.add(key); out.append((cat, desc, g))
    return out


# ---------------------------------------------------------------------------
# Esecuzione
# ---------------------------------------------------------------------------
def carica_layout(fmt):
    with open(os.path.join(LAYOUTS, f"{fmt}.json"), encoding="utf-8") as fh:
        return json.load(fh)


def carica_svg(fmt, mese):
    p = os.path.join(SWEEP, f"{fmt}_{mese:02d}.svg")
    with open(p, encoding="utf-8") as fh:
        return fh.read()


CAT_ORDINE = ["1_pannello", "2_banda", "3_etichette", "4_cardinale", "5_tacca"]
CAT_NOME = {"1_pannello": "sotto-pannello", "2_banda": "altra-banda",
            "3_etichette": "etichetta-etichetta", "4_cardinale": "cardinale",
            "5_tacca": "tacca-testo"}


def sweep_completo():
    ris = {}   # (fmt,mese) -> list
    for fmt in FORMATI:
        lay = carica_layout(fmt)
        for m in MESI:
            ris[(fmt, m)] = analizza(lay, carica_svg(fmt, m))
    return ris


def stampa_tabella(ris):
    print("\n=== COLLISIONI: 12 mesi x 5 formati (gav, Vicenza, 2026) ===\n")
    intest = f"{'formato':<11}" + "".join(f"{MESI_IT[m]:>4}" for m in MESI) + f"{'  tot':>6}{'  media':>7}"
    print(intest)
    print("-" * len(intest))
    tot_cat = defaultdict(int)
    picco = {}
    for fmt in FORMATI:
        conteggi = [len(ris[(fmt, m)]) for m in MESI]
        riga = f"{fmt:<11}" + "".join(f"{c:>4}" for c in conteggi)
        tot = sum(conteggi)
        riga += f"{tot:>6}{tot/12:>7.1f}"
        print(riga)
        mmax = max(MESI, key=lambda m: len(ris[(fmt, m)]))
        mmin = min(MESI, key=lambda m: len(ris[(fmt, m)]))
        picco[fmt] = (mmax, len(ris[(fmt, mmax)]), mmin, len(ris[(fmt, mmin)]))
        for m in MESI:
            for cat, _, _ in ris[(fmt, m)]:
                tot_cat[(fmt, cat)] += 1
    print("\n--- per categoria (totale sui 12 mesi) ---")
    print(f"{'formato':<11}" + "".join(f"{CAT_NOME[c][:11]:>13}" for c in CAT_ORDINE))
    for fmt in FORMATI:
        print(f"{fmt:<11}" + "".join(f"{tot_cat[(fmt,c)]:>13}" for c in CAT_ORDINE))
    print("\n--- picco / minimo per formato ---")
    for fmt in FORMATI:
        mx, cmx, mn, cmn = picco[fmt]
        print(f"  {fmt:<11} picco {MESI_IT[mx]} ({cmx})   minimo {MESI_IT[mn]} ({cmn})")


def stampa_dettaglio(ris, fmt, mese):
    print(f"\n=== {fmt} {MESI_IT[mese]} ({mese:02d}) ===")
    items = sorted(ris[(fmt, mese)], key=lambda x: (CAT_ORDINE.index(x[0]), -x[2]))
    if not items:
        print("  nessuna collisione")
    for cat, desc, _ in items:
        print(f"  [{CAT_NOME[cat]:<19}] {desc}")


def main():
    args = sys.argv[1:]
    if args and args[0] == "--dettaglio":
        fmt, mese = args[1], int(args[2])
        lay = carica_layout(fmt)
        ris = {(fmt, mese): analizza(lay, carica_svg(fmt, mese))}
        stampa_dettaglio(ris, fmt, mese)
        return
    if args and args[0] == "--layout-alt":
        # calibrazione su una geometria diversa (es. layout pre-fix)
        altfile, fmt, mese = args[1], args[2], int(args[3])
        with open(altfile, encoding="utf-8") as fh:
            lay = json.load(fh)
        ris = {(fmt, mese): analizza(lay, carica_svg(fmt, mese))}
        stampa_dettaglio(ris, fmt, mese)
        return
    ris = sweep_completo()
    stampa_tabella(ris)


if __name__ == "__main__":
    main()
