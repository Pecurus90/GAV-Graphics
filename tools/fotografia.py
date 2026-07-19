#!/usr/bin/env python3
"""
Rete di sicurezza per il refactor di pulizia: FOTOGRAFIA SHA256 dell'output.

I golden (tests/golden/) coprono SOLO l'A4 di agosto. In #7e quel buco lascio'
i test verdi con un import dimenticato (la pagina 2 non era coperta). Questa
fotografia copre cio' che i golden NON coprono: TUTTI e 5 i formati su 4 mesi
(uno per stagione). Criterio come #7e: output identico BYTE PER BYTE, verificato
e non promesso.

Uso:
  python tools/fotografia.py --scatta   # genera gli SVG e salva gli SHA256
  python tools/fotografia.py            # rigenera e CONFRONTA con la fotografia
                                        # (exit 1 e diff se anche un byte cambia)

Parametri canonici (come i golden): 2026, Vicenza (45.5455, 11.5353), osservatorio.
Deterministico: seed fisso del rumore di sfondo + matematica deterministica
(la stessa proprieta' che regge il golden).
"""
import hashlib
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from engine.generate import Engine  # noqa: E402
import validate                     # noqa: E402

SNAPSHOT = os.path.join(HERE, "fotografia_sha256.txt")

FORMATI = ["dashboard", "parata", "zenit", "a4", "deep-space"]
MESI = [2, 5, 8, 11]   # una per stagione: inverno, primavera, estate, autunno
ANNO, LAT, LON, LUOGO, PALETTE = 2026, 45.5455, 11.5353, "Vicenza", "osservatorio"


def _hash_tutti():
    """Ritorna {'<fmt>_<mm>': sha256hex} per ogni (formato, mese)."""
    eng = Engine(datadir=os.path.join(ROOT, "data"))
    theme = validate.carica_palette(PALETTE)
    out = {}
    with tempfile.TemporaryDirectory() as d:
        for fmt in FORMATI:
            with open(os.path.join(ROOT, "brand", "layouts", f"{fmt}.json"),
                      encoding="utf-8") as fh:
                layout = json.load(fh)
            for m in MESI:
                svg = os.path.join(d, f"{fmt}_{m:02d}.svg")
                eng.generate(ANNO, m, LAT, LON, LUOGO, theme, svg, layout=layout)
                with open(svg, "rb") as fh:
                    out[f"{fmt}_{m:02d}"] = hashlib.sha256(fh.read()).hexdigest()
    return out


def scatta():
    h = _hash_tutti()
    with open(SNAPSHOT, "w", encoding="utf-8", newline="\n") as fh:
        for k in sorted(h):
            fh.write(f"{h[k]}  {k}\n")
    print(f"Fotografia salvata: {len(h)} SVG ({len(FORMATI)} formati x {len(MESI)} mesi) -> {SNAPSHOT}")


def verifica():
    if not os.path.exists(SNAPSHOT):
        print(f"Fotografia mancante: {SNAPSHOT}. Fai prima --scatta.")
        return 1
    atteso = {}
    with open(SNAPSHOT, encoding="utf-8") as fh:
        for line in fh:
            sha, k = line.split()
            atteso[k] = sha
    ora = _hash_tutti()
    diff = []
    for k in sorted(set(atteso) | set(ora)):
        if atteso.get(k) != ora.get(k):
            diff.append(k)
    if diff:
        print(f"DIVERSO: {len(diff)} SVG cambiati rispetto alla fotografia:")
        for k in diff:
            print(f"  {k}: {atteso.get(k, '(nuovo)')[:12]} -> {ora.get(k, '(sparito)')[:12]}")
        return 1
    print(f"OK: tutti i {len(ora)} SVG identici alla fotografia (byte per byte).")
    return 0


if __name__ == "__main__":
    if "--scatta" in sys.argv:
        scatta()
    else:
        sys.exit(verifica())
