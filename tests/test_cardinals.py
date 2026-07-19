"""
I CARDINALI DEVONO ESSERE VISIBILI — orientamento (invariante #3).

DUE criteri, perche' il primo aveva un buco della stessa forma del bug che
doveva sorvegliare:

1. DENTRO IL CANVAS. Zenit disegnava N/E/S/O FUORI dal canvas 1080 (N y=-43, S
   y=1141, E x=-52, O x=1132): resvg li tagliava, e una carta del cielo senza
   N-in-alto/E-a-sinistra ha perso la sua identita'.

2. NON SOTTO UN PANNELLO. Rimpicciolendo il disco di Zenit (r560->445) i cardinali
   sono rientrati nel canvas ma la S e' finita SOPRA la striscia lunare e la N
   sotto la testata: tecnicamente nel quadro, praticamente NASCOSTI. Il criterio
   #1 non lo vedeva -- passava. Quindi ora la rete pretende anche questo: nessun
   cardinale dentro il rettangolo di un pannello. Il test legge i rettangoli DAL
   LAYOUT (li vede tutti), quindi non e' vincolato dal sigillo del disco (D7): il
   disco non sa dove sono i pannelli, il test si'.

3. NON IN UN'ALTRA BANDA. Terzo buco della stessa forma: Parata NON ha pannelli
   -- le sue corsie (pianeti sopra, luna sotto) sono delimitate da 'line' a tutta
   larghezza, non da 'panel'. Il criterio #2 cercava solo 'panel', non trovava
   nulla, e passava a vuoto MENTRE N cadeva dentro il testo «Telescopico / a Est»
   della banda pianeti (y333,6) e S nella striscia lunare (y862,2). Un divisore a
   tutta larghezza e' un CONFINE DICHIARATO fra zone di contenuto: il cardinale
   deve restare dalla parte del disco. Se un divisore che copre la sua x sta fra
   il cardinale e il centro del disco, il cardinale e' finito in un'altra banda.

Tutti e tre i difetti sono sopravvissuti a occhi che GUARDAVANO i PNG: guardare
trova solo cio' che cerchi (come R10). Per questo li sorveglia un test, non lo
sguardo.
"""
import json
import os
import re

import pytest

# Il set finale dei formati (cornice RITIRATO in X1, D19; deep-space promosso a
# formato a se' il 2026-07-19, tolto il carosello).
FORMATI = ["a4", "dashboard", "parata", "zenit", "deep-space"]
# I cardinali: <text ... font-weight="bold" text-anchor="middle">N|E|S|O</text>.
_CARD = re.compile(r'<text x="([\-\d.]+)" y="([\-\d.]+)"[^>]*'
                   r'font-weight="bold" text-anchor="middle">([NESO])</text>')


def _theme(root):
    return json.load(open(os.path.join(root, "brand", "palettes", "osservatorio.json"),
                          encoding="utf-8"))


def _disc_cy(layout):
    for b in layout["blocks"]:
        if b.get("type") == "disc":
            return b["cy"]
    return None


def _dividers_a_tutta_larghezza(layout):
    """I divisori orizzontali a (quasi) tutta larghezza: i confini fra le bande di
    contenuto. Ritorna (x0, x1, y) per ognuno. Ignora le 'line' corte (divisori
    INTERNI a un pannello, es. sotto un titolo) che non separano bande."""
    w = layout["canvas"]["w"]
    out = []
    for b in layout["blocks"]:
        if b.get("type") != "line":
            continue
        x1, y1, x2, y2 = b.get("x1"), b.get("y1"), b.get("x2"), b.get("y2")
        if None in (x1, y1, x2, y2):
            continue
        if abs(y1 - y2) > 1:                    # dev'essere orizzontale
            continue
        if abs(x2 - x1) < 0.7 * w:              # a tutta (o quasi) larghezza
            continue
        out.append((min(x1, x2), max(x1, x2), y1))
    return out


@pytest.mark.parametrize("fmt", FORMATI)
def test_cardinali_dentro_il_canvas(eng, root, tmp_path, fmt):
    layout = json.load(open(os.path.join(root, "brand", "layouts", f"{fmt}.json"),
                            encoding="utf-8"))
    w, h = layout["canvas"]["w"], layout["canvas"]["h"]
    out = str(tmp_path / f"{fmt}.svg")
    eng.generate(2026, 8, 45.5455, 11.5353, "Vicenza", _theme(root), out, layout=layout)
    svg = open(out, encoding="utf-8").read()
    card = {lab: (float(x), float(y)) for x, y, lab in _CARD.findall(svg)}
    assert set(card) == {"N", "E", "S", "O"}, f"{fmt}: cardinali trovati {sorted(card)} (attesi N/E/S/O)"
    # criterio 1: dentro il canvas
    for lab, (x, y) in card.items():
        assert 0 <= x <= w and 0 <= y <= h, \
            f"{fmt}: cardinale {lab} FUORI dal canvas {w}x{h}: (x={x}, y={y})"
    # criterio 2: non sotto un pannello HUD (rettangoli letti dal layout)
    panels = [(b["x"], b["y"], b["x"] + b["w"], b["y"] + b["h"])
              for b in layout["blocks"] if b.get("type") == "panel"]
    for lab, (x, y) in card.items():
        for (px0, py0, px1, py1) in panels:
            assert not (px0 <= x <= px1 and py0 <= y <= py1), \
                f"{fmt}: cardinale {lab} ({x:.0f},{y:.0f}) SOTTO il pannello " \
                f"({px0},{py0})-({px1},{py1}): nel canvas ma nascosto."
    # criterio 3: non oltre un divisore a tutta larghezza (in un'altra banda).
    # Le corsie di Parata sono delimitate da 'line', non da 'panel': e' il buco
    # che il criterio 2 non vedeva.
    cy = _disc_cy(layout)
    dividers = _dividers_a_tutta_larghezza(layout)
    if cy is not None:
        for lab, (x, y) in card.items():
            for (dx0, dx1, dy) in dividers:
                if not (dx0 <= x <= dx1):
                    continue
                # dy STRETTAMENTE fra il cardinale e il centro del disco -> il
                # cardinale ha attraversato il confine, e' in un'altra banda.
                if (dy - y) * (dy - cy) < 0:
                    pytest.fail(
                        f"{fmt}: cardinale {lab} ({x:.0f},{y:.0f}) oltre il divisore "
                        f"y={dy:.0f}: e' in una banda di altro contenuto, non in "
                        f"quella del disco (cy={cy:.0f}).")
