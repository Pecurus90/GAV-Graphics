"""
TEST GOLDEN / DI REGRESSIONE — snapshot dell'SVG attuale.

*** QUESTO TEST NON DIMOSTRA CHE L'OUTPUT SIA CORRETTO. ***
Dimostra solo che l'output NON E' CAMBIATO rispetto al riferimento congelato.
La correttezza (geometria, effemeridi) e' compito di test_correctness.py.

A cosa serve: il prossimo lavoro sara' estrarre il layout dal metodo generate()
per abilitare i formati social. E' un refactor che tocca la geometria. Questo
test dice se sposta anche un solo pixel.

Confronto: BYTE-A-BYTE. Verificato (2026-07-09) che due generazioni consecutive
sullo stesso ambiente sono identiche (stesso sha256) grazie al seed fisso del
rumore di sfondo (np.random.default_rng(7)) e a matematica deterministica.
CAVEAT: il confronto byte-a-byte puo' rompersi cambiando ambiente (versione di
numpy/OS -> ultimo bit dei float -> cifra diversa nei "%.2f"). In quel caso NON
e' un vero cambiamento di output: passare a un confronto strutturale / con
tolleranza numerica. Vedi "Decisioni per l'architetto" nel report del task.

Parametri canonici del riferimento (devono combaciare con chi ha generato il
golden): anno 2026, mese 8, lat 45.5455, lon 11.5353, Vicenza, tema gav.
"""
import json
import os

import pytest

from golden_compare import svg_diff  # confronto a TOLLERANZA (D5)

GOLDEN = os.path.join(os.path.dirname(__file__), "golden", "cielo_2026-08_vicenza.svg")

# Parametri canonici: NON cambiarli senza rigenerare il golden apposta.
PARAMS = dict(year=2026, month=8, lat=45.5455, lon=11.5353, place="Vicenza")


def _genera_svg(eng, root, tmp_path):
    theme = json.load(open(os.path.join(root, "brand", "palettes", "gav.json"),
                           encoding="utf-8"))
    out = str(tmp_path / "cielo.svg")
    eng.generate(PARAMS["year"], PARAMS["month"], PARAMS["lat"], PARAMS["lon"],
                 PARAMS["place"], theme, out)
    return open(out, encoding="utf-8").read()


def test_golden_svg_invariato(eng, root, tmp_path):
    """Rigenera l'SVG canonico e lo confronta col riferimento a TOLLERANZA (D5):
    i numeri entro `TOL` px, tutto il resto (nomi, testo, COLORI) esatto. Cosi'
    la deriva d'ultima-cifra tra piattaforme (CI, D4) non fa ROSSO fantasma, ma
    una regressione vera (coordinata spostata, colore cambiato) resta rossa.
    Se fallisce per un cambiamento VOLUTO: rigenerare il golden apposta."""
    assert os.path.exists(GOLDEN), (
        f"Riferimento golden mancante: {GOLDEN}. "
        "Rigeneralo con i parametri canonici e committalo."
    )
    atteso = open(GOLDEN, encoding="utf-8").read()
    ottenuto = _genera_svg(eng, root, tmp_path)

    msg = svg_diff(ottenuto, atteso)
    if msg:
        pytest.fail("SVG divergente dal golden oltre la tolleranza numerica.\n" + msg)


def test_golden_generazione_deterministica(eng, root, tmp_path):
    """Genera due volte di fila e verifica che l'output sia identico: se non lo
    fosse, ci sarebbe non-determinismo (seed mancante, ordinamento instabile) e
    QUALSIASI test golden sarebbe inaffidabile. Rete di sicurezza del golden."""
    a = _genera_svg(eng, root, tmp_path)
    b = _genera_svg(eng, root, tmp_path)
    assert a == b, "Output non deterministico: due generazioni differiscono."
