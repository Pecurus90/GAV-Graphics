"""
TEST DI COERENZA INCROCIATA — fasi lunari (moon_phases).

moon_phases dice "il giorno X c'e' il plenilunio". Lo verifichiamo per un
percorso indipendente: all'istante di quell'evento, la geometria Sole-Luna deve
corrispondere all'etichetta.
- Luna Nuova  -> separazione angolare Sole-Luna ~ 0 gradi
- Luna Piena  -> separazione ~ 180 gradi
- Primo/Ultimo Quarto -> separazione ~ 90 gradi
- Primo (crescente) e Ultimo (calante) su lati OPPOSTI: differenza di longitudine
  eclittica Luna-Sole ~ 90 vs ~ 270 gradi.
La separazione e' un calcolo di effemeridi diverso dall'algoritmo che trova le
fasi (che lavora sulla differenza di longitudine eclittica): un'etichetta
scambiata o un fuso sbagliato si presentano come contraddizione.

*** RISCHIO RESIDUO ACCETTATO CONSAPEVOLMENTE ***
Come per i pianeti: questi test NON catturerebbero un errore DENTRO skyfield.
Catturano gli errori NOSTRI (ordine di names[]/keys[] in moon_phases, fuso,
formattazione della data).
"""
import calendar

import pytz
from skyfield import almanac

TZ = pytz.timezone("Europe/Rome")

# Mesi con copertura DST esplicita: gennaio/febbraio in ora solare,
# luglio/agosto in ora legale.
MESI = [(2026, 1), (2026, 2), (2026, 7), (2026, 8)]


def _classifica_per_geometria(eng, t):
    """Etichetta la fase all'istante t SOLO dalla geometria (indipendente
    dall'indice restituito dal cercatore di fasi). Restituisce una chiave
    compatibile con quelle di moon_phases: new/first/full/last."""
    e = eng.eph["earth"].at(t)
    sun = e.observe(eng.eph["sun"]).apparent()
    moon = e.observe(eng.eph["moon"]).apparent()
    sep = sun.separation_from(moon).degrees
    slon = sun.ecliptic_latlon()[1].degrees
    mlon = moon.ecliptic_latlon()[1].degrees
    dlon = (mlon - slon) % 360.0

    # Tolleranze motivate:
    # - Nuova sep < 8: al novilunio la separazione = latitudine eclittica lunare,
    #   al massimo ~5.3 gradi. Margine a 8.
    # - Piena sep > 170: all'opposizione separazione >= 180 - 5.3 = ~174.7.
    #   Margine a 170.
    # - Quarti |sep-90| < 2: a Delta-lambda=90 la separazione e' esattamente 90
    #   (il termine cos(90) annulla la dipendenza dalla latitudine). Misurato:
    #   90.000. Margine 2 gradi.
    if sep < 8:
        return "new"
    if sep > 170:
        return "full"
    if abs(sep - 90.0) < 2.0:
        # crescente (est del Sole, dlon~90) vs calante (ovest, dlon~270)
        if abs(dlon - 90.0) < 5.0:
            return "first"
        if abs(dlon - 270.0) < 5.0:
            return "last"
    return f"AMBIGUA(sep={sep:.2f},dlon={dlon:.2f})"


def _istanti_fasi(eng, year, month):
    """Gli STESSI istanti che moon_phases usa internamente (find_discrete sul
    mese di calendario). moon_phases scarta l'ora e tiene solo la data: qui
    servono gli istanti per la geometria."""
    t0 = eng.ts.utc(year, month, 1)
    nm = calendar.monthrange(year, month)[1]
    t1 = eng.ts.utc(year, month, nm, 23, 59)
    tt, _yy = almanac.find_discrete(t0, t1, almanac.moon_phases(eng.eph))
    return list(tt)


def test_fasi_etichette_e_date_coerenti_con_geometria(eng):
    """L'output PUBBLICO di moon_phases (etichetta + data) deve combaciare, evento
    per evento, con l'etichetta dedotta dalla sola geometria e con la data locale
    dell'istante. Un'etichetta scambiata nella mappatura names[]/keys[] o una
    data sballata dal fuso qui saltano fuori."""
    controllati = 0
    for year, month in MESI:
        # verita' indipendente: (chiave-da-geometria, data locale) per ogni istante
        atteso = set()
        for t in _istanti_fasi(eng, year, month):
            key = _classifica_per_geometria(eng, t)
            assert not key.startswith("AMBIGUA"), (
                f"{year}-{month:02d}: fase non classificabile dalla geometria: {key}"
            )
            atteso.add((key, t.astimezone(TZ).strftime("%d/%m")))
            controllati += 1

        # output reale della funzione sotto test
        ottenuto = {(key, ddmm) for (_name, key, ddmm) in eng.moon_phases(year, month, TZ)}

        assert ottenuto == atteso, (
            f"{year}-{month:02d}: moon_phases incoerente con la geometria.\n"
            f"  atteso (geometria): {sorted(atteso)}\n"
            f"  ottenuto (codice) : {sorted(ottenuto)}"
        )
    assert controllati >= 12, f"troppe poche fasi controllate: {controllati}"


def test_mese_sinodico_fra_pleniluni_consecutivi(eng):
    """La distanza fra pleniluni CONSECUTIVI deve valere ~1 mese sinodico.
    Riferimento esterno: il mese sinodico medio e' 29.53 giorni ma varia
    fisicamente ~29.2-29.9 g per l'eccentricita' orbitale. Banda accettata
    [29.0, 30.0]: rispetta la variazione reale e scarta un'anomalia grossolana
    (lunazione mancante ~59 g o spuria ~15 g). Misurato 2026: 29.50-29.57 g."""
    # raccolgo TUTTI i pleniluni del 2026 (mesi consecutivi) e li ordino
    pleniluni = []
    for month in range(1, 13):
        for t in _istanti_fasi(eng, 2026, month):
            if _classifica_per_geometria(eng, t) == "full":
                pleniluni.append(t.tt)
    pleniluni.sort()
    assert len(pleniluni) >= 6, f"troppi pochi pleniluni: {len(pleniluni)}"
    for i in range(1, len(pleniluni)):
        d = pleniluni[i] - pleniluni[i - 1]
        assert 29.0 < d < 30.0, f"intervallo sinodico anomalo: {d:.4f} giorni"
