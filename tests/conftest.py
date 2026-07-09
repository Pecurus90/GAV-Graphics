"""Configurazione pytest condivisa.

Aggiunge la radice del progetto al path (così `import engine...` funziona a
prescindere da dove si lancia pytest) e fornisce un'istanza di Engine caricata
una sola volta per sessione (carica effemeridi e cataloghi: costoso).
"""
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from engine.generate import Engine  # noqa: E402  (dopo il sys.path)


@pytest.fixture(scope="session")
def eng():
    return Engine(datadir=os.path.join(ROOT, "data"))


@pytest.fixture(scope="session")
def root():
    return ROOT
