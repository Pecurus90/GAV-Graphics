"""
R14 - LA RETE SULL'ALLINEAMENTO FRA I FORMATI.

Per mesi due formati «cielo» hanno dichiarato 23 nomi di stelle e due ne hanno
dichiarati 14 - con SIRIO, la stella piu' luminosa del cielo notturno, ASSENTE
dal volantino A4 stampato - e NESSUN test se n'e' accorto. A trovarlo fu una
tabella feature x formato costruita a mano dall'architetto. Questo file e' quella
tabella diventata rete.

I quattro formati «cielo» (mappa del cielo + pannelli) devono dichiarare le STESSE
feature e gli STESSI contenuti (nomi di stelle, costellazioni). Deep Space e'
L'UNICA ECCEZIONE, DICHIARATA E MOTIVATA in un posto solo (ECCEZIONI, sotto): e'
il formato Messier, con tabella/legenda/simboli del profondo cielo al posto di
pianeti/luna/temperatura-stelle, e senza i nomi delle stelle luminose.

Il punto che rende questa una RETE e non un placebo: l'eccezione e' esplicita.
Aggiungere un formato nuovo, o una nuova eccezione, OBBLIGA a scrivere qui - un
formato che SBAGLIA l'allineamento salta rosso, non passa 'saltato' in silenzio
insieme a deep-space (e' esattamente cosi' che il buco di Sirio era entrato).
"""
import glob
import json
import os

# I formati che condividono l'identita' «carta del cielo»: stessi contenuti.
FORMATI_CIELO = ["dashboard", "parata", "zenit", "a4"]

# L'UNICA eccezione, DICHIARATA e MOTIVATA. Chi vuole allargarla scrive QUI, con
# il perche': cosi' una nuova eccezione non si insinua, va decisa apposta.
ECCEZIONI = {
    "deep-space": "formato Messier (profondo cielo): tabella, legenda e simboli "
                  "Messier al posto di pianeti/luna/temperatura-stelle; niente "
                  "nomi delle stelle luminose (mostra gli oggetti del catalogo). "
                  "Diverso DOVE E' GIUSTO.",
}

# Le feature che ogni formato «cielo» deve dichiarare, e come si riconoscono nel
# layout (i tipi di blocco su disco - la stessa verita' che legge il motore).
FEATURE = {
    "star_names": lambda lay: bool(_disc(lay).get("star_names")),
    "labels":     lambda lay: bool(_disc(lay).get("labels")),
    "ticks":      lambda lay: "ticks" in _disc(lay),
    "pianeti":    lambda lay: _ha_tipo(lay, "planet_panel", "planet_parade"),
    "legenda":    lambda lay: _ha_tipo(lay, "swatches"),
    "luna":       lambda lay: _ha_tipo(lay, "moon_calendar"),
    "icone":      lambda lay: bool(_icone(lay)),
}


def _carica(root, fmt):
    with open(os.path.join(root, "brand", "layouts", f"{fmt}.json"), encoding="utf-8") as fh:
        return json.load(fh)


def _blocchi(lay):
    return lay.get("blocks", [])


def _disc(lay):
    for b in _blocchi(lay):
        if b.get("type") == "disc":
            return b
    return {}


def _ha_tipo(lay, *tipi):
    return any(b.get("type") in tipi for b in _blocchi(lay))


def _icone(lay):
    return sorted(b.get("name") for b in _blocchi(lay) if b.get("type") == "icon")


def _star_names(lay):
    return set(_disc(lay).get("star_names") or [])


def _labels(lay):
    return set(_disc(lay).get("labels") or [])


# ---------------------------------------------------------------------------
def test_formati_cielo_hanno_le_stesse_feature(root):
    """Ogni formato «cielo» deve dichiarare TUTTE le feature: star_names, labels,
    ticks, pianeti, legenda, luna, icone. Se una manca a un formato, il messaggio
    dice QUALE formato e QUALE feature."""
    feats = {f: _carica(root, f) for f in FORMATI_CIELO}
    problemi = []
    for nome, ha in FEATURE.items():
        for f, lay in feats.items():
            if not ha(lay):
                problemi.append(f"{f}: manca la feature '{nome}'")
    assert not problemi, (
        "I formati «cielo» devono avere le STESSE feature (R14):\n  "
        + "\n  ".join(problemi))


def test_star_names_allineati_fra_i_formati_cielo(root):
    """I formati «cielo» devono nominare le STESSE stelle. E' il cuore di R14:
    Sirio spari' dall'A4 perche' due formati ne dichiaravano 23 e due 14, e nulla
    lo sorvegliava. Confronto sull'UNIONE: se a un formato manca una stella che gli
    altri hanno, salta rosso dicendo QUALE formato e QUALE stella."""
    sets = {f: _star_names(_carica(root, f)) for f in FORMATI_CIELO}
    union = set().union(*sets.values())
    problemi = [f"{f}: 'star_names' non allineato, mancano {sorted(union - s)}"
                for f, s in sets.items() if union - s]
    assert not problemi, (
        "Nomi di stelle disallineati fra i formati «cielo» (R14 - Sirio):\n  "
        + "\n  ".join(problemi))


def test_costellazioni_allineate_fra_i_formati_cielo(root):
    """Stessa rete per le etichette delle costellazioni (labels): un formato non
    deve nominare una costellazione che gli altri ignorano, o viceversa."""
    sets = {f: _labels(_carica(root, f)) for f in FORMATI_CIELO}
    union = set().union(*sets.values())
    problemi = [f"{f}: 'labels' non allineato, mancano {sorted(union - s)}"
                for f, s in sets.items() if union - s]
    assert not problemi, (
        "Costellazioni disallineate fra i formati «cielo»:\n  "
        + "\n  ".join(problemi))


def test_icone_social_allineate_fra_i_formati_cielo(root):
    """Le stesse icone social (instagram/facebook/email) su tutti i formati «cielo»."""
    sets = {f: _icone(_carica(root, f)) for f in FORMATI_CIELO}
    atteso = sets[FORMATI_CIELO[0]]
    problemi = [f"{f}: icone {ic} invece di {atteso}"
                for f, ic in sets.items() if ic != atteso]
    assert not problemi, (
        "Icone social disallineate fra i formati «cielo»:\n  "
        + "\n  ".join(problemi))


def test_ogni_formato_e_classificato_cielo_o_eccezione(root):
    """La guardia che rende viva la rete: ogni layout su disco dev'essere o un
    formato «cielo» (allineato) o un'ECCEZIONE dichiarata e motivata. Un formato
    nuovo non classificato fa ROSSO - cosi' non puo' entrare 'saltato' e sbagliare
    l'allineamento in silenzio (com'era entrato il buco di Sirio)."""
    files = sorted(os.path.basename(p)[:-5]
                   for p in glob.glob(os.path.join(root, "brand", "layouts", "*.json")))
    noti = set(FORMATI_CIELO) | set(ECCEZIONI)
    orfani = [f for f in files if f not in noti]
    assert not orfani, (
        f"Formati non classificati: {orfani}. Ogni layout va dichiarato «cielo» "
        "(FORMATI_CIELO) oppure ECCEZIONE motivata in questo file.")
    fantasma = [f for f in noti if f not in files]
    assert not fantasma, (
        f"Formati dichiarati ma inesistenti su disco: {fantasma}. "
        "Aggiorna FORMATI_CIELO / ECCEZIONI.")
