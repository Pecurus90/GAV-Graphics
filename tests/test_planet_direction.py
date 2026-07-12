"""
TEST DI COERENZA INCROCIATA — direzione dei pianeti (planet_table.az/direction).

planet_table dichiara, per ogni pianeta, l'azimut al suo istante migliore
(massima altezza della notte) e la direzione cardinale corrispondente. Verifichiamo:

1. AZIMUT per via indipendente. L'azimut del motore viene da skyfield
   apparent().altaz(). Lo ricalcoliamo per un ALTRO percorso: effemeride
   observe->radec(di data) passata dentro la nostra altaz() (trig sferica
   fatta in casa, gia' ancorata a riferimenti esterni in test_correctness.py).
   Due strade diverse per lo stesso azimut: se il motore usasse l'ora sbagliata,
   il segno invertito o l'asse ruotato, i due valori divergerebbero.

2. SENSATEZZA FISICA. Un pianeta al suo meglio la SERA (dopo il tramonto) non
   puo' stare a Est; uno al suo meglio all'ALBA non puo' stare a Ovest. E' la
   geometria del moto diurno: se fallisce, e' un bug vero.

3. La stringa di direzione dev'essere coerente col settore dell'azimut.

*** RISCHIO RESIDUO ACCETTATO ***
Come gli altri test di effemeridi: NON catturano un errore DENTRO skyfield.
Catturano gli errori NOSTRI (ora scelta, orientamento, mappatura dei settori).
"""
import math
from datetime import datetime

import pytz
from skyfield.api import wgs84

LAT, LON = 45.5455, 11.5353
TZ = pytz.timezone("Europe/Rome")

# Pianeti con eventi/altezze stabili (Mercurio escluso, come test_planets).
PIANETI = {"Venere": "venus", "Marte": "mars",
           "Giove": "jupiter barycenter", "Saturno": "saturn barycenter"}
MESI = [(2026, 8), (2026, 1)]  # agosto (ora legale) + gennaio (ora solare)

# Le stesse ore campionate da planet_table per il best_alt.
ORE = [21, 22, 23, 0, 1, 2, 3, 4]

# Tolleranza azimut: i due percorsi (skyfield altaz vs nostra altaz da radec)
# coincidono a 0.000 gradi sui pianeti testati (misurato). 0.5 e' un margine
# ampio contro il rumore float fra piattaforme, ma resta minuscolo rispetto a un
# errore reale (uno sfasamento di 90 gradi, o l'ora sbagliata che sposta l'az di
# decine di gradi).
TOL_AZ = 0.5

# Copia INDIPENDENTE della rosa a 8 settori: se il motore ruotasse la sua lista,
# il confronto qui sotto lo prenderebbe.
SETTORI = ["Nord", "Nord-Est", "Est", "Sud-Est", "Sud", "Sud-Ovest", "Ovest", "Nord-Ovest"]


def _best_indip(eng, pkey, year, month):
    """Ricalcola (best_alt, best_h, azimut) in modo indipendente: stesse ore di
    planet_table, ma l'azimut passa per la NOSTRA altaz(radec, lst)."""
    obs = eng.eph["earth"] + wgs84.latlon(LAT, LON, elevation_m=50)
    tgt = eng.eph[pkey]
    best = (-90.0, None, None)
    for h in ORE:
        dd = 15 + (1 if h < 12 else 0)
        t = eng.ts.from_datetime(TZ.localize(datetime(year, month, dd, h, 0)))
        astro = obs.at(t).observe(tgt).apparent()
        alt_sf = astro.altaz()[0].degrees
        if alt_sf > best[0]:
            ra, dec, _ = astro.radec(epoch="date")
            lst = (t.gast + LON / 15.0) % 24.0
            _alt, az = eng.altaz(ra.hours * 15.0, dec.degrees, lst, math.radians(LAT))
            best = (alt_sf, h, float(az))
    return best


def _delta_ang(a, b):
    return abs((a - b + 180.0) % 360.0 - 180.0)


def test_azimut_pianeti_coerente_e_fisico(eng):
    controllati = 0
    for year, month in MESI:
        planets = {p.name: p for p in eng.sky_data(year, month, LAT, LON, "Vicenza").planets}
        for name, pkey in PIANETI.items():
            p = planets[name]
            if p.status == "muted":
                assert p.direction == "", f"{name}: non osservabile ma con direzione {p.direction!r}"
                continue

            best_alt, best_h, az_ind = _best_indip(eng, pkey, year, month)

            # (1) cross-check azimut, due percorsi diversi allo stesso istante
            d = _delta_ang(p.az, az_ind)
            assert d < TOL_AZ, (
                f"{name} {year}-{month:02d}: azimut {p.az:.2f} incoerente con la via "
                f"indipendente {az_ind:.2f} (scarto {d:.3f} >= {TOL_AZ})"
            )

            # (3) stringa coerente col settore dell'azimut
            atteso = SETTORI[round(p.az / 45.0) % 8]
            assert atteso in p.direction, (
                f"{name}: direzione {p.direction!r} non contiene il settore atteso "
                f"'{atteso}' per azimut {p.az:.1f}"
            )

            # (2) sensatezza fisica, solo se davvero sopra l'orizzonte
            if best_alt > 5.0:
                if best_h in (21, 22):  # serale, dopo il tramonto
                    assert not (45.0 <= p.az <= 135.0), (
                        f"{name} {year}-{month:02d}: al meglio la sera ma a Est (az {p.az:.1f})"
                    )
                if best_h in (3, 4):    # verso l'alba
                    assert not (225.0 <= p.az <= 315.0), (
                        f"{name} {year}-{month:02d}: al meglio all'alba ma a Ovest (az {p.az:.1f})"
                    )
                controllati += 1

    assert controllati >= 4, f"troppi pochi pianeti osservabili controllati: {controllati}"


def test_qualificatore_basso(eng):
    """La direzione porta 'basso' se e solo se l'altezza migliore e' sotto 20 gradi
    (per i pianeti osservabili). Verifica incrociata col best_alt indipendente."""
    for year, month in MESI:
        planets = {p.name: p for p in eng.sky_data(year, month, LAT, LON, "Vicenza").planets}
        for name, pkey in PIANETI.items():
            p = planets[name]
            if p.status == "muted":
                continue
            best_alt, _h, _az = _best_indip(eng, pkey, year, month)
            if best_alt <= 0.0:
                assert p.direction == "", (
                    f"{name}: non sorge (alt {best_alt:.1f}<=0) ma direzione {p.direction!r}"
                )
            elif best_alt < 20.0:
                assert p.direction.startswith("basso"), (
                    f"{name}: alt migliore {best_alt:.1f}<20 ma direzione {p.direction!r} senza 'basso'"
                )
            else:
                assert not p.direction.startswith("basso"), (
                    f"{name}: alt migliore {best_alt:.1f}>=20 ma direzione {p.direction!r} con 'basso'"
                )


def test_direzione_pura_e_correzione_sotto_orizzonte(eng):
    """Unit test della funzione pura _planet_direction: settori, 'basso', e la
    CORREZIONE #6d (best_alt<=0 -> '' anche se il pianeta non e' muted). Questo
    ancora la correzione a un caso deterministico, indipendente dalle effemeridi
    del mese (dove i pianeti sotto l'orizzonte capitano di essere anche muted)."""
    d = eng._planet_direction
    assert d(90.0, 30.0, "ok") == "a Est"
    assert d(90.0, 10.0, "ok") == "basso a Est"        # sopra l'orizzonte ma basso
    assert d(135.0, 30.0, "info") == "a Sud-Est"
    assert d(270.0, 40.0, "ok") == "a Ovest"
    assert d(0.0, 50.0, "ok") == "a Nord"
    # la correzione: sotto o all'orizzonte -> nessuna direzione, anche se NON muted
    assert d(90.0, 0.0, "warn") == "", "alt=0 dovrebbe dare direzione vuota"
    assert d(90.0, -5.0, "ok") == "", "best_alt<0 dovrebbe dare direzione vuota"
    assert d(90.0, -30.0, "muted") == ""
