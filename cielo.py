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
  python cielo.py --year 2026 --month 8 --format zenit --png                  # quadrato 1080, SVG + PNG
  python cielo.py --year 2026 --month 8 --format parata --png                 # design social

Il formato si sceglie per NOME, non per percorso: i nomi validi sono i file in
brand/layouts/ (a4, dashboard, parata, zenit, deep-space). La PALETTE non si
sceglie: e' una sola, l'identita' visiva del GAV (brand/palettes/gav.json).
"""
import os, json, argparse

from engine.generate import Engine
import render
import validate

BASE = os.path.dirname(os.path.abspath(__file__))
LAYOUTS_DIR = os.path.join(BASE, "brand", "layouts")


def main():
    p = argparse.ArgumentParser(description="Genera il Cielo del Mese (SVG, e PNG con --png).")
    # NB: year/month/lat/lon sono stringhe, non type=int/float: cosi' un valore
    # sbagliato (mese=13, lat=abc) e' validato da validate.py con un messaggio in
    # italiano, non intercettato prima da argparse (in inglese).
    p.add_argument('--year', required=True)
    p.add_argument('--month', required=True)
    p.add_argument('--lat', default='45.5455')
    p.add_argument('--lon', default='11.5353')
    p.add_argument('--place', default='Vicenza')
    p.add_argument('--format', default='a4',
                   help="nome del layout in brand/layouts/ (a4, dashboard, parata, zenit, ...)")
    p.add_argument('--out', default=None,
                   help="file SVG di uscita (default: out/cielo_<formato>.svg)")
    p.add_argument('--png', action='store_true', help="produce ANCHE il PNG accanto all'SVG")
    p.add_argument('--png-width', type=int, default=None,
                   help="larghezza PNG in px (default sensato per formato)")
    args = p.parse_args()

    # Validazione condivisa con la web app (R4/D2): input + contratto del tema.
    # Un errore diventa un'uscita pulita con messaggio in italiano, mai un traceback.
    try:
        year = validate.valida_anno(args.year)
        month = validate.valida_mese(args.month)
        lat = validate.valida_lat(args.lat)
        lon = validate.valida_lon(args.lon)
        fmt = validate.valida_formato(args.format)
        with open(os.path.join(LAYOUTS_DIR, f"{fmt}.json"), encoding="utf-8") as fh:
            layout = json.load(fh)
        theme = validate.carica_palette()
        validate.valida_tema(theme, f"{validate.PALETTE}.json")
    except validate.InputError as e:
        raise SystemExit(f"Errore: {e}")
    # Default: out/ e' la cartella dei prodotti (usa-e-getta, gitignored). Con
    # --out l'utente sceglie il proprio percorso. In entrambi i casi assicura
    # che la cartella esista, altrimenti la scrittura dell'SVG fallirebbe.
    out = args.out or os.path.join("out", f"cielo_{fmt}.svg")
    outdir = os.path.dirname(out)
    if outdir:
        os.makedirs(outdir, exist_ok=True)

    eng = Engine(datadir=os.path.join(BASE, "data"))
    svg = eng.generate(year, month, lat, lon, args.place, theme, out, layout=layout)
    print("SVG:", svg)

    if args.png:
        width = render.png_width(layout, args.png_width)
        png = os.path.splitext(svg)[0] + ".png"
        render.svg_file_to_png(svg, png, width=width)
        print("PNG:", png, f"(larghezza {width}px)")


if __name__ == '__main__':
    main()
