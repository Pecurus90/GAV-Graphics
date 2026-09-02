#!/usr/bin/env python3
"""
App "Cielo del Mese" del Gruppo Astrofili Vicentini.

Avvio (dalla cartella del progetto):
    python -m uvicorn app.main:app --port 8000
Poi apri http://localhost:8000

L'interfaccia e' PORTATA dal design "Guscio App 1c" (chrome d'applicazione neutro
e serio): stessi stili/proporzioni dei componenti (barra laterale, toolbar in
alto, Quando/Dove compatto, formato segmentato),
RIESPRESSI nel nostro markup con OGNI hook JS preservato. Le schede e le pastiglie
si popolano DAI FILE su disco (come il CLI): aggiungere un layout domani non
richiede di toccare la UI. La palette e' UNA SOLA (l'identita' GAV): non si
sceglie, quindi non ha un controllo.

- D10: barra laterale, voce attiva + voce "Prossimamente".
- D11: le QUATTRO FASI REALI riportate MAN MANO via Server-Sent Events. Il motore
  non conosce la UI (invariante #1): riceve un callback e lo chiama.
- Cinque formati, UNO ALLA VOLTA (2026-07-19: tolto il carosello a due pagine).
  Deep Space e' un formato come gli altri; si abbina a mano in pubblicazione.
- Larghezza PNG per formato: render.png_width, la STESSA logica del CLI.
Tutto OFFLINE (D4/D15): font e logo locali, nessun CDN.
"""
import json, tempfile, os, uuid, queue, threading
from fastapi import FastAPI, HTTPException
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

# Glifo a filo per formato noto (design "Guscio App 1c": niente miniature
# illustrate, un simbolo di linea sobrio). Un formato senza glifo dedicato prende
# quello generico (un disco): la cella compare lo stesso. Solo il tratto interno
# dell'SVG; il wrapper (viewBox, stroke=currentColor) lo mette _schede_html, cosi'
# il glifo eredita il colore della cella (selezionata = scuro, spenta = tenue).
_GLYPH = {
 "dashboard": '<circle cx="9" cy="12" r="6"/><rect x="17" y="7" width="4" height="4" rx="1"/><rect x="17" y="13" width="4" height="4" rx="1"/>',
 "parata": '<rect x="3" y="5" width="18" height="14" rx="1"/><line x1="6" y1="9" x2="18" y2="9"/><line x1="6" y1="12" x2="18" y2="12"/><line x1="6" y1="15" x2="18" y2="15"/>',
 "zenit": '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="3"/>',
 "a4": '<rect x="6" y="3" width="12" height="18" rx="1"/><circle cx="12" cy="10" r="4"/><line x1="8" y1="17" x2="16" y2="17"/>',
 # Deep Space: i simboli degli atlanti che il formato USA - galassia (ellisse
 # inclinata) + ammasso aperto (cerchio tratteggiato). Unico glifo con ellisse,
 # rotazione e tratteggio: non si confonde con lo zenit (due cerchi concentrici).
 "deep-space": '<ellipse cx="10" cy="14" rx="8" ry="3.4" transform="rotate(-26 10 14)"/><circle cx="17.5" cy="7" r="3" stroke-dasharray="1.7 1.9"/>',
}
_GLYPH_GEN = '<circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="3"/>'


def _leggi(dirp, nome):
    with open(os.path.join(dirp, f"{nome}.json"), encoding="utf-8") as fh:
        return json.load(fh)


def formati_scheda():
    """I formati con una 'scheda', dal disco, ordinati per scheda.ordine.
    Aggiungere un layout con una scheda = una scheda nella UI, senza toccare qui.
    (Deep Space ha la sua scheda: e' un formato come gli altri, non piu' la
    pagina 2 di un carosello - tolto il 2026-07-19.)"""
    out = []
    for f in sorted(x[:-5] for x in os.listdir(LAYOUTS) if x.endswith(".json")):
        d = _leggi(LAYOUTS, f)
        if "scheda" not in d:
            continue
        s = d["scheda"]
        out.append((s.get("ordine", 99), f, s))
    out.sort()
    return [(f, s) for _o, f, s in out]


# ---------------------------------------------------------------------------
# Generazione condivisa (validazione R4 + contratto D2/D13 + larghezza per formato).
# ---------------------------------------------------------------------------
def _valida(year, month, lat, lon, formato, hour):
    y = validate.valida_anno(year); m = validate.valida_mese(month)
    la = validate.valida_lat(lat); lo = validate.valida_lon(lon)
    ho = validate.valida_ora(hour); fo = validate.valida_formato(formato)
    th = validate.carica_palette(); validate.valida_tema(th, f"{validate.PALETTE}.json")
    layout = _leggi(LAYOUTS, fo)
    return y, m, la, lo, ho, th, layout, fo


def _render(year, month, lat, lon, place, formato="a4", hour=23, progress=None):
    y, m, la, lo, ho, th, layout, _fo = _valida(year, month, lat, lon, formato, hour)
    out = os.path.join(tempfile.gettempdir(), "cielo.svg")
    engine.generate(y, m, la, lo, place, th, out, hour_local=ho, layout=layout, progress=progress)
    return out, layout


@app.get("/preview")
def preview(year=2026, month=8, lat=45.5455, lon=11.5353, place="Vicenza",
            formato="a4", hour=23):
    try:
        svg, _ = _render(year, month, lat, lon, place, formato, hour)
    except validate.InputError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return FileResponse(svg, media_type="image/svg+xml")


@app.get("/download")
def download(fmt="svg", year=2026, month=8, lat=45.5455, lon=11.5353,
             place="Vicenza", formato="a4", hour=23):
    if fmt not in ("svg", "png"):
        raise HTTPException(status_code=400,
                            detail=f"Formato di uscita sconosciuto: '{fmt}'. Ammessi: svg, png.")
    try:
        svg, layout = _render(year, month, lat, lon, place, formato, hour)
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
           formato="a4", hour=23):
    try:
        args = _valida(year, month, lat, lon, formato, hour)
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


@app.get("/anteprima")
def anteprima(token=""):
    p = _risultati.get(token)
    if not p or not os.path.exists(p):
        raise HTTPException(status_code=404, detail="Anteprima non trovata o scaduta.")
    return FileResponse(p, media_type="image/png")


# ---------------------------------------------------------------------------
# La pagina: schede/pastiglie popolate dal disco, poi il markup portato dal design.
# ---------------------------------------------------------------------------
def _schede_html(default="dashboard"):
    """Le celle del CONTROLLO SEGMENTATO del formato (design 1c): glifo a filo +
    nome. La selezione e' un riempimento (classe .sel), non una spunta. I
    data-attributi restano quelli che il JS legge (data-fmt/name/ar); data-sub
    alimenta la riga descrittiva sotto il segmentato."""
    out = []
    for f, s in formati_scheda():
        sel = " sel" if f == default else ""
        glyph = _GLYPH.get(f, _GLYPH_GEN)
        out.append(
            f'<button type="button" class="fmt{sel}" data-fmt="{f}" '
            f'data-name="{s["nome"]}" data-ar="{s.get("aspect","sq")}" '
            f'data-sub="{s["tag"]}" title="{s["nome"]} · {s["tag"]}">'
            f'<span class="fg"><svg viewBox="0 0 24 24" width="19" height="19" '
            f'fill="none" stroke="currentColor" stroke-width="1.45">{glyph}</svg></span>'
            f'<span class="fl">{s["nome"]}</span></button>')
    return "\n".join(out)


@app.get("/", response_class=HTMLResponse)
def index():
    mesi = "".join(f'<option value="{i+1}"{" selected" if i==7 else ""}>{i+1:02d} · {n}</option>'
                   for i, n in enumerate(MESI))
    return (PAGINA
            .replace("<!--MESI-->", mesi)
            .replace("<!--SCHEDE-->", _schede_html()))


PAGINA = r"""<!DOCTYPE html><html lang="it"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Cielo del Mese · GAV</title>
<style>
@font-face{font-family:'Barlow Semi Condensed';src:url('/fonts/BarlowSemiCondensed-SemiBold.ttf') format('truetype');font-weight:600;font-display:swap}
@font-face{font-family:'Barlow Semi Condensed';src:url('/fonts/BarlowSemiCondensed-ExtraBold.ttf') format('truetype');font-weight:800;font-display:swap}
@font-face{font-family:'Instrument Sans';src:url('/fonts/InstrumentSans-Regular.ttf') format('truetype');font-weight:400;font-display:swap}
@font-face{font-family:'Instrument Sans';src:url('/fonts/InstrumentSans-Medium.ttf') format('truetype');font-weight:500;font-display:swap}
@font-face{font-family:'Instrument Sans';src:url('/fonts/InstrumentSans-SemiBold.ttf') format('truetype');font-weight:600;font-display:swap}
:root{--bg:#0b0e13;--panel:#10141b;--surf:#161c25;--surf2:#1d2530;
--hair:rgba(132,158,192,.12);--hair2:rgba(132,158,192,.24);
--t1:#eaf0f8;--t2:#a2afc4;--t3:#75839a;--t4:#556074;
--acc:#6f89a8;--acc2:#8fa7c4;--prim:#3f5f83;--primtx:#f2f7ff;
--warn:#e8b45f;--danger:#e0664a;--ok:#5fd08a;
--display:'Barlow Semi Condensed','Arial Narrow',system-ui,sans-serif;
--testo:'Instrument Sans',system-ui,-apple-system,'Segoe UI',sans-serif}
*{box-sizing:border-box;margin:0;padding:0}html,body{height:100%}
body{font-family:var(--testo);color:var(--t1);background:var(--bg);overflow:hidden;-webkit-font-smoothing:antialiased}
a{color:var(--acc);text-decoration:none}a:hover{color:var(--acc2)}
::-webkit-scrollbar{width:9px;height:9px}::-webkit-scrollbar-thumb{background:rgba(132,158,192,.2);border-radius:9px}::-webkit-scrollbar-track{background:transparent}
input[type=color]{-webkit-appearance:none;-moz-appearance:none;appearance:none;border:none;padding:0;background:none;cursor:pointer}
input[type=color]::-webkit-color-swatch-wrapper{padding:0}input[type=color]::-webkit-color-swatch{border:none;border-radius:5px}input[type=color]::-moz-color-swatch{border:none;border-radius:5px}
@keyframes spin{to{transform:rotate(360deg)}}
@keyframes pulse{0%,100%{opacity:.55}50%{opacity:1}}
/* --- titlebar --- */
.titlebar{height:36px;flex:0 0 36px;display:flex;align-items:center;gap:8px;padding:0 15px;background:rgba(0,0,0,.3);border-bottom:1px solid var(--hair)}
.titlebar .dot{width:11px;height:11px;border-radius:50%;background:#2b3543}
.titlebar .tb-name{font-family:var(--display);font-weight:600;font-size:12px;letter-spacing:.16em;text-transform:uppercase;color:var(--t4);margin-left:12px}
.app{display:flex;height:calc(100% - 36px);min-height:0}
/* --- nav --- */
.nav{width:212px;flex:0 0 212px;height:100%;display:flex;flex-direction:column;padding:17px 12px 15px;gap:3px;background:rgba(0,0,0,.24);border-right:1px solid var(--hair)}
.nav .nav-brand{display:flex;align-items:center;gap:11px;padding:2px 6px 16px}
.nav .nav-brand img{width:32px;height:32px;filter:drop-shadow(0 3px 9px rgba(0,0,0,.5))}
.nav .nav-brand .nb-txt{font-family:var(--display);font-weight:800;font-size:15px;line-height:1;color:var(--t1)}
.nav .nav-brand .nb-sub{font-family:var(--display);font-weight:600;font-size:9px;letter-spacing:.18em;text-transform:uppercase;color:var(--t4);margin-top:3px}
.nav .nav-cap{font-family:var(--display);font-weight:600;font-size:9.5px;letter-spacing:.22em;text-transform:uppercase;color:var(--t4);padding:0 9px 7px}
.nav-item{display:flex;align-items:center;gap:11px;width:100%;text-align:left;background:none;border:1px solid transparent;border-radius:7px;padding:11px 10px;cursor:pointer;transition:.14s;color:var(--t2);font-family:var(--testo)}
.nav-item .ic{flex:0 0 19px;width:19px;height:19px;color:var(--t3);transition:.14s}
.nav-item .nm{font-size:14.5px;font-weight:600;line-height:1.12}
.nav-item .badge{font-family:var(--display);font-weight:600;font-size:9px;letter-spacing:.14em;text-transform:uppercase;color:var(--t4);margin-top:3px;display:block}
.nav-item:hover{background:rgba(132,158,192,.06)}
.nav-item.on{background:var(--surf2);border-color:var(--hair2);border-left:3px solid var(--acc);color:var(--t1)}
.nav-item.on .ic{color:var(--acc2)}.nav-item.on .nm{color:var(--t1)}
.nav-item.soon{cursor:not-allowed;opacity:.4}.nav-item.soon:hover{background:none}
.nav-foot{margin-top:auto;padding:12px 9px 0;border-top:1px solid var(--hair);font-size:11px;color:var(--t4);line-height:1.5}
/* --- panel --- */
.panel{width:404px;flex:0 0 404px;height:100%;display:flex;flex-direction:column;background:var(--panel);border-right:1px solid var(--hair);min-height:0}
.panel-toolbar{flex:0 0 auto;padding:12px 16px;border-bottom:1px solid var(--hair);display:flex;align-items:center;gap:9px}
.panel-body{flex:1;min-height:0;overflow-y:auto;padding:16px;display:flex;flex-direction:column;gap:16px}
.genera{flex:1;background:var(--prim);color:var(--primtx);border:none;border-radius:7px;padding:12px;font-family:var(--display);font-weight:800;font-size:15.5px;letter-spacing:.03em;cursor:pointer;transition:.14s}
.genera:hover{background:#4a6d96}.genera:disabled{opacity:.55;cursor:not-allowed}
.blk-lbl{font-family:var(--display);font-weight:700;font-size:10.5px;letter-spacing:.2em;text-transform:uppercase;color:var(--t3);margin-bottom:9px}
.field-lbl{font-size:11.5px;color:var(--t3);margin-bottom:5px;font-weight:500}
/* Quando · Dove */
.qd-card{border:1px solid var(--hair);border-radius:9px;overflow:hidden}
.qd-head{padding:8px 12px;background:var(--surf);border-bottom:1px solid var(--hair);font-family:var(--display);font-weight:700;font-size:10.5px;letter-spacing:.2em;text-transform:uppercase;color:var(--t3)}
.qd-row{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:9px 12px;border-bottom:1px solid var(--hair)}
.qd-lbl{font-size:12.5px;color:var(--t3);flex:0 0 auto}
.qd-sel{flex:1;max-width:210px;background:none;border:none;text-align:right;color:var(--t1);font-family:var(--display);font-weight:800;font-size:15px;font-variant-numeric:tabular-nums;cursor:pointer;-webkit-appearance:none;-moz-appearance:none;appearance:none;padding:2px 20px 2px 4px;background-image:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='14' height='14' viewBox='0 0 24 24' fill='none' stroke='%2375839a' stroke-width='2.4' stroke-linecap='round'><path d='M6 9l6 6 6-6'/></svg>");background-repeat:no-repeat;background-position:right center}
.qd-sel:focus{outline:none;color:var(--acc2)}.qd-sel option{background:#0e1626;color:var(--t1);font-size:14px;text-align:left}
.qd-step{display:flex;align-items:center;gap:12px}
.qd-step button{background:none;border:none;color:var(--t3);font-size:17px;line-height:1;cursor:pointer;padding:0 2px;transition:.13s;font-family:var(--testo)}
.qd-step button:hover{color:var(--acc2)}
.qd-step input{width:52px;border:none;background:none;text-align:center;color:var(--t1);font-family:var(--display);font-weight:800;font-size:15px;font-variant-numeric:tabular-nums;padding:0}
.qd-step input:focus{outline:none}
.qd-step.bad input{color:var(--danger)}.qd-step.bad{box-shadow:0 0 0 2px rgba(224,102,74,.3);border-radius:6px}
.qd-loc{flex:1;max-width:210px;background:none;border:none;text-align:right;color:var(--t1);font-family:var(--testo);font-size:14px;font-weight:600;padding:2px 4px}
.qd-loc:focus{outline:none;color:var(--acc2)}
.qd-coord{padding:9px 12px}
.coord-toggle{display:inline-flex;align-items:center;gap:7px;background:none;border:none;color:var(--t3);font-family:var(--testo);font-size:12px;font-weight:500;cursor:pointer;padding:0}
.coord-toggle:hover{color:var(--acc2)}
.coord-toggle .chev{transition:transform .18s;display:inline-block}.coord-toggle.open .chev{transform:rotate(90deg)}
.coord-wrap{max-height:0;overflow:hidden;transition:max-height .22s ease}.coord-wrap.open{max-height:120px}
.coord-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:11px}
.coord-grid .qd-loc{text-align:left;max-width:none;width:100%;background:var(--surf);border:1px solid var(--hair);border-radius:7px;padding:9px 10px;font-size:13px}
/* Formato segmentato */
.formats{display:flex;border:1px solid var(--hair2);border-radius:8px;overflow:hidden}
.fmt{flex:1;min-width:0;display:flex;flex-direction:column;align-items:center;gap:5px;padding:9px 2px;cursor:pointer;background:none;border:none;border-left:1px solid var(--hair);color:var(--t2);transition:.13s;font-family:var(--testo)}
.fmt:first-child{border-left:none}
.fmt:hover{background:rgba(132,158,192,.06);color:var(--t1)}
.fmt .fg{display:flex;align-items:center;justify-content:center;height:20px}
.fmt .fl{font-size:9.5px;font-weight:700;letter-spacing:.01em}
.fmt.sel{background:var(--acc);color:#0b0e13}.fmt.sel:hover{background:var(--acc)}
.fmt-sub{font-size:11.5px;color:var(--t3);margin-top:8px;line-height:1.35}
/* --- stage --- */
.stage{flex:1;min-width:0;height:100%;display:flex;flex-direction:column;padding:18px 22px;gap:14px;position:relative}
.meta-chips{display:flex;align-items:center;gap:7px;flex-wrap:wrap;font-variant-numeric:tabular-nums}
.chip{font-size:11.5px;color:var(--t2);background:var(--surf);border:1px solid var(--hair);border-radius:5px;padding:5px 10px;display:inline-flex;align-items:center;gap:6px;text-transform:uppercase}
.chip b{color:var(--t1);font-weight:600}
.chip .sw{width:9px;height:9px;border-radius:50%}
.stage-box{flex:1;min-height:0;display:flex;align-items:center;justify-content:center;background:rgba(0,0,0,.26);border:1px solid var(--hair);border-radius:10px;padding:20px;position:relative;overflow:hidden}
.state{display:none;width:100%;height:100%;align-items:center;justify-content:center}
.state.active{display:flex}
/* stato iniziale */
.init-card{display:flex;flex-direction:column;align-items:center;gap:16px;text-align:center;max-width:380px}
.init-card .ii{color:var(--t4)}
.init-card .it{font-family:var(--display);font-weight:800;font-size:22px;color:var(--t2)}
.init-card .ix{font-size:13.5px;color:var(--t3);line-height:1.55}
.init-card .ix b{color:var(--acc2);font-weight:600}
/* stato generazione */
.gen-card{width:100%;max-width:520px;display:flex;flex-direction:column;gap:20px}
.gen-head{display:flex;align-items:center;gap:14px}
.gen-spin{width:40px;height:40px;border-radius:50%;border:2px solid var(--hair2);border-top-color:var(--acc2);animation:spin .8s linear infinite;flex:0 0 auto}
.gen-kicker{font-family:var(--display);font-weight:700;font-size:10.5px;letter-spacing:.22em;text-transform:uppercase;color:var(--t3)}
.gen-title{font-family:var(--display);font-weight:800;font-size:23px;color:var(--t1);line-height:1.05;margin-top:3px}
.gen-sub{font-size:12px;color:var(--t4);margin-top:2px}
.seg-strip{display:flex;gap:5px}
.seg{flex:1;height:5px;border-radius:3px;background:var(--surf2);transition:.2s}
#s-generating:has(.phase[data-ph="0"].done) .seg[data-seg="0"],#s-generating:has(.phase[data-ph="1"].done) .seg[data-seg="1"],#s-generating:has(.phase[data-ph="2"].done) .seg[data-seg="2"],#s-generating:has(.phase[data-ph="3"].done) .seg[data-seg="3"]{background:var(--acc)}
#s-generating:has(.phase[data-ph="0"].active) .seg[data-seg="0"],#s-generating:has(.phase[data-ph="1"].active) .seg[data-seg="1"],#s-generating:has(.phase[data-ph="2"].active) .seg[data-seg="2"],#s-generating:has(.phase[data-ph="3"].active) .seg[data-seg="3"]{background:linear-gradient(90deg,var(--acc),var(--acc2));box-shadow:0 0 10px var(--acc)}
.phases{border:1px solid var(--hair);border-radius:9px;overflow:hidden;background:rgba(0,0,0,.2)}
.phase{display:flex;align-items:center;gap:12px;padding:11px 13px;border-bottom:1px solid var(--hair);transition:.2s}
.phase:last-child{border-bottom:none}
.phase .dot{flex:0 0 24px;width:24px;height:24px;border-radius:50%;position:relative;border:1.5px solid var(--hair2);background:var(--surf);display:flex;align-items:center;justify-content:center;transition:.2s}
.phase .dot .num{font-family:var(--display);font-weight:800;font-size:12px;color:var(--t4)}
.phase .dot .chk{display:none;color:#0b0e13;font-size:13px;font-weight:800}
.phase .dot .spin{display:none;width:14px;height:14px;border-radius:50%;border:2px solid rgba(143,167,196,.3);border-top-color:var(--acc2);animation:spin .7s linear infinite}
.phase .nm{flex:1;font-size:13.5px;color:var(--t4);transition:.2s;line-height:1.3}
.phase .ptag{font-size:11px;color:var(--t4);font-variant-numeric:tabular-nums}
.phase .pstate{flex:0 0 auto;font-size:11px;font-variant-numeric:tabular-nums;color:var(--t4)}
.phase .pstate::after{content:"in attesa"}
.phase.done .dot{background:var(--acc);border-color:var(--acc)}.phase.done .dot .num{display:none}.phase.done .dot .chk{display:block}.phase.done .nm{color:var(--t2)}.phase.done .pstate{color:var(--acc2)}.phase.done .pstate::after{content:"fatto"}
.phase.active{background:rgba(111,137,168,.06)}
.phase.active .dot{border-color:var(--acc);background:rgba(111,137,168,.16)}.phase.active .dot .num{display:none}.phase.active .dot .spin{display:block}.phase.active .nm{color:var(--t1);font-weight:600}.phase.active .pstate{color:var(--acc2);font-weight:600;animation:pulse 1.2s ease-in-out infinite}.phase.active .pstate::after{content:"in corso…"}
.gen-note{font-size:11.5px;color:var(--t4);line-height:1.5}.gen-note b{color:var(--t3);font-weight:600}
/* stato anteprima */
.preview-wrap{display:flex;flex-direction:column;align-items:center;gap:16px;width:100%;height:100%}
.frames{flex:1;min-height:0;width:100%;display:flex;gap:16px;align-items:center;justify-content:center}
/* L'anteprima riempie il palco: la vera altezza disponibile e' 100% (il flex del
   palco), il vincolo di LARGHEZZA e' viewport meno la chrome fissa a sinistra
   (nav 212 + pannello 404 + padding/bordi ~= 704, +8 di margine). Aspetto intatto
   -> mai stirata; sempre tutto il poster (object-fit:contain). Niente cap a 640. */
.poster-frame{height:min(100%,100vw - 712px);width:auto;max-width:100%;aspect-ratio:1/1;border-radius:10px;overflow:hidden;box-shadow:0 20px 50px rgba(0,0,0,.55);border:1px solid var(--hair);background:#05070f}
.poster-frame.a4{aspect-ratio:1/1.414;height:min(100%,calc((100vw - 712px) * 1.414))}
.poster-frame img{width:100%;height:100%;object-fit:contain;display:block}
.save-row{display:flex;gap:9px;align-items:center;flex-wrap:wrap;justify-content:center}
.btn{font-family:var(--testo);font-weight:600;font-size:13px;border-radius:7px;padding:10px 16px;cursor:pointer;transition:.14s;display:inline-flex;align-items:center;gap:8px;border:1px solid transparent;text-decoration:none}
.btn small{font-weight:400;color:var(--t3);font-size:10.5px}
.btn-gold{background:var(--prim);color:var(--primtx)}.btn-gold:hover{background:#4a6d96}
.btn-ghost{background:var(--surf2);border-color:var(--hair2);color:var(--t1)}.btn-ghost:hover{border-color:var(--acc)}
.btn-text{background:none;border:none;color:var(--t3);font-family:var(--testo);font-weight:500;font-size:13px;cursor:pointer;padding:8px}.btn-text:hover{color:var(--acc2)}
/* stato errore */
.err-card{max-width:460px;background:var(--surf);border:1px solid rgba(224,102,74,.4);border-radius:14px;padding:30px 32px;text-align:center;box-shadow:0 24px 60px rgba(0,0,0,.5)}
.err-icon{width:54px;height:54px;border-radius:50%;background:rgba(224,102,74,.14);display:flex;align-items:center;justify-content:center;margin:0 auto 18px}
.err-title{font-family:var(--display);font-weight:800;font-size:22px;color:#f2d3c9;margin-bottom:11px}
.err-msg{font-size:15px;color:#f0c6b6;line-height:1.5;font-weight:500;background:rgba(224,102,74,.09);border:1px solid rgba(224,102,74,.22);border-radius:10px;padding:13px 16px;margin-bottom:16px}
.err-hint{font-size:13px;color:var(--t3);line-height:1.55;margin-bottom:20px}
</style></head>
<body>
<div class="titlebar"><span class="dot"></span><span class="dot"></span><span class="dot"></span>
<span class="tb-name">Cielo del Mese — Generatore poster · Gruppo Astrofili Vicentini</span></div>
<div class="app">
  <nav class="nav">
    <div class="nav-brand"><img src="/assets/logo-emblema.png" alt="GAV">
      <div><div class="nb-txt">GAV</div><div class="nb-sub">Astrofili Vicentini</div></div></div>
    <div class="nav-cap">Strumenti</div>
    <button type="button" class="nav-item on" aria-current="page">
      <svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="3" fill="currentColor" stroke="none"/></svg>
      <span class="nm">Cielo del Mese</span></button>
    <button type="button" class="nav-item soon" disabled aria-disabled="true" title="Prossimamente">
      <svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="4"/><path d="M12 3v2M12 19v2M3 12h2M19 12h2M6 6l1.4 1.4M18 6l-1.4 1.4M6 18l1.4-1.4M18 18l-1.4-1.4" stroke-linecap="round"/></svg>
      <div><div class="nm">Pillole di astronomia</div><div class="badge">Prossimamente</div></div></button>
    <div class="nav-foot">Altri strumenti arriveranno qui.</div>
  </nav>
  <aside class="panel">
    <div class="panel-toolbar">
      <button class="genera" id="genera">Genera anteprima</button>
    </div>
    <div class="panel-body">
      <div class="qd-card">
        <div class="qd-head">Quando · Dove</div>
        <div class="qd-row"><span class="qd-lbl">Mese</span>
          <select class="qd-sel" id="in-mese" aria-label="Mese"><!--MESI--></select></div>
        <div class="qd-row"><span class="qd-lbl">Anno</span>
          <span class="qd-step" id="st-anno"><button type="button" data-step="anno" data-d="-1">−</button>
            <input id="in-anno" type="text" inputmode="numeric" value="2026"><button type="button" data-step="anno" data-d="1">+</button></span></div>
        <div class="qd-row"><span class="qd-lbl">Ora</span>
          <span class="qd-step" id="st-ora"><button type="button" data-step="ora" data-d="-1">−</button>
            <input id="in-ora" type="text" value="23:00" readonly><button type="button" data-step="ora" data-d="1">+</button></span></div>
        <div class="qd-row"><span class="qd-lbl">Località</span>
          <input class="qd-loc" id="in-loc" type="text" value="Vicenza" placeholder="Es. Vicenza"></div>
        <div class="qd-coord">
          <button type="button" class="coord-toggle" id="coord-btn"><span class="chev">›</span> <span id="coord-lbl">Coordinate precise</span></button>
          <div class="coord-wrap" id="coord-wrap"><div class="coord-grid">
            <div><div class="field-lbl">Latitudine</div><input class="qd-loc" id="in-lat" value="45.5455"></div>
            <div><div class="field-lbl">Longitudine</div><input class="qd-loc" id="in-lon" value="11.5353"></div></div></div>
        </div>
      </div>
      <div class="fmt-block">
        <div class="blk-lbl">Formato</div>
        <div class="formats" id="formats"><!--SCHEDE--></div>
        <div class="fmt-sub" id="fmt-sub"></div>
      </div>
    </div>
  </aside>
  <main class="stage" id="stage">
    <div class="meta-chips">
      <span class="chip"><b id="cap-when">Agosto 2026</b></span>
      <span class="chip">📍 <b id="cap-loc">Vicenza</b></span>
      <span class="chip"><b id="cap-fmt">Dashboard</b></span>
    </div>
    <div class="stage-box">
      <div class="state active" id="s-initial">
        <div class="init-card">
          <svg class="ii" viewBox="0 0 24 24" width="46" height="46" fill="none" stroke="currentColor" stroke-width="1.3"><circle cx="12" cy="12" r="9"/><path d="M12 3v18M3 12h18" opacity=".5"/><circle cx="12" cy="12" r="3.2"/></svg>
          <div class="it">L'anteprima comparirà qui</div>
          <div class="ix">Imposta i parametri nel pannello a sinistra, poi premi <b>Genera anteprima</b>. La barra in alto tiene l'azione sempre a portata.</div>
        </div></div>
      <div class="state" id="s-generating">
        <div class="gen-card">
          <div class="gen-head">
            <div class="gen-spin"></div>
            <div>
              <div class="gen-kicker">Generazione in corso</div>
              <div class="gen-title" id="gen-title">Sto disegnando il cielo…</div>
              <div class="gen-sub" id="gen-sub"></div></div></div>
          <div class="seg-strip">
            <i class="seg" data-seg="0"></i><i class="seg" data-seg="1"></i><i class="seg" data-seg="2"></i><i class="seg" data-seg="3"></i></div>
          <div class="phases" id="phases">
            <div class="phase" data-ph="0"><span class="dot"><span class="num">1</span><span class="chk">✓</span><span class="spin"></span></span><span class="nm">Calcolo dove sono stasera i pianeti e la Luna</span><span class="ptag">effemeridi</span><span class="pstate"></span></div>
            <div class="phase" data-ph="1"><span class="dot"><span class="num">2</span><span class="chk">✓</span><span class="spin"></span></span><span class="nm">Metto cinquemila stelle sulla mappa</span><span class="ptag">proiezione</span><span class="pstate"></span></div>
            <div class="phase" data-ph="2"><span class="dot"><span class="num">3</span><span class="chk">✓</span><span class="spin"></span></span><span class="nm">Compongo il poster</span><span class="ptag">composizione</span><span class="pstate"></span></div>
            <div class="phase" data-ph="3"><span class="dot"><span class="num">4</span><span class="chk">✓</span><span class="spin"></span></span><span class="nm">Disegno l'immagine finale</span><span class="ptag">rendering</span><span class="pstate"></span></div>
          </div>
          <div class="gen-note">L'indicatore segue le fasi <b>reali</b> del motore: ogni riga si accende quando quel calcolo parte davvero.</div>
        </div></div>
      <div class="state" id="s-preview">
        <div class="preview-wrap">
          <div class="frames" id="frames"></div>
          <div class="save-row" id="save-row"></div></div></div>
      <div class="state" id="s-error">
        <div class="err-card"><div class="err-icon">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none"><path d="M12 8v5" stroke="#e0664a" stroke-width="2.4" stroke-linecap="round"/><circle cx="12" cy="17" r="1.4" fill="#e0664a"/><circle cx="12" cy="12" r="10" stroke="#e0664a" stroke-width="1.6" opacity=".5"/></svg></div>
          <div class="err-title">Controlla un dato</div>
          <div class="err-msg" id="err-msg"></div>
          <div class="err-hint">Correggi il valore nel pannello a sinistra e premi di nuovo.</div>
          <button class="btn btn-gold" id="err-back">Torna alle impostazioni</button></div></div>
    </div>
  </main>
</div>
<script>
(function(){
 var MESI=["Gennaio","Febbraio","Marzo","Aprile","Maggio","Giugno","Luglio","Agosto","Settembre","Ottobre","Novembre","Dicembre"];
 var $=function(id){return document.getElementById(id);};
 var st={fmt:"dashboard",fmtName:"Dashboard",ar:"sq",ora:23};
 // stepper
 document.querySelectorAll('[data-step]').forEach(function(btn){btn.addEventListener('click',function(){
   var w=btn.getAttribute('data-step'),d=parseInt(btn.getAttribute('data-d'),10);
   if(w==='anno'){var i=$('in-anno');var v=parseInt(i.value,10);if(isNaN(v))v=2026;v+=d;if(v<1900)v=1900;if(v>2050)v=2050;i.value=v;$('st-anno').classList.remove('bad');}
   else{st.ora=((st.ora+d)%24+24)%24;$('in-ora').value=(st.ora<10?'0':'')+st.ora+':00';}});});
 $('coord-btn').addEventListener('click',function(){this.classList.toggle('open');$('coord-wrap').classList.toggle('open');$('coord-lbl').textContent=this.classList.contains('open')?'Nascondi coordinate':'Coordinate precise';});
 // selezione schede/pastiglie
 function updateFmtSub(b){var el=$('fmt-sub');if(el)el.textContent=b.getAttribute('data-name')+' · '+(b.getAttribute('data-sub')||'');}
 document.querySelectorAll('.fmt').forEach(function(b){b.addEventListener('click',function(){document.querySelectorAll('.fmt').forEach(function(x){x.classList.remove('sel');});b.classList.add('sel');st.fmt=b.getAttribute('data-fmt');st.fmtName=b.getAttribute('data-name');st.ar=b.getAttribute('data-ar');updateFmtSub(b);});});
 // stati
 var S={initial:'s-initial',generating:'s-generating',preview:'s-preview',error:'s-error'};
 function show(n){Object.keys(S).forEach(function(k){$(S[k]).classList.toggle('active',k===n);});}
 function setPhase(i){document.querySelectorAll('#phases .phase').forEach(function(p,k){p.classList.toggle('done',k<i);p.classList.toggle('active',k===i);});}
 function allDone(){document.querySelectorAll('#phases .phase').forEach(function(p){p.classList.remove('active');p.classList.add('done');});}
 function params(){var m=parseInt($('in-mese').value,10),a=parseInt($('in-anno').value,10);
   return{p:new URLSearchParams({year:$('in-anno').value,month:$('in-mese').value,hour:st.ora,place:$('in-loc').value.trim()||'Vicenza',lat:$('in-lat').value,lon:$('in-lon').value,formato:st.fmt}),m:m,a:a};}
 function fillCaps(m,a){$('cap-when').textContent=MESI[m-1]+' '+a+' · '+(st.ora<10?'0':'')+st.ora+':00';$('cap-loc').textContent=$('in-loc').value.trim()||'Vicenza';$('cap-fmt').textContent=st.fmtName;}
 function frame(token,ar){return '<div class="poster-frame'+(ar==='a4'?' a4':'')+'"><img src="/anteprima?token='+token+'&_='+Date.now()+'"></div>';}
 function dlLink(fmt,formato,label,cls,small){var q=params().p;q.set('fmt',fmt);q.set('formato',formato);return '<a class="btn '+cls+'" href="/download?'+q.toString()+'" download>'+label+(small?' <small>'+small+'</small>':'')+'</a>';}
 function busy(b){$('genera').disabled=b;$('genera').textContent=b?'Generazione in corso…':'Genera anteprima';}
 function fail(msg){$('err-msg').textContent=msg;show('error');busy(false);}
 function run(){
   var pr=params();busy(true);show('generating');setPhase(0);
   $('gen-title').textContent='Sto disegnando il cielo…';$('gen-sub').textContent='';
   var es=new EventSource('/genera?'+pr.p.toString());
   es.addEventListener('fase',function(e){setPhase(+e.data);});
   es.addEventListener('errore',function(e){es.close();fail(e.data);});
   es.addEventListener('fatto',function(e){es.close();allDone();var toks=e.data.split(',');
     setTimeout(function(){fillCaps(pr.m,pr.a);
       $('frames').innerHTML=frame(toks[0],st.ar);
       $('save-row').innerHTML=dlLink('png',st.fmt,'Salva PNG','btn-gold','per i social')+dlLink('svg',st.fmt,'Salva SVG','btn-ghost','per la stampa')+'<button class="btn-text" id="regen">↻ Rigenera</button>';
       show('preview');busy(false);
       var rg=$('regen');if(rg)rg.addEventListener('click',run);
     },420);});
   es.onerror=function(){es.close();fail('Connessione al motore interrotta.');};
 }
 $('genera').addEventListener('click',run);
 $('err-back').addEventListener('click',function(){show('initial');});

 var selFmt0=document.querySelector('.fmt.sel');if(selFmt0)updateFmtSub(selFmt0);
})();
</script>
</body></html>"""
