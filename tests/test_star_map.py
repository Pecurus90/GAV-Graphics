"""
TEST END-TO-END sul catalogo reale — orientamento globale della mappa.

Il golden (test_golden.py) approva anche una mappa SBAGLIATA, purche' sia sempre
la stessa mappa sbagliata: non vedrebbe un ribaltamento o una rotazione globale.
Qui prendiamo stelle notoriamente riconoscibili dal CATALOGO reale (stars6.json)
e verifichiamo che finiscano nella zona giusta del disco a una data/ora note,
percorrendo la pipeline vera: altaz -> project, con LST da sky_context.

Fatti astronomici usati come ancore (verita' esterne, non output del codice):
- Polaris ~ polo nord celeste: altezza ~ latitudine, azimut ~ Nord -> META' ALTA,
  vicino all'asse verticale del disco.
- Deneb (Triangolo Estivo): quasi allo zenit nelle sere d'agosto -> vicino al
  CENTRO del disco.
- Antares (Scorpione): bassa a SUD nelle sere d'estate -> META' BASSA.
- Sirius: stella invernale, nelle sere d'agosto e' SOTTO l'orizzonte -> non
  visibile (altezza < 0).

Non serve precisione al pixel: serve escludere flip verticale (N/S), flip
orizzontale (E/O), rotazione e inversione radiale (zenit<->orizzonte).

*** RISCHIO RESIDUO: come gli altri test incrociati, non cattura un errore
    interno a skyfield; cattura errori nostri di orientamento/proiezione. ***
"""
import math

import numpy as np
import pytest

LAT, LON = 45.5455, 11.5353
CX, CY, R = 450.0, 500.0, 384.0        # geometria del disco A4 (engine.generate)
ANNO, MESE, ORA = 2026, 8, 23          # 15 agosto 2026, 23:00 locali

# Coordinate standard J2000 (RA gradi, Dec gradi): verita' esterna.
STELLE = {
    "Polaris": (37.954, 89.264),
    "Deneb": (310.358, 45.280),
    "Antares": (247.352, -26.432),
}


def _catalogo_piu_vicina(eng, ra, dec):
    """Indice della stella di catalogo piu' vicina a (ra,dec) e separazione in
    gradi. Serve a usare il CATALOGO REALE, non coordinate esterne, e a
    confermare che la stella riconoscibile e' davvero nel catalogo."""
    r1, d1 = math.radians(ra), math.radians(dec)
    r2, d2 = np.radians(eng.sra), np.radians(eng.sdec)
    cos_sep = np.sin(d1) * np.sin(d2) + np.cos(d1) * np.cos(d2) * np.cos(r1 - r2)
    sep = np.degrees(np.arccos(np.clip(cos_sep, -1, 1)))
    i = int(np.argmin(sep))
    return i, float(sep[i])


def _proietta(eng, ra, dec):
    lst, latr, _tz = eng.sky_context(ANNO, MESE, LAT, LON, hour_local=ORA)
    alt, az = eng.altaz(ra, dec, lst, latr)
    x, y = eng.project(alt, az, CX, CY, R)
    return float(alt), float(az), float(x), float(y)


def test_polaris_alta_e_sull_asse_nord(eng):
    """Polaris: nel catalogo, altezza ~ latitudine, azimut ~ Nord; sul disco sta
    nella META' ALTA (y < centro) e vicino all'asse verticale (x ~ centro).
    Tolleranze: altezza entro 1.5 gradi dalla latitudine (dec=89.26, non 90);
    azimut entro 3 gradi da Nord; |x-CX| < 0.12*R (l'asse N-S)."""
    i, sep = _catalogo_piu_vicina(eng, *STELLE["Polaris"])
    assert sep < 0.5, f"Polaris non trovata nel catalogo (sep {sep:.3f} gradi)"
    alt, az, x, y = _proietta(eng, eng.sra[i], eng.sdec[i])
    assert alt == pytest.approx(LAT, abs=1.5)
    assert min(az, 360.0 - az) < 3.0                 # ~Nord
    assert y < CY                                     # meta' alta
    assert abs(x - CX) < 0.12 * R                     # sull'asse verticale


def test_deneb_vicino_allo_zenit(eng):
    """Deneb: quasi allo zenit nelle sere d'agosto -> vicino al CENTRO del disco.
    Tolleranza: distanza dal centro < 0.3*R (lo zenit e' il centro esatto; qui
    Deneb e' alta ~76 gradi -> raggio ~0.15*R). Esclude l'inversione radiale
    zenit<->orizzonte."""
    i, sep = _catalogo_piu_vicina(eng, *STELLE["Deneb"])
    assert sep < 0.5, f"Deneb non trovata nel catalogo (sep {sep:.3f} gradi)"
    alt, az, x, y = _proietta(eng, eng.sra[i], eng.sdec[i])
    assert alt > 60.0                                 # davvero alta
    assert math.hypot(x - CX, y - CY) < 0.3 * R       # vicino al centro


def test_antares_bassa_a_sud(eng):
    """Antares: bassa a SUD nelle sere d'estate -> META' BASSA del disco (y >
    centro), altezza positiva ma piccola. Esclude il flip verticale N/S: se il
    Sud finisse in alto, questo test fallirebbe."""
    i, sep = _catalogo_piu_vicina(eng, *STELLE["Antares"])
    assert sep < 0.5, f"Antares non trovata nel catalogo (sep {sep:.3f} gradi)"
    alt, az, x, y = _proietta(eng, eng.sra[i], eng.sdec[i])
    assert 0.0 < alt < 20.0                           # visibile ma bassa
    assert y > CY                                     # meta' bassa (Sud in basso)


def test_sirius_sotto_orizzonte_in_agosto(eng):
    """Sirius e' una stella INVERNALE: la sera del 15 agosto e' sotto l'orizzonte
    dal Nord Italia. La pipeline deve darle altezza < 0 (non verrebbe disegnata).
    Ancora di sanita' temporale/emisferica; usa coordinate standard (il fatto
    'sotto orizzonte' non richiede l'appartenenza al catalogo)."""
    alt, az, x, y = _proietta(eng, 101.287, -16.716)
    assert alt < 0.0
