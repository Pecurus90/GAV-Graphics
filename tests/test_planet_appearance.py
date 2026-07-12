"""
Aspetto dei pianeti (#6h): colore REALE dal tema, sagoma dal DATO.

- Il pallino prende il colore del pianeta da theme["planet_colors"] (mai cablato
  nel motore: invariante #2). Con un tema modificato, il pallino segue.
- La sagoma ('ringed' per Saturno) vive nel DATO (Planet.shape): il disegno la
  sceglie per token, non con un if sul nome. Con fill_planet, Saturno prende gli
  anelli (un <ellipse>), gli altri no.
- L'A4 (fill_status) non e' toccato: continua a colorare per stato.
"""
import copy
import json
import os
import re


def _theme(root, name="osservatorio"):
    return json.load(open(os.path.join(root, "brand", "palettes", f"{name}.json"), encoding="utf-8"))


def _render(eng, tmp_path, theme, dot):
    layout = {"canvas": {"w": 400, "h": 400, "font_family": "Arial"}, "blocks": [{
        "type": "planet_panel", "from": "planets", "x0": 40, "y0": 40, "step": 44,
        "dot": dot,
        "name": {"dx": 30, "fill": "text", "size": 14, "content": "{name}"}}]}
    out = str(tmp_path / "p.svg")
    eng.generate(2026, 8, 45.5455, 11.5353, "Vicenza", theme, out, layout=layout)
    return open(out, encoding="utf-8").read()


def test_sagoma_dal_dato(eng):
    """Saturno porta shape='ringed', gli altri 'plain'. E' un DATO, non un nome
    cablato nel disegno."""
    planets = {p.name: p for p in eng.sky_data(2026, 8, 45.5455, 11.5353, "Vicenza").planets}
    assert planets["Saturno"].shape == "ringed"
    for nome in ("Venere", "Marte", "Giove", "Urano", "Nettuno", "Mercurio"):
        assert planets[nome].shape == "plain", f"{nome} non dovrebbe avere una sagoma speciale"


def test_pallino_colore_pianeta_dal_tema(eng, root, tmp_path):
    """Con fill_planet il pallino usa theme['planet_colors'][nome]; NON il colore
    di stato. E se cambio il tema, il pallino segue (invariante #2)."""
    theme = _theme(root)
    svg = _render(eng, tmp_path, theme, {"dx": 6, "dy": -4, "r": 6, "fill_planet": True})
    # ogni colore-pianeta del tema compare come fill di un pallino
    for nome, col in theme["planet_colors"].items():
        assert f'fill="{col}"' in svg, f"manca il pallino colore di {nome} ({col})"
    # NON e' colorato per stato: nessun colore di status usato come pallino
    # (verifica su 'ok', il verde, che nell'A4 sarebbe il pallino di Venere/Marte)
    assert theme["status"]["ok"] not in re.findall(r'<circle[^>]*fill="([^"]+)"', svg)

    # tema modificato -> il pallino segue (non cablato nel motore)
    t2 = copy.deepcopy(theme); t2["planet_colors"]["Marte"] = "#123456"
    svg2 = _render(eng, tmp_path, t2, {"dx": 6, "dy": -4, "r": 6, "fill_planet": True})
    assert 'fill="#123456"' in svg2


def test_saturno_ha_gli_anelli_solo_coi_pallini_pianeta(eng, root, tmp_path):
    """Con fill_planet, Saturno (shape ringed) produce un <ellipse> (gli anelli);
    con fill_status (A4) no: gli anelli sono legati all'identita', non allo stato."""
    theme = _theme(root)
    svg_planet = _render(eng, tmp_path, theme, {"dx": 6, "dy": -4, "r": 6, "fill_planet": True})
    assert "<ellipse" in svg_planet, "Saturno dovrebbe avere gli anelli (ellisse)"
    svg_status = _render(eng, tmp_path, theme, {"dx": 6, "dy": -4, "r": 6, "fill_status": True})
    assert "<ellipse" not in svg_status, "senza fill_planet niente anelli"


def test_anello_di_stato_variante_B(eng, root, tmp_path):
    """La variante B aggiunge un anello col colore di STATO attorno al pallino."""
    theme = _theme(root)
    dot = {"dx": 6, "dy": -4, "r": 6, "fill_planet": True,
           "status_ring": {"r_extra": 3, "width": 1.6}}
    svg = _render(eng, tmp_path, theme, dot)
    # compaiono i colori di stato come STROKE (anello), non come fill del pallino
    assert re.search(r'<circle[^>]*stroke="' + re.escape(theme["status"]["ok"]), svg)
