#!/usr/bin/env python3
"""
Rasterizzazione SVG -> PNG per i post GAV.

Usa `resvg` (motore Rust): rende correttamente i filtri "glow" del brand ed e'
un binario autonomo, quindi si impacchetta pulito nell'.exe senza librerie
native da rincorrere (a differenza di cairosvg).

I font del brand vengono caricati dalla cartella `brand/fonts/` cosi' l'app
funziona offline e dentro l'eseguibile.
"""
import pathlib
import resvg_py

BASE = pathlib.Path(__file__).parent
FONTS_DIR = BASE / "brand" / "fonts"

# Famiglia di default usata dai template (risolta dai font in brand/fonts/).
SANS = "Inter"


def _font_dirs():
    return [str(FONTS_DIR)] if FONTS_DIR.exists() else []


def svg_to_png(svg: str, out_path, width: int | None = None,
               height: int | None = None, zoom: float | None = None) -> str:
    """Rasterizza una stringa SVG in un file PNG.

    width/height: dimensione di uscita in px (se omessi usa quella dell'SVG).
    zoom: moltiplicatore alternativo (per esportare a risoluzione maggiore).
    Restituisce il percorso scritto.
    """
    png = resvg_py.svg_to_bytes(
        svg_string=svg,
        width=width,
        height=height,
        zoom=zoom,
        font_dirs=_font_dirs(),
        sans_serif_family=SANS,
    )
    out_path = str(out_path)
    pathlib.Path(out_path).write_bytes(bytes(png))
    return out_path


def svg_file_to_png(svg_path, out_path, **kw) -> str:
    """Comodo: legge un SVG da file (UTF-8) e lo rasterizza in PNG."""
    svg = pathlib.Path(svg_path).read_text(encoding="utf-8")
    return svg_to_png(svg, out_path, **kw)
