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
    ("/preview?theme=arcobaleno", "Palette sconosciuta"),
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
    r = client.get("/genera?year=2026&month=8&formato=post")
    assert r.status_code == 200
    for i in range(4):
        assert f"event: fase\ndata: {i}" in r.text, f"manca la fase {i}"
    assert "event: fatto" in r.text


def test_anteprima_token_ignoto_404():
    r = client.get("/anteprima?token=inesistente")
    assert r.status_code == 404


# --- schede dal disco: profondo NON e' una scheda, e' la pagina 2 del carosello ---
def test_schede_dal_disco_escludono_profondo():
    import app.main as A
    nomi = [f for f, _ in A.formati_scheda()]
    assert "profondo" not in nomi, "profondo non e' un formato-scheda: e' la pagina 2"
    assert set(nomi) == {"a4", "post", "dashboard", "editorial", "rail"}, nomi
    assert A._pagina2_formato() == "profondo"


# --- il carosello: UN'AZIONE, DUE pagine con gli stessi parametri ---
def test_carosello_produce_due_pagine():
    r = client.get("/carosello?year=2026&month=8&formato=post")
    assert r.status_code == 200
    assert "event: pagina\ndata: 1" in r.text and "event: pagina\ndata: 2" in r.text
    # 'fatto' porta DUE token (pagina 1 e pagina 2)
    import re
    m = re.search(r"event: fatto\ndata: ([0-9a-f]+),([0-9a-f]+)", r.text)
    assert m, "il carosello deve finire con due token"


# --- la larghezza PNG e' quella GIUSTA per formato (stessa logica del CLI) ---
def test_larghezza_png_per_formato():
    import json, os
    import render
    ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    def w(fmt):
        lay = json.load(open(os.path.join(ROOT, "brand", "layouts", f"{fmt}.json"), encoding="utf-8"))
        return render.png_width(lay)
    assert w("a4") == 1800, "l'A4 (canvas 900) va a 1800"
    assert w("post") == 1080, "il post social va a 1080, NON alla misura dell'A4"
    assert w("profondo") == 1080
    import cielo
    assert cielo.render.png_width is render.png_width, "il CLI riusa la stessa logica"
