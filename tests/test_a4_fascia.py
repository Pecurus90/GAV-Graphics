"""
La fascia inferiore dell'A4, ridisegno del designer (proposta B, #7h).

Due corsie orizzontali: i 7 pianeti in parata SOPRA, la striscia lunare 1->31
SOTTO, un divisore in mezzo. E' cio' che risolve la collisione R10 (fasi lunari
a tutta larghezza che si sovrapponevano ai pianeti). Questa rete vieta che le due
corsie tornino a condividere spazio verticale.
"""
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def _a4():
    return json.load(open(os.path.join(ROOT, "brand", "layouts", "a4.json"), encoding="utf-8"))


def _block(layout, tipo):
    return next(b for b in layout["blocks"] if b.get("type") == tipo)


def test_parata_e_striscia_lunare_non_si_intersecano():
    """Le due corsie NON devono condividere spazio verticale (R10): la banda dei
    pianeti (dal pallino in cima all'ultima riga di nota) deve finire PRIMA che
    cominci quella della striscia lunare. Diventa rosso se qualcuno rimette i due
    contenuti nello stesso spazio (es. sposta la striscia su nella parata)."""
    a4 = _a4()
    par = _block(a4, "planet_parade")
    moon = _block(a4, "moon_calendar")
    par_top = par["cy_dot"] - par["r"]
    par_bot = par["cy_dot"] + max(par[k]["dy"] for k in ("name", "rise", "set", "note1", "note2") if k in par)
    moon_top = moon["y0"] - moon["radius"]
    moon_bot = moon["phase_labels"]["y"]
    assert par_top < par_bot <= moon_top < moon_bot, (
        f"le corsie si sovrappongono: pianeti [{par_top}, {par_bot}], "
        f"luna [{moon_top}, {moon_bot}]. Devono stare in bande separate (R10).")


def test_striscia_lunare_a4_rende_31_giorni(eng, root, tmp_path):
    """La striscia lunare dell'A4 e' il blocco moon_calendar (lo stesso del
    dashboard) adattato alla larghezza: agosto ha 31 giorni, deve disegnare 31
    numeri 1..31. Test sul conteggio, non a occhio."""
    theme = json.load(open(os.path.join(root, "brand", "palettes", "osservatorio.json"),
                           encoding="utf-8"))
    a4 = _a4()
    out = str(tmp_path / "a4.svg")
    eng.generate(2026, 8, 45.5455, 11.5353, "Vicenza", theme, out, layout=a4)
    svg = open(out, encoding="utf-8").read()
    moon = _block(a4, "moon_calendar")
    ynum = moon["y0"] + moon["day_number"]["dy"]            # riga dei numeri dei giorni
    nums = re.findall(rf'<text[^>]*y="{ynum:.2f}"[^>]*>(\d+)</text>', svg)
    assert sorted(int(n) for n in nums) == list(range(1, 32)), \
        f"attesi 31 giorni (1..31), trovati {sorted(int(n) for n in nums)}"
