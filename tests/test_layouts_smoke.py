"""
SMOKE TEST di ORTOGONALITA' layout × palette.

Ogni layout in brand/layouts/ deve rendere con OGNI palette in brand/palettes/,
senza eccezioni. E' la rete che sostiene la REGOLA DI FERRO di #6d: nessun colore
cablato nei layout. Se un layout nominasse un token inesistente in una palette
(o cablasse un hex al posto di un token), qui salterebbe fuori come KeyError.

Copre le 4×(numero di layout) combinazioni, incluse le 4×3 dei design social.
Non verifica l'ESTETICA (quella la guarda un umano sui PNG): verifica che il
motore produca un SVG valido e non vuoto per ogni accoppiamento.
"""
import glob
import json
import os

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
LAYOUTS = sorted(glob.glob(os.path.join(ROOT, "brand", "layouts", "*.json")))
PALETTES = sorted(glob.glob(os.path.join(ROOT, "brand", "palettes", "*.json")))


def _ids(paths):
    return [os.path.splitext(os.path.basename(p))[0] for p in paths]


@pytest.mark.parametrize("layout_path", LAYOUTS, ids=_ids(LAYOUTS))
@pytest.mark.parametrize("palette_path", PALETTES, ids=_ids(PALETTES))
def test_layout_rende_con_ogni_palette(eng, tmp_path, layout_path, palette_path):
    layout = json.load(open(layout_path, encoding="utf-8"))
    theme = json.load(open(palette_path, encoding="utf-8"))
    out = str(tmp_path / "prova.svg")
    eng.generate(2026, 8, 45.5455, 11.5353, "Vicenza", theme, out, layout=layout)
    svg = open(out, encoding="utf-8").read()
    assert svg.startswith("<svg") and svg.rstrip().endswith("</svg>")
    assert len(svg) > 500, "SVG sospettosamente corto"


def test_i_tre_quadrati_del_set_finale():
    """Guardia sulla copertura: i 3 quadrati del set finale × le palette devono
    esistere davvero (non un parametrize vuoto che passa a vuoto). Il set: dashboard
    (l'ancora) + Parata/Zenit (eredi di colonna/post). Cornice RITIRATO (D19), come
    post/editorial/rail."""
    nomi = set(_ids(LAYOUTS))
    assert {"dashboard", "parata", "zenit"} <= nomi, f"quadrati mancanti: {nomi}"
    assert {"post", "editorial", "rail", "cornice"}.isdisjoint(nomi), f"ritirati ancora presenti: {nomi}"
    # UNA sola palette, ed e' l'identita' GAV: se un giorno ne ricompare una
    # seconda dev'essere una decisione, non una ricaduta.
    assert len(PALETTES) == 1, f"attesa 1 sola palette, trovate {len(PALETTES)}"
    assert os.path.basename(PALETTES[0]) == "gav.json", PALETTES
