"""
Validazione input (R4) e contratto del tema (D2), in un solo posto condiviso.
"""
import copy
import json
import os

import pytest

import validate as V


def _osservatorio(root):
    return json.load(open(os.path.join(root, "brand", "palettes", "osservatorio.json"), encoding="utf-8"))


# ---------------------------------------------------------------------------
# R4 — input
# ---------------------------------------------------------------------------
def test_input_validi_passano():
    assert V.valida_anno("2026") == 2026
    assert V.valida_mese("8") == 8
    assert V.valida_lat("45.5") == 45.5
    assert V.valida_lon("11.5") == 11.5


@pytest.mark.parametrize("fn,val", [
    (V.valida_mese, "13"), (V.valida_mese, "0"), (V.valida_mese, "abc"),
    (V.valida_anno, "3000"), (V.valida_anno, "abc"),
    (V.valida_lat, "abc"), (V.valida_lat, "120"),
    (V.valida_lon, "abc"), (V.valida_lon, "999"),
])
def test_input_sbagliati_alzano_inputerror(fn, val):
    with pytest.raises(V.InputError):
        fn(val)


def test_messaggi_in_italiano():
    """Invariante #5: gli errori sono in italiano, non un traceback inglese."""
    with pytest.raises(V.InputError) as e:
        V.valida_mese("13")
    assert "Mese fuori intervallo" in str(e.value)


def test_formato_e_palette_sconosciuti():
    with pytest.raises(V.InputError):
        V.valida_formato("storia")
    with pytest.raises(V.InputError):
        V.valida_palette("arcobaleno")


# ---------------------------------------------------------------------------
# D2 — contratto del tema
# ---------------------------------------------------------------------------
def test_tutte_le_palette_reali_passano(root):
    for name in V.palette_disponibili():
        th = json.load(open(os.path.join(root, "brand", "palettes", f"{name}.json"), encoding="utf-8"))
        V.valida_tema(th, f"{name}.json")  # non deve alzare


def test_chiave_mancante_dice_quale_e_dove(root):
    th = _osservatorio(root)
    del th["gold"]
    with pytest.raises(V.InputError) as e:
        V.valida_tema(th, "rotta.json")
    msg = str(e.value)
    assert "rotta.json" in msg and "gold" in msg  # QUALE chiave e in QUALE file


def test_status_incompleto(root):
    th = _osservatorio(root)
    del th["status"]["muted"]
    with pytest.raises(V.InputError) as e:
        V.valida_tema(th, "x.json")
    assert "status.muted" in str(e.value)


def test_planet_colors_mancante(root):
    th = _osservatorio(root)
    del th["planet_colors"]["Marte"]
    with pytest.raises(V.InputError) as e:
        V.valida_tema(th, "x.json")
    assert "planet_colors.Marte" in str(e.value)


# --- FISICA della rampa ---
def test_star_ramp_fisica_debole_passa_con_i_plateau(root):
    """La rampa reale satura a 255 (plateau): la monotonia e' DEBOLE. Un contratto
    che pretendesse monotonia STRETTA la respingerebbe pur essendo corretta."""
    th = _osservatorio(root)
    R = [int(c[1][1:3], 16) for c in th["star_ramp"]]
    assert any(R[i + 1] == R[i] for i in range(len(R) - 1)), "atteso almeno un plateau nel rosso"
    V.valida_tema(th, "osservatorio.json")  # passa lo stesso


def test_star_ramp_colori_invertiti_e_fisica_falsa(root):
    """B-V crescente ma colori rovesciati: rosso in calo -> mente sull'astronomia."""
    th = _osservatorio(root)
    bvs = [s[0] for s in th["star_ramp"]]
    cols = [s[1] for s in th["star_ramp"]][::-1]
    th["star_ramp"] = [[bv, c] for bv, c in zip(bvs, cols)]
    with pytest.raises(V.InputError) as e:
        V.valida_tema(th, "x.json")
    assert "ROSSO" in str(e.value)


def test_star_ramp_asse_bv_non_crescente(root):
    th = _osservatorio(root)
    th["star_ramp"] = list(reversed(th["star_ramp"]))
    with pytest.raises(V.InputError) as e:
        V.valida_tema(th, "x.json")
    assert "B-V" in str(e.value)


def test_planet_colors_marte_non_rosso(root):
    th = _osservatorio(root)
    th["planet_colors"]["Marte"] = "#3f6cb5"  # blu: fisicamente falso
    with pytest.raises(V.InputError) as e:
        V.valida_tema(th, "x.json")
    assert "Marte" in str(e.value)


# ---------------------------------------------------------------------------
# D13 — contratto del tema PER-STRUMENTO. Il secondo strumento (generico) e'
# SIMULATO con CONTRATTO_MARCA: niente file di Pillole in anticipo.
# ---------------------------------------------------------------------------
def test_cielo_rifiuta_palette_senza_star_ramp(root):
    """Il cuore di D13: una palette senza star_ramp non puo' disegnare il cielo.
    Il contratto del CIELO la rifiuta, e l'errore nomina lo strumento."""
    th = _osservatorio(root)
    del th["star_ramp"]
    with pytest.raises(V.InputError) as e:
        V.valida_tema(th, "x.json")  # default = CONTRATTO_CIELO
    msg = str(e.value)
    assert "star_ramp" in msg and "Cielo del Mese" in msg


def test_strumento_generico_accetta_palette_senza_astronomia(root):
    """L'altra meta' di D13: uno strumento che NON disegna il cielo non deve
    rifiutare una palette a cui mancano le chiavi d'astronomia. Stessa palette
    del test sopra, contratto generico: passa."""
    th = _osservatorio(root)
    del th["star_ramp"]
    del th["planet_colors"]
    del th["disk"]
    V.valida_tema(th, "x.json", contratto=V.CONTRATTO_MARCA)  # non deve alzare


def test_generico_pretende_comunque_la_marca(root):
    """Il contratto generico molla l'astronomia, NON la marca: una palette senza
    una chiave di marca (gold) viene rifiutata anche dallo strumento generico."""
    th = _osservatorio(root)
    del th["gold"]
    with pytest.raises(V.InputError) as e:
        V.valida_tema(th, "rotta.json", contratto=V.CONTRATTO_MARCA)
    assert "rotta.json" in str(e.value) and "gold" in str(e.value)
