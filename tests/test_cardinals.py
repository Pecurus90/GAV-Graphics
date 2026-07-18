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

Entrambi i difetti sono sopravvissuti a occhi che GUARDAVANO i PNG: guardare trova
solo cio' che cerchi (come R10). Per questo li sorveglia un test, non lo sguardo.
"""
import json
import os
import re

import pytest

# Il set finale dei formati (cornice RITIRATO in X1, D19).
FORMATI = ["a4", "dashboard", "parata", "zenit"]
# I cardinali: <text ... font-weight="bold" text-anchor="middle">N|E|S|O</text>.
_CARD = re.compile(r'<text x="([\-\d.]+)" y="([\-\d.]+)"[^>]*'
                   r'font-weight="bold" text-anchor="middle">([NESO])</text>')


def _theme(root):
    return json.load(open(os.path.join(root, "brand", "palettes", "osservatorio.json"),
                          encoding="utf-8"))


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
