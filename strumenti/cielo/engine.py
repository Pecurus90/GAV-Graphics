#!/usr/bin/env python3
"""
Cielo del Mese - motore di generazione.
Genera un volantino SVG del cielo notturno per un dato mese/anno/localita,
con fasi lunari e pianeti calcolati dinamicamente. Colori da file di tema.

Uso:
  python engine/generate.py --year 2026 --month 8 \
      --lat 45.5455 --lon 11.5353 --place Vicenza \
      --theme themes/osservatorio.json --out cielo.svg

Nota onesta: la classificazione di visibilita dei pianeti (ok/telescopico/
difficile/non osservabile) e un'euristica ragionevole ma semplificata; per un
uso "serio" andrebbe rifinita (vedi README).
"""
import os, json, calendar
from datetime import datetime
import numpy as np
import pytz
from skyfield_data import get_skyfield_data_path
from skyfield.api import Loader, wgs84
from skyfield import almanac

from compose.compositor import Compositor
from .messier import MessierMixin
from .panels import PanelsMixin
from .disc import DiscMixin
from .catalog import (MONTHS_IT, DIREZIONI_IT, CONST_IT, MARQUEE, STARS, PLANETS,
                      PLANET_SHAPES, CX, CY, R, MoonPhase, MoonDay, Planet,
                      SkyData, hex2rgb, rgb2hex, bv2hex, point_in_poly)

# file di layout di default: la composizione A4 come dati (D7)
# radice del progetto: <root>/strumenti/cielo/engine.py -> tre dirname.
_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_LAYOUT = os.path.join(_BASE, "brand", "layouts", "a4.json")


class Engine(Compositor, MessierMixin, PanelsMixin, DiscMixin):
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

    # ---- geometry ----
    def altaz(self, ra_deg, dec_deg, lst_hours, lat_rad):
        ra=np.radians(np.asarray(ra_deg)%360.0); dec=np.radians(np.asarray(dec_deg))
        ha=np.radians((lst_hours*15.0)-np.degrees(ra))
        sinalt=np.sin(dec)*np.sin(lat_rad)+np.cos(dec)*np.cos(lat_rad)*np.cos(ha)
        alt=np.arcsin(np.clip(sinalt,-1,1))
        cosA=(np.sin(dec)-np.sin(alt)*np.sin(lat_rad))/(np.cos(alt)*np.cos(lat_rad)+1e-9)
        A=np.arccos(np.clip(cosA,-1,1)); A=np.where(np.sin(ha)>0,2*np.pi-A,A)
        return np.degrees(alt), np.degrees(A)

    def project(self, alt, az, cx=CX, cy=CY, rad=R):
        """Proiezione azimutale equidistante su un disco di centro (cx,cy) e
        raggio rad. Parametrica: lo stesso disco si disegna a qualsiasi misura."""
        r=rad*(90.0-alt)/90.0; a=np.radians(az)
        return cx-r*np.sin(a), cy-r*np.cos(a)

    def sky_context(self, year, month, lat, lon, hour_local=23, tzname='Europe/Rome'):
        """Calcola il tempo siderale locale e la latitudine (radianti) per una
        data/localita. E' tutto cio' che serve al disco cielo; restituisce anche
        il fuso per i pannelli."""
        tz=pytz.timezone(tzname)
        t=self.ts.from_datetime(tz.localize(datetime(year,month,15,hour_local,0)))
        lst=(t.gast+lon/15.0)%24.0
        return lst, np.radians(lat), tz

    # ---- ephemeris ----
    def moon_phases(self, year, month, tz):
        t0=self.ts.utc(year,month,1); nm=calendar.monthrange(year,month)[1]
        t1=self.ts.utc(year,month,nm,23,59)
        tt,yy=almanac.find_discrete(t0,t1,almanac.moon_phases(self.eph))
        names=['Luna Nuova','Primo Quarto','Luna Piena','Ultimo Quarto']
        keys=['new','first','full','last']
        out=[]
        for t,y in zip(tt,yy):
            loc=t.astimezone(tz)
            out.append((names[y],keys[y],loc.strftime('%d/%m')))
        return out

    def moon_days(self, year, month, tz, hour_local=23):
        """Illuminazione della Luna giorno per giorno, per i giorni VERI del mese
        (28-31). Per ogni giorno: frazione illuminata (0..1), se è crescente o
        calante, e se una fase principale cade quel giorno.

        Ora di riferimento: la STESSA del volantino (hour_local locale, di default
        le 23:00 Europe/Rome). Motivo: il volantino è già costruito per l'osservatore
        della sera a quell'ora (il disco cielo usa lo stesso istante); tenere UN
        solo riferimento evita un secondo orologio nel motore e mostra la Luna
        "com'è stasera". L'istante è fisso e derivato dagli argomenti: nessun
        orologio di sistema (invariante #6). La differenza rispetto a mezzogiorno
        UTC è astronomicamente trascurabile (l'illuminazione varia <~1% in un
        giorno vicino ai quarti).

        Crescente/calante dalla differenza di longitudine eclittica Luna-Sole
        (dlon in (0,180) = crescente): è la stessa grandezza che distingue primo
        e ultimo quarto in moon_phases, quindi coerente per costruzione."""
        nm=calendar.monthrange(year,month)[1]
        # giorno -> chiave della fase principale che ci cade (incrocio con moon_phases,
        # unica fonte di verità sulle date delle fasi: calendario e pannello concordano)
        phase_day={int(dt.split('/')[0]):key for _nm,key,dt in self.moon_phases(year,month,tz)}
        earth=self.eph['earth']; sun=self.eph['sun']; moon=self.eph['moon']
        out=[]
        for d in range(1,nm+1):
            t=self.ts.from_datetime(tz.localize(datetime(year,month,d,hour_local,0)))
            frac=float(almanac.fraction_illuminated(self.eph,'moon',t))
            e=earth.at(t)
            slon=e.observe(sun).apparent().ecliptic_latlon()[1].degrees
            mlon=e.observe(moon).apparent().ecliptic_latlon()[1].degrees
            waxing=bool(((mlon-slon)%360.0)<180.0)
            out.append((d,frac,waxing,phase_day.get(d)))
        return out

    def _rise_set(self, target, loc, tz, year, month, day):
        start=tz.localize(datetime(year,month,day,0,0))
        end=tz.localize(datetime(year,month,day,23,59))
        t0=self.ts.from_datetime(start); t1=self.ts.from_datetime(end)
        f=almanac.risings_and_settings(self.eph,target,loc)
        t,ev=almanac.find_discrete(t0,t1,f)
        rise=set_=None
        for ti,e in zip(t,ev):
            s=ti.astimezone(tz).strftime('%H:%M')
            if e==1 and rise is None: rise=s
            if e==0 and set_ is None: set_=s
        return rise, set_

    def planet_table(self, year, month, tz, loc):
        day=15
        earth=self.eph['earth']; sun=self.eph['sun']
        # sample night altitudes (local dark hours, summer & winter safe-ish)
        hours=[21,22,23,0,1,2,3,4]
        rows=[]
        for label,key in PLANETS.items():
            tgt=self.eph[key]
            rise,set_=self._rise_set(tgt,loc,tz,year,month,day)
            # elongation from sun at local midnight
            tmid=self.ts.from_datetime(tz.localize(datetime(year,month,day,0,0)))
            app_s=(earth+loc).at(tmid).observe(sun).apparent()
            app_p=(earth+loc).at(tmid).observe(tgt).apparent()
            elong=app_s.separation_from(app_p).degrees
            # best night altitude and when (+ azimut a quell'istante)
            best_alt=-90; best_h=None; best_az=0.0
            for h in hours:
                dd=day+(1 if h<12 else 0)
                tt=self.ts.from_datetime(tz.localize(datetime(year,month,dd,h,0)))
                aa=(earth+loc).at(tt).observe(tgt).apparent().altaz()
                if aa[0].degrees>best_alt: best_alt=aa[0].degrees; best_h=h; best_az=aa[1].degrees
            # classify
            if elong<15:
                status='muted'; note='Non osservabile, vicino al Sole'
            elif label in ('Urano','Nettuno'):
                status='info'; note=f'Telescopico, {"serale" if best_h in (21,22,23) else "a fine notte"}'
            elif best_alt<8:
                status='warn'; note='Difficile, molto basso'
            else:
                status='ok'
                when=('serale' if best_h in (21,22) else
                      'a inizio notte' if best_h==23 else
                      'a notte fonda' if best_h in (0,1,2) else 'verso l\'alba')
                note=f'Visibile {when}'
            direction=self._planet_direction(best_az, best_alt, status)
            shape=PLANET_SHAPES.get(label, "plain")
            rows.append((label,rise or '--',set_ or '--',note,status,best_az,direction,shape))
        # ordine: osservabili prima
        order={'ok':0,'info':1,'warn':2,'muted':3}
        rows.sort(key=lambda r:order[r[4]])
        return rows

    @staticmethod
    def _planet_direction(az, alt, status):
        """Direzione cardinale (8 settori, italiano) verso cui guardare quando il
        pianeta e' MEGLIO PIAZZATO, cioe' alla massima altezza della notte: e' il
        compagno naturale del best_alt gia' calcolato per la visibilita', e da'
        la direzione "dove punto lo sguardo quando conviene". Qualificatore
        'basso' sotto 20 gradi (sotto questa quota estinzione e ostacoli
        all'orizzonte pesano). Niente direzione (stringa vuota) se il pianeta e'
        non osservabile (muted) O se non sale sopra l'orizzonte quella notte
        (best_alt <= 0): indicare 'basso a Est' di un pianeta che non sorge
        manderebbe l'osservatore a cercare il nulla."""
        if status=='muted' or alt<=0.0:
            return ''
        settore=DIREZIONI_IT[round(az/45.0)%8]
        return f'basso a {settore}' if alt<20.0 else f'a {settore}'

    # ---- dati (contenuto, separato dal disegno) ----
    def sky_data(self, year, month, lat, lon, place,
                 hour_local=23, tzname='Europe/Rome'):
        """Calcola i DATI del volantino (fasi lunari, pianeti, data, località)
        come struttura esplicita, separata dal disegno. È l'interfaccia che il
        compositore A4 — e i futuri file di layout (D7) — riempiono."""
        _, _, tz = self.sky_context(year,month,lat,lon,hour_local,tzname)
        loc=wgs84.latlon(lat,lon,elevation_m=50)
        phases=[MoonPhase(nm,ph,dt)
                for nm,ph,dt in self.moon_phases(year,month,tz)]
        days=[MoonDay(d,frac,wax,pk)
              for d,frac,wax,pk in self.moon_days(year,month,tz,hour_local)]
        planets=[Planet(nm,rise,set_,note,st,az,dirn,shp)
                 for nm,rise,set_,note,st,az,dirn,shp in self.planet_table(year,month,tz,loc)]
        return SkyData(year=year, month=month, place=place, lat=lat, lon=lon,
                       hour_local=hour_local, moon_phases=phases, moon_days=days,
                       planets=planets)

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
