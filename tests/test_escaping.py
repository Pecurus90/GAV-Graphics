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

IL RESIDUO DI R11, CHIUSO QUI (2026-09-03). `place` passa da _render_text, che e'
UN choke point difeso. Ma ci sono **13** punti che lo BYPASSANO e chiamano `_esc()`
a mano (4 in disc.py, 9 in messier.py), e nessuno era coperto: passavano solo
perche' i DATI su disco non contengono `&`. Quindi la disciplina reggeva, non la
rete - e in questo progetto la disciplina e' gia' fallita piu' volte.
I test in fondo al file avvelenano i **DATI** (nomi di costellazione, di stelle,
Messier) invece dell'input, che e' dove sta il buco: sono dati che il GAV modifica,
quindi una `&` li' e' plausibile, non ipotetica.
*(CLAUDE.md diceva 11 punti: ricontati, sono 13.)*
"""
import json
import os
from xml.dom.minidom import parseString

import pytest

# Tutti i metacaratteri XML in un colpo solo, nel nome del luogo.
PLACE_OSTILE = "Bassano & Dintorni <Test> \"quote\" 'apos'"


def _theme(root):
    return json.load(open(os.path.join(root, "brand", "palettes", "gav.json"),
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


# ---------------------------------------------------------------------------
# IL RESIDUO DI R11: i 13 `_esc()` scritti a mano, che bypassano _render_text.
# Si avvelenano i DATI, non l'input.
# ---------------------------------------------------------------------------
OSTILE = "Test & <Prova>"


def _avvelena(monkeypatch, eng):
    """Mette `& < >` in OGNI sorgente di testo che bypassa _render_text:
    nomi di costellazione (disc.py e messier.py li importano SEPARATAMENTE, quindi
    si patchano tutti e due i binding), nomi di stelle, e catalogo Messier."""
    import strumenti.cielo.disc as D
    import strumenti.cielo.messier as M

    monkeypatch.setattr(D, "CONST_IT", {k: f"{v} {OSTILE}" for k, v in D.CONST_IT.items()})
    monkeypatch.setattr(M, "CONST_IT", {k: f"{v} {OSTILE}" for k, v in M.CONST_IT.items()})
    # stelle: la CHIAVE e' il nome mostrato, quindi si rinomina
    monkeypatch.setattr(D, "STARS", {f"{k} {OSTILE}": v for k, v in D.STARS.items()})
    monkeypatch.setattr(D, "MARQUEE", [(f"{m[0]} {OSTILE}",) + tuple(m[1:]) for m in D.MARQUEE])
    # Messier: si avvelena la cache pigra. VIA MONKEYPATCH, non con
    # `eng._messier_doc = ...`: la fixture `eng` e' SESSION-SCOPED, quindi
    # un'assegnazione diretta resterebbe addosso e avvelenerebbe gli altri test
    # (successo davvero: 13 rossi altrove).
    doc = json.load(open(os.path.join(eng.datadir, "messier.json"), encoding="utf-8"))
    for o in doc["oggetti"]:
        for campo in ("nome_it", "sigla", "costellazione_it", "famiglia"):
            if isinstance(o.get(campo), str):
                o[campo] = f"{o[campo]} {OSTILE}"
    monkeypatch.setattr(eng, "_messier_doc", doc, raising=False)


def _con_stelle_ostili(layout):
    """Il layout dichiara i nomi di stelle: vanno rinominati come le chiavi."""
    lay = json.loads(json.dumps(layout))
    for b in lay["blocks"]:
        if b.get("type") == "disc" and "star_names" in b:
            b["star_names"] = [f"{n} {OSTILE}" for n in b["star_names"]]
    return lay


@pytest.mark.parametrize("fmt", ["a4", "dashboard", "parata", "zenit", "deep-space"])
def test_dati_ostili_producono_svg_parsabile(eng, root, tmp_path, monkeypatch, fmt):
    """Costellazioni, stelle e Messier con `& < >` NEI DATI: l'SVG resta ben
    formato su tutti e cinque i formati.

    Copre i punti RAGGIUNGIBILI dai cinque layout. Provato vivo: togliendo `_esc`
    dal declutter di disc.py -> 4 rossi con ExpatError; dalla riga secondaria della
    tabella Messier -> 1 rosso.

    LIMITE DICHIARATO: due dei 13 punti restano scoperti perche' sono su RAMI NON
    PRESI - il percorso naive di disc.py (nessun formato lo usa piu': tutti e cinque
    dichiarano declutter) e la riga di gruppo della tabella Messier. Sono
    test-only/condizionali, non morti: se un giorno un layout li riaccende, questa
    rete NON li coprira'. Meglio saperlo scritto che scoprirlo."""
    _avvelena(monkeypatch, eng)
    out = str(tmp_path / f"{fmt}.svg")
    eng.generate(2026, 3, 45.5455, 11.5353, "Vicenza", _theme(root), out,
                 layout=_con_stelle_ostili(_layout(root, fmt)))
    svg = open(out, encoding="utf-8").read()
    parseString(svg)          # non deve sollevare: se solleva, l'SVG e' malformato
    assert "&amp;" in svg, "nessun testo avvelenato e' finito nell'SVG: il test non prova nulla"
