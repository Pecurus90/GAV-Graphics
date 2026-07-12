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
