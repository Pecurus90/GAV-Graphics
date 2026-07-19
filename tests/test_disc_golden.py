"""
TEST GOLDEN DEL SOLO DISCO — snapshot del frammento sky_disc_svg reso da solo.

Perche' separato dal golden A4: il golden A4 sorveglia disco + composizione
INSIEME. Per D7 la composizione diventa dati (file di layout) e cambiera' a ogni
ritocco estetico legittimo; la geometria del disco NO. Questo golden isola la
guardia sul rendering del disco, cosi' in #5c potremo cambiare le composizioni
a occhio senza perdere la rete sulla matematica del disco.

*** NON dimostra che il disco sia CORRETTO *** (quello e' test_correctness.py):
dimostra che il suo RENDERING non e' cambiato.

Confronto in modalita' testo (newline universali) come test_golden; il blob del
riferimento e' forzato a LF da .gitattributes.

Parametri canonici (uguali al golden A4, cosi' il frammento e' letteralmente una
fetta dell'A4): anno 2026, mese 8, lat 45.5455, lon 11.5353, tema osservatorio,
disco a (cx,cy,rad)=(450,500,360). (rad 384->360 col giro dei formati 2026-07-19:
l'A4 rimpicciolito per liberare i cardinali N/S -- deciso da Marco.)
"""
import json
import os

import pytest

from golden_compare import svg_diff  # confronto a TOLLERANZA (D5)

GOLDEN = os.path.join(os.path.dirname(__file__), "golden", "disc_2026-08_vicenza.svg")

# Parametri canonici del disco. NON cambiarli senza rigenerare il golden apposta.
DISC = dict(year=2026, month=8, lat=45.5455, lon=11.5353, cx=450.0, cy=500.0, rad=360.0)

# Corona di tacche del disco social (niente numeri). Il golden del disco ora
# sorveglia il disco SOCIAL: anti-collisione delle etichette + tacche. Le stelle
# restano quelle del MARQUEE (star_names=None) e le costellazioni tutte, cosi'
# cambiano SOLO etichette e tacche, non le posizioni di stelle/linee.
TICKS = {"minor": 10, "major": 30}


def _theme(root):
    return json.load(open(os.path.join(root, "brand", "palettes", "osservatorio.json"),
                          encoding="utf-8"))


def _fragment(eng, theme, social=False):
    """Il frammento del SOLO disco, agli stessi parametri del golden A4. Con
    social=True accende anti-collisione + tacche (cio' che il disc-golden ora
    sorveglia); senza, e' il disco ingenuo che resta una fetta VERBATIM dell'A4.
    (Le tacche furono aggiunte all'A4 in commit 5 e TOLTE subito dopo: sulla
    striscia di 16 px la tacca Sud tagliava la legenda -- vedi CLAUDE.md.)"""
    lst, lat_rad, _ = eng.sky_context(DISC["year"], DISC["month"], DISC["lat"], DISC["lon"])
    if social:
        return eng.sky_disc_svg(DISC["cx"], DISC["cy"], DISC["rad"], lst, lat_rad, theme,
                                declutter=True, ticks=TICKS)
    return eng.sky_disc_svg(DISC["cx"], DISC["cy"], DISC["rad"], lst, lat_rad, theme)


def disc_document(eng, theme):
    """Il frammento reso come SVG autonomo: defs (gradienti/glow) + disco, dentro
    un <svg> di cornice. E' cio' che un compositore assembla per il disco da solo.
    Funzione pubblica: la usa anche lo script che (ri)genera il golden."""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="900" height="950" '
            f'viewBox="0 0 900 950" font-family="Helvetica,Arial,sans-serif">\n'
            + eng.defs_svg(theme) + '\n'
            + _fragment(eng, theme, social=True) + '\n'
            + '</svg>')


def test_disc_golden_invariato(eng, root):
    """Rende il disco da solo e lo confronta col riferimento. Se fallisce: il
    rendering del disco e' cambiato. Capire SE e' voluto; se lo e', rigenerare
    il golden del disco apposta e committarlo a parte."""
    assert os.path.exists(GOLDEN), (
        f"Riferimento disc-golden mancante: {GOLDEN}. Rigeneralo e committalo.")
    atteso = open(GOLDEN, encoding="utf-8").read()
    ottenuto = disc_document(eng, _theme(root))
    msg = svg_diff(ottenuto, atteso)
    if msg:
        pytest.fail("Disco divergente dal golden oltre la tolleranza numerica.\n" + msg)


def test_disc_e_fetta_dell_a4(eng, root, tmp_path):
    """Invariante D7: il disco sigillato compare VERBATIM dentro l'A4 (la
    composizione lo scala e lo posiziona, non lo ridisegna). Confronto fra due
    generazioni FRESCHE dello STESSO run (frammento + A4): e' una relazione
    STRUTTURALE, esatta su qualunque piattaforma. NON si legge il file golden
    A4 (generato su Windows): la sua deriva d'ultima-cifra su un altro OS
    (D5/CI) rifarebbe scattare la mina, mentre qui non c'entra nulla."""
    theme = _theme(root)
    out = str(tmp_path / "a4.svg")
    eng.generate(DISC["year"], DISC["month"], DISC["lat"], DISC["lon"], "Vicenza",
                 theme, out)                      # layout di default = A4
    a4 = open(out, encoding="utf-8").read()
    frag = _fragment(eng, theme)                  # disco "naive", come nell'A4 (senza tacche)
    assert frag in a4, "Il disco non e' piu' una fetta VERBATIM dell'A4 (invariante D7)."


def test_disc_generazione_deterministica(eng, root):
    """Due rendering di fila devono essere identici: il disco non ha rumore
    casuale (a differenza dello sfondo A4), quindi deve essere deterministico."""
    theme = _theme(root)
    assert disc_document(eng, theme) == disc_document(eng, theme), \
        "Rendering del disco non deterministico."
