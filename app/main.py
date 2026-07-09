#!/usr/bin/env python3
"""
Web app minimale per il generatore Cielo del Mese.
Avvio (dalla cartella del progetto):
    uvicorn app.main:app --reload --port 8000
Poi apri http://localhost:8000

Questo e' uno SCHELETRO funzionante ma volutamente essenziale: e' il punto di
partenza per Claude Code (vedi README, sezione "Cosa costruire con Claude Code").
"""
import json, tempfile, os
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, FileResponse

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from engine.generate import Engine
from render import svg_file_to_png

BASE = os.path.join(os.path.dirname(__file__), "..")
PALETTES = os.path.join(BASE, "brand", "palettes")
app = FastAPI(title="Cielo del Mese")
engine = Engine(datadir=os.path.join(BASE, "data"))  # caricato una volta sola


def list_themes():
    return [f[:-5] for f in os.listdir(PALETTES) if f.endswith(".json")]


@app.get("/", response_class=HTMLResponse)
def index():
    opts = "".join(f'<option>{t}</option>' for t in list_themes())
    return f"""
    <html><head><meta charset="utf-8"><title>Cielo del Mese</title>
    <style>body{{background:#070c1e;color:#eef3ff;font-family:system-ui;padding:24px}}
    input,select{{padding:6px;margin:4px;border-radius:6px;border:1px solid #2b3f73;
    background:#0c1330;color:#eef3ff}} label{{display:inline-block;width:90px}}
    a.btn,button{{background:#45c8ff;color:#04060f;border:0;padding:8px 14px;
    border-radius:8px;text-decoration:none;font-weight:bold;margin:4px}}</style></head>
    <body><h2>Cielo del Mese</h2>
    <form action="/preview" method="get" target="pv">
      <label>Anno</label><input name="year" value="2026"><br>
      <label>Mese</label><input name="month" value="8"><br>
      <label>Localita</label><input name="place" value="Vicenza"><br>
      <label>Lat</label><input name="lat" value="45.5455">
      <label>Lon</label><input name="lon" value="11.5353"><br>
      <label>Tema</label><select name="theme">{opts}</select><br>
      <button type="submit">Genera anteprima</button>
    </form>
    <p><a class="btn" href="/download?fmt=svg" target="_blank">SVG</a>
       <a class="btn" href="/download?fmt=png" target="_blank">PNG</a>
       (usano gli ultimi parametri inviati)</p>
    <iframe name="pv" style="width:100%;height:900px;border:1px solid #2b3f73;
      border-radius:12px;background:#04060f"></iframe>
    </body></html>"""


def _render(year, month, lat, lon, place, theme):
    th = json.load(open(os.path.join(PALETTES, f"{theme}.json"), encoding="utf-8"))
    out = os.path.join(tempfile.gettempdir(), "cielo.svg")
    engine.generate(int(year), int(month), float(lat), float(lon), place, th, out)
    return out


@app.get("/preview")
def preview(year=2026, month=8, lat=45.5455, lon=11.5353, place="Vicenza",
            theme="osservatorio"):
    svg = _render(year, month, lat, lon, place, theme)
    return FileResponse(svg, media_type="image/svg+xml")


@app.get("/download")
def download(fmt="svg", year=2026, month=8, lat=45.5455, lon=11.5353,
             place="Vicenza", theme="osservatorio"):
    svg = _render(year, month, lat, lon, place, theme)
    if fmt == "svg":
        return FileResponse(svg, media_type="image/svg+xml", filename="cielo.svg")
    if fmt == "png":
        tmp = os.path.join(tempfile.gettempdir(), "cielo.png")
        svg_file_to_png(svg, tmp, width=1800)
        return FileResponse(tmp, media_type="image/png", filename="cielo.png")
    return {"error": "formato non valido"}
