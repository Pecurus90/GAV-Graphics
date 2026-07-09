"""
TEST DI CORRETTEZZA — validano la matematica del motore contro riferimenti
astronomici/geometrici INDIPENDENTI, MAI contro l'output del nostro codice.

Ogni test dichiara: da dove viene il valore atteso e con quale tolleranza.
Se uno fallisce, NON aggiustare il test né il codice: potrebbe essere un bug
reale. Segnalarlo (vedi CLAUDE.md, metodo di lavoro).

Coprono: altaz, project, sky_context (tempo siderale), bv2hex.
Funzioni NON coperte / scoperte: vedi il report del task.
"""
import math

import numpy as np
import pytest

from engine.generate import bv2hex

VICENZA_LAT = 45.5455  # gradi


def _f(x):
    """altaz/project restituiscono array/scalari numpy: normalizzo a float."""
    return float(np.asarray(x).reshape(-1)[0])


def _ang_dist_deg(a, b):
    """Distanza angolare minima fra due azimut in gradi (gestisce il wrap 0/360)."""
    d = (a - b) % 360.0
    return min(d, 360.0 - d)


# ---------------------------------------------------------------------------
# altaz(ra_deg, dec_deg, lst_hours, lat_rad) -> (alt_deg, az_deg)
# ---------------------------------------------------------------------------

def test_altaz_polo_altezza_uguale_latitudine(eng):
    """RIFERIMENTO: teorema di astronomia sferica. Una stella al polo celeste
    nord (dec = +90) ha altezza ESATTAMENTE uguale alla latitudine
    dell'osservatore, per qualsiasi ora siderale (sin(alt)=sin(lat)).
    Tolleranza 1e-4 gradi (identita' esatta, solo errore numerico)."""
    lat = math.radians(VICENZA_LAT)
    for lst in (0.0, 6.0, 13.3, 21.7):
        alt, _ = eng.altaz(123.0, 90.0, lst, lat)  # RA irrilevante al polo
        assert _f(alt) == pytest.approx(VICENZA_LAT, abs=1e-4)


def test_altaz_transito_a_sud_dec_minore_latitudine(eng):
    """RIFERIMENTO: al transito al meridiano (angolo orario = 0) l'altezza vale
    90 - |lat - dec| e l'azimut e' 180 (sud) se la stella e' a sud dello zenit
    (dec < lat). Impongo HA=0 con lst_hours = RA/15.
    lat=45, dec=20 -> alt=65, az=180. Tolleranze: alt 0.01, az 0.02."""
    lat = math.radians(45.0)
    alt, az = eng.altaz(180.0, 20.0, 12.0, lat)  # RA=180 -> lst=12h -> HA=0
    assert _f(alt) == pytest.approx(65.0, abs=0.01)
    assert _ang_dist_deg(_f(az), 180.0) < 0.02


def test_altaz_transito_a_nord_dec_maggiore_latitudine(eng):
    """RIFERIMENTO: stessa legge del transito, ma con dec > lat la stella
    culmina a NORD dello zenit -> azimut 0. lat=45, dec=70 -> alt=65, az=0.
    Tolleranze: alt 0.01, az 0.02."""
    lat = math.radians(45.0)
    alt, az = eng.altaz(180.0, 70.0, 12.0, lat)
    assert _f(alt) == pytest.approx(65.0, abs=0.01)
    assert _ang_dist_deg(_f(az), 0.0) < 0.02


def test_altaz_circumpolare_non_tramonta(eng):
    """RIFERIMENTO: da Vicenza (lat 45.55) una stella con dec > 90-lat = 44.45
    e' circumpolare: non scende MAI sotto l'orizzonte. dec=+80 -> altezza
    minima teorica = dec-(90-lat) = 35.55 > 0. Campiono 24h di ora siderale."""
    lat = math.radians(VICENZA_LAT)
    alts = [_f(eng.altaz(50.0, 80.0, lst, lat)[0]) for lst in np.linspace(0, 24, 97)]
    assert min(alts) > 0.0


def test_altaz_stella_australe_non_sorge_mai(eng):
    """RIFERIMENTO: da Vicenza una stella con dec < -(90-lat) = -44.45 non
    sorge MAI. dec=-80 -> altezza massima teorica = 90-|lat-dec| < 0.
    Campiono 24h di ora siderale."""
    lat = math.radians(VICENZA_LAT)
    alts = [_f(eng.altaz(50.0, -80.0, lst, lat)[0]) for lst in np.linspace(0, 24, 97)]
    assert max(alts) < 0.0


# ---------------------------------------------------------------------------
# project(alt, az, cx, cy, rad) -> (x, y)
# ---------------------------------------------------------------------------

CX, CY, RAD = 450.0, 500.0, 384.0


def test_project_zenit_al_centro(eng):
    """RIFERIMENTO: proiezione azimutale equidistante -> lo zenit (alt=90) cade
    esattamente al centro del disco. Identita' geometrica, tolleranza 1e-9."""
    x, y = eng.project(90.0, 0.0, CX, CY, RAD)
    assert _f(x) == pytest.approx(CX, abs=1e-9)
    assert _f(y) == pytest.approx(CY, abs=1e-9)


def test_project_orizzonte_sul_bordo_e_orientamento(eng):
    """RIFERIMENTO: invariante di orientamento di CLAUDE.md (#3): N in alto,
    E a sinistra, zenit al centro, orizzonte sul bordo. Per alt=0 il punto sta
    a distanza rad dal centro, nella direzione cardinale attesa.
      N (az=0)   -> alto   (cx, cy-rad)
      E (az=90)  -> sinistra(cx-rad, cy)
      S (az=180) -> basso  (cx, cy+rad)
      O (az=270) -> destra (cx+rad, cy)
    Geometria esatta, tolleranza 1e-6."""
    casi = {
        0.0:   (CX,        CY - RAD),  # Nord in alto
        90.0:  (CX - RAD,  CY),        # Est a sinistra
        180.0: (CX,        CY + RAD),  # Sud in basso
        270.0: (CX + RAD,  CY),        # Ovest a destra
    }
    for az, (ex, ey) in casi.items():
        x, y = eng.project(0.0, az, CX, CY, RAD)
        assert _f(x) == pytest.approx(ex, abs=1e-6)
        assert _f(y) == pytest.approx(ey, abs=1e-6)


# ---------------------------------------------------------------------------
# sky_context(...) -> (lst_hours, lat_rad, tz)   [tempo siderale locale]
# ---------------------------------------------------------------------------

def _gmst_hours_meeus(jd_ut):
    """RIFERIMENTO INDIPENDENTE: tempo siderale medio di Greenwich (GMST) dalla
    formula polinomiale di Meeus (Astronomical Algorithms, cap.12) — algoritmo
    DIVERSO da skyfield. Validato a parte contro la costante USNO tabulata
    (GMST @ 2000-01-01 00:00 UT = 6h39m52.2714s): accordo entro 0.001 s."""
    d = jd_ut - 2451545.0
    t = d / 36525.0
    g = 280.46061837 + 360.98564736629 * d + 0.000387933 * t * t - t * t * t / 38710000.0
    return (g % 360.0) / 15.0


def _jd_from_utc(y, mo, d, h, mi, s=0):
    """Giorno giuliano da data UTC (Meeus cap.7, calendario gregoriano)."""
    if mo <= 2:
        y -= 1
        mo += 12
    a = y // 100
    b = 2 - a + a // 4
    day = d + (h + mi / 60 + s / 3600) / 24
    return int(365.25 * (y + 4716)) + int(30.6001 * (mo + 1)) + day + b - 1524.5


def test_sky_context_valore_assoluto_vs_meeus(eng):
    """RIFERIMENTO: confronto del tempo siderale locale a longitudine 0 con la
    formula GMST di Meeus (indipendente). Uso GENNAIO per evitare l'ora legale:
    2000-01-15 23:00 a Roma = 22:00 UTC (CET = UTC+1, niente DST).
    A lon=0 il LST locale coincide col GST di Greenwich.
    Tolleranza 5 s: assorbe la differenza apparente-vs-medio (equazione degli
    equinozi, <=~1.1s) e UT1-UTC (<0.9s). Scopo: catturare errori GROSSOLANI
    (segno, scala, fuso: minuti/ore). Misurato in sviluppo: ~0.49 s."""
    lst, _, _ = eng.sky_context(2000, 1, VICENZA_LAT, 0.0, hour_local=23,
                                tzname="Europe/Rome")
    jd = _jd_from_utc(2000, 1, 15, 22, 0, 0)
    exp = _gmst_hours_meeus(jd)
    diff_h = ((lst - exp + 12.0) % 24.0) - 12.0  # differenza circolare con segno
    assert abs(diff_h) * 3600.0 < 5.0


def test_sky_context_longitudine_est_avanza_siderale(eng):
    """RIFERIMENTO: definizione di tempo siderale LOCALE. A parita' di istante,
    spostarsi di +15 gradi di longitudine EST anticipa il tempo siderale di
    esattamente 1 ora (LST = GST + long_est/15). Valida segno e scala del
    termine di longitudine. Tolleranza 1e-6 h (aritmetica esatta)."""
    l0, _, _ = eng.sky_context(2026, 8, 45.0, 0.0, hour_local=23)
    l15, _, _ = eng.sky_context(2026, 8, 45.0, 15.0, hour_local=23)
    assert ((l15 - l0) % 24.0) == pytest.approx(1.0, abs=1e-6)


# ---------------------------------------------------------------------------
# bv2hex(ramp, bv) -> colore esadecimale (temperatura stellare)
# ---------------------------------------------------------------------------

def _rgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


# Rampa sintetica nero->bianco: permette di verificare la MATEMATICA
# dell'interpolazione a mano, indipendente dai colori reali del tema.
RAMP_SINT = [[0.0, "#000000"], [1.0, "#ffffff"]]


def test_bv2hex_interpolazione_lineare_a_meta():
    """RIFERIMENTO: interpolazione lineare a mano. A meta' fra 0 e 255 il valore
    e' 127.5; con quantizzazione a 8 bit ci si aspetta 127 o 128 su ogni canale.
    Tolleranza +-1/canale (copre l'ambiguita' troncamento-vs-arrotondamento)."""
    r, g, b = _rgb(bv2hex(RAMP_SINT, 0.5))
    assert r == pytest.approx(127.5, abs=1.0)
    assert g == pytest.approx(127.5, abs=1.0)
    assert b == pytest.approx(127.5, abs=1.0)


def test_bv2hex_estremi_e_clamp():
    """RIFERIMENTO: semantica di clamping. Valori fuori dalla rampa mappano al
    colore di estremita'; il minimo esatto deve dare il colore iniziale.
    Tolleranza +-1/canale.
    NOTA (finding, vedi report): al MASSIMO il codice restituisce #fefefe invece
    di #ffffff (off-by-one da +1e-9 e int() troncante). Rientra nella tolleranza
    +-1; il difetto e' segnalato, NON corretto (fuori scope del task)."""
    # sotto il minimo -> colore iniziale, esatto (#000000, f=0)
    assert bv2hex(RAMP_SINT, -5.0) == "#000000"
    # estremo minimo esatto
    assert bv2hex(RAMP_SINT, 0.0) == "#000000"
    # sopra il massimo -> ~colore finale (entro +-1/canale)
    r, g, b = _rgb(bv2hex(RAMP_SINT, 5.0))
    assert (r, g, b) == pytest.approx((255, 255, 255), abs=1.0)


def test_bv2hex_monotonia_fisica_temperatura(root):
    """RIFERIMENTO: fisica dell'indice di colore B-V. B-V basso/negativo = stella
    CALDA (bluastra); B-V alto = stella FREDDA (rossastra). Quindi al crescere di
    B-V il canale ROSSO deve aumentare e il BLU diminuire. Verificato sulla rampa
    REALE del tema (non sull'output del nostro codice: e' una legge fisica)."""
    import json
    import os
    ramp = json.load(open(os.path.join(root, "brand", "palettes", "osservatorio.json"),
                          encoding="utf-8"))["star_ramp"]
    caldo = _rgb(bv2hex(ramp, -0.2))
    freddo = _rgb(bv2hex(ramp, 1.9))
    assert freddo[0] > caldo[0]   # piu' rosso da freddo
    assert caldo[2] > freddo[2]   # piu' blu da caldo
