"""
Web app: input sbagliato -> HTTP 4xx (mai 200 incoerente, mai 500).
Skippa se il TestClient (httpx) non e' installato.
"""
import pytest

pytest.importorskip("httpx")
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402  (carica un Engine: costa, ma una volta)

client = TestClient(app)


@pytest.mark.parametrize("url,frammento", [
    ("/preview?month=13", "Mese"),
    ("/preview?lat=abc", "Latitudine"),
    ("/preview?year=3000", "Anno"),
    ("/download?fmt=gif", "Formato di uscita"),
])
def test_input_sbagliato_da_400_in_italiano(url, frammento):
    r = client.get(url)
    assert r.status_code == 400, f"{url}: atteso 400, ottenuto {r.status_code}"
    assert frammento in r.json()["detail"]


def test_richiesta_valida_da_200_svg():
    r = client.get("/preview?year=2026&month=8")
    assert r.status_code == 200
    assert r.text.lstrip().startswith("<svg")


# --- D10/D11: la pagina con la barra laterale, e la generazione a fasi (SSE) ---
def test_home_ha_la_barra_laterale():
    r = client.get("/")
    assert r.status_code == 200
    body = r.text
    assert "Cielo del Mese" in body            # voce attiva
    assert "Pillole di astronomia" in body     # voce futura
    assert "Prossimamente" in body             # badge spento (non rotto)


def test_genera_input_sbagliato_da_evento_errore_non_500():
    """/genera e' uno stream SSE: input sbagliato -> un evento 'errore' in
    italiano, MAI un 500 muto."""
    r = client.get("/genera?month=13")
    assert r.status_code == 200
    assert "event: errore" in r.text and "Mese" in r.text


def test_genera_valida_riporta_le_quattro_fasi():
    """La barra dice il vero: lo stream riporta le fasi 0..3 e poi 'fatto'."""
    r = client.get("/genera?year=2026&month=8&formato=zenit")
    assert r.status_code == 200
    for i in range(4):
        assert f"event: fase\ndata: {i}" in r.text, f"manca la fase {i}"
    assert "event: fatto" in r.text


def test_anteprima_token_ignoto_404():
    r = client.get("/anteprima?token=inesistente")
    assert r.status_code == 404


# --- schede dal disco: il set finale e' CINQUE (Deep Space e' un formato a se',
#     non piu' la pagina 2 di un carosello - tolto il 2026-07-19) ---
def test_schede_dal_disco_sono_i_cinque_formati():
    import app.main as A
    nomi = [f for f, _ in A.formati_scheda()]
    assert set(nomi) == {"a4", "dashboard", "parata", "zenit", "deep-space"}, nomi
    # niente piu' carosello: la funzione _pagina2_formato e l'endpoint sono spariti
    assert not hasattr(A, "_pagina2_formato"), "il carosello e' stato tolto"


def test_niente_endpoint_carosello():
    """Il carosello e' stato tolto: /carosello non esiste piu' (404)."""
    r = client.get("/carosello?year=2026&month=8&formato=zenit")
    assert r.status_code == 404


def test_deep_space_e_un_formato_generabile():
    """Deep Space si genera da solo, come gli altri formati quadrati."""
    r = client.get("/genera?year=2026&month=8&formato=deep-space")
    assert r.status_code == 200
    assert "event: fatto" in r.text


# --- la larghezza PNG e' quella GIUSTA per formato (stessa logica del CLI) ---
def test_larghezza_png_per_formato():
    import json, os
    import render
    ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    def w(fmt):
        lay = json.load(open(os.path.join(ROOT, "brand", "layouts", f"{fmt}.json"), encoding="utf-8"))
        return render.png_width(lay)
    assert w("a4") == 1800, "l'A4 (canvas 900) va a 1800"
    assert w("zenit") == 1080, "il quadrato social va a 1080, NON alla misura dell'A4"
    assert w("deep-space") == 1080
    import cielo
    assert cielo.render.png_width is render.png_width, "il CLI riusa la stessa logica"
