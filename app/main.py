#!/usr/bin/env python3
"""
App "Cielo del Mese" del Gruppo Astrofili Vicentini.

Avvio (dalla cartella del progetto):
    python -m uvicorn app.main:app --port 8000
Poi apri http://localhost:8000

L'interfaccia e' PORTATA dal design consegnato (docs/design_handoff/
generatore_app): stesso CSS/markup dei componenti (barra laterale, stepper,
schede formato, pastiglie palette, quattro fasi), collegato al motore vero. Le
schede e le pastiglie si popolano DAI FILE su disco (come il CLI): aggiungere un
layout o una palette domani non richiede di toccare la UI.

- D10: barra laterale, voce attiva + voce "Prossimamente".
- D11: le QUATTRO FASI REALI riportate MAN MANO via Server-Sent Events. Il motore
  non conosce la UI (invariante #1): riceve un callback e lo chiama.
- Carosello: UN'AZIONE produce ENTRAMBE le pagine (il cielo + il profondo cielo)
  con gli STESSI parametri.
- Larghezza PNG per formato: render.png_width, la STESSA logica del CLI.
Tutto OFFLINE (D4/D15): font e logo locali, nessun CDN.
"""
import json, tempfile, os, uuid, queue, threading
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from engine.generate import Engine
import render
import validate

BASE = os.path.join(os.path.dirname(__file__), "..")
LAYOUTS = os.path.join(BASE, "brand", "layouts")

app = FastAPI(title="Cielo del Mese")
app.mount("/fonts", StaticFiles(directory=os.path.join(BASE, "brand", "fonts")), name="fonts")
app.mount("/assets", StaticFiles(directory=os.path.join(BASE, "brand", "logo")), name="assets")

engine = Engine(datadir=os.path.join(BASE, "data"))  # caricato una volta sola
_risultati = {}  # token -> percorso PNG (app locale mono-utente: dict in memoria)

MESI = ["Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno", "Luglio",
        "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"]

# Thumbnail bespoke del design, per formato noto (asset di design). Un formato
# senza thumbnail dedicata prende quella generica: la scheda compare lo stesso.
_TH = {
 "dashboard": '<svg width="82" height="58" viewBox="0 0 82 58"><rect x="1" y="1" width="80" height="56" rx="5" fill="#0c1526" stroke="#2a3a5a"/><circle cx="24" cy="27" r="15" fill="none" stroke="#45c8ff" stroke-width="1.4" opacity=".8"/><circle cx="24" cy="27" r="7.5" fill="none" stroke="#2a4a7a" stroke-width="1"/><rect x="47" y="12" width="27" height="8" rx="2" fill="#16233d"/><rect x="47" y="24" width="27" height="8" rx="2" fill="#16233d"/><rect x="47" y="36" width="27" height="8" rx="2" fill="#16233d"/><circle cx="12" cy="49" r="1.6" fill="#3a4d70"/><circle cx="20" cy="49" r="1.6" fill="#3a4d70"/><circle cx="28" cy="49" r="1.6" fill="#e4ac4a"/><circle cx="36" cy="49" r="1.6" fill="#3a4d70"/></svg>',
 "parata": '<svg width="82" height="58" viewBox="0 0 82 58"><rect x="1" y="1" width="80" height="56" rx="5" fill="#0c1526" stroke="#2a3a5a"/><rect x="8" y="7" width="30" height="3.5" rx="1.7" fill="#e4ac4a"/><rect x="8" y="16" width="66" height="10" rx="2" fill="#16233d"/><circle cx="15" cy="21" r="2" fill="#45c8ff"/><circle cx="27" cy="21" r="2" fill="#45c8ff"/><circle cx="39" cy="21" r="2" fill="#45c8ff"/><circle cx="51" cy="21" r="2" fill="#45c8ff"/><circle cx="41" cy="38" r="10" fill="none" stroke="#45c8ff" stroke-width="1.3" opacity=".8"/><rect x="8" y="50" width="66" height="4" rx="2" fill="#111c33"/></svg>',
 "cornice": '<svg width="82" height="58" viewBox="0 0 82 58"><rect x="1" y="1" width="80" height="56" rx="5" fill="#0c1526" stroke="#2a3a5a"/><rect x="7" y="6" width="26" height="3" rx="1.5" fill="#e4ac4a"/><rect x="18" y="12" width="46" height="26" rx="5" fill="none" stroke="#45c8ff" stroke-width="1.3"/><circle cx="41" cy="25" r="10" fill="none" stroke="#45c8ff" stroke-width="1.1" opacity=".7"/><rect x="8" y="43" width="20" height="11" rx="2" fill="#16233d"/><rect x="31" y="43" width="20" height="11" rx="2" fill="#16233d"/><rect x="54" y="43" width="20" height="11" rx="2" fill="#16233d"/></svg>',
 "zenit": '<svg width="82" height="58" viewBox="0 0 82 58"><rect x="1" y="1" width="80" height="56" rx="5" fill="#0c1526"/><circle cx="41" cy="29" r="30" fill="none" stroke="#45c8ff" stroke-width="1.3" opacity=".85"/><circle cx="41" cy="29" r="18" fill="none" stroke="#2a4a7a" stroke-width="1"/><rect x="5" y="5" width="30" height="10" rx="2.5" fill="#0c1526" fill-opacity=".72" stroke="#2a3a5a" stroke-width=".8"/><rect x="49" y="5" width="28" height="14" rx="2.5" fill="#0c1526" fill-opacity=".72" stroke="#2a3a5a" stroke-width=".8"/><rect x="5" y="44" width="72" height="9" rx="2.5" fill="#0c1526" fill-opacity=".72" stroke="#2a3a5a" stroke-width=".8"/></svg>',
 "a4": '<svg width="44" height="58" viewBox="0 0 44 58"><rect x="1" y="1" width="42" height="56" rx="4" fill="#0c1526" stroke="#2a3a5a"/><rect x="9" y="7" width="26" height="3.5" rx="1.7" fill="#e4ac4a"/><circle cx="22" cy="27" r="14" fill="none" stroke="#45c8ff" stroke-width="1.3" opacity=".8"/><circle cx="22" cy="27" r="7" fill="none" stroke="#2a4a7a" stroke-width="1"/><rect x="9" y="46" width="26" height="2.5" rx="1.2" fill="#26344f"/><rect x="9" y="51" width="18" height="2.5" rx="1.2" fill="#26344f"/></svg>',
}
_TH_GEN = '<svg width="82" height="58" viewBox="0 0 82 58"><rect x="1" y="1" width="80" height="56" rx="5" fill="#0c1526" stroke="#2a3a5a"/><circle cx="41" cy="29" r="18" fill="none" stroke="#45c8ff" stroke-width="1.4" opacity=".7"/></svg>'


def _leggi(dirp, nome):
    with open(os.path.join(dirp, f"{nome}.json"), encoding="utf-8") as fh:
        return json.load(fh)


def formati_scheda():
    """I formati con una 'scheda' (esclusi quelli di solo-carosello, es. profondo),
    dal disco, ordinati per scheda.ordine. Aggiungere un layout con una scheda =
    una scheda nella UI, senza toccare qui."""
    out = []
    for f in sorted(x[:-5] for x in os.listdir(LAYOUTS) if x.endswith(".json")):
        d = _leggi(LAYOUTS, f)
        if d.get("carosello_pagina2") or "scheda" not in d:
            continue
        s = d["scheda"]
        out.append((s.get("ordine", 99), f, s))
    out.sort()
    return [(f, s) for _o, f, s in out]


def _pagina2_formato():
    """Il formato marcato come pagina 2 del carosello (profondo), dal disco."""
    for f in sorted(x[:-5] for x in os.listdir(LAYOUTS) if x.endswith(".json")):
        if _leggi(LAYOUTS, f).get("carosello_pagina2"):
            return f
    return None


def palette_pastiglie():
    """Le palette dal disco (di serie + create dal socio, UNIONE via validate): nome,
    descrizione, e i colori VERI (bg, neon) per il campione. Nessun colore scritto a
    mano nella UI: viene dalla palette."""
    out = []
    for p in validate.palette_disponibili():
        out.append((p, validate.carica_palette(p)))
    return out


# ---------------------------------------------------------------------------
# Generazione condivisa (validazione R4 + contratto D2/D13 + larghezza per formato).
# ---------------------------------------------------------------------------
def _valida(year, month, lat, lon, theme, formato, hour):
    y = validate.valida_anno(year); m = validate.valida_mese(month)
    la = validate.valida_lat(lat); lo = validate.valida_lon(lon)
    ho = validate.valida_ora(hour)
    pal = validate.valida_palette(theme); fo = validate.valida_formato(formato)
    th = validate.carica_palette(pal); validate.valida_tema(th, f"{pal}.json")
    layout = _leggi(LAYOUTS, fo)
    return y, m, la, lo, ho, th, layout, fo


def _render(year, month, lat, lon, place, theme, formato="a4", hour=23, progress=None):
    y, m, la, lo, ho, th, layout, _fo = _valida(year, month, lat, lon, theme, formato, hour)
    out = os.path.join(tempfile.gettempdir(), "cielo.svg")
    engine.generate(y, m, la, lo, place, th, out, hour_local=ho, layout=layout, progress=progress)
    return out, layout


@app.get("/preview")
def preview(year=2026, month=8, lat=45.5455, lon=11.5353, place="Vicenza",
            theme="osservatorio", formato="a4", hour=23):
    try:
        svg, _ = _render(year, month, lat, lon, place, theme, formato, hour)
    except validate.InputError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return FileResponse(svg, media_type="image/svg+xml")


@app.get("/download")
def download(fmt="svg", year=2026, month=8, lat=45.5455, lon=11.5353,
             place="Vicenza", theme="osservatorio", formato="a4", hour=23):
    if fmt not in ("svg", "png"):
        raise HTTPException(status_code=400,
                            detail=f"Formato di uscita sconosciuto: '{fmt}'. Ammessi: svg, png.")
    try:
        svg, layout = _render(year, month, lat, lon, place, theme, formato, hour)
    except validate.InputError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if fmt == "svg":
        return FileResponse(svg, media_type="image/svg+xml", filename=f"cielo_{formato}.svg")
    tmp = os.path.join(tempfile.gettempdir(), "cielo_dl.png")
    render.svg_file_to_png(svg, tmp, width=render.png_width(layout))  # larghezza per formato
    return FileResponse(tmp, media_type="image/png", filename=f"cielo_{formato}.png")


# ---------------------------------------------------------------------------
# SSE: le QUATTRO FASI REALI riportate MAN MANO (D11). Niente barra finta.
# ---------------------------------------------------------------------------
def _sse(ev, dato):
    return f"event: {ev}\ndata: {dato}\n\n"


def _genera_pagina(q, args, place, formato):
    """Genera UNA pagina (SVG+PNG) riportando le fasi su `q`; ritorna il token."""
    y, m, la, lo, ho, th, layout, fo = args
    token = uuid.uuid4().hex
    svg = os.path.join(tempfile.gettempdir(), f"cielo_{token}.svg")
    engine.generate(y, m, la, lo, place, th, svg, hour_local=ho, layout=layout,
                    progress=lambda i: q.put(("fase", i)))
    q.put(("fase", engine.FASE_RENDERING))                 # fase 4: rasterizzazione PNG
    png = os.path.join(tempfile.gettempdir(), f"cielo_{token}.png")
    render.svg_file_to_png(svg, png, width=render.png_width(layout))
    _risultati[token] = png
    return token


def _stream(q):
    while True:
        ev, val = q.get()
        if ev is None:
            break
        yield _sse(ev, val)


@app.get("/genera")
def genera(year=2026, month=8, lat=45.5455, lon=11.5353, place="Vicenza",
           theme="osservatorio", formato="a4", hour=23):
    try:
        args = _valida(year, month, lat, lon, theme, formato, hour)
    except validate.InputError as e:
        return StreamingResponse(iter([_sse("errore", str(e))]), media_type="text/event-stream")
    q = queue.Queue()

    def lavora():
        try:
            token = _genera_pagina(q, args, place, formato)
            q.put(("fatto", token))
        except Exception as e:
            q.put(("errore", f"Errore imprevisto: {e}"))
        finally:
            q.put((None, None))
    threading.Thread(target=lavora, daemon=True).start()
    return StreamingResponse(_stream(q), media_type="text/event-stream")


@app.get("/carosello")
def carosello(year=2026, month=8, lat=45.5455, lon=11.5353, place="Vicenza",
              theme="osservatorio", formato="dashboard", hour=23):
    """UN'AZIONE, DUE pagine con gli STESSI parametri: il cielo (formato scelto) +
    il profondo cielo (la pagina 2, marcata sul disco). E' il prodotto mensile."""
    p2 = _pagina2_formato()
    if p2 is None:
        return StreamingResponse(iter([_sse("errore", "Nessuna pagina 2 (profondo) trovata.")]),
                                 media_type="text/event-stream")
    try:
        a1 = _valida(year, month, lat, lon, theme, formato, hour)
        a2 = _valida(year, month, lat, lon, theme, p2, hour)
    except validate.InputError as e:
        return StreamingResponse(iter([_sse("errore", str(e))]), media_type="text/event-stream")
    # Il carosello vale SOLO fra formati quadrati: Instagram pretende che tutte le
    # immagini di un carosello abbiano le STESSE proporzioni, altrimenti le ritaglia
    # (l'A4 verticale accanto al quadrato profondo verrebbe tagliato). L'aspetto e'
    # un DATO della scheda, non una lista di formati scritta a mano.
    scheda1 = a1[6].get("scheda", {})
    if scheda1.get("aspect") != "sq":
        nome = scheda1.get("nome", formato)
        return StreamingResponse(iter([_sse("errore",
            f"Il carosello affianca due pagine e Instagram pretende le stesse "
            f"proporzioni: «{nome}» e' verticale e verrebbe ritagliato. Scegli un "
            f"formato quadrato.")]), media_type="text/event-stream")
    q = queue.Queue()

    def lavora():
        try:
            q.put(("pagina", 1))
            t1 = _genera_pagina(q, a1, place, formato)
            q.put(("pagina", 2))
            t2 = _genera_pagina(q, a2, place, p2)
            q.put(("fatto", f"{t1},{t2}"))
        except Exception as e:
            q.put(("errore", f"Errore imprevisto: {e}"))
        finally:
            q.put((None, None))
    threading.Thread(target=lavora, daemon=True).start()
    return StreamingResponse(_stream(q), media_type="text/event-stream")


@app.get("/anteprima")
def anteprima(token=""):
    p = _risultati.get(token)
    if not p or not os.path.exists(p):
        raise HTTPException(status_code=404, detail="Anteprima non trovata o scaduta.")
    return FileResponse(p, media_type="image/png")


# ---------------------------------------------------------------------------
# D18 — L'EDITOR DI PALETTE. Anteprima sul cielo VERO + salva-come-palette.
# ---------------------------------------------------------------------------
# L'anteprima si rende a LARGHEZZA RIDOTTA: misurato (2026-07-16) che il costo e'
# quasi tutto rasterizzazione resvg (raster 1080 ~0,93s, geometria ~0), quindi
# NON serve cachare la geometria — basta rasterizzare piu' piccolo. A 600px
# l'anteprima e' ~0,8s: buona per un aggiornamento a RILASCIO del colore, non una
# live-preview per-pixel (che resvg non puo' dare, e non la promettiamo).
ANTEPRIMA_W = 600


def _tema_da_richiesta(body):
    """Compone il tema dai token di marca del client + astro innestate (validate),
    poi lo VALIDA. La whitelist e l'innesto sono in validate: qui non si tocca."""
    theme = validate.componi_palette_utente(body.get("tokens") or {}, "Anteprima", "")
    validate.valida_tema(theme, "anteprima")
    return theme


@app.post("/palette/anteprima")
async def palette_anteprima(request: Request):
    body = await request.json()
    try:
        y = validate.valida_anno(body.get("year", 2026))
        m = validate.valida_mese(body.get("month", 8))
        la = validate.valida_lat(body.get("lat", 45.5455))
        lo = validate.valida_lon(body.get("lon", 11.5353))
        ho = validate.valida_ora(body.get("hour", 23))
        fo = validate.valida_formato(body.get("formato", "dashboard"))
        theme = _tema_da_richiesta(body)
        layout = _leggi(LAYOUTS, fo)
    except validate.InputError as e:
        raise HTTPException(status_code=400, detail=str(e))
    place = (body.get("place") or "Vicenza").strip() or "Vicenza"
    token = uuid.uuid4().hex
    svg = os.path.join(tempfile.gettempdir(), f"editor_{token}.svg")
    png = os.path.join(tempfile.gettempdir(), f"editor_{token}.png")
    engine.generate(y, m, la, lo, place, theme, svg, hour_local=ho, layout=layout)
    render.svg_file_to_png(svg, png, width=ANTEPRIMA_W)
    return FileResponse(png, media_type="image/png")


@app.post("/palette/salva")
async def palette_salva(request: Request):
    body = await request.json()
    try:
        slug, theme, _path = validate.salva_palette_utente(
            body.get("name"), body.get("descrizione"), body.get("tokens") or {})
    except validate.InputError as e:
        raise HTTPException(status_code=400, detail=str(e))
    # la pastiglia gia' pronta: il client la infila nella lista e la seleziona
    return {"slug": slug, "name": theme["name"], "dot": theme["neon"],
            "pastiglia": _pastiglia_html(slug, theme, sel=True)}


# ---------------------------------------------------------------------------
# La pagina: schede/pastiglie popolate dal disco, poi il markup portato dal design.
# ---------------------------------------------------------------------------
def _schede_html(default="dashboard"):
    out = []
    for f, s in formati_scheda():
        wide = " wide" if s.get("aspect") == "a4" else ""
        sel = " sel" if f == default else ""
        thumb = _TH.get(f, _TH_GEN)
        out.append(
            f'<button type="button" class="fmt{wide}{sel}" data-fmt="{f}" '
            f'data-name="{s["nome"]}" data-ar="{s.get("aspect","sq")}">'
            f'<span class="tick">✓</span><span class="thumb">{thumb}</span>'
            f'<span class="meta"><span class="fname">{s["nome"]}</span>'
            f'<div class="ftag">{s["tag"]}</div></span></button>')
    return "\n".join(out)


def _pastiglia_html(p, d, sel=False):
    """UNA pastiglia palette. Un solo posto che sa com'e' fatta: la usano sia la
    pagina iniziale sia la risposta di /palette/salva (cosi' una palette creata
    compare identica alle altre)."""
    bg = d["bg"]; neon = d["neon"]
    grad = f"linear-gradient(160deg,{bg[0]},{bg[1]} 55%,{bg[2]})"
    selc = " sel" if sel else ""
    nv = (f'<span class="nv">◑ {d["nota"]}</span>' if d.get("nota") else "")
    return (
        f'<button type="button" class="pal{selc}" data-pal="{p}" '
        f'data-name="{d["name"]}" data-dot="{neon}">'
        f'<span class="tick">✓</span>'
        f'<span class="swatch" style="background:{grad};">'
        f'<span class="stars"></span><span class="disc"></span>'
        f'<span class="neon" style="background:{neon};box-shadow:0 0 12px {neon};"></span></span>'
        f'<span class="meta"><div class="pname">{d["name"]}</div>'
        f'<div class="ptag">{d.get("descrizione","")}</div>{nv}</span></button>')


def _pastiglie_html(default="osservatorio"):
    return "\n".join(_pastiglia_html(p, d, sel=(p == default))
                     for p, d in palette_pastiglie())


# Token DI MARCA (solo quelli) di ogni palette, per SEMINARE l'editor da una
# palette esistente. Le 2 chiavi astronomiche NON entrano qui: il client non le
# vede mai (D2/D18) — l'innesto avviene solo server-side al salvataggio.
def _brand_tokens(d):
    bt = {k: d.get(k) for k in validate.STYLE_TOKENS}
    bt["bg"] = d.get("bg"); bt["disk"] = d.get("disk")
    bt["status"] = {k: (d.get("status") or {}).get(k) for k in validate.STATUS_KEYS}
    return bt


def _paldata_json():
    return json.dumps({p: _brand_tokens(d) for p, d in palette_pastiglie()},
                      ensure_ascii=False)


@app.get("/", response_class=HTMLResponse)
def index():
    mesi = "".join(f'<option value="{i+1}"{" selected" if i==7 else ""}>{i+1:02d} · {n}</option>'
                   for i, n in enumerate(MESI))
    return (PAGINA
            .replace("<!--MESI-->", mesi)
            .replace("<!--SCHEDE-->", _schede_html())
            .replace("<!--PASTIGLIE-->", _pastiglie_html())
            .replace("/*PALDATA*/", _paldata_json()))


PAGINA = r"""<!DOCTYPE html><html lang="it"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Cielo del Mese · GAV</title>
<style>
@font-face{font-family:'Barlow Semi Condensed';src:url('/fonts/BarlowSemiCondensed-SemiBold.ttf') format('truetype');font-weight:600;font-display:swap}
@font-face{font-family:'Barlow Semi Condensed';src:url('/fonts/BarlowSemiCondensed-ExtraBold.ttf') format('truetype');font-weight:800;font-display:swap}
@font-face{font-family:'Instrument Sans';src:url('/fonts/InstrumentSans-Regular.ttf') format('truetype');font-weight:400;font-display:swap}
@font-face{font-family:'Instrument Sans';src:url('/fonts/InstrumentSans-Medium.ttf') format('truetype');font-weight:500;font-display:swap}
@font-face{font-family:'Instrument Sans';src:url('/fonts/InstrumentSans-SemiBold.ttf') format('truetype');font-weight:600;font-display:swap}
:root{--notte:#05070f;--blunotte:#0a1222;--bluprof:#12203a;--superficie:#0e1626;--superficie2:#131d31;
--bordo:rgba(150,170,215,.14);--bordo-forte:rgba(150,170,215,.26);--oro:#e4ac4a;--oro-chiaro:#f0c274;
--petrolio:#004f6d;--neon:#45c8ff;--t1:#eef2fb;--t2:#b9c4dc;--t3:#8e9bb8;--t4:#6a768f;
--warn:#f0b45a;--danger:#f08a6a;--ok:#6fe0a0;--display:'Barlow Semi Condensed','Arial Narrow',system-ui,sans-serif;
--testo:'Instrument Sans',system-ui,-apple-system,'Segoe UI',sans-serif}
*{box-sizing:border-box;margin:0;padding:0}html,body{height:100%}
body{font-family:var(--testo);color:var(--t1);background:radial-gradient(135% 75% at 50% -12%,#12203a 0%,#0a1222 42%,#05070f 100%);overflow:hidden;-webkit-font-smoothing:antialiased}
.titlebar{height:38px;display:flex;align-items:center;gap:9px;padding:0 16px;background:rgba(5,7,15,.55);border-bottom:1px solid var(--bordo);font-family:var(--display);font-weight:600;font-size:12.5px;letter-spacing:.16em;text-transform:uppercase;color:var(--t4)}
.titlebar .dot{width:11px;height:11px;border-radius:50%;background:#2a344b}
.titlebar .dot:first-child{background:#c96a52}.titlebar .dot:nth-child(2){background:#d8a24a}.titlebar .dot:nth-child(3){background:#5a8f6a}
.titlebar .name{margin-left:12px}
.app{display:flex;height:calc(100% - 38px)}
.nav{width:224px;flex:0 0 224px;height:100%;display:flex;flex-direction:column;padding:22px 16px 20px;gap:6px;background:linear-gradient(180deg,rgba(5,7,15,.6),rgba(5,7,15,.28));border-right:1px solid var(--bordo)}
.nav .nav-brand{display:flex;align-items:center;gap:12px;padding:2px 8px 20px}
.nav .nav-brand img{width:40px;height:40px;filter:drop-shadow(0 3px 10px rgba(0,0,0,.5))}
.nav .nav-brand .nb-txt{font-family:var(--display);font-weight:800;font-size:16px;line-height:1.02;color:var(--t1);letter-spacing:.01em}
.nav .nav-brand .nb-sub{font-family:var(--display);font-weight:600;font-size:9.5px;letter-spacing:.18em;text-transform:uppercase;color:var(--t4);margin-top:3px}
.nav .nav-cap{font-family:var(--display);font-weight:600;font-size:10.5px;letter-spacing:.2em;text-transform:uppercase;color:var(--t4);padding:0 10px 8px}
.nav-item{display:flex;align-items:center;gap:13px;width:100%;text-align:left;background:none;border:1px solid transparent;border-radius:13px;padding:14px 13px;cursor:pointer;transition:.14s;color:var(--t2);font-family:var(--testo)}
.nav-item .ic{flex:0 0 26px;width:26px;height:26px;color:var(--t3);transition:.14s}
.nav-item .nm{font-size:16px;font-weight:600;line-height:1.15}
.nav-item .badge{font-family:var(--display);font-weight:600;font-size:9.5px;letter-spacing:.12em;text-transform:uppercase;color:var(--t4);margin-top:3px;display:block}
.nav-item:hover{background:rgba(150,170,215,.07);border-color:var(--bordo)}
.nav-item.on{background:linear-gradient(180deg,rgba(228,172,74,.14),rgba(228,172,74,.04));border-color:rgba(228,172,74,.4);color:var(--t1);box-shadow:0 8px 22px rgba(0,0,0,.28)}
.nav-item.on .ic{color:var(--oro)}.nav-item.on .nm{color:var(--t1)}
.nav-item.soon{cursor:not-allowed}.nav-item.soon:hover{background:none;border-color:transparent}
.nav-item.soon .nm,.nav-item.soon .ic{opacity:.5}
.nav-foot{margin-top:auto;padding:14px 10px 0;border-top:1px solid var(--bordo);font-size:11.5px;color:var(--t4);line-height:1.5}
.panel{width:404px;flex:0 0 404px;height:100%;overflow-y:auto;padding:26px 26px 30px;background:linear-gradient(180deg,rgba(19,29,49,.55),rgba(10,18,34,.35));border-right:1px solid var(--bordo)}
.brand{display:flex;align-items:center;gap:14px;margin-bottom:6px}
.brand img{width:46px;height:46px;filter:drop-shadow(0 4px 14px rgba(0,0,0,.5))}
.brand .eyebrow{font-family:var(--display);font-weight:600;font-size:11px;letter-spacing:.24em;text-transform:uppercase;color:var(--oro)}
.brand h1{font-family:var(--display);font-weight:800;font-size:27px;line-height:.98;color:var(--t1)}
.brand-sub{font-size:12.5px;color:var(--t4);margin:4px 0 26px;line-height:1.5}
.section{margin-bottom:26px}
.sec-head{display:flex;align-items:center;gap:11px;margin-bottom:14px}
.sec-head .lbl{font-family:var(--display);font-weight:600;font-size:12px;letter-spacing:.2em;text-transform:uppercase;color:#a9b8d6;white-space:nowrap}
.sec-head .line{flex:1;height:1px;background:linear-gradient(90deg,rgba(228,172,74,.5),transparent)}
.field-lbl{font-size:12px;color:var(--t3);margin-bottom:7px;font-weight:500}
.stepper{display:flex;align-items:stretch;background:var(--superficie);border:1px solid var(--bordo);border-radius:12px;overflow:hidden}
.stepper button{width:46px;flex:0 0 46px;border:none;background:transparent;color:var(--t2);font-size:22px;line-height:1;cursor:pointer;transition:.13s;font-family:var(--testo)}
.stepper button:hover{background:rgba(228,172,74,.13);color:var(--oro-chiaro)}
.stepper input{flex:1;width:100%;min-width:0;border:none;background:transparent;text-align:center;color:var(--t1);font-family:var(--display);font-weight:800;font-size:23px;font-variant-numeric:tabular-nums;padding:14px 0}
.stepper input:focus{outline:none}
.stepper.bad{border-color:rgba(240,138,106,.7);box-shadow:0 0 0 3px rgba(240,138,106,.14)}
.sel-field{width:100%;background:var(--superficie);border:1px solid var(--bordo);border-radius:12px;color:var(--t1);font-family:var(--display);font-weight:800;font-size:21px;padding:14px 42px 14px 16px;cursor:pointer;-webkit-appearance:none;-moz-appearance:none;appearance:none;background-image:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='%238e9bb8' stroke-width='2.4' stroke-linecap='round'><path d='M6 9l6 6 6-6'/></svg>");background-repeat:no-repeat;background-position:right 15px center}
.sel-field:focus{outline:none;border-color:rgba(228,172,74,.6);box-shadow:0 0 0 3px rgba(228,172,74,.12)}
.sel-field option{background:#0e1626;color:var(--t1);font-size:15px}
.when-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:14px}
.txt{width:100%;background:var(--superficie);border:1px solid var(--bordo);border-radius:12px;color:var(--t1);font-family:var(--testo);font-size:16px;font-weight:500;padding:13px 15px}
.txt:focus{outline:none;border-color:rgba(228,172,74,.6);box-shadow:0 0 0 3px rgba(228,172,74,.12)}
.coord-toggle{display:inline-flex;align-items:center;gap:7px;margin-top:12px;background:none;border:none;color:var(--t3);font-family:var(--testo);font-size:13px;font-weight:500;cursor:pointer}
.coord-toggle:hover{color:var(--oro-chiaro)}
.coord-toggle .chev{transition:transform .18s;display:inline-block}.coord-toggle.open .chev{transform:rotate(90deg)}
.coord-wrap{max-height:0;overflow:hidden;transition:max-height .22s ease}.coord-wrap.open{max-height:120px}
.coord-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:12px}
.formats{display:grid;grid-template-columns:1fr 1fr;gap:11px}
.fmt{position:relative;text-align:left;background:var(--superficie);border:1.5px solid var(--bordo);border-radius:14px;padding:12px 13px 11px;cursor:pointer;transition:.15s;overflow:hidden}
.fmt:hover{border-color:var(--bordo-forte);background:var(--superficie2)}
.fmt.sel{border-color:var(--oro);background:linear-gradient(180deg,rgba(228,172,74,.09),rgba(228,172,74,.02));box-shadow:0 0 0 3px rgba(228,172,74,.12),0 10px 26px rgba(0,0,0,.35)}
.fmt .thumb{width:100%;height:60px;display:flex;align-items:center;justify-content:center;margin-bottom:9px}
.fmt .fname{font-family:var(--display);font-weight:800;font-size:15px;color:var(--t1)}
.fmt .ftag{font-size:11px;color:var(--t3);margin-top:1px;line-height:1.3}
.fmt .tick{position:absolute;top:9px;right:9px;width:19px;height:19px;border-radius:50%;background:var(--oro);color:#05070f;display:none;align-items:center;justify-content:center;font-size:12px;font-weight:800}
.fmt.sel .tick{display:flex}.fmt.wide{grid-column:1 / -1}.fmt.wide .thumb{height:66px}
.palettes{display:flex;flex-direction:column;gap:10px}
.pal{position:relative;text-align:left;border:1.5px solid var(--bordo);border-radius:14px;padding:10px;cursor:pointer;transition:.15s;overflow:hidden;background:var(--superficie);display:flex;align-items:center;gap:14px}
.pal:hover{border-color:var(--bordo-forte);background:var(--superficie2)}
.pal.sel{border-color:var(--oro);box-shadow:0 0 0 3px rgba(228,172,74,.12),0 10px 26px rgba(0,0,0,.35)}
.pal .swatch{width:106px;flex:0 0 106px;height:62px;border-radius:10px;position:relative;overflow:hidden;border:1px solid rgba(0,0,0,.45)}
.pal .disc{position:absolute;left:36px;top:50%;transform:translate(-50%,-50%);width:42px;height:42px;border-radius:50%;border:1px solid rgba(255,255,255,.18);box-shadow:inset 0 0 14px rgba(0,0,0,.45)}
.pal .neon{position:absolute;right:11px;top:50%;transform:translateY(-50%);width:16px;height:16px;border-radius:50%}
.pal .stars{position:absolute;inset:0}.pal .stars i{position:absolute;width:2px;height:2px;border-radius:50%;background:rgba(255,255,255,.82)}
.pal .meta{flex:1;min-width:0}
.pal .pname{font-family:var(--display);font-weight:800;font-size:16.5px;color:var(--t1)}
.pal .ptag{font-size:12px;color:var(--t3);margin-top:2px;line-height:1.35}
.pal .nv{display:inline-flex;align-items:center;gap:5px;margin-top:7px;font-size:10.5px;color:#e7b9a6;background:rgba(240,138,106,.1);border:1px solid rgba(240,138,106,.24);border-radius:99px;padding:2px 9px;font-weight:600}
.pal .tick{position:absolute;top:8px;right:8px;width:18px;height:18px;border-radius:50%;background:var(--oro);color:#05070f;display:none;align-items:center;justify-content:center;font-size:11px;font-weight:800;z-index:2}
.pal.sel .tick{display:flex}
.genera{width:100%;margin-top:6px;background:var(--oro);color:#05070f;border:none;border-radius:13px;font-family:var(--display);font-weight:800;font-size:19px;letter-spacing:.02em;padding:16px;cursor:pointer;transition:.15s;box-shadow:0 12px 30px rgba(228,172,74,.22)}
.genera:hover{background:var(--oro-chiaro)}.genera:disabled{opacity:.5;cursor:not-allowed;box-shadow:none}
.carosello-btn{width:100%;margin-top:10px;background:rgba(19,29,49,.6);color:var(--t1);border:1.5px solid var(--bordo-forte);border-radius:13px;font-family:var(--display);font-weight:800;font-size:16px;padding:13px;cursor:pointer;transition:.15s;display:flex;align-items:center;justify-content:center;gap:9px}
.carosello-btn:hover{border-color:var(--oro);color:var(--oro-chiaro)}.carosello-btn:disabled{opacity:.5;cursor:not-allowed}
.carosello-btn small{font-weight:400;color:var(--t4);font-family:var(--testo);font-size:12px}
.stage{flex:1;position:relative;display:flex;align-items:center;justify-content:center;padding:38px;min-width:0}
.state{position:absolute;inset:38px;display:none;align-items:center;justify-content:center;flex-direction:column}
.state.active{display:flex}
.poster-frame{height:min(100%,720px);aspect-ratio:1/1;border-radius:18px;overflow:hidden;box-shadow:0 30px 70px rgba(0,0,0,.6);border:1px solid var(--bordo);background:#05070f}
.poster-frame.a4{aspect-ratio:1/1.414}
.poster-frame img{width:100%;height:100%;object-fit:contain;display:block}
.ph-frame{height:min(100%,520px);aspect-ratio:1/1;border-radius:20px;border:1.5px dashed var(--bordo-forte);display:flex;flex-direction:column;align-items:center;justify-content:center;gap:18px;padding:40px;background:radial-gradient(120% 90% at 50% 20%,rgba(18,32,58,.5),rgba(5,7,15,.2))}
.ph-title{font-family:var(--display);font-weight:800;font-size:24px;color:var(--t2);text-align:center}
.ph-text{font-size:14.5px;color:var(--t4);text-align:center;max-width:340px;line-height:1.6}
.ph-arrow{margin-top:2px;font-size:13px;color:var(--oro);font-weight:600}
.gen-card{display:flex;flex-direction:column;align-items:center;gap:24px;text-align:center;max-width:400px}
.orbit{width:120px;height:120px;position:relative}
.orbit .core{position:absolute;inset:0;margin:auto;width:20px;height:20px;border-radius:50%;background:var(--oro);box-shadow:0 0 26px rgba(228,172,74,.7)}
.orbit .ring{position:absolute;inset:0;border-radius:50%;border:1.5px solid rgba(150,170,215,.18)}.orbit .ring.r2{inset:22px}
.orbit .sat{position:absolute;top:50%;left:50%;width:120px;height:120px;margin:-60px 0 0 -60px;animation:spin 1.5s linear infinite}
.orbit .sat.s2{width:76px;height:76px;margin:-38px 0 0 -38px;animation-duration:2.4s;animation-direction:reverse}
.orbit .sat b{position:absolute;top:-4px;left:50%;margin-left:-4px;width:8px;height:8px;border-radius:50%;background:var(--neon);box-shadow:0 0 12px var(--neon)}
.orbit .sat.s2 b{background:#d3deff;box-shadow:0 0 10px #d3deff;width:6px;height:6px}
@keyframes spin{to{transform:rotate(360deg)}}
.gen-title{font-family:var(--display);font-weight:800;font-size:26px;color:var(--t1)}
.gen-sub{font-size:13px;color:var(--t4);margin-top:-14px}
.phases{display:flex;flex-direction:column;gap:2px;width:330px;text-align:left}
.phase{display:flex;align-items:center;gap:14px;padding:11px 4px;transition:.2s}
.phase .dot{flex:0 0 26px;width:26px;height:26px;border-radius:50%;position:relative;border:1.6px solid var(--bordo-forte);background:var(--superficie);display:flex;align-items:center;justify-content:center;transition:.2s}
.phase .dot .num{font-family:var(--display);font-weight:800;font-size:13px;color:var(--t4)}
.phase .dot .chk{display:none;color:#05070f;font-size:14px;font-weight:800}
.phase .dot .spin{display:none;width:15px;height:15px;border-radius:50%;border:2px solid rgba(228,172,74,.3);border-top-color:var(--oro);animation:spin .7s linear infinite}
.phase .nm{font-size:15.5px;font-weight:500;color:var(--t4);transition:.2s;line-height:1.3}
.phase.done .dot{background:var(--oro);border-color:var(--oro)}.phase.done .dot .num{display:none}.phase.done .dot .chk{display:block}.phase.done .nm{color:var(--t2)}
.phase.active .dot{border-color:var(--oro);background:rgba(228,172,74,.1);box-shadow:0 0 0 4px rgba(228,172,74,.1)}.phase.active .dot .num{display:none}.phase.active .dot .spin{display:block}.phase.active .nm{color:var(--t1);font-weight:600}
.preview-wrap{display:flex;flex-direction:column;align-items:center;gap:18px;height:100%;justify-content:center}
.cap-bar{display:flex;align-items:center;flex-wrap:wrap;justify-content:center;gap:8px}
.cap{display:inline-flex;align-items:center;gap:7px;font-size:12.5px;color:var(--t2);font-weight:500;background:rgba(19,29,49,.7);border:1px solid var(--bordo);border-radius:99px;padding:6px 13px}
.cap b{color:var(--t1);font-weight:600}.cap .sw{width:11px;height:11px;border-radius:50%}
.frames{display:flex;gap:16px;align-items:center;justify-content:center;max-height:62vh}
.frames .poster-frame{height:min(62vh,620px)}
.save-row{display:flex;gap:12px;align-items:center;flex-wrap:wrap;justify-content:center}
.btn{font-family:var(--testo);font-weight:600;font-size:15px;border-radius:12px;padding:13px 22px;cursor:pointer;transition:.14s;display:inline-flex;align-items:center;gap:9px;border:1.5px solid transparent;text-decoration:none}
.btn-gold{background:var(--oro);color:#05070f;box-shadow:0 10px 24px rgba(228,172,74,.2)}.btn-gold:hover{background:var(--oro-chiaro)}
.btn-ghost{background:rgba(19,29,49,.6);border-color:var(--bordo-forte);color:var(--t2)}.btn-ghost:hover{border-color:var(--oro);color:var(--t1)}
.btn-text{background:none;border:none;color:var(--t3);font-family:var(--testo);font-weight:500;font-size:13.5px;cursor:pointer;padding:8px}.btn-text:hover{color:var(--oro-chiaro)}
.btn small{font-weight:400;opacity:.7;font-size:12px}
.err-card{max-width:460px;background:linear-gradient(180deg,rgba(46,20,16,.7),rgba(24,10,10,.55));border:1px solid rgba(240,138,106,.4);border-radius:20px;padding:34px 36px;text-align:center;box-shadow:0 24px 60px rgba(0,0,0,.5)}
.err-icon{width:58px;height:58px;border-radius:50%;background:rgba(240,138,106,.15);display:flex;align-items:center;justify-content:center;margin:0 auto 20px}
.err-title{font-family:var(--display);font-weight:800;font-size:24px;color:#f7d9cc;margin-bottom:12px}
.err-msg{font-size:16.5px;color:#f6c6b3;line-height:1.5;font-weight:500;background:rgba(240,138,106,.09);border:1px solid rgba(240,138,106,.22);border-radius:12px;padding:15px 18px;margin-bottom:18px}
.err-hint{font-size:13.5px;color:var(--t3);line-height:1.55;margin-bottom:22px}
.err-card .btn-gold{background:#f0a074}.err-card .btn-gold:hover{background:#f4b48c}
/* --- D18: editor di palette --- */
.pal-add{width:100%;margin-top:10px;background:rgba(19,29,49,.4);border:1.5px dashed var(--bordo-forte);border-radius:13px;color:var(--t2);font-family:var(--testo);font-weight:600;font-size:14px;padding:12px;cursor:pointer;display:flex;align-items:center;justify-content:center;gap:8px;transition:.14s}
.pal-add:hover{border-color:var(--oro);color:var(--oro-chiaro)}
.pal-add .plus{font-family:var(--display);font-weight:800;font-size:17px;line-height:1}
.editor{position:fixed;inset:0;z-index:50;display:none;align-items:center;justify-content:center;padding:26px;background:rgba(3,5,11,.72)}
.editor.on{display:flex}
.ed-card{width:min(1050px,100%);max-height:calc(100vh - 44px);display:flex;flex-direction:column;background:linear-gradient(180deg,#0e1728,#0a1120);border:1px solid var(--bordo-forte);border-radius:20px;box-shadow:0 40px 100px rgba(0,0,0,.6);overflow:hidden}
.ed-head{display:flex;align-items:center;gap:14px;padding:19px 24px;border-bottom:1px solid var(--bordo)}
.ed-head .eh-ic{width:34px;height:34px;border-radius:10px;background:rgba(228,172,74,.14);border:1px solid rgba(228,172,74,.34);display:flex;align-items:center;justify-content:center;color:var(--oro);font-size:17px}
.ed-head h2{font-family:var(--display);font-weight:800;font-size:20px;color:var(--t1);line-height:1.1}
.ed-head .eh-sub{font-size:11.5px;color:var(--t4);margin-top:2px}
.ed-head .eh-x{margin-left:auto;background:none;border:none;color:var(--t3);font-size:20px;cursor:pointer;padding:4px 9px;border-radius:8px;line-height:1}
.ed-head .eh-x:hover{color:var(--t1);background:rgba(150,170,215,.1)}
.ed-body{display:grid;grid-template-columns:1fr 384px;min-height:0;flex:1;overflow:hidden}
.ed-controls{overflow-y:auto;padding:20px 24px}
.ed-group{margin-bottom:19px}
.ed-grp-title{font-family:var(--display);font-weight:600;font-size:11px;letter-spacing:.18em;text-transform:uppercase;color:#a9b8d6;margin-bottom:10px;display:flex;align-items:center;gap:10px}
.ed-grp-title .line{flex:1;height:1px;background:linear-gradient(90deg,rgba(228,172,74,.4),transparent)}
.ed-sws{display:grid;grid-template-columns:1fr 1fr;gap:9px}
.ed-sw{display:flex;align-items:center;gap:10px;background:var(--superficie);border:1px solid var(--bordo);border-radius:10px;padding:7px 10px}
.ed-sw label{font-size:12px;color:var(--t2);flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-weight:500}
.ed-sw input[type=color]{-webkit-appearance:none;-moz-appearance:none;appearance:none;width:34px;height:26px;border:1px solid var(--bordo-forte);border-radius:7px;background:none;cursor:pointer;padding:0;flex:0 0 34px}
.ed-sw input[type=color]::-webkit-color-swatch-wrapper{padding:2px}
.ed-sw input[type=color]::-webkit-color-swatch{border:none;border-radius:5px}
.ed-sw input[type=color]::-moz-color-swatch{border:none;border-radius:5px}
.ed-side{background:linear-gradient(180deg,rgba(5,7,15,.4),rgba(5,7,15,.2));border-left:1px solid var(--bordo);display:flex;flex-direction:column;padding:20px;overflow-y:auto}
.ed-prev-wrap{position:relative;display:flex;align-items:center;justify-content:center;flex:1;min-height:230px;margin-bottom:16px}
.ed-frame{height:min(46vh,420px)}
.ed-load{position:absolute;inset:0;display:none;align-items:center;justify-content:center;background:rgba(5,7,15,.32);border-radius:18px}
.ed-load.on{display:flex}
.ed-load .sp{width:26px;height:26px;border-radius:50%;border:3px solid rgba(228,172,74,.25);border-top-color:var(--oro);animation:spin .7s linear infinite}
.ed-load .txt{margin-left:11px;font-size:12.5px;color:var(--t2);font-weight:500}
.ed-foot .field-lbl{margin-top:2px}
.ed-foot .txt{margin-bottom:11px}
.ed-err{display:none;font-size:13px;color:#f6c6b3;background:rgba(240,138,106,.1);border:1px solid rgba(240,138,106,.28);border-radius:10px;padding:9px 12px;margin-bottom:11px;line-height:1.4}
.ed-err.on{display:block}
.ed-actions{display:flex;gap:10px}
.ed-actions .btn{flex:1;justify-content:center}
</style></head>
<body>
<div class="titlebar"><span class="dot"></span><span class="dot"></span><span class="dot"></span>
<span class="name">Cielo del Mese — Generatore poster · Gruppo Astrofili Vicentini</span></div>
<div class="app">
  <nav class="nav">
    <div class="nav-brand"><img src="/assets/logo-emblema.png" alt="GAV">
      <div><div class="nb-txt">GAV</div><div class="nb-sub">Astrofili Vicentini</div></div></div>
    <div class="nav-cap">Strumenti</div>
    <button type="button" class="nav-item on" aria-current="page">
      <svg class="ic" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="1.6"/><path d="M12 3a9 9 0 0 0 0 18" stroke="currentColor" stroke-width="1.6"/><circle cx="15.5" cy="8" r="1.3" fill="currentColor"/><circle cx="9" cy="14.5" r="1" fill="currentColor"/></svg>
      <span><span class="nm">Cielo del Mese</span></span></button>
    <button type="button" class="nav-item soon" disabled aria-disabled="true" title="Prossimamente">
      <svg class="ic" viewBox="0 0 24 24" fill="none"><path d="M12 3v3M12 18v3M3 12h3M18 12h3M6 6l2 2M16 16l2 2M18 6l-2 2M8 16l-2 2" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/><circle cx="12" cy="12" r="3.2" stroke="currentColor" stroke-width="1.6"/></svg>
      <span><span class="nm">Pillole di astronomia</span><span class="badge">Prossimamente</span></span></button>
    <div class="nav-foot">Altri strumenti arriveranno qui.</div>
  </nav>
  <aside class="panel">
    <div class="brand"><img src="/assets/logo-emblema.png" alt="GAV">
      <div><div class="eyebrow">Gruppo Astrofili Vicentini</div><h1>Cielo del Mese</h1></div></div>
    <div class="brand-sub">Crea il poster del cielo del mese da pubblicare e stampare. Scegli quando, dove e come lo vuoi — poi genera l'anteprima.</div>
    <div class="section"><div class="sec-head"><span class="lbl">Quando</span><span class="line"></span></div>
      <div class="field-lbl">Mese</div>
      <select class="sel-field" id="in-mese" aria-label="Mese"><!--MESI--></select>
      <div class="when-grid">
        <div><div class="field-lbl">Anno</div>
          <div class="stepper" id="st-anno"><button type="button" data-step="anno" data-d="-1">−</button>
            <input id="in-anno" type="text" inputmode="numeric" value="2026"><button type="button" data-step="anno" data-d="1">+</button></div></div>
        <div><div class="field-lbl">Ora</div>
          <div class="stepper" id="st-ora"><button type="button" data-step="ora" data-d="-1">−</button>
            <input id="in-ora" type="text" value="23:00" readonly><button type="button" data-step="ora" data-d="1">+</button></div></div>
      </div></div>
    <div class="section"><div class="sec-head"><span class="lbl">Dove</span><span class="line"></span></div>
      <div class="field-lbl">Località</div>
      <input class="txt" id="in-loc" type="text" value="Vicenza" placeholder="Es. Vicenza">
      <button type="button" class="coord-toggle" id="coord-btn"><span class="chev">›</span> <span id="coord-lbl">Inserisci coordinate precise</span></button>
      <div class="coord-wrap" id="coord-wrap"><div class="coord-grid">
        <div><div class="field-lbl">Latitudine</div><input class="txt" id="in-lat" value="45.5455"></div>
        <div><div class="field-lbl">Longitudine</div><input class="txt" id="in-lon" value="11.5353"></div></div></div></div>
    <div class="section"><div class="sec-head"><span class="lbl">Formato</span><span class="line"></span></div>
      <div class="formats" id="formats"><!--SCHEDE--></div></div>
    <div class="section"><div class="sec-head"><span class="lbl">Palette</span><span class="line"></span></div>
      <div class="palettes" id="palettes"><!--PASTIGLIE--></div>
      <button type="button" class="pal-add" id="pal-add"><span class="plus">＋</span> Crea la tua palette</button></div>
    <button class="genera" id="genera">Genera anteprima</button>
    <button class="carosello-btn" id="carosello">Genera il carosello <small>2 pagine: cielo + profondo</small></button>
  </aside>
  <main class="stage" id="stage">
    <div class="state active" id="s-initial">
      <div class="ph-frame"><div class="ph-title">L'anteprima comparirà qui</div>
        <div class="ph-text">Scegli mese, luogo, formato e palette nel pannello a sinistra, poi premi <b style="color:#c6d0e4">Genera anteprima</b>.</div>
        <div class="ph-arrow">← Comincia da “Quando”</div></div></div>
    <div class="state" id="s-generating">
      <div class="gen-card"><div class="orbit"><div class="ring"></div><div class="ring r2"></div>
        <div class="sat"><b></b></div><div class="sat s2"><b></b></div><div class="core"></div></div>
        <div class="gen-title" id="gen-title">Sto disegnando il cielo…</div>
        <div class="gen-sub" id="gen-sub"></div>
        <div class="phases" id="phases">
          <div class="phase" data-ph="0"><span class="dot"><span class="num">1</span><span class="chk">✓</span><span class="spin"></span></span><span class="nm">Calcolo dove sono stasera i pianeti e la Luna</span></div>
          <div class="phase" data-ph="1"><span class="dot"><span class="num">2</span><span class="chk">✓</span><span class="spin"></span></span><span class="nm">Metto cinquemila stelle sulla mappa</span></div>
          <div class="phase" data-ph="2"><span class="dot"><span class="num">3</span><span class="chk">✓</span><span class="spin"></span></span><span class="nm">Compongo il poster</span></div>
          <div class="phase" data-ph="3"><span class="dot"><span class="num">4</span><span class="chk">✓</span><span class="spin"></span></span><span class="nm">Disegno l'immagine finale</span></div>
        </div></div></div>
    <div class="state" id="s-preview">
      <div class="preview-wrap">
        <div class="cap-bar"><span class="cap"><b id="cap-when">Agosto 2026</b></span>
          <span class="cap">📍 <b id="cap-loc">Vicenza</b></span>
          <span class="cap"><b id="cap-fmt">Dashboard</b></span>
          <span class="cap"><span class="sw" id="cap-sw"></span><b id="cap-pal">Osservatorio</b></span></div>
        <div class="frames" id="frames"></div>
        <div class="save-row" id="save-row"></div></div></div>
    <div class="state" id="s-error">
      <div class="err-card"><div class="err-icon">
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none"><path d="M12 8v5" stroke="#f08a6a" stroke-width="2.4" stroke-linecap="round"/><circle cx="12" cy="17" r="1.4" fill="#f08a6a"/><circle cx="12" cy="12" r="10" stroke="#f08a6a" stroke-width="1.6" opacity=".5"/></svg></div>
        <div class="err-title">Controlla un dato</div>
        <div class="err-msg" id="err-msg"></div>
        <div class="err-hint">Correggi il valore nel pannello a sinistra e premi di nuovo.</div>
        <button class="btn btn-gold" id="err-back">Torna alle impostazioni</button></div></div>
  </main>
  <div class="editor" id="editor">
    <div class="ed-card">
      <div class="ed-head">
        <span class="eh-ic">✦</span>
        <div><h2>Crea una palette</h2>
          <div class="eh-sub">Componi i colori del brand · le stelle restano coi loro colori reali</div></div>
        <button class="eh-x" id="ed-x" type="button" aria-label="Chiudi">✕</button>
      </div>
      <div class="ed-body">
        <div class="ed-controls" id="ed-groups"></div>
        <div class="ed-side">
          <div class="ed-prev-wrap">
            <div class="poster-frame ed-frame" id="ed-frame"><img id="ed-prev-img" alt="Anteprima"></div>
            <div class="ed-load" id="ed-prev-load"><span class="sp"></span><span class="txt">aggiorno…</span></div>
          </div>
          <div class="ed-foot">
            <div class="ed-err" id="ed-err"></div>
            <div class="field-lbl">Nome della palette</div>
            <input class="txt" id="ed-name" type="text" placeholder="Es. Tramonto adriatico" maxlength="40">
            <div class="field-lbl">Descrizione <span style="color:var(--t4)">(facoltativa)</span></div>
            <input class="txt" id="ed-desc" type="text" placeholder="Due parole sul carattere" maxlength="80">
            <div class="ed-actions">
              <button class="btn btn-ghost" id="ed-cancel" type="button">Annulla</button>
              <button class="btn btn-gold" id="ed-save" type="button">Salva palette</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</div>
<script>
(function(){
 var MESI=["Gennaio","Febbraio","Marzo","Aprile","Maggio","Giugno","Luglio","Agosto","Settembre","Ottobre","Novembre","Dicembre"];
 var $=function(id){return document.getElementById(id);};
 var st={fmt:"dashboard",fmtName:"Dashboard",ar:"sq",pal:"osservatorio",palName:"Osservatorio",dot:"#45c8ff",ora:23};
 // stelle finte nelle swatch
 document.querySelectorAll('.pal .stars').forEach(function(b){for(var i=0;i<7;i++){var s=document.createElement('i');s.style.left=(8+Math.random()*70)+'%';s.style.top=(12+Math.random()*70)+'%';s.style.opacity=(0.4+Math.random()*0.5).toFixed(2);b.appendChild(s);}});
 // stepper
 document.querySelectorAll('[data-step]').forEach(function(btn){btn.addEventListener('click',function(){
   var w=btn.getAttribute('data-step'),d=parseInt(btn.getAttribute('data-d'),10);
   if(w==='anno'){var i=$('in-anno');var v=parseInt(i.value,10);if(isNaN(v))v=2026;v+=d;if(v<1900)v=1900;if(v>2050)v=2050;i.value=v;$('st-anno').classList.remove('bad');}
   else{st.ora=((st.ora+d)%24+24)%24;$('in-ora').value=(st.ora<10?'0':'')+st.ora+':00';}});});
 $('coord-btn').addEventListener('click',function(){this.classList.toggle('open');$('coord-wrap').classList.toggle('open');$('coord-lbl').textContent=this.classList.contains('open')?'Nascondi coordinate':'Inserisci coordinate precise';});
 // selezione schede/pastiglie
 // Il carosello vale SOLO fra formati quadrati (Instagram ritaglia le proporzioni
 // diverse): per un formato verticale il pulsante si spegne e SPIEGA il perche'.
 function updateCarosello(){var sq=st.ar==='sq',c=$('carosello');c.disabled=!sq;
   c.querySelector('small').textContent=sq?'2 pagine: cielo + profondo'
     :'solo per i formati quadrati — Instagram ritaglia le proporzioni diverse';}
 document.querySelectorAll('.fmt').forEach(function(b){b.addEventListener('click',function(){document.querySelectorAll('.fmt').forEach(function(x){x.classList.remove('sel');});b.classList.add('sel');st.fmt=b.getAttribute('data-fmt');st.fmtName=b.getAttribute('data-name');st.ar=b.getAttribute('data-ar');updateCarosello();});});
 function wirePal(b){b.addEventListener('click',function(){document.querySelectorAll('.pal').forEach(function(x){x.classList.remove('sel');});b.classList.add('sel');st.pal=b.getAttribute('data-pal');st.palName=b.getAttribute('data-name');st.dot=b.getAttribute('data-dot');});}
 document.querySelectorAll('.pal').forEach(wirePal);
 // stati
 var S={initial:'s-initial',generating:'s-generating',preview:'s-preview',error:'s-error'};
 function show(n){Object.keys(S).forEach(function(k){$(S[k]).classList.toggle('active',k===n);});}
 function setPhase(i){document.querySelectorAll('#phases .phase').forEach(function(p,k){p.classList.toggle('done',k<i);p.classList.toggle('active',k===i);});}
 function allDone(){document.querySelectorAll('#phases .phase').forEach(function(p){p.classList.remove('active');p.classList.add('done');});}
 function params(){var m=parseInt($('in-mese').value,10),a=parseInt($('in-anno').value,10);
   return{p:new URLSearchParams({year:$('in-anno').value,month:$('in-mese').value,hour:st.ora,place:$('in-loc').value.trim()||'Vicenza',lat:$('in-lat').value,lon:$('in-lon').value,theme:st.pal,formato:st.fmt}),m:m,a:a};}
 function fillCaps(m,a){$('cap-when').textContent=MESI[m-1]+' '+a+' · '+(st.ora<10?'0':'')+st.ora+':00';$('cap-loc').textContent=$('in-loc').value.trim()||'Vicenza';$('cap-fmt').textContent=st.fmtName;$('cap-pal').textContent=st.palName;$('cap-sw').style.background=st.dot;}
 function frame(token,ar){return '<div class="poster-frame'+(ar==='a4'?' a4':'')+'"><img src="/anteprima?token='+token+'&_='+Date.now()+'"></div>';}
 function dlLink(fmt,formato,label,cls,small){var q=params().p;q.set('fmt',fmt);q.set('formato',formato);return '<a class="btn '+cls+'" href="/download?'+q.toString()+'" download>'+label+(small?' <small>'+small+'</small>':'')+'</a>';}
 function busy(b,car){$('genera').disabled=b;$('carosello').disabled=b||st.ar!=='sq';$('genera').textContent=b?'Generazione in corso…':'Genera anteprima';}
 function fail(msg){$('err-msg').textContent=msg;show('error');busy(false);}
 function run(url,carosello){
   var pr=params();busy(true);show('generating');setPhase(0);
   $('gen-title').textContent='Sto disegnando il cielo…';$('gen-sub').textContent=carosello?'Pagina 1 di 2 · il cielo':'';
   var es=new EventSource(url+'?'+pr.p.toString());
   es.addEventListener('fase',function(e){setPhase(+e.data);});
   es.addEventListener('pagina',function(e){if(e.data==='2'){setPhase(0);$('gen-sub').textContent='Pagina 2 di 2 · il profondo cielo';}});
   es.addEventListener('errore',function(e){es.close();fail(e.data);});
   es.addEventListener('fatto',function(e){es.close();allDone();var toks=e.data.split(',');
     setTimeout(function(){fillCaps(pr.m,pr.a);
       if(carosello){
         $('frames').innerHTML=frame(toks[0],st.ar)+frame(toks[1],'sq');
         $('save-row').innerHTML=dlLink('png',st.fmt,'Salva pagina 1','btn-gold','PNG')+dlLink('png',(window.__p2||'profondo'),'Salva pagina 2','btn-gold','PNG')+'<button class="btn-text" id="regen">↻ Rigenera</button>';
       }else{
         $('frames').innerHTML=frame(toks[0],st.ar);
         $('save-row').innerHTML=dlLink('png',st.fmt,'Salva PNG','btn-gold','per i social')+dlLink('svg',st.fmt,'Salva SVG','btn-ghost','per la stampa')+'<button class="btn-text" id="regen">↻ Rigenera</button>';
       }
       show('preview');busy(false);
       var rg=$('regen');if(rg)rg.addEventListener('click',function(){run(url,carosello);});
     },420);});
   es.onerror=function(){es.close();fail('Connessione al motore interrotta.');};
 }
 $('genera').addEventListener('click',function(){run('/genera',false);});
 $('carosello').addEventListener('click',function(){run('/carosello',true);});
 $('err-back').addEventListener('click',function(){show('initial');});

 // --- D18: editor di palette ---
 // I 20+ token DI MARCA, raggruppati in modo leggibile. Le 2 chiavi astronomiche
 // (star_ramp/planet_colors) NON compaiono: il client non le vede mai (D2/D18).
 var __PAL=/*PALDATA*/;
 var GROUPS=[
  {t:'Sfondi',items:[['bg.0','Sfondo · cima'],['bg.1','Sfondo · centro'],['bg.2','Sfondo · fondo'],['disk.0','Disco · cima'],['disk.1','Disco · centro'],['disk.2','Disco · fondo']]},
  {t:'Accenti',items:[['neon','Neon'],['gold','Oro']]},
  {t:'Struttura',items:[['border','Bordo'],['border2','Bordo forte'],['grid','Griglia'],['divider','Divisori'],['panel','Pannello']]},
  {t:'Testo',items:[['text','Testo'],['text2','Testo 2'],['text3','Testo 3'],['text4','Testo 4']]},
  {t:'Etichette e Luna',items:[['moon_lit','Luna illuminata'],['moon_label','Etichetta Luna'],['bgstar','Stelle di sfondo'],['label','Etichette'],['cardinal','Punti cardinali']]},
  {t:'Stati',items:[['status.ok','Visibile'],['status.info','Informazione'],['status.warn','Attenzione'],['status.muted','Spento']]}
 ];
 var groupsBuilt=false;
 function buildGroups(){
   if(groupsBuilt)return; groupsBuilt=true;
   var html='';
   GROUPS.forEach(function(g){
     html+='<div class="ed-group"><div class="ed-grp-title">'+g.t+'<span class="line"></span></div><div class="ed-sws">';
     g.items.forEach(function(it){
       html+='<div class="ed-sw"><label title="'+it[1]+'">'+it[1]+'</label><input type="color" data-k="'+it[0]+'"></div>';
     });
     html+='</div></div>';
   });
   $('ed-groups').innerHTML=html;
   document.querySelectorAll('#ed-groups input[type=color]').forEach(function(inp){
     inp.addEventListener('input',schedulePreview);
   });
 }
 function collectTokens(){
   var t={status:{},bg:[],disk:[]};
   document.querySelectorAll('#ed-groups input[type=color]').forEach(function(inp){
     var k=inp.getAttribute('data-k'),v=inp.value;
     if(k.indexOf('.')<0){t[k]=v;return;}
     var pp=k.split('.');
     if(pp[0]==='status'){t.status[pp[1]]=v;}else{t[pp[0]][+pp[1]]=v;}
   });
   return t;
 }
 function seed(slug){
   var d=__PAL[slug]||__PAL['osservatorio'];
   document.querySelectorAll('#ed-groups input[type=color]').forEach(function(inp){
     var k=inp.getAttribute('data-k'),v,pp;
     if(k.indexOf('.')<0){v=d[k];}
     else{pp=k.split('.');v=(pp[0]==='status')?(d.status||{})[pp[1]]:(d[pp[0]]||[])[+pp[1]];}
     if(v)inp.value=v;
   });
 }
 var pvSeq=0,pvT;
 function schedulePreview(){clearTimeout(pvT);pvT=setTimeout(updatePreview,220);}
 function updatePreview(){
   var my=++pvSeq;$('ed-prev-load').classList.add('on');
   var payload={tokens:collectTokens(),year:$('in-anno').value,month:$('in-mese').value,
     hour:st.ora,place:$('in-loc').value.trim()||'Vicenza',lat:$('in-lat').value,
     lon:$('in-lon').value,formato:st.fmt};
   fetch('/palette/anteprima',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)})
    .then(function(r){if(!r.ok)return r.json().then(function(j){throw new Error(j.detail||'Errore');});return r.blob();})
    .then(function(b){if(my!==pvSeq)return;var u=URL.createObjectURL(b);var img=$('ed-prev-img');
      if(img.dataset.u)URL.revokeObjectURL(img.dataset.u);img.src=u;img.dataset.u=u;$('ed-prev-load').classList.remove('on');})
    .catch(function(e){if(my!==pvSeq)return;$('ed-prev-load').classList.remove('on');edErr(e.message);});
 }
 function edErr(msg){var e=$('ed-err');if(msg){e.textContent=msg;e.classList.add('on');}else{e.classList.remove('on');}}
 function openEditor(){
   buildGroups();seed(st.pal);
   $('ed-name').value='';$('ed-desc').value='';edErr('');
   $('ed-frame').className='poster-frame ed-frame'+(st.ar==='a4'?' a4':'');
   $('editor').classList.add('on');updatePreview();
 }
 function closeEditor(){$('editor').classList.remove('on');}
 function addPastiglia(j){
   document.querySelectorAll('.pal').forEach(function(x){x.classList.remove('sel');});
   var tmp=document.createElement('div');tmp.innerHTML=j.pastiglia.trim();var btn=tmp.firstChild;
   $('palettes').appendChild(btn);wirePal(btn);btn.classList.add('sel');
   var box=btn.querySelector('.stars');for(var i=0;i<7;i++){var s=document.createElement('i');s.style.left=(8+Math.random()*70)+'%';s.style.top=(12+Math.random()*70)+'%';s.style.opacity=(0.4+Math.random()*0.5).toFixed(2);box.appendChild(s);}
   __PAL[j.slug]=collectTokens();
   st.pal=j.slug;st.palName=j.name;st.dot=j.dot;
 }
 function save(){
   var name=$('ed-name').value.trim();
   if(!name){edErr('Serve un nome per la palette.');return;}
   $('ed-save').disabled=true;edErr('');
   fetch('/palette/salva',{method:'POST',headers:{'Content-Type':'application/json'},
     body:JSON.stringify({name:name,descrizione:$('ed-desc').value.trim(),tokens:collectTokens()})})
    .then(function(r){if(!r.ok)return r.json().then(function(j){throw new Error(j.detail||'Errore');});return r.json();})
    .then(function(j){addPastiglia(j);closeEditor();})
    .catch(function(e){edErr(e.message);})
    .then(function(){$('ed-save').disabled=false;});
 }
 $('pal-add').addEventListener('click',openEditor);
 $('ed-x').addEventListener('click',closeEditor);
 $('ed-cancel').addEventListener('click',closeEditor);
 $('ed-save').addEventListener('click',save);
 $('editor').addEventListener('click',function(e){if(e.target===this)closeEditor();});

 updateCarosello();  // stato iniziale coerente col formato di default
})();
</script>
</body></html>"""
