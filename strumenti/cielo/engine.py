#!/usr/bin/env python3
"""
Cielo del Mese - il MOTORE, come ASSEMBLAGGIO (taglio D14, giro #7e).

La classe Engine non contiene piu' quasi codice: e' il punto in cui i pezzi si
compongono. Eredita dalla base condivisa (compose/Compositor: il ciclo che
cammina i blocchi + le primitive generiche) e dai mixin SOLO-cielo, ognuno nel
suo file:
  - EphemerisMixin (ephemeris.py) : effemeridi, proiezione, SkyData
  - DiscMixin      (disc.py)      : il disco sigillato
  - PanelsMixin    (panels.py)    : pannelli luna/pianeti/colori
  - MessierMixin   (messier.py)   : il profondo cielo (pagina 2)
  - i dati e le funzioni pure stanno in catalog.py

Qui restano solo: __init__ (carica effemeridi e cataloghi), _render_ctx (i testi
derivati da SkyData), il dispatch dei tipi di blocco del cielo (_render_block_tool)
e generate() (prepara i dati del cielo, poi delega al compositore).

Re-esporta bv2hex/STARS/point_in_poly perche' engine/generate.py (il ponte) e i
test li trovino qui.
"""
import os, json
import numpy as np
from skyfield_data import get_skyfield_data_path
from skyfield.api import Loader

from compose.compositor import Compositor
from .messier import MessierMixin
from .panels import PanelsMixin
from .disc import DiscMixin
from .ephemeris import EphemerisMixin
from .catalog import MONTHS_IT, bv2hex, STARS, point_in_poly  # noqa: F401 (re-export)

# file di layout di default: la composizione A4 come dati (D7)
# radice del progetto: <root>/strumenti/cielo/engine.py -> tre dirname.
_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_LAYOUT = os.path.join(_BASE, "brand", "layouts", "a4.json")


class Engine(Compositor, MessierMixin, PanelsMixin, DiscMixin, EphemerisMixin):
    def __init__(self, datadir="data"):
        self.datadir = datadir
        load = Loader(get_skyfield_data_path())
        self.ts = load.timescale()
        self.eph = load('de421.bsp')
        self.stars = json.load(open(f"{datadir}/stars6.json"))['features']
        self.clines = json.load(open(f"{datadir}/const_lines.json"))['features']
        # pre-extract star arrays
        self.sra = np.array([s['geometry']['coordinates'][0] for s in self.stars])
        self.sdec = np.array([s['geometry']['coordinates'][1] for s in self.stars])
        self.smag = np.array([s['properties']['mag'] for s in self.stars])
        def _bv(s):
            try: return float(s['properties']['bv'])
            except: return 0.5
        self.sbv = np.array([_bv(s) for s in self.stars])

    def defs_svg(self, theme, extra_gradients=""):
        """Il Cielo del Mese aggiunge al <defs> di marca il gradiente del proprio
        DISCO (#7f, D13): compose/ non conosce piu' il token 'disk'. L'output
        e' identico a prima (disk fra bg e i glow)."""
        return super().defs_svg(theme, extra_gradients=self._disk_gradient(theme))

    @staticmethod
    def _render_ctx(data):
        """Presentazione DERIVATA da SkyData: stringhe pronte che i template del
        layout referenziano per nome. Qui vivono MONTHS_IT, il troncamento a 3
        lettere e il formato dei float (decisione #5b)."""
        return {"year": data.year,
                "month_name": MONTHS_IT[data.month],
                "month_upper": MONTHS_IT[data.month].upper(),
                "month_abbr": MONTHS_IT[data.month][:3],
                "place": data.place, "hour": data.hour_local,
                "lat1": f"{data.lat:.1f}", "lon1": f"{data.lon:.1f}"}

    def _render_block_tool(self, b, theme, ctx, w, h, tool_ctx):
        """I tipi di blocco SPECIFICI del Cielo del Mese (disco, luna, pianeti,
        campioni, Messier). Sovrascrive il hook di Compositor: i tipi generici li
        gestisce gia' la base. `tool_ctx` porta i dati che questi blocchi
        consumano (SkyData, tempo siderale/latitudine, contesto Messier)."""
        t=b["type"]
        data=tool_ctx["data"]; lst=tool_ctx["lst"]; lat_rad=tool_ctx["lat_rad"]; mctx=tool_ctx["mctx"]
        if t=="disc":         return self._render_disc(b, theme, lst, lat_rad)
        if t=="moon_panel":   return self._render_moon_panel(b, theme, data)
        if t=="moon_calendar":return self._render_moon_calendar(b, theme, data)
        if t=="planet_panel": return self._render_planet_panel(b, theme, data)
        if t=="swatches":     return self._render_swatches(b, theme)
        if t=="messier_symbols": return self._render_messier_symbols(b, theme, mctx)
        if t=="messier_table":   return self._render_messier_table(b, theme, mctx)
        if t=="messier_legend":  return self._render_messier_legend(b, theme)
        raise ValueError(f"tipo di blocco sconosciuto nel layout: {t!r}")

    # ---- render: volantino A4 (prepara i dati del cielo, poi compone) ----
    def generate(self, year, month, lat, lon, place, theme, out,
                 hour_local=23, tzname='Europe/Rome', layout=None):
        if layout is None:
            with open(DEFAULT_LAYOUT, encoding='utf-8') as fh:
                layout=json.load(fh)
        lst, lat_rad, _ = self.sky_context(year,month,lat,lon,hour_local,tzname)
        data=self.sky_data(year,month,lat,lon,place,hour_local,tzname)
        ctx=self._render_ctx(data)
        # Contesto Messier (D9): calcolato SOLO se il layout lo chiede (sezione
        # "messier" col disco e il N della tabella). Cosi' l'A4 non carica nulla.
        mctx=None
        if "messier" in layout:
            mc=layout["messier"]
            mctx=self.messier_context(lst, lat_rad, mc["cx"], mc["cy"], mc["rad"], mc["n"])
        return self._compose(layout, theme, ctx, out,
                             tool_ctx={"data":data, "lst":lst, "lat_rad":lat_rad, "mctx":mctx})
