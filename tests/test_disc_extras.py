"""
Extra del disco social (#6i): corona di sole tacche, anti-collisione deterministica.
"""
import json
import os
import re


def _theme(root, name="osservatorio"):
    return json.load(open(os.path.join(root, "brand", "palettes", f"{name}.json"), encoding="utf-8"))


def _disc(eng, root, **kw):
    theme = _theme(root)
    lst, lat_rad, _ = eng.sky_context(2026, 8, 45.5455, 11.5353)
    return eng.sky_disc_svg(450.0, 500.0, 384.0, lst, lat_rad, theme, **kw)


def test_corona_tacche_senza_numeri(eng, root):
    """La corona accesa aggiunge tacche (<line>) e NESSUN numero: a 1080 i numeri
    sono rumore (deciso da Marco). Confronto: piu' linee con le tacche, stesso
    numero di <text> (nessuna cifra nuova)."""
    base = _disc(eng, root)
    con = _disc(eng, root, ticks={"minor": 10, "major": 30})
    assert con.count("<line") == base.count("<line") + 36, "attese 36 tacche (360/10)"
    # nessun <text> in piu' (niente numeri) e nessun testo puramente numerico nuovo
    assert con.count("<text") == base.count("<text")
    tacca_numeri = [t for t in re.findall(r'<text[^>]*>(.*?)</text>', con) if t.strip().isdigit()]
    assert tacca_numeri == [], f"la corona non deve avere numeri: {tacca_numeri}"


def test_anticollisione_deterministica(eng, root):
    """Stessa data ⇒ stesso disco (invariante #6): l'anti-collisione non usa
    caso ne' ordine instabile."""
    a = _disc(eng, root, declutter=True, star_names=["Vega", "Antares", "Polare"])
    b = _disc(eng, root, declutter=True, star_names=["Vega", "Antares", "Polare"])
    assert a == b


def test_polare_nominata_quando_su(eng, root):
    """La Polare (fioca ma serve a orientarsi) va nominata: dal Nord Italia e'
    sempre sopra l'orizzonte, quindi il suo nome deve comparire."""
    svg = _disc(eng, root, declutter=True, star_names=["Polare", "Vega"])
    assert re.search(r'>\s*Polare\s*<', svg), "la Polare dovrebbe essere etichettata"
