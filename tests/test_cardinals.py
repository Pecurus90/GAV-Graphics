"""
I CARDINALI DEVONO STARE DENTRO IL CANVAS — orientamento (invariante #3).

Zenit disegnava N/E/S/O FUORI dal canvas 1080 (N y=-43, S y=1141, E x=-52, O
x=1132): resvg li tagliava, e una carta del cielo senza N-in-alto/E-a-sinistra ha
perso la sua identita'. Il difetto e' sopravvissuto a occhi che GUARDAVANO i PNG:
guardare trova solo cio' che cerchi. Come R10. Quindi lo sorveglia un test.

Il criterio e' il DIFETTO (le lettere sono nel canvas), non la toppa: si estrae la
posizione REALE dei quattro cardinali dall'SVG e si pretende che cada dentro
[0,w]x[0,h]. Se un formato li mette fuori, qui diventa rosso.
"""
import json
import os
import re

import pytest

FORMATI = ["a4", "dashboard", "parata", "cornice", "zenit"]
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
    for lab, (x, y) in card.items():
        assert 0 <= x <= w and 0 <= y <= h, \
            f"{fmt}: cardinale {lab} FUORI dal canvas {w}x{h}: (x={x}, y={y})"
