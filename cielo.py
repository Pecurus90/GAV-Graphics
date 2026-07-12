#!/usr/bin/env python3
"""
CLI del Cielo del Mese.

Questo e' il PUNTO DI COMPOSIZIONE (decisione D1): compone il motore
(engine/generate.py, che produce solo SVG ed e' puro) con render.py (SVG->PNG).
Vive FUORI da engine/ apposta — il motore non conosce render.py (invariante #1),
esattamente come gia' fa la web app (app/main.py). Il motore non importa nulla
di qui; e' il CLI che tira le fila dei due moduli.

Uso:
  python cielo.py --year 2026 --month 8 --place Vicenza                       # A4, SVG
  python cielo.py --year 2026 --month 8 --place Vicenza --png                 # A4, SVG + PNG
  python cielo.py --year 2026 --month 8 --format post --png                   # post 1080, SVG + PNG
  python cielo.py --year 2026 --month 8 --format dashboard --palette notte-blu # design social

Formato e palette si scelgono per NOME, non per percorso: i nomi validi sono i
file in brand/layouts/ (a4, post, dashboard, editorial, rail, ...) e in
brand/palettes/ (osservatorio, notte-blu, petrolio, luce-rossa, ...).
"""
import os, json, argparse

from engine.generate import Engine
import render

BASE = os.path.dirname(os.path.abspath(__file__))
LAYOUTS_DIR = os.path.join(BASE, "brand", "layouts")
PALETTES_DIR = os.path.join(BASE, "brand", "palettes")

# Il vocabolario dei formati E' la cartella brand/layouts/: ogni <nome>.json e'
# un formato/design. Aggiungere un design domani = lasciar cadere un file, ZERO
# modifiche qui (stessa filosofia di --palette e della web app). Un layout porta
# gia' il proprio canvas (w/h/font_family): non serve una mappa che ripeta cosa
# il file dice di se'. Il canvas puo' dichiarare 'png_width'; se non lo fa, la
# larghezza PNG si deriva (2x sotto i 1000px, per la qualita' di stampa dell'A4;
# 1x da 1000px in su, tipico dei social gia' a piena risoluzione).
def _formati_disponibili():
    return sorted(f[:-5] for f in os.listdir(LAYOUTS_DIR) if f.endswith(".json"))


def _load_layout(fmt):
    """Risolve un formato per NOME al suo file di layout. Errore leggibile (in
    italiano, non un traceback) se il nome non esiste."""
    path = os.path.join(LAYOUTS_DIR, f"{fmt}.json")
    if not os.path.isfile(path):
        disponibili = ", ".join(_formati_disponibili())
        raise SystemExit(f"Errore: formato sconosciuto '{fmt}'. "
                         f"Formati disponibili: {disponibili}.")
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _png_width(layout, override):
    """Larghezza del PNG: --png-width se dato, altrimenti canvas.png_width se il
    file lo dichiara, altrimenti derivata dalla larghezza del canvas."""
    if override:
        return override
    cv = layout["canvas"]
    if cv.get("png_width"):
        return cv["png_width"]
    w = cv["w"]
    return w if w >= 1000 else w * 2


def _palettes_disponibili():
    """Il vocabolario delle palette E' la cartella brand/palettes/: ogni file
    <nome>.json e' una palette. Aggiungere una palette = aggiungere un file,
    zero modifiche a questo codice (stessa filosofia della web app, che gia'
    scopre i temi cosi')."""
    return sorted(f[:-5] for f in os.listdir(PALETTES_DIR) if f.endswith(".json"))


def _load_palette(name):
    """Risolve una palette per NOME (non per percorso). Errore leggibile (in
    italiano, non un traceback) se il nome non esiste."""
    path = os.path.join(PALETTES_DIR, f"{name}.json")
    if not os.path.isfile(path):
        disponibili = ", ".join(_palettes_disponibili())
        raise SystemExit(f"Errore: palette sconosciuta '{name}'. "
                         f"Palette disponibili: {disponibili}.")
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def main():
    p = argparse.ArgumentParser(description="Genera il Cielo del Mese (SVG, e PNG con --png).")
    p.add_argument('--year', type=int, required=True)
    p.add_argument('--month', type=int, required=True)
    p.add_argument('--lat', type=float, default=45.5455)
    p.add_argument('--lon', type=float, default=11.5353)
    p.add_argument('--place', default='Vicenza')
    p.add_argument('--palette', default='osservatorio',
                   help="nome della palette in brand/palettes/ (default: osservatorio)")
    p.add_argument('--format', default='a4',
                   help="nome del layout in brand/layouts/ (a4, post, dashboard, editorial, rail, ...)")
    p.add_argument('--out', default=None,
                   help="file SVG di uscita (default: out/cielo_<formato>.svg)")
    p.add_argument('--png', action='store_true', help="produce ANCHE il PNG accanto all'SVG")
    p.add_argument('--png-width', type=int, default=None,
                   help="larghezza PNG in px (default sensato per formato)")
    args = p.parse_args()

    layout = _load_layout(args.format)
    theme = _load_palette(args.palette)
    # Default: out/ e' la cartella dei prodotti (usa-e-getta, gitignored). Con
    # --out l'utente sceglie il proprio percorso. In entrambi i casi assicura
    # che la cartella esista, altrimenti la scrittura dell'SVG fallirebbe.
    out = args.out or os.path.join("out", f"cielo_{args.format}.svg")
    outdir = os.path.dirname(out)
    if outdir:
        os.makedirs(outdir, exist_ok=True)

    eng = Engine(datadir=os.path.join(BASE, "data"))
    svg = eng.generate(args.year, args.month, args.lat, args.lon, args.place,
                       theme, out, layout=layout)
    print("SVG:", svg)

    if args.png:
        width = _png_width(layout, args.png_width)
        png = os.path.splitext(svg)[0] + ".png"
        render.svg_file_to_png(svg, png, width=width)
        print("PNG:", png, f"(larghezza {width}px)")


if __name__ == '__main__':
    main()
