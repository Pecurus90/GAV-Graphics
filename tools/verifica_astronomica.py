#!/usr/bin/env python3
"""
tools/verifica_astronomica.py - IL CONFRONTO COL "PLANETARIO".

Risponde alla domanda che CLAUDE.md ha tenuto aperta piu' a lungo di ogni altra:
*l'output e' astronomicamente GIUSTO?* I test della suite validano la matematica
contro TEOREMI (una stella al polo celeste sta all'altezza della latitudine) e
contro POSIZIONI NOTE. Qui si fa una cosa diversa e piu' forte: si ricalcola tutto
con una LIBRERIA INDIPENDENTE e si confrontano i numeri.

PERCHE' ASTROPY E NON SKYFIELD: il motore usa skyfield + de421. Rifare il conto
con skyfield proverebbe solo che skyfield e' d'accordo con se' stesso. `astropy`
usa **ERFA** (la libreria derivata da SOFA dello IAU): un'altra implementazione,
un altro autore, un'altra catena di trasformazioni. Se due catene indipendenti
danno lo stesso cielo, il cielo e' quello.

NON E' UN TEST, ed e' deliberato: `astropy` NON sta in requirements.txt e non deve
starci - peserebbe ~100 MB nel pacchetto portatile (D17) per una verifica che si
fa una volta ogni tanto. Sta in tools/ accanto a collisioni.py e fotografia.py:
diagnosi su richiesta, non rete permanente.

    python tools/verifica_astronomica.py            # i quattro controlli
    python tools/verifica_astronomica.py --mese 3   # un altro mese

--------------------------------------------------------------------------------
ESITO DEL PRIMO GIRO (2026-09-03, Vicenza, 2026):

  1. STELLE (23 nominate)      scarto medio 0,30 gradi, massimo 0,38
     = 1,2-1,5 px su un A4 largo 900. NON e' un errore: e' la PRECESSIONE
     J2000 -> 2026 (26 anni x ~50"/anno = 0,36 gradi) che il motore non applica,
     perche' usa RA/Dec di catalogo J2000 col tempo siderale APPARENTE di data.
     Sotto il diametro della Luna piena (0,5 gradi): invisibile su una carta a
     occhio nudo, e comunque piu' piccolo del disco con cui si disegna una stella.

  2. PIANETI E LUNA            scarto massimo 0,005 gradi = 0,3 primi d'arco
     Qui il motore usa le effemeridi vere (de421) e le due catene coincidono.

  3. FASI LUNARI (48 su 12 mesi)   ZERO discordanze
     Confrontate col metodo indipendente dell'elongazione eclittica Luna-Sole,
     non con l'almanac di skyfield.

  4. DAL CATALOGO AL PIXEL     scarto medio 1,34 px, massimo 2,14
     Chiude il cerchio: non solo la matematica, ma il DISCO DISEGNATO nell'SVG.
     Posizione attesa da astropy -> proiettata con la geometria del layout ->
     confrontata col cerchio piu' vicino nell'SVG vero.

  + Il controllo che nessun numero da', fatto a occhio sul disco reso di agosto:
    Polare a meta' fra centro e bordo nord (altezza = latitudine); il Triangolo
    Estivo (Vega-Deneb-Altair) allo ZENIT, cioe' al centro; le costellazioni
    d'autunno (Pegaso, Andromeda, Pesci) a SINISTRA = sorgono a Est, quelle di
    primavera (Boote, Vergine, Bilancia) a DESTRA = tramontano a Ovest; Scorpione
    e Sagittario bassi a Sud-Ovest. E' la firma di meta' agosto alle 23 da 45°N,
    e conferma anche l'orientamento (invariante #3) per una strada che non passa
    dalla matematica.
--------------------------------------------------------------------------------
"""
import argparse
import calendar
import io
import os
import re
import sys
import warnings
from datetime import datetime, timezone

import numpy as np

warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

LAT, LON = 45.5455, 11.5353          # Vicenza, i parametri canonici
NOMI = ["Sirio", "Vega", "Altair", "Deneb", "Arturo", "Capella", "Rigel",
        "Betelgeuse", "Aldebaran", "Pollux", "Regolo", "Antares", "Spica",
        "Fomalhaut", "Polare", "Mizar", "Schedar", "Thuban", "Alphecca",
        "Kaus Australis", "Mirach", "Algol", "Enif"]


def _sep(alt1, az1, alt2, az2):
    """Separazione angolare vera fra due direzioni (gradi). Non la differenza
    delle coordinate: vicino allo zenit l'azimut diverge e mentirebbe."""
    def v(al, az):
        al, az = np.radians(al), np.radians(az)
        return np.array([np.cos(al) * np.cos(az), np.cos(al) * np.sin(az), np.sin(al)])
    return float(np.degrees(np.arccos(np.clip(v(alt1, az1) @ v(alt2, az2), -1, 1))))


def main(anno, mese):
    try:
        from astropy.coordinates import (SkyCoord, EarthLocation, AltAz, get_body,
                                         GeocentricTrueEcliptic)
        from astropy.time import Time
        import astropy.units as u
    except ImportError:
        print("astropy non installato. E' voluto che NON sia in requirements.txt "
              "(pesa ~100 MB nel pacchetto, D17).\n  pip install astropy")
        return 1

    import pytz
    from engine.generate import Engine
    from strumenti.cielo.catalog import STARS

    eng = Engine(datadir=os.path.join(ROOT, "data"))
    tz = pytz.timezone("Europe/Rome")
    lst, latr, _ = eng.sky_context(anno, mese, LAT, LON, hour_local=23)

    locale = tz.localize(datetime(anno, mese, 15, 23, 0))
    t = Time(locale.astimezone(timezone.utc), scale="utc")
    eloc = EarthLocation(lat=LAT * u.deg, lon=LON * u.deg, height=39 * u.m)
    frame = AltAz(obstime=t, location=eloc)      # senza rifrazione

    print(f"CONFRONTO COL PLANETARIO - Vicenza, 15/{mese:02d}/{anno} 23:00")
    print("motore (skyfield + de421)  vs  astropy (ERFA/SOFA)\n")

    # -- 1. stelle -----------------------------------------------------------
    scarti = []
    for nm in NOMI:
        ra, dec, _bv, _mag = STARS[nm]
        ae, ze = (float(x) for x in eng.altaz(ra, dec, lst, latr))
        c = SkyCoord(ra=ra * u.deg, dec=dec * u.deg, frame="icrs").transform_to(frame)
        scarti.append(_sep(ae, ze, float(c.alt.deg), float(c.az.deg)))
    print(f"1. STELLE ({len(NOMI)})           medio {np.mean(scarti):.3f}° "
          f"massimo {max(scarti):.3f}°  = {max(scarti)*4:.1f} px sull'A4")
    print("   atteso: e' la PRECESSIONE J2000->oggi non applicata, non un errore.")

    # -- 2. pianeti e Luna ---------------------------------------------------
    from skyfield.api import wgs84
    obs = (eng.eph["earth"] + wgs84.latlon(LAT, LON)).at(eng.ts.from_datetime(locale))
    CORPI = [("Mercurio", "mercury", "mercury"), ("Venere", "venus", "venus"),
             ("Marte", "mars", "mars"), ("Giove", "jupiter barycenter", "jupiter"),
             ("Saturno", "saturn barycenter", "saturn"),
             ("Urano", "uranus barycenter", "uranus"),
             ("Nettuno", "neptune barycenter", "neptune"), ("Luna", "moon", "moon")]
    dp = []
    for _nome, ksf, kap in CORPI:
        a, z, _ = obs.observe(eng.eph[ksf]).apparent().altaz()
        c = get_body(kap, t, eloc).transform_to(frame)
        dp.append(_sep(a.degrees, z.degrees, float(c.alt.deg), float(c.az.deg)))
    print(f"2. PIANETI E LUNA (8)      massimo {max(dp):.4f}° = {max(dp)*60:.1f} primi d'arco")

    # -- 3. fasi lunari (elongazione eclittica: metodo indipendente) ----------
    ko = tot = 0
    for m in range(1, 13):
        n = calendar.monthrange(anno, m)[1]
        tt = Time(f"{anno}-{m:02d}-01") + np.arange(0, n * 96) * 15 * u.min
        s = get_body("sun", tt).transform_to(GeocentricTrueEcliptic(equinox="J2000"))
        mo = get_body("moon", tt).transform_to(GeocentricTrueEcliptic(equinox="J2000"))
        d = (mo.lon.deg - s.lon.deg) % 360
        att = {}
        for tg, nome in ((0, "Luna Nuova"), (90, "Primo Quarto"),
                         (180, "Luna Piena"), (270, "Ultimo Quarto")):
            f = ((d - tg + 180) % 360) - 180
            for i in range(len(f) - 1):
                if f[i] < 0 <= f[i + 1] and abs(f[i + 1] - f[i]) < 10:
                    q = (tt[i] + (tt[i + 1] - tt[i]) * (-f[i] / (f[i + 1] - f[i]))).to_datetime()
                    att[nome] = q.replace(tzinfo=pytz.utc).astimezone(tz).strftime("%d/%m")
        mot = {nome: dd for nome, _k, dd in eng.moon_phases(anno, m, tz)}
        for nome, dd in att.items():
            tot += 1
            if mot.get(nome) != dd:
                ko += 1
                print(f"   DIVERSO mese {m}: {nome} motore {mot.get(nome)} astropy {dd}")
    print(f"3. FASI LUNARI ({tot} su 12 mesi)  discordanti: {ko}")

    # -- 4. dal catalogo al PIXEL dell'SVG -----------------------------------
    svg_path = os.path.join(ROOT, "out", "sweep", f"a4_{mese:02d}.svg")
    if os.path.exists(svg_path):
        import json
        lay = json.load(io.open(os.path.join(ROOT, "brand", "layouts", "a4.json"),
                                encoding="utf-8"))
        disc = next(b for b in lay["blocks"] if b.get("type") == "disc")
        cx, cy, rad = disc["cx"], disc["cy"], disc["rad"]
        svg = io.open(svg_path, encoding="utf-8").read()
        punti = [(float(a), float(b)) for a, b, _r in
                 re.findall(r'<circle cx="([\d.]+)" cy="([\d.]+)" r="([\d.]+)"', svg)]
        dd = []
        for nm in NOMI:
            ra, dec, _bv, _mag = STARS[nm]
            c = SkyCoord(ra=ra * u.deg, dec=dec * u.deg, frame="icrs").transform_to(frame)
            alt, az = float(c.alt.deg), float(c.az.deg)
            if alt <= 2:
                continue
            r = rad * (90.0 - alt) / 90.0
            x, y = cx - r * np.sin(np.radians(az)), cy - r * np.cos(np.radians(az))
            dd.append(min((np.hypot(px - x, py - y) for px, py in punti), default=999))
        print(f"4. CATALOGO -> PIXEL ({len(dd)})   medio {np.mean(dd):.2f} px "
              f"massimo {max(dd):.2f} px  (disco r{rad:.0f})")
    else:
        print(f"4. CATALOGO -> PIXEL       saltato: manca {svg_path}")
        print("   (generalo con lo sweep, vedi tools/collisioni.py)")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--mese", type=int, default=8)
    ap.add_argument("--anno", type=int, default=2026)
    sys.exit(main(ap.parse_args().anno, ap.parse_args().mese))
