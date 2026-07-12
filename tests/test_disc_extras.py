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


def _lum(hexcol):
    """Luminanza relativa (Rec.709), 0..1."""
    h = hexcol.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def test_corona_tacche_visibili(eng, root):
    """Le tacche devono VEDERSI, non solo esistere. Rende alla dimensione REALE
    della dashboard (rad 270) e, su DUE palette (il contrasto cambia col tema):
    - spessore e lunghezza sopra la soglia del rumore sub-pixel;
    - contrasto di luminanza reale col fondo su cui poggiano.
    Con il vecchio token `grid` (quasi lo sfondo) e lo spessore 0.56px questo
    test FALLISCE: e' la rete che prima mancava."""
    RAD = 270.0
    MIN_W, MIN_L, MIN_DLUM = 0.9, 4.0, 0.15
    for pal in ("notte-blu", "luce-rossa"):
        theme = _theme(root, pal)
        lst, lat_rad, _ = eng.sky_context(2026, 8, 45.5455, 11.5353)
        svg = eng.sky_disc_svg(340.0, 520.0, RAD, lst, lat_rad, theme,
                               ticks={"minor": 10, "major": 30})
        # SOLO le tacche hanno stroke/width/opacity espliciti (le linee delle
        # costellazioni ereditano dal gruppo): il match isola la corona.
        rows = re.findall(
            r'<line x1="([-\d.]+)" y1="([-\d.]+)" x2="([-\d.]+)" y2="([-\d.]+)" '
            r'stroke="([^"]+)" stroke-width="([\d.]+)" opacity="([\d.]+)"', svg)
        assert rows, f"[{pal}] nessuna tacca trovata"
        ticks = [(((float(x2) - float(x1)) ** 2 + (float(y2) - float(y1)) ** 2) ** 0.5,
                  float(w), col) for x1, y1, x2, y2, col, w, op in rows]
        minlen = min(t[0] for t in ticks)
        minor = [t for t in ticks if t[0] - minlen < 0.5]  # le piu' corte
        w_min = min(t[1] for t in minor)
        col = minor[0][2]
        assert w_min >= MIN_W, f"[{pal}] tacca minore sub-pixel: spessore {w_min:.2f}px < {MIN_W}"
        assert minlen >= MIN_L, f"[{pal}] tacca minore troppo corta: {minlen:.2f}px < {MIN_L}"
        dlum = abs(_lum(col) - _lum(theme["bg"][0]))
        assert dlum >= MIN_DLUM, (
            f"[{pal}] tacca {col} senza contrasto col fondo {theme['bg'][0]}: "
            f"dLum={dlum:.3f} < {MIN_DLUM} (invisibile)")


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


def test_star_names_dei_layout_sono_nel_catalogo(root):
    """Ogni stella citata in un layout deve esistere nel catalogo STARS: un
    refuso ('Mizzar') qui salta subito, invece di sparire in silenzio dal disco."""
    import glob
    from engine.generate import STARS
    for lp in glob.glob(os.path.join(root, "brand", "layouts", "*.json")):
        layout = json.load(open(lp, encoding="utf-8"))
        for b in layout.get("blocks", []):
            for nm in b.get("star_names", []):
                assert nm in STARS, f"{os.path.basename(lp)}: stella '{nm}' non nel catalogo STARS"


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
