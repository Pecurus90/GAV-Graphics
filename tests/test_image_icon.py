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


def test_icona_a_tratto_esce_a_tratto(eng, root, tmp_path):
    """Un glifo che si dichiara `stroke` esce A TRATTO, non pieno: e' la
    convenzione Lucide che il manuale (sez.7) prescrive - griglia 24, tratto 2,
    estremi tondi. Il colore resta un TOKEN, come per i glifi pieni.

    Sorveglia il DIFETTO che conta: se qualcuno tornasse a disegnare `fill=<token>`
    su un'icona a tratto, l'envelope diventerebbe una macchia nera piena."""
    theme = _palette(root, "gav")
    svg = _gen(eng, tmp_path, [
        {"type": "icon", "name": "email", "x": 10, "y": 10, "size": 24, "fill": "gold"}
    ], theme)
    assert 'fill="none"' in svg, "l'icona a tratto e' stata riempita"
    assert f'stroke="{theme["gold"]}"' in svg, "il colore del tratto non viene dal tema"
    assert 'stroke-width="2"' in svg, "il tratto non e' 2 (griglia 24 di Lucide)"
    assert f'<path d="M4 4H20' in svg and f'fill="{theme["gold"]}"' not in svg


def test_icona_piena_conserva_il_fill_rule(eng, root, tmp_path):
    """Un glifo PIENO che dichiara `fill_rule` deve ancora emetterlo: e' la
    capacita' che serviva alla vecchia envelope (il lembo si ritagliava con
    evenodd).

    Nessuna icona SU DISCO la usa piu', quindi il glifo di prova si inietta
    IN MEMORIA: la rete guarda la primitiva, non l'inventario di
    brand/icons/icons.json. (Stessa mossa di #7r col secondo tema.)"""
    eng._icons_cache = {"prova": {"fill_rule": "evenodd", "d": "M0 0h24v24H0Z"}}
    try:
        svg = _gen(eng, tmp_path, [
            {"type": "icon", "name": "prova", "x": 10, "y": 10, "size": 24, "fill": "text"}
        ], _palette(root, "gav"))
    finally:
        del eng._icons_cache
    assert 'fill-rule="evenodd"' in svg
