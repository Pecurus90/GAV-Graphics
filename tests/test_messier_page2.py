"""RETE della pagina 2 (profondo cielo). Sorveglia cio' che il giro #7a/#7b ha
ottenuto e che prima NON era misurato da niente:

 (a) NESSUNA SOVRAPPOSIZIONE: i box delle etichette Messier non intersecano i
     box dei simboli, ne' fra loro. (Le LINEE di costellazione non sono
     ostacoli, per scelta: le etichette possono sfiorarle come negli atlanti.)
 (b) ZERO SCARTI: un'etichetta non si scarta mai (D9). `_last_messier_dropped==0`.
 (c) PATTO D9 nei DUE SENSI: l'insieme dei nomi sulla mappa == l'insieme delle
     righe di tabella (il gruppo Vergine vale UNA voce da entrambe le parti).

Mesi campione: gennaio (rado), marzo (il peggiore, con l'Ammasso della Vergine),
luglio (max densita', 86 simboli), agosto. Vicenza, 2026, ore 23:00.

Se uno fallisce, NON aggiustare il test: e' un difetto di piazzamento reale.
"""
import json
import os

import pytest

MESI = [1, 3, 7, 8]
VLAT, VLON = 45.5455, 11.5353


def _inter(a, b):
    """True se i due box [x0,y0,x1,y1] si intersecano (bordo che tocca = no)."""
    return not (a[2] <= b[0] or a[0] >= b[2] or a[3] <= b[1] or a[1] >= b[3])


@pytest.fixture(scope="module")
def profondo(root):
    with open(os.path.join(root, "brand", "layouts", "profondo.json"), encoding="utf-8") as fh:
        layout = json.load(fh)
    with open(os.path.join(root, "brand", "palettes", "osservatorio.json"), encoding="utf-8") as fh:
        theme = json.load(fh)
    sym_block = next(b for b in layout["blocks"] if b["type"] == "messier_symbols")
    return layout, theme, sym_block


def _render(eng, profondo, month):
    """Rende i simboli/etichette di un mese e restituisce il contesto Messier.
    Gli effetti (box, contatori) restano su `eng._last_*`."""
    layout, theme, sym_block = profondo
    ms = layout["messier"]
    lst, lat_rad, _ = eng.sky_context(2026, month, VLAT, VLON, hour_local=23)
    mctx = eng.messier_context(lst, lat_rad, ms["cx"], ms["cy"], ms["rad"], ms["n"])
    eng._render_messier_symbols(sym_block, theme, mctx)
    return mctx


@pytest.mark.parametrize("month", MESI)
def test_etichette_non_sovrappongono_simboli(eng, profondo, month):
    """(a) Nessun box-etichetta interseca un box-simbolo."""
    _render(eng, profondo, month)
    labels = eng._last_label_boxes
    symbols = eng._last_symbol_boxes
    assert labels and symbols
    guasti = [(key, i) for (bx, key) in labels
              for i, sb in enumerate(symbols) if _inter(bx, sb)]
    assert not guasti, f"mese {month}: etichette sopra simboli: {guasti}"


@pytest.mark.parametrize("month", MESI)
def test_etichette_non_si_sovrappongono_fra_loro(eng, profondo, month):
    """(a) Nessun box-etichetta interseca un altro box-etichetta."""
    _render(eng, profondo, month)
    lb = eng._last_label_boxes
    guasti = [(lb[i][1], lb[j][1]) for i in range(len(lb)) for j in range(i + 1, len(lb))
              if _inter(lb[i][0], lb[j][0])]
    assert not guasti, f"mese {month}: etichette sovrapposte: {guasti}"


@pytest.mark.parametrize("month", MESI)
def test_zero_scarti(eng, profondo, month):
    """(b) Un'etichetta non si scarta mai: dropped == 0."""
    _render(eng, profondo, month)
    assert eng._last_messier_dropped == 0, \
        f"mese {month}: {eng._last_messier_dropped} etichette scartate (dovrebbero essere 0)"


@pytest.mark.parametrize("month", MESI)
def test_patto_d9_insiemi_uguali(eng, profondo, month):
    """(c) Insieme dei nomi sulla mappa == insieme delle righe di tabella, nei
    DUE sensi (uguaglianza, non inclusione). Il gruppo Vergine = UNA voce."""
    mctx = _render(eng, profondo, month)
    su_mappa = {key for (_bx, key) in eng._last_label_boxes}
    in_tabella = {("__group__" + r["_group"]) if r.get("_group") else r["sigla"]
                  for r in mctx["table"]}
    assert su_mappa == in_tabella, (
        f"mese {month}: patto rotto. Solo sulla mappa: {su_mappa - in_tabella}; "
        f"solo in tabella: {in_tabella - su_mappa}")


def test_gruppo_vergine_strutturale_a_marzo(eng, profondo):
    """Il gruppo, quando i membri superano i 30 gradi (marzo), e' in tabella E
    ha l'etichetta sulla mappa: strutturale, non scartabile."""
    mctx = _render(eng, profondo, 3)
    assert any(r.get("_group") == "vergine" for r in mctx["table"])
    assert any(key == "__group__vergine" for (_bx, key) in eng._last_label_boxes)
