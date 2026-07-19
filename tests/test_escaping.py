"""
ESCAPING DEL TESTO nell'SVG — la rete sul buco di R4 lasciato aperto dal `place`.

Il nome del luogo (`--place` da CLI, `place` sul web) e' input LIBERO dell'utente e
finisce nel sottotitolo. Un `&` grezzo (es. «Bassano & Dintorni») produceva un SVG
MALFORMATO: resvg e xml.dom.minidom lo rifiutano -> un 500 sul PC del socio (D4).

QUESTO TEST GUARDA IL DIFETTO, NON LA TOPPA: pretende un SVG *parsabile*
(`xml.dom.minidom.parseString`), non che compaia `&amp;` nella stringa (quello
controllerebbe come l'abbiamo scritto, non che funzioni). Se togli l'escaping, il
parse fallisce: e' il rosso che dimostra che la rete e' viva.

NB: NON si valida `place` (scelta di Marco: cosa sia un nome-luogo lecito e' una
domanda di prodotto, giro a parte). Qui si pretende solo che QUALUNQUE testo non
rompa l'SVG.
"""
import json
import os
from xml.dom.minidom import parseString

import pytest

# Tutti i metacaratteri XML in un colpo solo, nel nome del luogo.
PLACE_OSTILE = "Bassano & Dintorni <Test> \"quote\" 'apos'"


def _theme(root):
    return json.load(open(os.path.join(root, "brand", "palettes", "osservatorio.json"),
                          encoding="utf-8"))


def _layout(root, nome):
    return json.load(open(os.path.join(root, "brand", "layouts", f"{nome}.json"),
                          encoding="utf-8"))


@pytest.mark.parametrize("fmt", ["a4", "dashboard", "zenit"])
def test_place_ostile_produce_svg_parsabile(eng, root, tmp_path, fmt):
    """Un place con & < > (e virgolette) deve dare un SVG BEN FORMATO su piu'
    layout. parseString alza se l'SVG e' malformato: e' il criterio, non un match
    di stringa."""
    out = str(tmp_path / f"{fmt}.svg")
    eng.generate(2026, 8, 45.5455, 11.5353, PLACE_OSTILE, _theme(root), out,
                 layout=_layout(root, fmt))
    svg = open(out, encoding="utf-8").read()
    # NON deve sollevare: se solleva, l'SVG e' malformato (il difetto).
    dom = parseString(svg)
    # e il testo, una volta ri-parsato, deve tornare il place GREZZO (l'entita' e'
    # stata decodificata): la & e' passata come dato, non come sintassi.
    testi = " ".join(t.firstChild.data for t in dom.getElementsByTagName("text")
                     if t.firstChild and t.firstChild.nodeType == t.TEXT_NODE)
    assert "Bassano & Dintorni <Test>" in testi, \
        "il nome del luogo, ri-parsato, deve tornare grezzo (& come dato, non sintassi)"


def test_deep_space_messier_con_place_ostile_parsabile(eng, root, tmp_path):
    """Deep Space (ex 'profondo') ha i propri punti d'emissione del testo (nomi
    Messier, costellazioni, legenda) che BYPASSANO _render_text. Anche con un place
    ostile l'SVG resta parsabile: la rete copre anche quei punti."""
    out = str(tmp_path / "deep-space.svg")
    eng.generate(2026, 8, 45.5455, 11.5353, PLACE_OSTILE, _theme(root), out,
                 layout=_layout(root, "deep-space"))
    parseString(open(out, encoding="utf-8").read())  # non deve sollevare
