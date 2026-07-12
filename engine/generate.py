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
from dataclasses import dataclass
from datetime import datetime
import numpy as np
import pytz
from skyfield_data import get_skyfield_data_path
from skyfield.api import Loader, wgs84
from skyfield import almanac

MONTHS_IT = ["", "gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno",
             "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"]

# rosa a 8 settori in italiano (azimut 0=Nord, 90=Est, orario): indice = round(az/45)%8
DIREZIONI_IT = ["Nord", "Nord-Est", "Est", "Sud-Est", "Sud", "Sud-Ovest", "Ovest", "Nord-Ovest"]

# nomi italiani costellazioni principali da etichettare
CONST_IT = {'Aql':'Aquila','Boo':'Boote','CrB':'Corona Boreale','Cas':'Cassiopea',
 'Cep':'Cefeo','Cyg':'Cigno','Del':'Delfino','Dra':'Dragone','Her':'Ercole',
 'Lyr':'Lira','Oph':'Ofiuco','Peg':'Pegaso','Sgr':'Sagittario','Sco':'Scorpione',
 'Ser':'Serpente','UMa':'Orsa Maggiore','UMi':'Orsa Minore','Vir':'Vergine',
 'Lib':'Bilancia','Cap':'Capricorno','And':'Andromeda','Aqr':'Acquario',
 'CVn':'Cani da Caccia','Ori':'Orione','Tau':'Toro','Gem':'Gemelli','Leo':'Leone',
 'Cnc':'Cancro','Per':'Perseo','Aur':'Auriga','CMi':'Cane Minore','CMa':'Cane Maggiore',
 'Cet':'Balena','Psc':'Pesci','Ari':'Ariete'}

# stelle guida: nome, RA(deg), Dec(deg), B-V (per colore reale dal tema)
MARQUEE = [("Vega",279.234,38.784,0.00),("Deneb",310.358,45.280,0.09),
 ("Altair",297.696,8.868,0.22),("Arturo",213.915,19.182,1.23),
 ("Antares",247.352,-26.432,1.83),("Spica",201.298,-11.161,-0.23),
 ("Capella",79.172,45.998,0.80),("Rigel",78.634,-8.202,-0.03),
 ("Betelgeuse",88.793,7.407,1.85),("Aldebaran",68.980,16.509,1.54),
 ("Pollux",116.329,28.026,1.00),("Regolo",152.093,11.967,-0.09),
 ("Deneb Kaitos",10.897,-17.987,1.02),("Fomalhaut",344.413,-29.622,0.14)]

# pianeti: etichetta -> chiave ephemeris
PLANETS = {"Mercurio":"mercury","Venere":"venus","Marte":"mars",
 "Giove":"jupiter barycenter","Saturno":"saturn barycenter",
 "Urano":"uranus barycenter","Nettuno":"neptune barycenter"}

# disco A4 di riferimento (centro/raggio): default geometrici di project()/
# sky_disc_svg. Il canvas della pagina vive ora nel file di layout (D7).
CX, CY, R = 450.0, 500.0, 384.0

# file di layout di default: la composizione A4 come dati (D7)
_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_LAYOUT = os.path.join(_BASE, "brand", "layouts", "a4.json")


# ---------------------------------------------------------------------------
# Contratto dei DATI (D7): tutto ciò che nel volantino finisce come TESTO/contenuto,
# separato dal disegno. È l'interfaccia che il compositore A4 e i futuri file di
# layout riempiono. NON contiene geometria del disco (lst, lat_rad): quella vive
# nel frammento SVG sigillato, prodotto a parte da sky_disc_svg.
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class MoonPhase:
    """Una fase lunare del mese. `key` ('new'|'first'|'full'|'last') pilota la
    forma del disco disegnato; `label`/`date` sono il testo mostrato."""
    label: str    # es. 'Luna Piena'
    key: str      # 'new'|'first'|'full'|'last'
    date: str     # data locale, formato '%d/%m'


@dataclass(frozen=True)
class MoonDay:
    """L'illuminazione della Luna in UN giorno del mese, all'ora di riferimento
    del volantino (istante fisso e deterministico, invariante #6). Alimenta il
    calendario lunare a 28-31 dischetti."""
    day: int              # numero del giorno (1..28-31)
    frac: float           # frazione illuminata del disco, 0..1
    waxing: bool          # True = crescente (falce a destra), False = calante
    phase_key: str | None # 'new'|'first'|'full'|'last' se una fase PRINCIPALE
                          # cade quel giorno (incrocio con moon_phases), altrimenti None


@dataclass(frozen=True)
class Planet:
    """Un pianeta con la sua visibilità. `status` ('ok'|'info'|'warn'|'muted')
    pilota il colore del pallino; il resto è testo."""
    name: str     # es. 'Venere'
    rise: str     # alzata '%H:%M' o '--'
    set_: str     # tramonto '%H:%M' o '--'
    note: str     # nota testuale di visibilità (NON toccare: la legge l'A4)
    status: str   # 'ok'|'info'|'warn'|'muted'
    az: float     # azimut (gradi, 0=Nord, 90=Est) all'istante di massima altezza
    direction: str  # direzione dove guardare, es. 'a Sud-Est' / 'basso a Est' /
                  # '' se non osservabile. Campo NUOVO: l'A4 non lo usa.


@dataclass(frozen=True)
class SkyData:
    """I dati di contenuto del volantino, distinti dal disegno (D7)."""
    year: int
    month: int
    place: str
    lat: float
    lon: float
    hour_local: int
    moon_phases: list[MoonPhase]
    moon_days: list[MoonDay]
    planets: list[Planet]


def hex2rgb(h): return tuple(int(h[i:i+2],16) for i in (1,3,5))
def rgb2hex(r): return '#%02x%02x%02x'%tuple(round(max(0,min(255,x))) for x in r)

def bv2hex(ramp, bv):
    xs=[p[0] for p in ramp]; bv=max(xs[0],min(xs[-1],bv))
    for i in range(len(ramp)-1):
        if ramp[i][0]<=bv<=ramp[i+1][0]:
            f=(bv-ramp[i][0])/(ramp[i+1][0]-ramp[i][0])
            a=hex2rgb(ramp[i][1]); b=hex2rgb(ramp[i+1][1])
            return rgb2hex([a[k]+f*(b[k]-a[k]) for k in range(3)])
    return ramp[-1][1]


class Engine:
    def __init__(self, datadir="data"):
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
            rows.append((label,rise or '--',set_ or '--',note,status,best_az,direction))
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

    # ---- render: componenti riutilizzabili ----
    @staticmethod
    def defs_svg(theme):
        """Gradienti e filtri (glow) condivisi. Vanno messi una volta per SVG."""
        return f'''<defs>
<radialGradient id="bg" cx="50%" cy="38%" r="75%"><stop offset="0%" stop-color="{theme['bg'][0]}"/><stop offset="55%" stop-color="{theme['bg'][1]}"/><stop offset="100%" stop-color="{theme['bg'][2]}"/></radialGradient>
<radialGradient id="disk" cx="50%" cy="46%" r="55%"><stop offset="0%" stop-color="{theme['disk'][0]}"/><stop offset="80%" stop-color="{theme['disk'][1]}"/><stop offset="100%" stop-color="{theme['disk'][2]}"/></radialGradient>
<filter id="glow" x="-60%" y="-60%" width="220%" height="220%"><feGaussianBlur stdDeviation="2.2" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
<filter id="softglow" x="-80%" y="-80%" width="260%" height="260%"><feGaussianBlur stdDeviation="3.4"/></filter>
</defs>'''

    def sky_disc_svg(self, cx, cy, rad, lst, lat_rad, theme, ramp=None,
                     cardinals=True, labels=True, marquee=True, clip_id='dclip'):
        """Disegna SOLO il disco cielo (cornice + stelle + costellazioni) di
        centro (cx,cy) e raggio rad, a QUALSIASI misura. Restituisce il
        frammento SVG (stringa). Le costanti visive scalano con k=rad/R, quindi
        a rad=384 (A4) l'output e' identico a prima. Richiede defs_svg() nel
        documento. Non disegna sfondo pagina, testata o pannelli: quelli sono
        compito del layout/template."""
        if ramp is None: ramp=theme['star_ramp']
        k=rad/R  # fattore di scala rispetto al disco A4 di riferimento
        s=[]; a=s.append
        # cornice del disco
        a(f'<circle cx="{cx}" cy="{cy}" r="{rad}" fill="url(#disk)" stroke="{theme["border"]}" stroke-width="{1.5*k:.2f}"/>')
        a(f'<circle cx="{cx}" cy="{cy}" r="{rad}" fill="none" stroke="{theme["neon"]}" stroke-width="{2.4*k:.2f}" opacity="0.55" filter="url(#softglow)"/>')
        for ar in (30,60):
            rr=rad*(90-ar)/90
            a(f'<circle cx="{cx}" cy="{cy}" r="{rr:.1f}" fill="none" stroke="{theme["grid"]}" stroke-width="{0.8*k:.2f}" stroke-dasharray="{2*k:.1f} {5*k:.1f}" opacity="0.7"/>')
        a(f'<clipPath id="{clip_id}"><circle cx="{cx}" cy="{cy}" r="{rad-1}"/></clipPath>')
        a(f'<g clip-path="url(#{clip_id})">')
        # linee costellazioni
        a(f'<g filter="url(#glow)" stroke="{theme["neon"]}" stroke-width="{1.15*k:.2f}" fill="none" opacity="0.9" stroke-linecap="round">')
        for f in self.clines:
            for line in f['geometry']['coordinates']:
                arr=np.array(line); alt,az=self.altaz(arr[:,0],arr[:,1],lst,lat_rad)
                xs,ys=self.project(alt,az,cx,cy,rad)
                for i in range(len(arr)-1):
                    if alt[i]>0 and alt[i+1]>0:
                        a(f'<line x1="{xs[i]:.1f}" y1="{ys[i]:.1f}" x2="{xs[i+1]:.1f}" y2="{ys[i+1]:.1f}"/>')
        a('</g>')
        # stelle
        alt,az=self.altaz(self.sra,self.sdec,lst,lat_rad); xs,ys=self.project(alt,az,cx,cy,rad)
        for i in np.argsort(-self.smag):
            if alt[i]<=0 or self.smag[i]>5.25: continue
            sr=k*max(0.45,(5.35-self.smag[i])*0.92); col=bv2hex(ramp,self.sbv[i])
            if self.smag[i]<1.5:
                a(f'<circle cx="{xs[i]:.1f}" cy="{ys[i]:.1f}" r="{sr*2.2:.1f}" fill="{col}" opacity="0.22" filter="url(#softglow)"/>')
            a(f'<circle cx="{xs[i]:.1f}" cy="{ys[i]:.1f}" r="{sr:.2f}" fill="{col}"/>')
        a('</g>')
        # stelle guida (marquee)
        if marquee:
            for nm,ra,dec,bv in MARQUEE:
                al,zz=self.altaz(ra,dec,lst,lat_rad)
                if al<=2: continue
                x,y=self.project(al,zz,cx,cy,rad); col=bv2hex(ramp,bv)
                a(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{7*k:.1f}" fill="{col}" opacity="0.30" filter="url(#softglow)"/>')
                a(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{2.6*k:.1f}" fill="{col}"/>')
                a(f'<text x="{x+7*k:.1f}" y="{y-5*k:.1f}" fill="{theme["text"]}" font-size="{11.5*k:.1f}" opacity="0.95">{nm}</text>')
        # etichette costellazioni
        if labels:
            for f in self.clines:
                ab=f['id']
                if ab not in CONST_IT: continue
                allp=np.array([p for line in f['geometry']['coordinates'] for p in line])
                al,zz=self.altaz(allp[:,0],allp[:,1],lst,lat_rad); m=al>3
                if m.sum()<2: continue
                x,y=self.project(al[m],zz[m],cx,cy,rad)
                a(f'<text x="{x.mean():.1f}" y="{y.mean():.1f}" fill="{theme["label"]}" font-size="{12.5*k:.1f}" opacity="0.82" text-anchor="middle" letter-spacing="0.5">{CONST_IT[ab]}</text>')
        # punti cardinali
        if cardinals:
            for lab,ang in (('N',0),('E',90),('S',180),('O',270)):
                rr=rad+22*k; ax=cx-rr*np.sin(np.radians(ang)); ay=cy-rr*np.cos(np.radians(ang))
                a(f'<text x="{ax:.1f}" y="{ay+6*k:.1f}" fill="{theme["cardinal"]}" font-size="{19*k:.1f}" font-weight="bold" text-anchor="middle">{lab}</text>')
        return '\n'.join(s)

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
        planets=[Planet(nm,rise,set_,note,st,az,dirn)
                 for nm,rise,set_,note,st,az,dirn in self.planet_table(year,month,tz,loc)]
        return SkyData(year=year, month=month, place=place, lat=lat, lon=lon,
                       hour_local=hour_local, moon_phases=phases, moon_days=days,
                       planets=planets)

    # ---- compositore: primitive di blocco (leggono il layout, D7) ----
    def _render_disc(self, b, theme, lst, lat_rad):
        """Piazza il disco alla misura chiesta dal layout. La geometria e'
        sigillata in sky_disc_svg (gia' parametrica su cx/cy/rad). Il file puo'
        SPEGNERE strati che a ~300px sul telefono diventano rumore: etichette
        delle costellazioni (`labels`), stelle guida (`marquee`), cardinali
        (`cardinals`). Assenti -> tutti accesi, quindi l'A4 non cambia."""
        return self.sky_disc_svg(b["cx"], b["cy"], b["rad"], lst, lat_rad, theme,
                                 cardinals=b.get("cardinals", True),
                                 labels=b.get("labels", True),
                                 marquee=b.get("marquee", True))

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

    def _render_text(self, b, theme, ctx):
        """Primitiva testo. Ordine di attributi canonico (ricavato dall'A4):
        x, y, fill, font-size, [font-weight], [text-anchor], [letter-spacing].
        `content` e' un template riempito da `ctx` (o dai campi di un item)."""
        s=(f'<text x="{b["x"]}" y="{b["y"]}" fill="{theme[b["fill"]]}" '
           f'font-size="{b["size"]}"')
        if b.get("weight"): s+=f' font-weight="{b["weight"]}"'
        if b.get("anchor"): s+=f' text-anchor="{b["anchor"]}"'
        if "letter_spacing" in b: s+=f' letter-spacing="{b["letter_spacing"]}"'
        return s+f'>{b["content"].format(**ctx)}</text>'

    def _render_line(self, b, theme):
        s=(f'<line x1="{b["x1"]}" y1="{b["y1"]}" x2="{b["x2"]}" y2="{b["y2"]}" '
           f'stroke="{theme[b["stroke"]]}" stroke-width="{b["stroke_width"]}"')
        if b.get("filter"): s+=f' filter="url(#{b["filter"]})"'
        return s+'/>'

    def _render_panel(self, b, theme):
        """Pannello: rettangolo (arrotondato con `rx`) usato come CONTENITORE nei
        design social. Primitiva NUOVA in #6d: i tre mockup incorniciano pianeti,
        luna e colori in pannelli, e nessuna primitiva esistente disegna un
        riquadro. Fill e stroke sono TOKEN del tema (mai hex cablati)."""
        s=(f'<rect x="{b["x"]}" y="{b["y"]}" width="{b["w"]}" height="{b["h"]}" '
           f'rx="{b.get("rx",0)}" fill="{theme[b["fill"]]}"')
        if b.get("stroke"):
            s+=f' stroke="{theme[b["stroke"]]}" stroke-width="{b.get("stroke_width",1)}"'
        return s+'/>'

    def _render_planet_panel(self, b, theme, data):
        """Righe pianeti (ancora x0/y0 + passo step). Il pallino di stato e'
        l'unico fill guidato dal dato (fill_status). `statuses` (opzionale)
        filtra quali pianeti mostrare per stato: assente -> tutti (come A4)."""
        out=[]
        dot=b["dot"]
        keep=b.get("statuses")
        planets=data.planets if keep is None else [p for p in data.planets if p.status in keep]
        for i,pl in enumerate(planets):
            # note_dir: presentazione derivata = nota + direzione, con separatore
            # SOLO se la direzione c'e' (i muted/sotto-orizzonte non lasciano un
            # ' · ' penzolante). L'A4 usa {note}, non {note_dir}: resta identico.
            note_dir=pl.note+(" · "+pl.direction if pl.direction else "")
            item={"name":pl.name,"rise":pl.rise,"set":pl.set_,"note":pl.note,
                  "note_dir":note_dir,"status":pl.status,"direction":pl.direction,
                  "az":f"{pl.az:.0f}"}
            y=b["y0"]+i*b["step"]
            fill=theme["status"][pl.status] if dot.get("fill_status") else theme[dot["fill"]]
            out.append(f'<circle cx="{b["x0"]+dot["dx"]}" cy="{y+dot["dy"]}" r="{dot["r"]}" fill="{fill}"/>')
            for part in ("name","times","note"):
                if part not in b:  # un design puo' omettere una parte (es. rail
                    continue        # senza nota, editorial senza orari)
                p=b[part]
                tb={"x":b["x0"]+p["dx"],"y":y+p.get("dy",0),"fill":p["fill"],
                    "size":p["size"],"weight":p.get("weight"),"content":p["content"]}
                if p.get("anchor"): tb["anchor"]=p["anchor"]
                out.append(self._render_text(tb, theme, item))
        return '\n'.join(out)

    def _render_moon_panel(self, b, theme, data):
        """Dischi delle fasi (fila x0 + passo gap). La forma illuminata dipende
        da `key` (piena=cerchio, primo/ultimo=semicerchio ad arco): logica di
        disegno, resta qui."""
        out=[]
        x0,cy,gap,mr=b["x0"],b["cy"],b["gap"],b["radius"]
        base=b["base"]; lit=theme[b["lit_fill"]]
        for i,mp in enumerate(data.moon_phases[:4]):
            mx=x0+i*gap
            out.append(f'<circle cx="{mx}" cy="{cy}" r="{mr}" fill="{theme[base["fill"]]}" stroke="{theme[base["stroke"]]}" stroke-width="{base["stroke_width"]}"/>')
            if mp.key=='full':
                out.append(f'<circle cx="{mx}" cy="{cy}" r="{mr}" fill="{lit}"/>')
            elif mp.key=='first':
                out.append(f'<path d="M{mx},{cy-mr} A{mr},{mr} 0 0 1 {mx},{cy+mr} Z" fill="{lit}"/>')
            elif mp.key=='last':
                out.append(f'<path d="M{mx},{cy-mr} A{mr},{mr} 0 0 0 {mx},{cy+mr} Z" fill="{lit}"/>')
            for part in ("label","date"):
                p=b[part]
                tb={"x":mx,"y":cy+p["dy"],"fill":p["fill"],"size":p["size"],
                    "anchor":"middle","content":p["content"]}
                out.append(self._render_text(tb, theme, {"label":mp.label,"date":mp.date}))
        return '\n'.join(out)

    @staticmethod
    def _moon_shape_svg(cx, cy, r, frac, waxing, lit, base):
        """Forma CONTINUA della Luna a frazione illuminata `frac` (0..1), col
        metodo del terminatore-ellisse (lo stesso dei mockup del designer):
          - un SEMIDISCO sul lembo illuminato (crescente = destra, sweep 1;
            calante = sinistra, sweep 0);
          - un'ELLISSE il cui semiasse orizzontale rx = r·|1-2·frac| è il
            terminatore proiettato. Riempita `lit` se gibbosa (frac>0.5, aggiunge
            luce oltre il centro) o `base` se falce (frac<0.5, scava la luce).
        A frac=0.5 rx=0: resta il semidisco netto. A frac→0 l'ellisse scura
        copre tutto (novilunio); a frac→1 l'ellisse chiara riempie (plenilunio).

        NUOVO codice, di proposito NON condiviso con _render_moon_panel (che
        disegna le 4 fasi discrete con path ad arco): unificarli ora muoverebbe
        la stringa del golden. La duplicazione è voluta e temporanea — vedi report."""
        sweep=1 if waxing else 0
        half=(f'<path d="M{cx:.2f},{cy-r:.2f} A{r:.2f},{r:.2f} 0 0 {sweep} '
              f'{cx:.2f},{cy+r:.2f} Z" fill="{lit}"/>')
        rx=r*abs(1.0-2.0*frac)
        fill=lit if frac>0.5 else base
        ell=f'<ellipse cx="{cx:.2f}" cy="{cy:.2f}" rx="{rx:.2f}" ry="{r:.2f}" fill="{fill}"/>'
        return half+'\n'+ell

    def _render_moon_calendar(self, b, theme, data):
        """Calendario lunare: un dischetto per ogni giorno del mese, con la forma
        CONTINUA della fase reale. Il FILE possiede cosa/dove/quale-dato: griglia
        (`cols` = dischetti per riga), passi (`col_gap`/`row_gap`), raggio, se
        mostrare il numero del giorno (`day_number`), se evidenziare le fasi
        principali (`highlight`). Il CODICE possiede il "come disegnare" la forma.

        Regge sia una riga da 31 (cols=31) sia una griglia N×M (es. 4×8, cols=8)
        SENZA saperlo: la disposizione è tutta nel file, la primitiva calcola
        riga = i//cols, colonna = i%cols."""
        out=[]
        x0,y0,r,cols=b["x0"],b["y0"],b["radius"],b["cols"]
        cgap,rgap=b["col_gap"],b["row_gap"]
        base=b["base"]; basefill=theme[base["fill"]]; lit=theme[b["lit_fill"]]
        daynum=b.get("day_number"); hi=b.get("highlight")
        for i,md in enumerate(data.moon_days):
            cx=x0+(i%cols)*cgap; cy=y0+(i//cols)*rgap
            out.append(f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{r}" fill="{basefill}"/>')
            out.append(self._moon_shape_svg(cx,cy,r,md.frac,md.waxing,lit,basefill))
            out.append(f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{r}" fill="none" '
                       f'stroke="{theme[base["stroke"]]}" stroke-width="{base["stroke_width"]}"/>')
            if hi and md.phase_key:
                out.append(f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{r+hi["r_extra"]}" '
                           f'fill="none" stroke="{theme[hi["stroke"]]}" stroke-width="{hi["stroke_width"]}"/>')
            if daynum:
                fill=(daynum["fill_highlight"] if hi and md.phase_key and "fill_highlight" in daynum
                      else daynum["fill"])
                tb={"x":f"{cx:.2f}","y":f"{cy+daynum['dy']:.2f}","fill":fill,
                    "size":daynum["size"],"anchor":"middle","content":"{day}"}
                out.append(self._render_text(tb, theme, {"day":md.day}))
        # riga opzionale di etichette delle fasi principali (giorno + nome),
        # spaziate uniformemente sotto il calendario (dashboard/rail). Il file
        # da' posizione, passo e la mappa chiave->nome breve; il dato da' quali
        # giorni e in che ordine (i giorni con phase_key, gia' incrociati con
        # moon_phases).
        pl=b.get("phase_labels")
        if pl:
            names=pl["names"]
            for j,md in enumerate(m for m in data.moon_days if m.phase_key):
                tb={"x":pl["x0"]+j*pl["gap"],"y":pl["y"],"fill":pl["fill"],
                    "size":pl["size"],"weight":pl.get("weight"),"content":pl["content"]}
                out.append(self._render_text(tb, theme, {"day":md.day,"name":names[md.phase_key]}))
        return '\n'.join(out)

    def _swatch_label(self, spec, cx, cy, text, theme):
        """Un'etichetta di campione, con dx/dy dal centro del pallino; opzionali
        weight e anchor (i design social allineano a destra la temperatura)."""
        tb={"x":cx+spec["dx"],"y":cy+spec["dy"],"fill":spec["fill"],
            "size":spec["size"],"content":text}
        if spec.get("weight"): tb["weight"]=spec["weight"]
        if spec.get("anchor"): tb["anchor"]=spec["anchor"]
        return self._render_text(tb, theme, {})

    def _render_swatches(self, b, theme):
        """Campioni di colore della legenda. Il colore viene da bv2hex(ramp,bv):
        calcolo, resta qui; il file da' i bv, le etichette e le posizioni.
        Due disposizioni: FILA orizzontale storica (x0 + i*step, `cy` fisso; e'
        l'A4) oppure GRIGLIA se il blocco dichiara `cols` (x0/cy origine,
        `col_step`/`row_step`), come la legenda in colonna dei design social.
        `label2` (opzionale) e' una seconda etichetta per campione (es. la
        temperatura). Senza `cols` e senza `label2` -> identico all'A4."""
        ramp=theme["star_ramp"]; lab=b["label"]; lab2=b.get("label2")
        cols=b.get("cols")
        out=[]
        for i,it in enumerate(b["items"]):
            if cols:  # griglia (nuova): riga=i//cols, colonna=i%cols
                cx=b["x0"]+(i%cols)*b.get("col_step",0)
                cy=b["cy"]+(i//cols)*b.get("row_step",0)
            else:     # fila orizzontale (storica, A4): x0 + i*step, cy fisso
                cx=b["x0"]+i*b["step"]; cy=b["cy"]
            out.append(f'<circle cx="{cx}" cy="{cy}" r="{b["r"]}" fill="{bv2hex(ramp, it["bv"])}"/>')
            out.append(self._swatch_label(lab, cx, cy, it["label"], theme))
            if lab2 and "label2" in it:
                out.append(self._swatch_label(lab2, cx, cy, it["label2"], theme))
        return '\n'.join(out)

    def _render_background(self, b, theme, w, h):
        """Sfondo pagina + campo di micro-stelle. La sequenza pseudo-casuale
        (seed fisso) e' generazione procedurale: resta qui; il file da' i
        parametri (seed, conteggio, raggi, opacita', colore)."""
        sf=b["starfield"]; col=theme[sf["fill"]]
        out=[f'<rect width="{w}" height="{h}" fill="url(#bg)"/>']
        rng=np.random.default_rng(sf["seed"])
        for x,y in zip(rng.uniform(0,w,sf["count"]),rng.uniform(0,h,sf["count"])):
            out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{rng.uniform(sf["r_min"],sf["r_max"]):.2f}" fill="{col}" opacity="{rng.uniform(sf["op_min"],sf["op_max"]):.2f}"/>')
        return '\n'.join(out)

    def _render_block(self, b, theme, data, ctx, lst, lat_rad, w, h):
        """Dispatch di un blocco del layout sulla primitiva giusta."""
        t=b["type"]
        if t=="background":   return self._render_background(b, theme, w, h)
        if t=="disc":         return self._render_disc(b, theme, lst, lat_rad)
        if t=="text":         return self._render_text(b, theme, ctx)
        if t=="line":         return self._render_line(b, theme)
        if t=="panel":        return self._render_panel(b, theme)
        if t=="moon_panel":   return self._render_moon_panel(b, theme, data)
        if t=="moon_calendar":return self._render_moon_calendar(b, theme, data)
        if t=="planet_panel": return self._render_planet_panel(b, theme, data)
        if t=="swatches":     return self._render_swatches(b, theme)
        raise ValueError(f"tipo di blocco sconosciuto nel layout: {t!r}")

    # ---- render: volantino A4 (compositore magro: cammina i blocchi) ----
    def generate(self, year, month, lat, lon, place, theme, out,
                 hour_local=23, tzname='Europe/Rome', layout=None):
        if layout is None:
            with open(DEFAULT_LAYOUT, encoding='utf-8') as fh:
                layout=json.load(fh)
        lst, lat_rad, _ = self.sky_context(year,month,lat,lon,hour_local,tzname)
        data=self.sky_data(year,month,lat,lon,place,hour_local,tzname)
        ctx=self._render_ctx(data)
        cv=layout['canvas']; cw,ch=cv['w'],cv['h']
        s=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{cw}" height="{ch}" viewBox="0 0 {cw} {ch}" font-family="{cv["font_family"]}">',
           self.defs_svg(theme)]
        for b in layout['blocks']:
            s.append(self._render_block(b, theme, data, ctx, lst, lat_rad, cw, ch))
        s.append('</svg>')
        with open(out,'w',encoding='utf-8') as fh:
            fh.write('\n'.join(s))
        return out
