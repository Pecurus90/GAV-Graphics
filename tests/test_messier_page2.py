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


def _render(eng, profondo, month, const_mode=None):
    """Rende i simboli/etichette di un mese e restituisce il contesto Messier.
    Gli effetti (box, contatori) restano su `eng._last_*`. `const_mode`
    sovrascrive il modo del terzo strato (nomi costellazioni) del blocco."""
    layout, theme, sym_block = profondo
    if const_mode is not None:
        sym_block = {**sym_block, "const_names": const_mode}
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


# ---------------------------------------------------------------------------
# TERZO STRATO (#7d): i NOMI delle costellazioni. Sfondo semantico, priorita'
# minima. La rete: un nome non copre MAI un simbolo, una sigla Messier o un
# altro nome. Testata nel modo piu' DENSO ('tutte'): se regge li', regge sempre.
# ---------------------------------------------------------------------------
CONST_MODI = ["tabella", "tutte"]


@pytest.mark.parametrize("month", MESI)
@pytest.mark.parametrize("mode", CONST_MODI)
def test_nome_costellazione_non_copre_simbolo(eng, profondo, month, mode):
    """Nessun box nome-costellazione interseca un box-simbolo Messier."""
    _render(eng, profondo, month, const_mode=mode)
    consts = eng._last_const_label_boxes
    symbols = eng._last_symbol_boxes
    assert symbols, "attesi dei simboli Messier"
    guasti = [(ab, i) for (bx, ab) in consts
              for i, sb in enumerate(symbols) if _inter(bx, sb)]
    assert not guasti, f"mese {month}/{mode}: nomi sopra simboli: {guasti}"


@pytest.mark.parametrize("month", MESI)
@pytest.mark.parametrize("mode", CONST_MODI)
def test_nome_costellazione_non_copre_sigla(eng, profondo, month, mode):
    """Nessun box nome-costellazione interseca un box-sigla Messier (Mxx).
    E' la subordinazione tipografica resa MISURABILE: lo sfondo non tocca il
    contenuto."""
    _render(eng, profondo, month, const_mode=mode)
    consts = eng._last_const_label_boxes
    siglas = eng._last_label_boxes
    guasti = [(ab, key) for (bx, ab) in consts
              for (sb, key) in siglas if _inter(bx, sb)]
    assert not guasti, f"mese {month}/{mode}: nomi sopra sigle: {guasti}"


@pytest.mark.parametrize("month", MESI)
@pytest.mark.parametrize("mode", CONST_MODI)
def test_nomi_costellazione_non_si_sovrappongono(eng, profondo, month, mode):
    """Nessun box nome-costellazione interseca un altro nome-costellazione."""
    _render(eng, profondo, month, const_mode=mode)
    cb = eng._last_const_label_boxes
    guasti = [(cb[i][1], cb[j][1]) for i in range(len(cb)) for j in range(i + 1, len(cb))
              if _inter(cb[i][0], cb[j][0])]
    assert not guasti, f"mese {month}/{mode}: nomi sovrapposti: {guasti}"


@pytest.mark.parametrize("month", MESI)
@pytest.mark.parametrize("mode", CONST_MODI)
def test_terzo_strato_non_disturba_messier(eng, profondo, month, mode):
    """Il terzo strato e' SUBORDINATO: aggiungerlo non tocca ne' gli scarti
    Messier (D9: sempre 0) ne' il patto sigle<->tabella. E' la garanzia che i
    nomi si piazzano DOPO, senza rubare il posto a una sigla."""
    mctx = _render(eng, profondo, month, const_mode=mode)
    assert eng._last_messier_dropped == 0, \
        f"mese {month}/{mode}: il terzo strato ha causato {eng._last_messier_dropped} scarti Messier"
    su_mappa = {key for (_bx, key) in eng._last_label_boxes}
    in_tabella = {("__group__" + r["_group"]) if r.get("_group") else r["sigla"]
                  for r in mctx["table"]}
    assert su_mappa == in_tabella, f"mese {month}/{mode}: patto D9 rotto dal terzo strato"


def test_modo_no_non_disegna_nomi(eng, profondo):
    """Con const_names='no' (default storico) il terzo strato non esiste: nessun
    box nome. E' la garanzia che 'no' resta possibile (D7: il file decide)."""
    _render(eng, profondo, 3, const_mode="no")
    assert eng._last_const_label_boxes == []
    assert eng._last_const_dropped == []


# ---------------------------------------------------------------------------
# #7d-bis: il nome sta DENTRO la sua figura, mai in deriva. Questa e' la
# guardia contro la "soluzione" di un domani che allarga il raggio di ricerca
# per chiudere gli scarti: farebbe galleggiare i nomi lontano dalle figure.
# Deve diventare ROSSA se l'ancora esce dal riquadro dei vertici della figura.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("month", MESI)
@pytest.mark.parametrize("mode", CONST_MODI)
def test_nome_non_lontano_dalla_figura(eng, profondo, month, mode):
    """Anti-deriva (#7d-ter): un nome puo' sfiorare la propria figura di un
    margine PICCOLO e proporzionato (`margin`), MAI di piu'. L'ancora deve stare
    nel riquadro dei vertici ESPANSO di quel margine. Diventa rossa se qualcuno
    "risolve" gli scarti allargando la ricerca: e' la guardia contro la
    scorciatoia. La soglia e' proporzionata, non fissa (una figura grande resta
    stretta, una minuscola puo' sporgere)."""
    _render(eng, profondo, month, const_mode=mode)
    placed = eng._last_const_placed
    assert placed, f"mese {month}/{mode}: nessun nome piazzato"
    eps = 0.5
    fuori = [(p["ab"], round(p["x"], 1), round(p["y"], 1), round(p["margin"], 1))
             for p in placed
             if not (p["vbbox"][0] - p["margin"] - eps <= p["x"] <= p["vbbox"][2] + p["margin"] + eps
                     and p["vbbox"][1] - p["margin"] - eps <= p["y"] <= p["vbbox"][3] + p["margin"] + eps)]
    assert not fuori, f"mese {month}/{mode}: nomi in deriva oltre il margine: {fuori}"


@pytest.mark.parametrize("month", MESI)
@pytest.mark.parametrize("mode", CONST_MODI)
def test_nome_non_dentro_altra_costellazione(eng, profondo, month, mode):
    """#7d-ter, vincolo non negoziabile: un nome non cade MAI dentro la figura
    (inviluppo convesso) di un'ALTRA costellazione. "Scudo" sopra l'Aquila e'
    una bugia, peggio di un'assenza. Se l'unico posto e' dentro il vicino, il
    codice SCARTA — quindi qui nessun nome piazzato deve violarlo."""
    mctx = _render(eng, profondo, month, const_mode=mode)
    from engine.generate import point_in_poly
    hulls = mctx["const_hulls"]
    guasti = []
    for p in eng._last_const_placed:
        for hab, poly, hb in hulls:
            if hab == p["ab"]:
                continue
            if hb[0] <= p["x"] <= hb[2] and hb[1] <= p["y"] <= hb[3] and point_in_poly(poly, p["x"], p["y"]):
                guasti.append((p["ab"], "dentro", hab))
    assert not guasti, f"mese {month}/{mode}: nomi dentro un'altra costellazione: {guasti}"


@pytest.mark.parametrize("month", MESI)
def test_zero_scarti_costellazioni_in_tabella(eng, profondo, month):
    """IL NUOVO PATTO (#7d-ter): ZERO scarti fra le costellazioni CITATE in
    tabella, in modo 'tutte'. Se una riga di tabella nomina una costellazione,
    quel nome DEVE stare sulla mappa. Mappa e tabella si guardano."""
    _render(eng, profondo, month, const_mode="tutte")
    assert eng._last_const_dropped_tab == [], (
        f"mese {month}: costellazioni in tabella senza nome sulla mappa "
        f"(patto rotto): {eng._last_const_dropped_tab}")
