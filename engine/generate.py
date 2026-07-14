#!/usr/bin/env python3
"""
Compatibilita': il motore del Cielo del Mese vive ora in strumenti/cielo/engine.py
(taglio D14, giro #7e). Questo modulo resta come PONTE perche' i chiamatori
esterni non cambino: `cielo.py` e `app/main.py` importano ancora
`from engine.generate import Engine`, e non vanno toccati (sono gia' snelli).

Re-esporta la superficie pubblica usata fuori dal motore:
- Engine        (cielo.py, app/main.py, tests/conftest.py)
- bv2hex        (tests/test_correctness.py)
- STARS         (tests/test_disc_extras.py)
- point_in_poly (tests/test_messier_page2.py)

Chi vuole il resto (CONST_IT, convex_hull, le dataclass...) importi direttamente
da strumenti.cielo.engine.
"""
from strumenti.cielo.engine import Engine, bv2hex, STARS, point_in_poly  # noqa: F401
