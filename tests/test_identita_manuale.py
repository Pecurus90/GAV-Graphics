"""
LA RETE SULL'IDENTITA' (C1) — i colori di marca vengono dal MANUALE.

Perche' esiste: fino al 2026-09-03 **nessun test guardava i VALORI** della
palette. L'unico che la nominava (`test_layouts_smoke`) asserisce che il file si
CHIAMI `gav.json`. I 26 colori di marca erano quindi giusti **per disciplina**,
non per costruzione: ritoccare un blu lasciava la suite verde.
E' l'ottavo buco della stessa famiglia in questo progetto (cardinali fuori
canvas -> cardinale sotto un pannello -> la banda che non e' un `panel` -> le
linee delle figure (R13) -> nessuna rete sull'allineamento (R14) -> le note dei
pianeti (R15) -> il piedino di zenit (Z1) -> questo).

COSA SORVEGLIA, E COSA NO — e' la parte che decide se e' una rete o un placebo:
  * SI': che ogni colore di marca sia **uno dei passi del manuale**.
  * NO: **quale** passo. Ritarare `border` da blu 400 a blu 600 e' esattamente
    cio' che D20 ha fatto guardando il poster reso, ed e' legittimo: la rete non
    deve impedirlo. Cio' che deve diventare rosso e' un colore **inventato**.
  * NO: `star_ramp` e `planet_colors`. Sono ASTRONOMIA (D2), non marchio: il
    divieto del manuale («nessun altro colore decorativo oltre a blu, giallo e
    neutri») governa il MARCHIO, non il DATO. Antares rossa non e' decorazione.
    L'esclusione e' STRUTTURALE, non una lista: quelle due chiavi non stanno in
    `validate.STYLE_TOKENS` ne' fra i gradienti, e c'e' un test qui sotto che
    dimostra che l'esclusione non e' vacua.

I valori del manuale non sono stati letti a schermo: sono stati **estratti dagli
oggetti vettoriali del PDF** (`page.get_drawings()`, la stessa tecnica del
secondo giro di D20), campione per campione.
"""
import json
import os

import pytest

import validate

# --- La tavolozza del manuale (docs/GAV-design-system.pdf, sez.3) -------------
# Scala blu, dal gradiente del logo: 50 -> 950. Verificati sui campioni vettoriali.
SCALA_BLU = {
    "#ddedf3", "#cbe4ed", "#9dccdc", "#53a6c2", "#007ba4", "#006e92",
    "#005d7c", "#024f6d", "#00465e", "#002936", "#01141d",
}
# Neutri, dalla versione grigi della scheda: 0 -> 900.
NEUTRI = {
    "#ffffff", "#f6f5f4", "#e6e1e5", "#c9c8c7", "#b3b1b1", "#7c7e80",
    "#545759", "#24272a",
}
# Giallo stella: l'unico accento ammesso oltre a blu e neutri.
GIALLO = {"#fde875"}
# Token semantici del TEMA NOTTE che non sono un passo della scala:
# --surface-card. (Sta nella tabella dei token, non fra i campioni.)
SEMANTICI = {"#013247"}

MANUALE = SCALA_BLU | NEUTRI | GIALLO | SEMANTICI

# --- Le chiavi che PORTANO un colore di marca --------------------------------
# Derivate da validate.py, non ricopiate: se domani il contratto del tema cambia,
# questa rete lo segue invece di restare indietro.
GRADIENTI = ["bg", "disk"]          # 3 stop ciascuno (disk = sfondo del disco:
                                    # identita' visiva, non fisica - vedi D18)
NON_COLORI = {"name", "descrizione"}
ASTRONOMIA = {"star_ramp", "planet_colors"}


@pytest.fixture
def palette(root):
    with open(os.path.join(root, "brand", "palettes", "gav.json"), encoding="utf-8") as fh:
        return json.load(fh)


def _colori_di_marca(p):
    """I 26 colori di marca, con l'etichetta di dove stanno (per il messaggio)."""
    out = []
    for k in validate.STYLE_TOKENS:
        out.append((k, p[k]))
    for k in validate.STATUS_KEYS:
        out.append((f"status.{k}", p["status"][k]))
    for g in GRADIENTI:
        for i, c in enumerate(p[g]):
            out.append((f"{g}[{i}]", c))
    return out


def test_ogni_colore_di_marca_viene_dal_manuale(palette):
    """Nessun colore INVENTATO. Ogni token di marca deve essere un passo della
    scala blu, un neutro, il giallo stella o un token semantico del tema notte."""
    fuori = [(k, v) for k, v in _colori_di_marca(palette) if v.lower() not in MANUALE]
    assert not fuori, (
        "colori di marca che NON stanno nella tavolozza del manuale "
        "(docs/GAV-design-system.pdf sez.3): "
        + ", ".join(f"{k}={v}" for k, v in fuori)
        + ". Il manuale ammette solo blu, giallo e neutri."
    )


def test_sono_ventisei(palette):
    """Il conteggio e' esso stesso una misura: 16 piatti + 4 status + 3 bg + 3 disk.
    Se cambia, qualcuno ha aggiunto o tolto un token e va deciso apposta."""
    assert len(_colori_di_marca(palette)) == 26


def test_nessuna_chiave_sfugge_alla_rete(palette):
    """LA GUARDIA — senza questa il test sopra e' aggirabile per distrazione.

    Ogni chiave della palette deve essere o un colore di marca (controllato), o
    astronomia (esclusa apposta), o un campo non-colore. Un token NUOVO non puo'
    scivolare fuori dalla rete: va classificato a mano, cioe' deciso.
    (Stessa forma della guardia di R14 sui formati.)"""
    coperte = set(validate.STYLE_TOKENS) | {"status"} | set(GRADIENTI) | ASTRONOMIA | NON_COLORI
    ignote = set(palette) - coperte
    assert not ignote, (
        f"chiavi non classificate nella palette: {sorted(ignote)}. "
        "Vanno aggiunte ai colori di marca (e allora devono venire dal manuale) "
        "oppure dichiarate astronomia, con scritto il perche'."
    )


@pytest.mark.parametrize("chiave", sorted(ASTRONOMIA))
def test_l_esclusione_dell_astronomia_non_e_vacua(palette, chiave):
    """Prova che escludere `star_ramp` e `planet_colors` SERVE davvero: contengono
    colori che il manuale non ammetterebbe mai (l'arancione di Arturo, il rosso
    di Antares, il ruggine di Marte). Se un giorno qualcuno li "allineasse" alla
    tavolozza, questo test diventa rosso — ed e' giusto che costringa a una
    conversazione, perche' significherebbe mentire sull'astronomia (D2).

    PARAMETRIZZATO su UNA chiave alla volta, e non e' un dettaglio: la prima
    stesura le controllava INSIEME, quindi bastava che una delle due fosse fuori
    tavolozza perche' il test restasse verde anche neutralizzando l'altra.
    L'iniezione del guasto l'ha stanato — il buco aveva la stessa forma del bug
    che la rete doveva sorvegliare, per l'ennesima volta in questo progetto."""
    v = palette[chiave]
    colori = [c for _bv, c in v] if chiave == "star_ramp" else list(v.values())
    fuori = [c for c in colori if c.lower() not in MANUALE]
    assert fuori, (
        f"'{chiave}' e' tutto dentro la tavolozza del manuale: o l'esclusione "
        "non serve piu', o qualcuno ha ricolorato l'astronomia (D2)."
    )
