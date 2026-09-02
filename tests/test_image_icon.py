"""
Primitive `image` e `icon` (#6f): incorporamento offline e colore dal TEMA.

- image: l'immagine finisce nell'SVG come data URI base64, senza riferimenti a
  file esterni (deve funzionare offline e dentro l'.exe, D4).
- icon: il glifo e' geometria; il colore viene da un TOKEN del tema, quindi
  cambia con la palette (mai hex cablato).
"""
import json
import os

CANVAS = {"w": 200, "h": 100, "font_family": "Arial"}


def _gen(eng, tmp_path, blocks, theme):
    layout = {"canvas": CANVAS, "blocks": blocks}
    out = str(tmp_path / "x.svg")
    eng.generate(2026, 8, 45.5455, 11.5353, "Vicenza", theme, out, layout=layout)
    return open(out, encoding="utf-8").read()


def _palette(root, name):
    return json.load(open(os.path.join(root, "brand", "palettes", f"{name}.json"), encoding="utf-8"))


def test_image_incorporata_come_base64(eng, root, tmp_path):
    theme = _palette(root, "gav")
    svg = _gen(eng, tmp_path, [
        {"type": "image", "href": "brand/logo/logo-emblema.png", "x": 10, "y": 10, "w": 80, "h": 80}
    ], theme)
    assert "data:image/png;base64," in svg, "il logo non e' incorporato come data URI"
    assert ".png\"" not in svg and "href=\"brand/" not in svg, "resta un riferimento a file esterno"


def test_icona_colorata_dal_tema(eng, root, tmp_path):
    """La stessa icona con due VALORI del token 'gold' deve avere fill DIVERSO:
    il colore viene dal tema, non e' cablato (invariante #2).

    La palette e' ORA UNA SOLA (l'identita' GAV), quindi il secondo tema si
    costruisce in memoria variando quell'unico token: la rete sorveglia il
    DIFETTO (un hex cablato), non l'esistenza di due file su disco."""
    blocks = [{"type": "icon", "name": "instagram", "x": 10, "y": 10, "size": 24, "fill": "gold"}]
    gav = _palette(root, "gav")
    altro = dict(gav, gold="#ff00aa")            # un solo token cambiato
    assert gav["gold"] != altro["gold"]
    a = _gen(eng, tmp_path, blocks, gav)
    b = _gen(eng, tmp_path, blocks, altro)
    assert f'fill="{gav["gold"]}"' in a
    assert f'fill="{altro["gold"]}"' in b


def test_icona_fill_rule_envelope(eng, root, tmp_path):
    """L'envelope usa fill-rule evenodd (per il lembo): deve finire nell'output."""
    svg = _gen(eng, tmp_path, [
        {"type": "icon", "name": "email", "x": 10, "y": 10, "size": 24, "fill": "text"}
    ], _palette(root, "gav"))
    assert 'fill-rule="evenodd"' in svg
