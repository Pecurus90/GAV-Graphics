"""
TEST DI COERENZA INCROCIATA — pianeti (_rise_set / planet_table).

Idea: non testare _rise_set contro se stesso ne' contro una tabella copiata a
mano, ma contro una FUNZIONE INDIPENDENTE gia' validata, raggiunta per un altro
percorso di codice. L'orario di alzata/tramonto e' prodotto da un algoritmo di
RICERCA (skyfield almanac.risings_and_settings). La posizione a quell'orario e'
prodotta da un calcolo di EFFEMERIDI (observe -> radec) passato dentro la nostra
funzione altaz, gia' ancorata a riferimenti esterni in test_correctness.py.
Se i due percorsi si contraddicono (fuso sbagliato, segno invertito, ora persa
nel DST, AM/PM), l'altezza al presunto orizzonte non sara' all'orizzonte.

*** RISCHIO RESIDUO ACCETTATO CONSAPEVOLMENTE ***
Questi test NON catturerebbero un errore DENTRO skyfield stesso (se sia la
ricerca sia il calcolo di posizione sbagliassero allo stesso modo). E' una
scelta deliberata: skyfield e' la libreria di effemeridi che diamo per fidata.
Catturano invece gli errori NOSTRI di uso: fuso, arrotondamento, orientamento,
conversioni.

Copertura DST: si testano ALMENO un mese in ora legale (agosto, CEST +2) e uno
in ora solare (gennaio, CET +1), perche' il progetto usa Europe/Rome ed e' li'
che questo codice muore piu' spesso.
"""
import math
from datetime import datetime, timedelta

import pytz
from skyfield.api import wgs84

LAT, LON = 45.5455, 11.5353          # Vicenza (come il default del motore)
TZ = pytz.timezone("Europe/Rome")

# Orizzonte di alzata/tramonto: skyfield colloca l'evento all'orizzonte con
# rifrazione standard -0.5667 gradi (non a 0 geometrico). Cfr. il default
# horizon_degrees di almanac.risings_and_settings.
ORIZZONTE_RIFRAZIONE = -0.5667

# Pianeti testati (Mercurio escluso: eventi talvolta assenti nel giorno).
PIANETI = {
    "Venere": "venus",
    "Marte": "mars",
    "Giove": "jupiter barycenter",
    "Saturno": "saturn barycenter",
}

# (anno, mese, etichetta-DST) — agosto in ora legale, gennaio in ora solare.
MESI = [(2026, 8, "CEST +2 (ora legale)"), (2026, 1, "CET +1 (ora solare)")]


def _loc():
    return wgs84.latlon(LAT, LON, elevation_m=50)


def _alt_via_altaz(eng, target, when_local):
    """Altezza del bersaglio a un istante locale, per un PERCORSO DIVERSO da
    quello che ha prodotto l'orario: effemeride skyfield (observe->radec di data)
    -> nostra altaz (fidata) con LST = (gast + lon/15) come in sky_context."""
    obs = eng.eph["earth"] + _loc()
    t = eng.ts.from_datetime(when_local)
    lst = (t.gast + LON / 15.0) % 24.0
    astro = obs.at(t).observe(target).apparent()
    ra, dec, _ = astro.radec(epoch="date")
    alt, _az = eng.altaz(ra.hours * 15.0, dec.degrees, lst, math.radians(LAT))
    return float(alt)


def test_pianeti_orari_coerenti_con_altezza(eng):
    """Per ogni alzata/tramonto riportato da _rise_set:
    (1) l'altezza a quell'istante e' all'orizzonte (~ -0.5667 gradi);
    (2) il moto ha il verso giusto: al sorgere SALE, al tramonto SCENDE.

    Tolleranze e loro motivo:
    - altezza: |alt - (-0.5667)| < 0.9 gradi. NON e' 0 perche' skyfield usa
      l'orizzonte con rifrazione -0.5667. Il margine 0.9 assorbe l'arrotondamento
      al minuto dell'orario (+-30s ~ +-0.13 gradi vicino all'orizzonte) e resta
      minuscolo rispetto a un errore di un'ora (~10 gradi). Misurato: scarto
      dall'orizzonte <= 0.15 gradi.
    - verso: confronto altezza a -3 min e +3 min. E' un test di SEGNO, quindi
      senza tolleranza numerica: ~1 grado di dislivello su 6 minuti, inequivoco.
    """
    controllati = 0
    for year, month, _dst in MESI:
        for pname, pkey in PIANETI.items():
            target = eng.eph[pkey]
            rise, set_ = eng._rise_set(target, _loc(), TZ, year, month, 15)
            for kind, hhmm in (("rise", rise), ("set", set_)):
                if hhmm is None:            # evento assente quel giorno: salto
                    continue
                h, m = map(int, hhmm.split(":"))
                base = TZ.localize(datetime(year, month, 15, h, m))

                alt0 = _alt_via_altaz(eng, target, base)
                assert abs(alt0 - ORIZZONTE_RIFRAZIONE) < 0.9, (
                    f"{pname} {kind} {hhmm} {year}-{month:02d}: altezza {alt0:+.3f} "
                    f"non all'orizzonte (atteso ~{ORIZZONTE_RIFRAZIONE})"
                )

                alt_prima = _alt_via_altaz(eng, target, base - timedelta(minutes=3))
                alt_dopo = _alt_via_altaz(eng, target, base + timedelta(minutes=3))
                if kind == "rise":
                    assert alt_dopo > alt_prima, (
                        f"{pname} rise {hhmm} {year}-{month:02d}: non sta salendo "
                        f"(-3min={alt_prima:+.2f}, +3min={alt_dopo:+.2f})"
                    )
                else:
                    assert alt_dopo < alt_prima, (
                        f"{pname} set {hhmm} {year}-{month:02d}: non sta scendendo "
                        f"(-3min={alt_prima:+.2f}, +3min={alt_dopo:+.2f})"
                    )
                controllati += 1

    # Il test non deve passare a vuoto: pretende di aver controllato piu' eventi
    # in entrambi i mesi (ora legale e ora solare).
    assert controllati >= 8, f"troppi pochi eventi controllati: {controllati}"
