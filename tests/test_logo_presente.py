"""
Il marchio del GAV su OGNI poster (#7g): test sui DATI, non a occhio.

Buco d'identita' trovato mettendo i formati uno accanto all'altro: prima di #7g
solo dashboard e profondo portavano il logo dell'associazione; a4, post,
editoriale e colonna uscivano SENZA marchio - e il volantino A4 il GAV lo stampa
e lo distribuisce. Marco ha deciso: il logo va su TUTTI.

Questa rete legge il FILE di layout (non l'immagine) e pretende, per ogni poster
in brand/layouts/, un blocco 'image' che punti al logo-emblema. Impedisce che un
layout nuovo - o uno ritoccato - riapra il buco senza che nessuno se ne accorga.
"""
import glob
import json
import os

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
LAYOUTS = sorted(glob.glob(os.path.join(ROOT, "brand", "layouts", "*.json")))


def _nome(p):
    return os.path.splitext(os.path.basename(p))[0]


@pytest.mark.parametrize("layout_path", LAYOUTS, ids=[_nome(p) for p in LAYOUTS])
def test_ogni_poster_porta_il_logo(layout_path):
    """Ogni layout di poster deve avere un blocco immagine col logo del GAV."""
    layout = json.load(open(layout_path, encoding="utf-8"))
    imgs = [b for b in layout["blocks"]
            if b.get("type") == "image" and "logo" in b.get("href", "")]
    assert imgs, f"{_nome(layout_path)}: nessun blocco immagine col logo del GAV"
