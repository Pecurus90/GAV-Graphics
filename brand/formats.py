#!/usr/bin/env python3
"""
Formati canvas condivisi da TUTTI i template di post GAV.

Un "formato" e' solo una dimensione di tela (larghezza x altezza in px). I
template (cielo del mese, pillola, ...) compongono i loro elementi dentro uno di
questi formati. Aggiungere un formato = aggiungere una riga qui.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Formato:
    key: str
    label: str
    w: int
    h: int

    @property
    def ratio(self) -> float:
        return self.w / self.h


# I formati social piu' diffusi (Instagram / Facebook) + l'A4 storico.
FORMATI = {
    "post_quadrato": Formato("post_quadrato", "Post quadrato (feed IG/FB)", 1080, 1080),
    "post_verticale": Formato("post_verticale", "Post verticale (feed IG)", 1080, 1350),
    "storia": Formato("storia", "Storia (IG/FB)", 1080, 1920),
    "a4": Formato("a4", "Volantino A4", 900, 1273),
}

# Formato di default quando non specificato.
DEFAULT = "post_quadrato"


def get(key: str) -> Formato:
    if key not in FORMATI:
        raise KeyError(f"Formato sconosciuto: {key!r}. Disponibili: {list(FORMATI)}")
    return FORMATI[key]
