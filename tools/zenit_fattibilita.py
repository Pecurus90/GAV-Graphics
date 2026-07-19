#!/usr/bin/env python3
"""
tools/zenit_fattibilita.py - MISURA DI FATTIBILITA' (non un fix, non un test).

LA DOMANDA, una sola: se le etichette di Zenit dovessero SCHIVARE i rettangoli
dei pannelli (il cielo - stelle, linee, tacche - continua a passarci sotto: e'
l'identita' di Zenit), CI SAREBBE POSTO DOVE METTERLE? Su tutti e 12 i mesi.

COME: si RIPRODUCE fedelmente il piazzamento di strumenti/cielo/disc.py
(_disc_labels_declutter) - stesse posizioni naturali, stesse priorita', stessi
offset candidati (0,0 + 5 anelli x 8 direzioni, passo 6k) - e si AGGIUNGE l'unico
vincolo nuovo: la bbox dell'etichetta non deve toccare nessuno dei 4 pannelli.
NON si tocca disc.py: si legge il motore (altaz/project/sky_context) e si rifa'
il greedy qui. Calibrato: senza il vincolo-pannelli, le posizioni prodotte
COMBACIANO con quelle dell'SVG reso da disc.py (verifica sotto).

IL PUNTO CHE DECIDE (c): la regola del progetto e' «MAI LONTANO» (#7d-bis/ter).
Un'etichetta senza collisione ma a 100 px dalla sua stella indica la stella
SBAGLIATA. Quindi non conta solo SE ci sta, ma DI QUANTO si sposta. Si riportano:
  - con la finestra del MOTORE (<=5 anelli, ~35 px per Zenit): quante entrano;
  - con una finestra ALLARGATA (sonda, fino a 25 anelli): di quanto dovrebbero
    spostarsi quelle che il motore scarta - per distinguere «appena fuori» da
    «sepolta, si salva solo buttandola lontano» (= editorialmente morta).

Uso:  python tools/zenit_fattibilita.py
"""
import json
import math
import os
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from engine.generate import Engine, STARS          # noqa: E402
from strumenti.cielo.catalog import CONST_IT        # noqa: E402

VLAT, VLON = 45.5455, 11.5353
MESI_IT = ["", "gen", "feb", "mar", "apr", "mag", "giu",
           "lug", "ago", "set", "ott", "nov", "dic"]

DIRS = [(0, -1), (1, 0), (0, 1), (-1, 0), (1, -1), (1, 1), (-1, 1), (-1, -1)]
RINGS_MOTORE = 5          # cio' che _disc_labels_declutter usa davvero
RINGS_SONDA = 25          # per misurare quanto lontano servirebbe andare


def _overlap(a, b):
    return not (a[2] <= b[0] or a[0] >= b[2] or a[3] <= b[1] or a[1] >= b[3])


def carica_zenit():
    lay = json.load(open(os.path.join(ROOT, "brand", "layouts", "zenit.json"),
                         encoding="utf-8"))
    disc = next(b for b in lay["blocks"] if b.get("type") == "disc")
    panels = [(b["x"], b["y"], b["x"] + b["w"], b["y"] + b["h"])
              for b in lay["blocks"] if b.get("type") == "panel"]
    return disc, panels


def reqs_del_mese(eng, month, disc):
    """Le richieste d'etichetta, IDENTICHE a _disc_labels_declutter: stelle
    (star_names) col punto naturale (x+7k, y-5k) e priorita' = magnitudine
    (Polare -100); costellazioni (le 22) al baricentro, priorita' 100+rango per
    impronta. Ritorna la lista + (cx,cy,rad,k)."""
    cx, cy, rad = disc["cx"], disc["cy"], disc["rad"]
    k = rad / 384.0
    lst, lat_rad, _ = eng.sky_context(2026, month, VLAT, VLON, 23)
    reqs = []
    for nm in disc["star_names"]:
        if nm not in STARS:
            continue
        ra, dec, bv, mag = STARS[nm]
        al, zz = eng.altaz(ra, dec, lst, lat_rad)
        if al <= 2:
            continue
        x, y = eng.project(al, zz, cx, cy, rad); x, y = float(x), float(y)
        reqs.append(dict(text=nm, natx=x + 7 * k, naty=y - 5 * k, objx=x, objy=y,
                         anchor="start", size=11.5 * k,
                         pri=(-100.0 if nm == "Polare" else mag), kind="stella"))
    label_set = set(disc["labels"])
    consts = []
    for f in eng.clines:
        ab = f["id"]
        if ab not in CONST_IT or ab not in label_set:
            continue
        allp = np.array([p for line in f["geometry"]["coordinates"] for p in line])
        al, zz = eng.altaz(allp[:, 0], allp[:, 1], lst, lat_rad)
        m = al > 3
        if m.sum() < 2:
            continue
        xs, ys = eng.project(al[m], zz[m], cx, cy, rad)
        area = float((xs.max() - xs.min()) * (ys.max() - ys.min()))
        consts.append((area, ab, float(xs.mean()), float(ys.mean())))
    consts.sort(key=lambda c: -c[0])
    for rank, (area, ab, mx, my) in enumerate(consts):
        reqs.append(dict(text=CONST_IT[ab], natx=mx, naty=my, objx=mx, objy=my,
                         anchor="middle", size=12.5 * k, pri=100.0 + rank,
                         kind="costellazione"))
    return reqs, cx, cy, rad, k


def _bbox(req, px, py):
    w = len(req["text"]) * req["size"] * 0.55
    h = req["size"]
    if req["anchor"] == "middle":
        return (px - w / 2, py - h, px + w / 2, py)
    return (px, py - h, px + w, py)


def piazza(reqs, cx, cy, rad, k, panels, evita_pannelli, rings):
    """Greedy IDENTICO al motore + (opzionale) vincolo-pannelli. Ritorna, per ogni
    req in ordine di priorita', (req, esito) con esito = dict(px,py,off) o None."""
    STEP = 6 * k
    cands = [(0, 0)] + [(dx * r * STEP, dy * r * STEP)
                        for r in range(1, rings + 1) for dx, dy in DIRS]
    placed = []
    esiti = []
    for req in sorted(reqs, key=lambda r: r["pri"]):
        scelto = None
        for ox, oy in cands:
            px, py = req["natx"] + ox, req["naty"] + oy
            if (px - cx) ** 2 + (py - cy) ** 2 > (rad - 3) ** 2:
                continue
            bb = _bbox(req, px, py)
            if any(_overlap(bb, p) for p in placed):
                continue
            if evita_pannelli and any(_overlap(bb, pan) for pan in panels):
                continue
            scelto = dict(px=px, py=py, bb=bb, off=math.hypot(ox, oy))
            break
        if scelto is None:
            esiti.append((req, None))
            continue
        placed.append(scelto["bb"])
        esiti.append((req, scelto))
    return esiti


# ---------------------------------------------------------------------------
# Calibrazione: senza vincolo-pannelli, le posizioni devono combaciare con l'SVG
# ---------------------------------------------------------------------------
def calibra(eng, disc):
    """Rende Zenit di agosto col motore vero, estrae le posizioni delle etichette,
    e le confronta con la simulazione (evita_pannelli=False). Se combaciano, la
    riproduzione e' fedele e la misura col vincolo-pannelli e' affidabile."""
    theme = json.load(open(os.path.join(ROOT, "brand", "palettes", "osservatorio.json"),
                           encoding="utf-8"))
    lay = json.load(open(os.path.join(ROOT, "brand", "layouts", "zenit.json"),
                         encoding="utf-8"))
    out = os.path.join(ROOT, "out", "fix", "_zcal.svg")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    eng.generate(2026, 8, VLAT, VLON, "Vicenza", theme, out, layout=lay)
    svg = open(out, encoding="utf-8").read()
    reali = {}
    for m in re.finditer(r'<text x="([\-\d.]+)" y="([\-\d.]+)"[^>]*opacity="0\.(?:82|95)"[^>]*>([^<]+)</text>', svg):
        reali[m.group(3)] = (float(m.group(1)), float(m.group(2)))
    reqs, cx, cy, rad, k = reqs_del_mese(eng, 8, disc)
    esiti = piazza(reqs, cx, cy, rad, k, [], evita_pannelli=False, rings=RINGS_MOTORE)
    diff_max = 0.0; confrontate = 0; mancano = 0
    for req, es in esiti:
        if req["text"] not in reali:
            mancano += 1
            continue
        if es is None:
            continue
        rx, ry = reali[req["text"]]
        d = math.hypot(es["px"] - rx, es["py"] - ry)
        diff_max = max(diff_max, d); confrontate += 1
    return confrontate, diff_max, mancano


# ---------------------------------------------------------------------------
# La misura
# ---------------------------------------------------------------------------
def main():
    eng = Engine(datadir=os.path.join(ROOT, "data"))
    disc, panels = carica_zenit()

    conf, dmax, manc = calibra(eng, disc)
    print("=== CALIBRAZIONE (agosto, senza vincolo-pannelli vs SVG reale) ===")
    print(f"  {conf} etichette confrontate, scarto MAX dalla posizione reale: {dmax:.2f} px"
          f"  (manca/e nell'SVG: {manc})")
    print(f"  -> se lo scarto e' ~0, la riproduzione e' fedele.\n")

    canvas_area = 1080 * 1080
    parea = sum((p[2] - p[0]) * (p[3] - p[1]) for p in panels)
    print(f"pannelli: {len(panels)}, coprono {parea/canvas_area*100:.0f}% del canvas\n")

    print("=== FATTIBILITA': etichette che TROVANO POSTO schivando i pannelli ===")
    print("(finestra del MOTORE: 5 anelli, ~35px per Zenit)\n")
    hdr = f"{'mese':<5}{'totali':>7}{'entrano':>9}{'FUORI':>7}{'spost.med':>10}{'spost.max':>10}"
    print(hdr); print("-" * len(hdr))
    peggiore = None
    tutti_spost = []
    per_mese = {}
    for month in range(1, 13):
        reqs, cx, cy, rad, k = reqs_del_mese(eng, month, disc)
        esiti = piazza(reqs, cx, cy, rad, k, panels, evita_pannelli=True, rings=RINGS_MOTORE)
        entrano = [(r, e) for r, e in esiti if e is not None]
        fuori = [r for r, e in esiti if e is None]
        spost = sorted(e["off"] for r, e in entrano)
        med = spost[len(spost) // 2] if spost else 0.0
        mx = spost[-1] if spost else 0.0
        tutti_spost += spost
        per_mese[month] = (len(reqs), len(entrano), fuori)
        print(f"{MESI_IT[month]:<5}{len(reqs):>7}{len(entrano):>9}{len(fuori):>7}{med:>10.1f}{mx:>10.1f}")
        if peggiore is None or len(fuori) > len(per_mese[peggiore][2]):
            peggiore = month

    print("\n=== MESE PEGGIORE ===")
    tot, entr, fuori = per_mese[peggiore]
    print(f"  {MESI_IT[peggiore]}: {len(fuori)} etichette NON trovano posto (su {tot}).")
    for r in fuori:
        print(f"    - «{r['text']}» ({r['kind']})")

    print("\n=== DISTRIBUZIONE SPOSTAMENTI (etichette entrate, finestra motore) ===")
    if tutti_spost:
        tutti_spost.sort()
        n = len(tutti_spost)
        print(f"  n={n}  mediana={tutti_spost[n//2]:.1f}px  "
              f"90mo pct={tutti_spost[int(n*0.9)]:.1f}px  max={tutti_spost[-1]:.1f}px")
        print(f"  a distanza 0 (punto naturale): {sum(1 for s in tutti_spost if s < 0.5)}/{n}")

    print("\n=== SONDA: le scartate, quanto LONTANO dovrebbero andare per entrare? ===")
    print("(finestra allargata a 25 anelli; se non entra neanche cosi', e' sepolta)\n")
    for month in range(1, 13):
        _, _, fuori_motore = per_mese[month]
        if not fuori_motore:
            continue
        reqs, cx, cy, rad, k = reqs_del_mese(eng, month, disc)
        esiti = piazza(reqs, cx, cy, rad, k, panels, evita_pannelli=True, rings=RINGS_SONDA)
        emap = {id(r): e for r, e in esiti}
        # rifaccio con gli stessi oggetti req: piazza() ordina internamente, uso il testo
        byname = {}
        for r, e in esiti:
            byname[r["text"]] = e
        righe = []
        for r in fuori_motore:
            e = byname.get(r["text"])
            if e is None:
                righe.append(f"«{r['text']}» SEPOLTA (nemmeno a 25 anelli)")
            else:
                righe.append(f"«{r['text']}» servirebbe {e['off']:.0f}px")
        print(f"  {MESI_IT[month]}: " + "; ".join(righe))


if __name__ == "__main__":
    main()
