#!/usr/bin/env python3
"""
App "Cielo del Mese" del Gruppo Astrofili Vicentini.

Avvio (dalla cartella del progetto):
    python -m uvicorn app.main:app --reload --port 8000
Poi apri http://localhost:8000

Contenitore di STRUMENTI (D10): una barra laterale con una voce attiva ("Cielo
del Mese") e una spenta "Prossimamente" ("Pillole di astronomia"). E' la barra,
NON un'infrastruttura per plugin: aggiungere uno strumento domani = una voce +
una vista, non un framework.

La generazione riporta le QUATTRO FASI REALI del motore (D11) via Server-Sent
Events: effemeridi -> proiezione -> composizione -> rendering PNG. Il motore non
conosce la UI (invariante #1): riceve un callback e lo chiama; l'app lo traduce
in eventi SSE. Niente barra finta.

Tutto e' OFFLINE (D4/D15): font locali da brand/fonts, logo locale, nessun CDN.
"""
import json, tempfile, os, uuid, queue, threading
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from engine.generate import Engine
from render import svg_file_to_png
import validate

BASE = os.path.join(os.path.dirname(__file__), "..")
PALETTES = os.path.join(BASE, "brand", "palettes")
LAYOUTS = os.path.join(BASE, "brand", "layouts")

app = FastAPI(title="Cielo del Mese")
app.mount("/fonts", StaticFiles(directory=os.path.join(BASE, "brand", "fonts")), name="fonts")
app.mount("/assets", StaticFiles(directory=os.path.join(BASE, "brand", "logo")), name="assets")

engine = Engine(datadir=os.path.join(BASE, "data"))  # caricato una volta sola
_risultati = {}  # token -> percorso PNG (app locale mono-utente: dict in memoria)

MESI = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio",
        "agosto", "settembre", "ottobre", "novembre", "dicembre"]
# larghezza PNG per formato (i post social nascono a 1080; l'A4 piu' grande)
PNG_W = {"post": 1080, "profondo": 1080, "dashboard": 1080, "editorial": 1080,
         "rail": 1080, "a4": 1800}


def list_themes():
    return sorted(f[:-5] for f in os.listdir(PALETTES) if f.endswith(".json"))


def list_formats():
    return sorted(f[:-5] for f in os.listdir(LAYOUTS) if f.endswith(".json"))


# ---------------------------------------------------------------------------
# Generazione condivisa da /preview e /download (validazione R4 + contratto D2).
# ---------------------------------------------------------------------------
def _render(year, month, lat, lon, place, theme, formato="a4", hour=23, progress=None):
    year = validate.valida_anno(year)
    month = validate.valida_mese(month)
    lat = validate.valida_lat(lat)
    lon = validate.valida_lon(lon)
    hour = validate.valida_ora(hour)
    theme = validate.valida_palette(theme)
    formato = validate.valida_formato(formato)
    th = json.load(open(os.path.join(PALETTES, f"{theme}.json"), encoding="utf-8"))
    validate.valida_tema(th, f"{theme}.json")  # contratto del CIELO (default)
    layout = json.load(open(os.path.join(LAYOUTS, f"{formato}.json"), encoding="utf-8"))
    out = os.path.join(tempfile.gettempdir(), "cielo.svg")
    engine.generate(year, month, lat, lon, place, th, out, hour_local=hour,
                    layout=layout, progress=progress)
    return out


@app.get("/preview")
def preview(year=2026, month=8, lat=45.5455, lon=11.5353, place="Vicenza",
            theme="osservatorio", formato="a4", hour=23):
    try:
        svg = _render(year, month, lat, lon, place, theme, formato, hour)
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
        svg = _render(year, month, lat, lon, place, theme, formato, hour)
    except validate.InputError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if fmt == "svg":
        return FileResponse(svg, media_type="image/svg+xml", filename="cielo.svg")
    tmp = os.path.join(tempfile.gettempdir(), "cielo.png")
    svg_file_to_png(svg, tmp, width=PNG_W.get(formato, 1800))
    return FileResponse(tmp, media_type="image/png", filename="cielo.png")


# ---------------------------------------------------------------------------
# /genera — Server-Sent Events: la generazione in un thread, le QUATTRO FASI
# REALI riportate MAN MANO (D11). Nessuna barra finta: la fase 4 resta "in corso"
# finche' resvg non ha davvero finito.
# ---------------------------------------------------------------------------
def _sse(evento, dato):
    return f"event: {evento}\ndata: {dato}\n\n"


@app.get("/genera")
def genera(year=2026, month=8, lat=45.5455, lon=11.5353, place="Vicenza",
           theme="osservatorio", formato="a4", hour=23):
    # Validazione PRIMA di aprire lo stream: se l'input e' sbagliato, un solo
    # evento 'errore' in italiano (la UI mostra lo stato Errore), mai un 500.
    try:
        y = validate.valida_anno(year); m = validate.valida_mese(month)
        la = validate.valida_lat(lat); lo = validate.valida_lon(lon)
        ho = validate.valida_ora(hour)
        pal = validate.valida_palette(theme); fo = validate.valida_formato(formato)
        th = json.load(open(os.path.join(PALETTES, f"{pal}.json"), encoding="utf-8"))
        validate.valida_tema(th, f"{pal}.json")
        layout = json.load(open(os.path.join(LAYOUTS, f"{fo}.json"), encoding="utf-8"))
    except validate.InputError as e:
        msg = str(e)
        return StreamingResponse(iter([_sse("errore", msg)]), media_type="text/event-stream")

    q = queue.Queue()
    token = uuid.uuid4().hex

    def lavora():
        try:
            svg = os.path.join(tempfile.gettempdir(), f"cielo_{token}.svg")
            engine.generate(y, m, la, lo, place, th, svg, hour_local=ho, layout=layout,
                            progress=lambda i: q.put(("fase", i)))
            q.put(("fase", engine.FASE_RENDERING))     # fase 4: rasterizzazione PNG
            png = os.path.join(tempfile.gettempdir(), f"cielo_{token}.png")
            svg_file_to_png(svg, png, width=PNG_W.get(fo, 1800))
            _risultati[token] = png
            q.put(("fatto", token))
        except Exception as e:                          # rete di sicurezza: mai un 500 muto
            q.put(("errore", f"Errore imprevisto: {e}"))
        finally:
            q.put((None, None))

    threading.Thread(target=lavora, daemon=True).start()

    def stream():
        while True:
            ev, val = q.get()
            if ev is None:
                break
            yield _sse(ev, val)
    return StreamingResponse(stream(), media_type="text/event-stream")


@app.get("/anteprima")
def anteprima(token=""):
    p = _risultati.get(token)
    if not p or not os.path.exists(p):
        raise HTTPException(status_code=404, detail="Anteprima non trovata o scaduta.")
    return FileResponse(p, media_type="image/png")


# ---------------------------------------------------------------------------
# La pagina: barra laterale (D10) + pannello + palco a quattro stati.
# ---------------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
def index():
    mesi = "".join(f'<option value="{i+1}"{" selected" if i==7 else ""}>{n}</option>'
                   for i, n in enumerate(MESI))
    formati = "".join(f'<option value="{f}"{" selected" if f=="a4" else ""}>{f}</option>'
                      for f in list_formats())
    palette = "".join(f'<option value="{t}"{" selected" if t=="osservatorio" else ""}>{t}</option>'
                      for t in list_themes())
    return (PAGINA
            .replace("<!--MESI-->", mesi)
            .replace("<!--FORMATI-->", formati)
            .replace("<!--PALETTE-->", palette))


PAGINA = """<!doctype html><html lang="it"><head><meta charset="utf-8">
<title>Cielo del Mese — GAV</title><meta name="viewport" content="width=device-width,initial-scale=1">
<style>
@font-face{font-family:'Barlow Semi Condensed';src:url('/fonts/BarlowSemiCondensed-SemiBold.ttf') format('truetype');font-weight:600;font-display:swap}
@font-face{font-family:'Barlow Semi Condensed';src:url('/fonts/BarlowSemiCondensed-ExtraBold.ttf') format('truetype');font-weight:800;font-display:swap}
@font-face{font-family:'Instrument Sans';src:url('/fonts/InstrumentSans-Regular.ttf') format('truetype');font-weight:400;font-display:swap}
@font-face{font-family:'Instrument Sans';src:url('/fonts/InstrumentSans-Medium.ttf') format('truetype');font-weight:500;font-display:swap}
@font-face{font-family:'Instrument Sans';src:url('/fonts/InstrumentSans-SemiBold.ttf') format('truetype');font-weight:600;font-display:swap}
:root{--notte:#05070f;--blunotte:#0a1222;--bluprof:#12203a;--superficie:#0e1626;--superficie2:#131d31;
--bordo:rgba(150,170,215,.14);--bordo-forte:rgba(150,170,215,.26);--oro:#e4ac4a;--oro-chiaro:#f0c274;
--petrolio:#004f6d;--neon:#45c8ff;--t1:#eef2fb;--t2:#b9c4dc;--t3:#8e9bb8;--t4:#6a768f;
--warn:#f0b45a;--danger:#f08a6a;--ok:#6fe0a0}
*{box-sizing:border-box;margin:0;padding:0}
body{height:100vh;background:radial-gradient(120% 90% at 50% 0%,var(--blunotte),var(--notte));
color:var(--t1);font-family:'Instrument Sans',system-ui,sans-serif;overflow:hidden}
.titlebar{height:38px;display:flex;align-items:center;gap:8px;padding:0 14px;
background:rgba(5,7,15,.55);border-bottom:1px solid var(--bordo);font-size:12.5px;color:var(--t4)}
.titlebar .dot{width:11px;height:11px;border-radius:50%}
.app{display:flex;height:calc(100% - 38px)}

/* --- BARRA LATERALE (D10) --- */
nav{width:224px;flex:0 0 224px;display:flex;flex-direction:column;gap:6px;padding:22px 16px 20px;
background:linear-gradient(180deg,rgba(5,7,15,.6),rgba(5,7,15,.28));border-right:1px solid var(--bordo)}
.nav-brand{display:flex;align-items:center;gap:12px;padding:2px 8px 20px}
.nav-brand img{width:40px;height:40px;filter:drop-shadow(0 3px 10px rgba(0,0,0,.5))}
.nav-brand .g{font-family:'Barlow Semi Condensed';font-weight:800;font-size:16px;color:var(--t1);line-height:1}
.nav-brand .s{font-family:'Barlow Semi Condensed';font-weight:600;font-size:9.5px;letter-spacing:.18em;
text-transform:uppercase;color:var(--t4);margin-top:3px}
.nav-cap{font-family:'Barlow Semi Condensed';font-weight:600;font-size:10.5px;letter-spacing:.2em;
text-transform:uppercase;color:var(--t4);padding:0 10px 8px}
.nav-item{display:flex;align-items:center;gap:13px;padding:14px 13px;border-radius:13px;
border:1px solid transparent;min-height:52px;text-decoration:none;color:var(--t1)}
.nav-item svg{width:26px;height:26px;flex:0 0 26px}
.nav-item .nm{font-family:'Instrument Sans';font-weight:600;font-size:16px}
.nav-item .badge{font-family:'Barlow Semi Condensed';font-weight:600;font-size:9.5px;letter-spacing:.12em;
text-transform:uppercase;color:var(--t4);margin-top:3px}
.nav-item.on{background:linear-gradient(180deg,rgba(228,172,74,.14),rgba(228,172,74,.04));
border-color:rgba(228,172,74,.4);box-shadow:0 8px 22px rgba(0,0,0,.28)}
.nav-item.on svg{color:var(--oro)}
.nav-item.tap{cursor:pointer}
.nav-item.tap:hover{background:rgba(150,170,215,.07);border-color:var(--bordo)}
.nav-item.soon{cursor:not-allowed}
.nav-item.soon .ic,.nav-item.soon .nm{opacity:.5}
.nav-foot{margin-top:auto;border-top:1px solid var(--bordo);padding:14px 10px 0;
font-size:11.5px;color:var(--t4)}

/* --- PANNELLO --- */
.panel{width:404px;flex:0 0 404px;overflow-y:auto;padding:26px 26px 40px;border-right:1px solid var(--bordo)}
.panel h1{font-family:'Barlow Semi Condensed';font-weight:800;font-size:23px;margin-bottom:2px}
.panel .sub{color:var(--t3);font-size:13px;margin-bottom:22px}
.grp{margin-bottom:20px}
.grp label{display:block;font-family:'Barlow Semi Condensed';font-weight:600;font-size:11px;
letter-spacing:.14em;text-transform:uppercase;color:var(--t4);margin-bottom:8px}
.grp input,.grp select{width:100%;padding:11px 12px;border-radius:11px;border:1px solid var(--bordo-forte);
background:var(--superficie);color:var(--t1);font-family:inherit;font-size:15px}
.row{display:flex;gap:10px}.row>div{flex:1}
.btn{width:100%;padding:14px;border:0;border-radius:13px;background:linear-gradient(180deg,var(--oro-chiaro),var(--oro));
color:#2a1c05;font-family:'Barlow Semi Condensed';font-weight:800;font-size:17px;cursor:pointer;margin-top:6px}
.btn:hover{filter:brightness(1.06)}

/* --- PALCO --- */
.stage{flex:1;display:flex;align-items:center;justify-content:center;padding:30px;position:relative}
.view{display:none;flex-direction:column;align-items:center;gap:26px;text-align:center}
.view.on{display:flex}
.hint{color:var(--t3);font-size:15px;max-width:420px;line-height:1.5}
.hint h2{font-family:'Barlow Semi Condensed';font-weight:800;font-size:26px;color:var(--t1);margin-bottom:8px}
/* orbita */
.orbit{width:120px;height:120px;position:relative}
.orbit .ring{position:absolute;inset:0;border-radius:50%;border:1px solid var(--bordo-forte)}
.orbit .ring.b{inset:22px;border-color:rgba(228,172,74,.25)}
.orbit .core{position:absolute;inset:46px;border-radius:50%;background:var(--oro);
box-shadow:0 0 22px rgba(228,172,74,.7)}
.orbit .sat{position:absolute;top:50%;left:50%;width:10px;height:10px;margin:-5px;border-radius:50%;
background:var(--neon);animation:spin 3.4s linear infinite;transform-origin:0 0}
.orbit .sat.two{background:var(--oro-chiaro);animation-duration:2.1s}
@keyframes spin{from{transform:rotate(0) translateX(58px)}to{transform:rotate(360deg) translateX(58px)}}
/* fasi */
.phases{display:flex;flex-direction:column;gap:2px;width:330px;text-align:left}
.phase{display:flex;align-items:center;gap:14px;padding:11px 4px}
.phase .dot{width:26px;height:26px;flex:0 0 26px;border-radius:50%;display:flex;align-items:center;
justify-content:center;border:1.6px solid var(--bordo-forte);background:var(--superficie);
font-family:'Barlow Semi Condensed';font-weight:800;font-size:13px;color:var(--t4)}
.phase .nm{font-size:15.5px;color:var(--t4)}
.phase.active .dot{border-color:var(--oro);background:rgba(228,172,74,.1);
box-shadow:0 0 0 4px rgba(228,172,74,.1);color:transparent}
.phase.active .dot::after{content:"";width:15px;height:15px;border-radius:50%;
border:2px solid rgba(228,172,74,.25);border-top-color:var(--oro);animation:sp .7s linear infinite}
@keyframes sp{to{transform:rotate(360deg)}}
.phase.active .nm{color:var(--t1);font-weight:600}
.phase.done .dot{background:var(--oro);border-color:var(--oro);color:#05070f}
.phase.done .dot::before{content:"✓"}
.phase.done .nm{color:var(--t2)}
.preview img{max-width:min(72vh,640px);max-height:74vh;border-radius:14px;border:1px solid var(--bordo);
box-shadow:0 18px 50px rgba(0,0,0,.5)}
.errbox{max-width:440px;background:rgba(240,138,106,.08);border:1px solid rgba(240,138,106,.4);
border-radius:14px;padding:22px;color:var(--danger);font-size:15px;line-height:1.5}
.errbox h2{font-family:'Barlow Semi Condensed';font-weight:800;font-size:20px;margin-bottom:8px;color:#f5a98d}
</style></head>
<body>
<div class="titlebar"><span class="dot" style="background:#f0605c"></span>
<span class="dot" style="background:#f0b64a"></span><span class="dot" style="background:#5cd07a"></span>
&nbsp;Cielo del Mese — Gruppo Astrofili Vicentini</div>
<div class="app">

  <nav>
    <div class="nav-brand"><img src="/assets/logo-emblema.png" alt="GAV">
      <div><div class="g">GAV</div><div class="s">Astrofili Vicentini</div></div></div>
    <div class="nav-cap">Strumenti</div>
    <a class="nav-item on" aria-current="page">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7">
        <circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c3 3 3 15 0 18M12 3c-3 3-3 15 0 18"/></svg>
      <span class="nm">Cielo del Mese</span></a>
    <div class="nav-item soon" aria-disabled="true" title="Prossimamente">
      <span class="ic"><svg viewBox="0 0 24 24" fill="none" stroke="var(--t2)" stroke-width="1.7">
        <path d="M12 3v3M12 18v3M3 12h3M18 12h3M6 6l2 2M16 16l2 2M18 6l-2 2M8 16l-2 2"/>
        <circle cx="12" cy="12" r="3"/></svg></span>
      <div><span class="nm">Pillole di astronomia</span><div class="badge">Prossimamente</div></div></div>
    <div class="nav-foot">Altri strumenti arriveranno qui.</div>
  </nav>

  <div class="panel">
    <h1>Cielo del Mese</h1>
    <div class="sub">Il poster del cielo notturno, mese per mese.</div>
    <div class="grp"><label>Quando</label>
      <div class="row"><div><select id="month"><!--MESI--></select></div>
        <div><input id="year" value="2026" inputmode="numeric"></div>
        <div><input id="hour" value="23" inputmode="numeric" title="ora"></div></div></div>
    <div class="grp"><label>Dove</label>
      <input id="place" value="Vicenza" style="margin-bottom:10px">
      <div class="row"><div><input id="lat" value="45.5455" title="latitudine"></div>
        <div><input id="lon" value="11.5353" title="longitudine"></div></div></div>
    <div class="grp"><label>Formato</label><select id="fmt"><!--FORMATI--></select></div>
    <div class="grp"><label>Palette</label><select id="theme"><!--PALETTE--></select></div>
    <button class="btn" id="go">Genera anteprima</button>
  </div>

  <div class="stage">
    <div class="view on" id="v-initial">
      <div class="orbit"><div class="ring"></div><div class="ring b"></div><div class="core"></div>
        <div class="sat"></div><div class="sat two"></div></div>
      <div class="hint"><h2>Pronto a disegnare il cielo</h2>
        Scegli quando, dove e con quale palette, poi premi <b>Genera anteprima</b>.</div>
    </div>
    <div class="view" id="v-generating">
      <div class="orbit"><div class="ring"></div><div class="ring b"></div><div class="core"></div>
        <div class="sat"></div><div class="sat two"></div></div>
      <div class="hint"><h2>Sto disegnando il cielo…</h2></div>
      <div class="phases" id="phases">
        <div class="phase" data-i="0"><div class="dot">1</div><div class="nm">Calcolo dove sono stasera i pianeti e la Luna</div></div>
        <div class="phase" data-i="1"><div class="dot">2</div><div class="nm">Metto cinquemila stelle sulla mappa</div></div>
        <div class="phase" data-i="2"><div class="dot">3</div><div class="nm">Compongo il poster</div></div>
        <div class="phase" data-i="3"><div class="dot">4</div><div class="nm">Disegno l'immagine finale</div></div>
      </div>
    </div>
    <div class="view preview" id="v-preview"><img id="pv" alt="anteprima del poster"></div>
    <div class="view" id="v-error"><div class="errbox"><h2>Non riesco a generare</h2>
      <span id="errmsg"></span></div></div>
  </div>
</div>

<script>
const $=s=>document.querySelector(s);
function show(id){document.querySelectorAll('.view').forEach(v=>v.classList.remove('on'));$('#'+id).classList.add('on');}
function setPhase(i){document.querySelectorAll('#phases .phase').forEach(p=>{
  const n=+p.dataset.i;p.classList.toggle('done',n<i);p.classList.toggle('active',n===i);
  if(n>=i){const d=p.querySelector('.dot');if(!p.classList.contains('done'))d.textContent=p.classList.contains('active')?'':(n+1);}});}
function allDone(){document.querySelectorAll('#phases .phase').forEach(p=>{p.classList.remove('active');p.classList.add('done');});}
$('#go').addEventListener('click',()=>{
  const p=new URLSearchParams({year:$('#year').value,month:$('#month').value,hour:$('#hour').value,
    place:$('#place').value,lat:$('#lat').value,lon:$('#lon').value,theme:$('#theme').value,formato:$('#fmt').value});
  show('v-generating');setPhase(0);
  const es=new EventSource('/genera?'+p.toString());
  es.addEventListener('fase',e=>setPhase(+e.data));
  es.addEventListener('fatto',e=>{allDone();setTimeout(()=>{$('#pv').src='/anteprima?token='+e.data+'&_='+Date.now();show('v-preview');},420);es.close();});
  es.addEventListener('errore',e=>{$('#errmsg').textContent=e.data;show('v-error');es.close();});
  es.onerror=()=>{$('#errmsg').textContent='Connessione al motore interrotta.';show('v-error');es.close();};
});
</script>
</body></html>"""
