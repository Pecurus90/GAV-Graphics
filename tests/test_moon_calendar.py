"""
TEST DI COERENZA INCROCIATA — illuminazione giornaliera (moon_days).

moon_days dice "il giorno X la Luna e' illuminata al frac%". Lo verifichiamo per
DUE vie indipendenti, mai contro se' stesso:

1. ELONGAZIONE Sole-Luna. La frazione illuminata e' legata alla separazione
   angolare geocentrica psi fra Sole e Luna: f = (1 - cos psi)/2. E' un calcolo
   di effemeridi DIVERSO da skyfield.almanac.fraction_illuminated (che usa
   l'angolo di fase visto dalla Luna): plenilunio (psi~180) -> ~1.0, novilunio
   (psi~0) -> ~0.0, quarto (psi~90) -> ~0.5.

2. COERENZA con moon_phases. Nel giorno del plenilunio dichiarato l'illuminazione
   e' quasi massima nel mese; nel novilunio quasi minima; ai quarti ~0.5 e col
   verso giusto (primo quarto crescente, ultimo calante).

*** RISCHIO RESIDUO ACCETTATO ***
Come per gli altri test lunari: NON catturerebbero un errore DENTRO skyfield.
Catturano gli errori NOSTRI (ora di riferimento, verso crescente/calante,
incrocio con le date delle fasi, sfasamento di un giorno).
"""
import calendar
import json
import os
import re
from datetime import datetime

import numpy as np
import pytz

TZ = pytz.timezone("Europe/Rome")
HOUR = 23  # l'ora di riferimento del volantino: la STESSA che usa moon_days

# Mesi con copertura DST esplicita (come test_moon): solare + legale.
MESI = [(2026, 1), (2026, 2), (2026, 7), (2026, 8)]

# --- Tolleranze, motivate ---
# Cross-check elongazione. Misurato max |f_engine - f_elong| = 0.00141 su
# gen/feb/lug/ago 2026. La differenza e' fisica: l'elongazione geocentrica psi
# non e' l'angolo di fase vero (il Sole e' a distanza finita: correzione di
# parallasse <= ~0.15 gradi -> Delta f <= ~0.0015). 0.005 = ~3.5x margine, e
# resta stretto abbastanza da prendere uno sfasamento di un giorno (Delta f fino
# a ~0.11) o un'etichetta scambiata.
TOL_ELONG = 0.005
# Giorno di plenilunio/novilunio: l'illuminazione dev'essere quasi estrema.
FULL_MIN, NEW_MAX = 0.98, 0.02
# Banda ai quarti. Misurato max |frac-0.5| = 0.087 (ago, ultimo quarto): il
# quarto ESATTO non cade alle 23:00 e vicino al quarto l'illuminazione varia
# ~0.1/giorno, quindi un divario di sotto-giornata sposta frac fino a ~0.09.
# 0.12 lo copre con margine; a discriminare e' il VERSO (crescente/calante).
QUART_BAND = 0.12


def _f_da_elongazione(eng, year, month, day):
    """Frazione illuminata per via INDIPENDENTE: dalla separazione angolare
    geocentrica Sole-Luna, allo stesso istante che usa moon_days (23:00 locali)."""
    t = eng.ts.from_datetime(TZ.localize(datetime(year, month, day, HOUR, 0)))
    e = eng.eph["earth"].at(t)
    sun = e.observe(eng.eph["sun"]).apparent()
    moon = e.observe(eng.eph["moon"]).apparent()
    psi = sun.separation_from(moon).degrees
    return (1.0 - np.cos(np.radians(psi))) / 2.0


def test_illuminazione_coerente_con_elongazione(eng):
    """f(engine) deve combaciare con f dedotta dall'elongazione, giorno per
    giorno, entro TOL_ELONG. Due percorsi di effemeridi diversi: se moon_days
    usasse l'ora sbagliata o un giorno sbagliato, qui salterebbe fuori."""
    controllati = 0
    peggiore = 0.0
    for year, month in MESI:
        for d, frac, _wax, _pk in eng.moon_days(year, month, TZ, HOUR):
            diff = abs(frac - _f_da_elongazione(eng, year, month, d))
            peggiore = max(peggiore, diff)
            assert diff < TOL_ELONG, (
                f"{year}-{month:02d} giorno {d}: illuminazione incoerente con "
                f"l'elongazione: |{frac:.4f} - elong| = {diff:.4f} >= {TOL_ELONG}"
            )
            controllati += 1
    assert controllati >= 100, f"troppi pochi giorni controllati: {controllati}"
    print(f"\n  max scarto illuminazione-elongazione: {peggiore:.5f} (tol {TOL_ELONG})")


def test_illuminazione_coerente_con_moon_phases(eng):
    """Nel giorno del plenilunio dichiarato l'illuminazione e' quasi massima nel
    mese (e il massimo cade entro +-1 giorno: l'evento non e' alle 23:00). Idem
    novilunio->minimo. Ai quarti: ~0.5 e col verso giusto."""
    for year, month in MESI:
        giorni = eng.moon_days(year, month, TZ, HOUR)
        frac = {d: f for d, f, _w, _k in giorni}
        wax = {d: w for d, _f, w, _k in giorni}
        pk = {d: k for d, _f, _w, k in giorni}
        gmax = max(frac, key=frac.get)
        gmin = min(frac, key=frac.get)
        for d, key in pk.items():
            if key is None:
                continue
            if key == "full":
                assert frac[d] >= FULL_MIN, f"{year}-{month:02d}: plenilunio g{d} frac={frac[d]:.3f} < {FULL_MIN}"
                assert abs(d - gmax) <= 1, f"{year}-{month:02d}: plenilunio g{d} lontano dal massimo g{gmax}"
            elif key == "new":
                assert frac[d] <= NEW_MAX, f"{year}-{month:02d}: novilunio g{d} frac={frac[d]:.3f} > {NEW_MAX}"
                assert abs(d - gmin) <= 1, f"{year}-{month:02d}: novilunio g{d} lontano dal minimo g{gmin}"
            elif key == "first":
                assert wax[d] is True, f"{year}-{month:02d}: primo quarto g{d} dovrebbe essere crescente"
                assert abs(frac[d] - 0.5) < QUART_BAND, f"{year}-{month:02d}: primo quarto g{d} frac={frac[d]:.3f}"
            elif key == "last":
                assert wax[d] is False, f"{year}-{month:02d}: ultimo quarto g{d} dovrebbe essere calante"
                assert abs(frac[d] - 0.5) < QUART_BAND, f"{year}-{month:02d}: ultimo quarto g{d} frac={frac[d]:.3f}"


def test_phase_key_incrocia_moon_phases(eng):
    """I giorni marcati con phase_key devono coincidere ESATTAMENTE con le date
    di moon_phases; tutti gli altri giorni devono avere phase_key None."""
    for year, month in MESI:
        atteso = {int(dt.split("/")[0]): key for _nm, key, dt in eng.moon_phases(year, month, TZ)}
        nm = calendar.monthrange(year, month)[1]
        ottenuto = {d: k for d, _f, _w, k in eng.moon_days(year, month, TZ, HOUR) if k is not None}
        assert ottenuto == atteso, (
            f"{year}-{month:02d}: phase_key incoerente con moon_phases.\n"
            f"  atteso:   {atteso}\n  ottenuto: {ottenuto}"
        )
        # e nessun giorno spurio marcato
        marcati = sum(1 for d, _f, _w, k in eng.moon_days(year, month, TZ, HOUR) if k is not None)
        assert marcati == len(atteso) <= nm


# --- NON-VACUITA': i test devono FALLIRE su dati guasti ---

def test_non_vacuita_sfasamento_di_un_giorno(eng):
    """Guasto iniettato: illuminazione SFASATA di un giorno. Il cross-check con
    l'elongazione DEVE respingerla (altrimenti il test non verificherebbe nulla)."""
    year, month = 2026, 8
    veri = [f for _d, f, _w, _k in eng.moon_days(year, month, TZ, HOUR)]
    sfasati = veri[1:] + veri[:1]  # ruota di un giorno
    giorni = [d for d, _f, _w, _k in eng.moon_days(year, month, TZ, HOUR)]
    peggiore = max(abs(fs - _f_da_elongazione(eng, year, month, d))
                   for d, fs in zip(giorni, sfasati))
    assert peggiore >= TOL_ELONG, (
        "il cross-check NON ha visto lo sfasamento di un giorno: sarebbe vacuo"
    )


def test_cinque_fasi_non_escono_dalla_tela(eng, root, tmp_path):
    """Mesi con 5 fasi principali (due lune nuove/piene) esistono: maggio 2026
    ne ha 5. Le etichette, ancorate alla COLONNA del giorno, devono restare TUTTE
    dentro la tela (il bug vecchio, a colonne fisse, ne spingeva la quinta fuori)."""
    # 1) maggio 2026 ha davvero 5 fasi principali
    assert len(eng.moon_phases(2026, 5, TZ)) == 5, "maggio 2026 dovrebbe avere 5 fasi"

    # 2) rende un calendario a riga da 31 con le etichette delle fasi
    W = 1080
    layout = {"canvas": {"w": W, "h": 200, "font_family": "Arial"}, "blocks": [{
        "type": "moon_calendar", "cols": 31,
        "x0": 71.6, "y0": 60, "col_gap": 31.22, "row_gap": 0, "radius": 10.5,
        "base": {"fill": "panel", "stroke": "border2", "stroke_width": 0.8},
        "lit_fill": "moon_lit",
        "phase_labels": {"y": 120, "fill": "moon_label", "size": 12,
                         "content": "{day} {name}",
                         "names": {"new": "Luna Nuova", "first": "Primo Q.",
                                   "full": "Luna Piena", "last": "Ultimo Q."}}}]}
    theme = json.load(open(os.path.join(root, "brand", "palettes", "osservatorio.json"), encoding="utf-8"))
    out = str(tmp_path / "maggio.svg")
    eng.generate(2026, 5, 45.5455, 11.5353, "Vicenza", theme, out, layout=layout)
    svg = open(out, encoding="utf-8").read()

    # 3) ci sono 5 etichette di fase, e ogni x sta dentro [0, W]
    etichette = re.findall(r'<text x="([\d.]+)"[^>]*>\d+ (?:Luna|Primo|Ultimo)', svg)
    assert len(etichette) == 5, f"attese 5 etichette di fase, trovate {len(etichette)}"
    for x in map(float, etichette):
        assert 0 <= x <= W, f"etichetta di fase fuori tela: x={x} (tela {W})"


def test_non_vacuita_verso_invertito(eng):
    """Guasto iniettato: crescente/calante INVERTITO. Il controllo del verso ai
    quarti DEVE respingerlo."""
    year, month = 2026, 8
    preso = False
    for d, _f, wax, key in eng.moon_days(year, month, TZ, HOUR):
        if key in ("first", "last"):
            wax_guasto = not wax
            atteso_crescente = (key == "first")
            # con il verso invertito, l'asserzione del test reale fallirebbe:
            assert wax_guasto != atteso_crescente
            preso = True
    assert preso, "nessun quarto nel mese di prova: guasto non esercitato"
