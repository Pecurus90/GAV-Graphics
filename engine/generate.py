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

from compose.compositor import Compositor

MONTHS_IT = ["", "gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno",
             "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"]

# rosa a 8 settori in italiano (azimut 0=Nord, 90=Est, orario): indice = round(az/45)%8
DIREZIONI_IT = ["Nord", "Nord-Est", "Est", "Sud-Est", "Sud", "Sud-Ovest", "Ovest", "Nord-Ovest"]

# Nomi italiani delle costellazioni PRINCIPALI: sono quelle che l'A4/pagina 1
# etichetta sul disco. NON allargare questo dizionario: e' sorvegliato dai golden
# (l'A4 disegna un'etichetta per ogni voce sopra l'orizzonte). Le minori vivono in
# CONST_IT_MINORI, che solo la pagina 2 ("tutte") legge.
CONST_IT = {'Aql':'Aquila','Boo':'Boote','CrB':'Corona Boreale','Cas':'Cassiopea',
 'Cep':'Cefeo','Cyg':'Cigno','Del':'Delfino','Dra':'Dragone','Her':'Ercole',
 'Lyr':'Lira','Oph':'Ofiuco','Peg':'Pegaso','Sgr':'Sagittario','Sco':'Scorpione',
 'Ser':'Serpente','UMa':'Orsa Maggiore','UMi':'Orsa Minore','Vir':'Vergine',
 'Lib':'Bilancia','Cap':'Capricorno','And':'Andromeda','Aqr':'Acquario',
 'CVn':'Cani da Caccia','Ori':'Orione','Tau':'Toro','Gem':'Gemelli','Leo':'Leone',
 'Cnc':'Cancro','Per':'Perseo','Aur':'Auriga','CMi':'Cane Minore','CMa':'Cane Maggiore',
 'Cet':'Balena','Psc':'Pesci','Ari':'Ariete'}

# Le costellazioni MINORI: le 44 restanti, aggiunte in #7d-ter (approvate da
# Marco), cosi' la PAGINA 2 in modo "tutte" puo' nominare ogni figura sopra
# l'orizzonte. Tenute SEPARATE da CONST_IT apposta: l'A4 non deve cambiare (golden).
# FONTE dei nomi: Wikipedia in italiano, "Lista delle costellazioni"
# (https://it.wikipedia.org/wiki/Lista_delle_costellazioni), nomi UAI. Riportati
# come sulla pagina, con UNA eccezione VOLUTA: Norma -> "Squadra" (NON "Regolo":
# collide con la stella Regolo/Regulus, gia' in STARS). DATO curato: per cambiarne
# uno, si cambia una riga.
CONST_IT_MINORI = {
 'Ant':'Macchina Pneumatica','Aps':'Uccello del Paradiso','Ara':'Altare',
 'Cae':'Bulino','Cam':'Giraffa','Car':'Carena','Cen':'Centauro','Cha':'Camaleonte',
 'Cir':'Compasso','Col':'Colomba','CrA':'Corona Australe','Crt':'Cratere',
 'Cru':'Croce del Sud','Crv':'Corvo','Dor':'Dorado','Equ':'Cavallino',
 'Eri':'Eridano','For':'Fornace','Gru':'Gru','Hor':'Orologio','Hyi':'Idra Maschio',
 'Ind':'Indiano','LMi':'Leone Minore','Lac':'Lucertola','Lup':'Lupo','Lyn':'Lince',
 'Men':'Mensa','Mic':'Microscopio','Mus':'Mosca','Nor':'Squadra','Oct':'Ottante',
 'Pav':'Pavone','Phe':'Fenice','Pic':'Pittore','PsA':'Pesce Australe','Pyx':'Bussola',
 'Ret':'Reticolo','Scl':'Scultore','Sex':'Sestante','Tel':'Telescopio',
 'TrA':'Triangolo Australe','Tuc':'Tucano','Vel':'Vele','Vol':'Pesce Volante'}

# stelle guida: nome, RA(deg), Dec(deg), B-V (per colore reale dal tema)
MARQUEE = [("Vega",279.234,38.784,0.00),("Deneb",310.358,45.280,0.09),
 ("Altair",297.696,8.868,0.22),("Arturo",213.915,19.182,1.23),
 ("Antares",247.352,-26.432,1.83),("Spica",201.298,-11.161,-0.23),
 ("Capella",79.172,45.998,0.80),("Rigel",78.634,-8.202,-0.03),
 ("Betelgeuse",88.793,7.407,1.85),("Aldebaran",68.980,16.509,1.54),
 ("Pollux",116.329,28.026,1.00),("Regolo",152.093,11.967,-0.09),
 ("Deneb Kaitos",10.897,-17.987,1.02),("Fomalhaut",344.413,-29.622,0.14)]

# Catalogo delle stelle NOMINABILI (per il percorso social a etichette curate):
# nome -> (RA deg, Dec deg, B-V, magnitudine). Superset del MARQUEE con l'aggiunta
# di Sirio (la piu' brillante) e della Polare (fioca ma serve a orientarsi). La
# magnitudine pilota la PRIORITA' dell'anti-collisione (piu' brillante = prima).
# MARQUEE resta separato e intatto: e' cio' che l'A4 disegna di default.
STARS = {
 "Sirio":(101.287,-16.716,0.00,-1.46), "Arturo":(213.915,19.182,1.23,-0.05),
 "Vega":(279.234,38.784,0.00,0.03), "Capella":(79.172,45.998,0.80,0.08),
 "Rigel":(78.634,-8.202,-0.03,0.13), "Betelgeuse":(88.793,7.407,1.85,0.50),
 "Altair":(297.696,8.868,0.22,0.76), "Aldebaran":(68.980,16.509,1.54,0.85),
 "Spica":(201.298,-11.161,-0.23,0.97), "Antares":(247.352,-26.432,1.83,1.06),
 "Pollux":(116.329,28.026,1.00,1.14), "Fomalhaut":(344.413,-29.622,0.14,1.16),
 "Deneb":(310.358,45.280,0.09,1.25), "Regolo":(152.093,11.967,-0.09,1.35),
 "Castore":(113.649,31.888,0.03,1.58), "Deneb Kaitos":(10.897,-17.987,1.02,2.04),
 "Polare":(37.954,89.264,0.60,1.98),
 # Aggiunte #6m: stelle che un DIVULGATORE indica davvero (spesso non le piu'
 # brillanti), per dare un nome alle costellazioni della whitelist che ne erano
 # prive. Vedi report per la ragione di ciascuna.
 "Mizar":(200.981,54.921,0.06,2.04),          # Orsa Maggiore: la doppia a occhio nudo
 "Schedar":(10.127,56.537,1.17,2.24),         # Cassiopea: l'ancora della W
 "Thuban":(211.097,64.376,-0.05,3.65),        # Dragone: la Polare dei faraoni
 "Alphecca":(233.672,26.715,-0.02,2.22),      # Corona Boreale: il gioiello
 "Kaus Australis":(276.043,-34.385,-0.03,1.85), # Sagittario: l'ancora della teiera
 "Mirach":(17.433,35.621,1.58,2.05),          # Andromeda: il salto verso M31
 "Algol":(47.042,40.956,-0.05,2.12),          # Perseo: la stella-demone variabile
 "Enif":(326.046,9.875,1.53,2.40),            # Pegaso: il naso, indica M15
}

# pianeti: etichetta -> chiave ephemeris
PLANETS = {"Mercurio":"mercury","Venere":"venus","Marte":"mars",
 "Giove":"jupiter barycenter","Saturno":"saturn barycenter",
 "Urano":"uranus barycenter","Nettuno":"neptune barycenter"}

# Sagoma riconoscibile del pianeta (metadato ASTRONOMICO, come la chiave di
# effemeride qui sopra): il DATO la porta con se', il disegno la sceglie per
# TOKEN ('ringed'), mai con un if sul nome. Assenti = 'plain'. Domani Giove puo'
# diventare 'banded' aggiungendo qui la voce + un ramo di disegno per quel token.
PLANET_SHAPES = {"Saturno": "ringed"}

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
    shape: str    # sagoma del pianeta ('plain' | 'ringed'): il DATO porta con se'
                  # la forma, cosi' il disegno la sceglie senza un if sul nome.


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


def convex_hull(points):
    """Inviluppo convesso (monotone chain di Andrew) di una lista di punti (x,y).
    Serve a definire la REGIONE di una costellazione: il nome di una costellazione
    non deve MAI cadere dentro la regione di un'ALTRA (#7d-ter). Restituisce i
    vertici dell'inviluppo in senso orario; <3 punti -> i punti stessi."""
    pts=sorted(set((float(x),float(y)) for x,y in points))
    if len(pts)<3: return pts
    def cross(o,a,b): return (a[0]-o[0])*(b[1]-o[1])-(a[1]-o[1])*(b[0]-o[0])
    lower=[]
    for p in pts:
        while len(lower)>=2 and cross(lower[-2],lower[-1],p)<=0: lower.pop()
        lower.append(p)
    upper=[]
    for p in reversed(pts):
        while len(upper)>=2 and cross(upper[-2],upper[-1],p)<=0: upper.pop()
        upper.append(p)
    return lower[:-1]+upper[:-1]


def point_in_poly(poly, x, y):
    """True se il punto (x,y) e' dentro il poligono `poly` (ray casting). Bordo
    contato come fuori e' sufficiente per il nostro uso (regioni, non pixel)."""
    n=len(poly)
    if n<3: return False
    inside=False; j=n-1
    for i in range(n):
        xi,yi=poly[i]; xj,yj=poly[j]
        if ((yi>y)!=(yj>y)) and (x < (xj-xi)*(y-yi)/(yj-yi+1e-12)+xi):
            inside=not inside
        j=i
    return inside


class Engine(Compositor):
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

    def sky_disc_svg(self, cx, cy, rad, lst, lat_rad, theme, ramp=None,
                     cardinals=True, labels=True, marquee=True, ticks=None,
                     star_names=None, declutter=False, clip_id='dclip',
                     figure_stars=False):
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
        if figure_stars:
            # PERCORSO PROFONDO CIELO: NON il campo completo, ma solo le stelle che
            # compongono le FIGURE (i vertici delle linee di costellazione). Svuota
            # il disco perche' i simboli Messier abbiano spazio (D9). Opt-in dal
            # layout; spento -> l'A4 e la pagina 1 non cambiano.
            fra, fdec = self._figure_star_points()
            alt,az=self.altaz(fra,fdec,lst,lat_rad); xs,ys=self.project(alt,az,cx,cy,rad)
            for i in range(len(fra)):
                if alt[i]<=0: continue
                a(f'<circle cx="{xs[i]:.1f}" cy="{ys[i]:.1f}" r="{2.2*k:.2f}" fill="{theme["text"]}" opacity="0.72"/>')
        else:
            alt,az=self.altaz(self.sra,self.sdec,lst,lat_rad); xs,ys=self.project(alt,az,cx,cy,rad)
            for i in np.argsort(-self.smag):
                if alt[i]<=0 or self.smag[i]>5.25: continue
                sr=k*max(0.45,(5.35-self.smag[i])*0.92); col=bv2hex(ramp,self.sbv[i])
                if self.smag[i]<1.5:
                    a(f'<circle cx="{xs[i]:.1f}" cy="{ys[i]:.1f}" r="{sr*2.2:.1f}" fill="{col}" opacity="0.22" filter="url(#softglow)"/>')
                a(f'<circle cx="{xs[i]:.1f}" cy="{ys[i]:.1f}" r="{sr:.2f}" fill="{col}"/>')
        a('</g>')
        # ---- ETICHETTE (stelle-guida + costellazioni) ----
        if not declutter:
            # PERCORSO STORICO (A4): invariato, byte per byte. Le etichette sono
            # piazzate ingenuamente (le sovrapposizioni restano); e' cio' che il
            # golden A4 sorveglia.
            if marquee:
                for nm,ra,dec,bv in MARQUEE:
                    al,zz=self.altaz(ra,dec,lst,lat_rad)
                    if al<=2: continue
                    x,y=self.project(al,zz,cx,cy,rad); col=bv2hex(ramp,bv)
                    a(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{7*k:.1f}" fill="{col}" opacity="0.30" filter="url(#softglow)"/>')
                    a(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{2.6*k:.1f}" fill="{col}"/>')
                    a(f'<text x="{x+7*k:.1f}" y="{y-5*k:.1f}" fill="{theme["text"]}" font-size="{11.5*k:.1f}" opacity="0.95">{nm}</text>')
            if labels:
                label_set = None if labels is True else set(labels)
                for f in self.clines:
                    ab=f['id']
                    if ab not in CONST_IT: continue
                    if label_set is not None and ab not in label_set: continue
                    allp=np.array([p for line in f['geometry']['coordinates'] for p in line])
                    al,zz=self.altaz(allp[:,0],allp[:,1],lst,lat_rad); m=al>3
                    if m.sum()<2: continue
                    x,y=self.project(al[m],zz[m],cx,cy,rad)
                    a(f'<text x="{x.mean():.1f}" y="{y.mean():.1f}" fill="{theme["label"]}" font-size="{12.5*k:.1f}" opacity="0.82" text-anchor="middle" letter-spacing="0.5">{CONST_IT[ab]}</text>')
        else:
            # PERCORSO SOCIAL: dischi delle stelle nominate + etichette con
            # ANTI-COLLISIONE deterministica (vedi _disc_labels_declutter).
            a(self._disc_labels_declutter(cx, cy, rad, k, lst, lat_rad, theme,
                                          ramp, labels, marquee, star_names))
        # tacche di azimut (corona SOLO tacche, niente numeri: a 1080 i numeri
        # sono rumore). Default SPENTA -> l'A4 non la disegna. `ticks` e' un dict
        # {"minor":10,"major":30}: una tacca ogni `minor` gradi, piu' lunga ogni
        # `major`. Geometria del disco (D7), stessa proiezione dei cardinali.
        if ticks:
            a(self._disc_ticks(cx, cy, rad, k, theme, ticks))
        # punti cardinali
        if cardinals:
            for lab,ang in (('N',0),('E',90),('S',180),('O',270)):
                rr=rad+22*k; ax=cx-rr*np.sin(np.radians(ang)); ay=cy-rr*np.cos(np.radians(ang))
                a(f'<text x="{ax:.1f}" y="{ay+6*k:.1f}" fill="{theme["cardinal"]}" font-size="{19*k:.1f}" font-weight="bold" text-anchor="middle">{lab}</text>')
        return '\n'.join(s)

    def _disc_ticks(self, cx, cy, rad, k, theme, ticks):
        """Corona di sole TACCHE (niente numeri): una ogni `minor` gradi, piu'
        lunga ogni `major`. Da' l'aria da strumento del planisfero senza chiedere
        di leggere un 6px. Colore dal token `cardinal` (come i cardinali, che si
        vedono benissimo): `grid` non ha contrasto col fondo. Dimensioni tarate
        per VEDERSI a 1080 (rad ~270): minore ~1.1px×6px, maggiore ~1.7px×12px —
        mai sotto il pixel. Tutto sovrascrivibile dal file."""
        minor=ticks.get("minor",10); major=ticks.get("major",30)
        col=theme[ticks.get("stroke","cardinal")]
        minl=ticks.get("minor_len",9.0)*k;   majl=ticks.get("major_len",17.0)*k
        minw=ticks.get("minor_width",1.6)*k;  majw=ticks.get("major_width",2.4)*k
        mino=ticks.get("minor_op",0.5);       majo=ticks.get("major_op",0.9)
        out=[]
        for az in range(0,360,minor):
            long=(az%major==0); ar=np.radians(az)
            t=majl if long else minl; w=majw if long else minw; op=majo if long else mino
            x1=cx-rad*np.sin(ar); y1=cy-rad*np.cos(ar)
            x2=cx-(rad+t)*np.sin(ar); y2=cy-(rad+t)*np.cos(ar)
            out.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                       f'stroke="{col}" stroke-width="{w:.2f}" opacity="{op}"/>')
        return '\n'.join(out)

    def _disc_labels_declutter(self, cx, cy, rad, k, lst, lat_rad, theme, ramp,
                               labels, marquee, star_names):
        """Etichette (stelle-guida + costellazioni) con ANTI-COLLISIONE
        deterministica. Niente motore a forze: piazzamento greedy per priorita'.

        Stelle nominate: da `star_names` (lista curata) o, in mancanza, dal MARQUEE.
        Priorita': prima le STELLE (piu' brillante = prima; la Polare forzata in
        testa, serve a orientarsi), poi le COSTELLAZIONI (impronta piu' grande
        prima). Ogni etichetta si prova al punto naturale, poi in posizioni via
        via piu' lontane attorno all'ancora; se non entra da nessuna parte, si
        SCARTA (meglio un nome in meno che due impastati). Deterministico."""
        out=[]; reqs=[]
        # stelle nominate: disco (sempre) + richiesta d'etichetta
        names = star_names if star_names is not None else [m[0] for m in MARQUEE]
        for nm in names:
            if nm not in STARS: continue
            ra,dec,bv,mag = STARS[nm]
            al,zz=self.altaz(ra,dec,lst,lat_rad)
            if al<=2: continue
            x,y=self.project(al,zz,cx,cy,rad); x,y=float(x),float(y); col=bv2hex(ramp,bv)
            out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{7*k:.1f}" fill="{col}" opacity="0.30" filter="url(#softglow)"/>')
            out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{2.6*k:.1f}" fill="{col}"/>')
            reqs.append({"text":nm,"x":x+7*k,"y":y-5*k,"anchor":"start",
                         "size":11.5*k,"fill":theme["text"],"opacity":0.95,
                         "pri":(-100.0 if nm=="Polare" else mag),"extra":""})
        # costellazioni: richiesta d'etichetta al baricentro, ordinate per impronta
        label_set = None if labels is True else set(labels or [])
        consts=[]
        if labels:
            for f in self.clines:
                ab=f['id']
                if ab not in CONST_IT: continue
                if label_set is not None and ab not in label_set: continue
                allp=np.array([p for line in f['geometry']['coordinates'] for p in line])
                al,zz=self.altaz(allp[:,0],allp[:,1],lst,lat_rad); m=al>3
                if m.sum()<2: continue
                xs,ys=self.project(al[m],zz[m],cx,cy,rad)
                area=float((xs.max()-xs.min())*(ys.max()-ys.min()))
                consts.append((area, ab, float(xs.mean()), float(ys.mean())))
        consts.sort(key=lambda c:-c[0])  # impronta piu' grande prima
        for rank,(area,ab,mx,my) in enumerate(consts):
            reqs.append({"text":CONST_IT[ab],"x":mx,"y":my,"anchor":"middle",
                         "size":12.5*k,"fill":theme["label"],"opacity":0.82,
                         "pri":100.0+rank,"extra":' letter-spacing="0.5"'})
        # piazzamento greedy
        placed=[]; dropped=0; dropped_labels=[]; STEP=6*k
        DIRS=[(0,-1),(1,0),(0,1),(-1,0),(1,-1),(1,1),(-1,1),(-1,-1)]
        cands=[(0,0)]+[(dx*r*STEP, dy*r*STEP) for r in range(1,6) for dx,dy in DIRS]
        for req in sorted(reqs, key=lambda r:r["pri"]):
            w=len(req["text"])*req["size"]*0.55; h=req["size"]
            def bbox(px,py):
                return (px-w/2,py-h,px+w/2,py) if req["anchor"]=="middle" else (px,py-h,px+w,py)
            chosen=None
            for ox,oy in cands:
                px,py=req["x"]+ox, req["y"]+oy
                if (px-cx)**2+(py-cy)**2 > (rad-3)**2: continue  # ancora dentro il disco
                bb=bbox(px,py)
                if any(not(bb[2]<=p[0] or bb[0]>=p[2] or bb[3]<=p[1] or bb[1]>=p[3]) for p in placed): continue
                chosen=(px,py,bb); break
            if chosen is None:
                dropped+=1; dropped_labels.append(req["text"]); continue
            placed.append(chosen[2])
            px,py=chosen[0],chosen[1]
            anc=f' text-anchor="{req["anchor"]}"' if req["anchor"]!="start" else ""
            out.append(f'<text x="{px:.1f}" y="{py:.1f}" fill="{req["fill"]}" '
                       f'font-size="{req["size"]:.1f}" opacity="{req["opacity"]}"{anc}{req["extra"]}>{req["text"]}</text>')
        self._last_dropped=dropped; self._last_dropped_labels=dropped_labels
        return '\n'.join(out)

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
                                 marquee=b.get("marquee", True),
                                 ticks=b.get("ticks"),
                                 star_names=b.get("star_names"),
                                 declutter=b.get("declutter", False),
                                 figure_stars=b.get("figure_stars", False))

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
            cx=b["x0"]+dot["dx"]; cy=y+dot["dy"]; rr=dot["r"]
            row=[]
            # colore del pallino: il PIANETA (fill_planet, colore reale dal tema),
            # lo STATO (fill_status, come l'A4) o un token fisso.
            if dot.get("fill_planet"):
                dotcol=theme["planet_colors"][pl.name]
            elif dot.get("fill_status"):
                dotcol=theme["status"][pl.status]
            else:
                dotcol=theme[dot["fill"]]
            row.append(f'<circle cx="{cx}" cy="{cy}" r="{rr}" fill="{dotcol}"/>')
            # sagoma dal DATO (solo coi pallini-pianeta): 'ringed' = anelli.
            if dot.get("fill_planet") and pl.shape=="ringed":
                rg=dot.get("ring", {})
                erx=rr*rg.get("rx",1.95); ery=rr*rg.get("ry",0.52); rot=rg.get("rot",-18)
                row.append(f'<ellipse cx="{cx}" cy="{cy}" rx="{erx:.1f}" ry="{ery:.1f}" '
                           f'fill="none" stroke="{theme[rg.get("stroke","moon_lit")]}" '
                           f'stroke-width="{rg.get("width",1.3)}" transform="rotate({rot} {cx} {cy})"/>')
            # anello di stato (variante B): identita' nel disco + stato attorno.
            if dot.get("status_ring"):
                sr=dot["status_ring"]
                row.append(f'<circle cx="{cx}" cy="{cy}" r="{rr+sr["r_extra"]}" fill="none" '
                           f'stroke="{theme["status"][pl.status]}" stroke-width="{sr["width"]}"/>')
            for part in ("name","times","note"):
                if part not in b:  # un design puo' omettere una parte (es. rail
                    continue        # senza nota, editorial senza orari)
                p=b[part]
                tb={"x":b["x0"]+p["dx"],"y":y+p.get("dy",0),"fill":p["fill"],
                    "size":p["size"],"weight":p.get("weight"),"content":p["content"]}
                if p.get("anchor"): tb["anchor"]=p["anchor"]
                row.append(self._render_text(tb, theme, item))
            # variante A: i non osservabili si spengono (riga piu' tenue).
            if b.get("dim_muted") and pl.status=="muted":
                out.append(f'<g opacity="{b.get("dim_muted_opacity",0.4)}">'+"\n".join(row)+'</g>')
            else:
                out.extend(row)
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
        # riga opzionale di etichette delle fasi principali (giorno + nome). Il
        # file da' altezza, colore e la mappa chiave->nome; il dato da' quali
        # giorni (quelli con phase_key, gia' incrociati con moon_phases).
        # Ogni etichetta e' ANCORATA alla COLONNA del suo giorno nel calendario
        # (centrata sotto il dischetto), non a colonne fisse: cosi' regge 3, 4 o
        # 5 fasi (mesi con due lune nuove) senza mai finire fuori tela.
        pl=b.get("phase_labels")
        if pl:
            names=pl["names"]
            for md in (m for m in data.moon_days if m.phase_key):
                cx=x0+((md.day-1)%cols)*cgap
                tb={"x":f"{cx:.2f}","y":pl["y"],"fill":pl["fill"],"size":pl["size"],
                    "weight":pl.get("weight"),"anchor":"middle","content":pl["content"]}
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

    # ---- PROFONDO CIELO (D9): catalogo Messier, geometria, simboli d'atlante ----
    def _figure_star_points(self):
        """Vertici UNICI delle linee di costellazione = le stelle che compongono
        le FIGURE. Le disegna il disco del profondo cielo al posto del campo
        completo (D9). Cache: geometria fissa, non dipende dalla data."""
        if not hasattr(self, "_fig_pts"):
            pts=set()
            for f in self.clines:
                for line in f['geometry']['coordinates']:
                    for p in line:
                        pts.add((round(p[0],4), round(p[1],4)))
            arr=np.array(sorted(pts)) if pts else np.zeros((0,2))
            self._fig_pts=(arr[:,0], arr[:,1]) if len(arr) else (np.zeros(0), np.zeros(0))
        return self._fig_pts

    def _load_messier(self):
        """Catalogo Messier (data/messier.json) come DATO del motore, caricato una
        volta e in modo pigro (come le icone): l'A4 non lo tocca mai."""
        if not hasattr(self, "_messier_doc"):
            with open(f"{self.datadir}/messier.json", encoding="utf-8") as fh:
                self._messier_doc=json.load(fh)
        return self._messier_doc["oggetti"]

    def _messier_meta(self):
        self._load_messier()
        return self._messier_doc.get("_meta", {})

    def messier_context(self, lst, lat_rad, cx, cy, rad, n):
        """Contesto Messier per una data/disco: gli oggetti sopra l'orizzonte con
        le coordinate sul disco (per i SIMBOLI), i punti delle stelle-figura (che
        l'anti-collisione delle etichette deve evitare), la TABELLA selezionata,
        e le sigle che meritano un'etichetta (patto mappa<->tabella, D9). Puro:
        dipende solo da lst/lat."""
        enriched=[]
        for o in self._load_messier():
            if o.get("disegna_mappa") is False:  # M40 (stella doppia): non si disegna
                continue
            alt,az=self.altaz(o["ra_deg"], o["dec_deg"], lst, lat_rad)
            alt=float(np.asarray(alt).reshape(-1)[0]); az=float(np.asarray(az).reshape(-1)[0])
            if alt<=0: continue
            x,y=self.project(alt,az,cx,cy,rad)
            enriched.append({**o, "alt":alt, "az":az, "x":float(x), "y":float(y)})
        # stelle-figura proiettate: OSTACOLI per le etichette (come i simboli)
        fra,fdec=self._figure_star_points()
        fig_pts=[]
        if len(fra):
            fa,faz=self.altaz(fra,fdec,lst,lat_rad); fx,fy=self.project(fa,faz,cx,cy,rad)
            fig_pts=[(float(fx[i]),float(fy[i])) for i in range(len(fra)) if fa[i]>0]
        gruppi=self._messier_meta().get("gruppi", {})
        table=self._messier_select(enriched, n, gruppi)
        labels=set()
        for r in table:
            labels.add(("__group__"+r["_group"]) if r.get("_group") else r["sigla"])
        # FIGURE di costellazione (#7d/#7d-bis): il TERZO strato di etichette. Un
        # nome sta DENTRO la sua figura, non sul suo baricentro (che nelle
        # costellazioni ricche cade sepolto nei loro stessi Messier). I CANDIDATI
        # di posizione sono percio' punti della figura, in ordine di preferenza:
        # baricentro (il migliore, se libero), poi i VERTICI, poi i PUNTI MEDI dei
        # segmenti. Il piazzamento prende il primo libero: mai deriva, mai un
        # candidato fuori dalla propria costellazione. Un'entrata per FIGURA (Ser
        # e' due figure -> due etichette "Serpente", corretto). Geometria (serve
        # lst/lat): vive qui, come fig_pts. Solo vertici sopra l'orizzonte (alt>3).
        const_figures=[]
        for f in self.clines:
            verts=[]; mids=[]
            for line in f['geometry']['coordinates']:
                arr=np.array(line)
                al,zz=self.altaz(arr[:,0],arr[:,1],lst,lat_rad)
                xs,ys=self.project(al,zz,cx,cy,rad); up=al>3
                for i in range(len(arr)):
                    if up[i]: verts.append((float(xs[i]),float(ys[i])))
                for i in range(len(arr)-1):
                    if up[i] and up[i+1]:
                        mids.append((float((xs[i]+xs[i+1])/2.0),float((ys[i]+ys[i+1])/2.0)))
            if len(verts)<2: continue
            vx=[p[0] for p in verts]; vy=[p[1] for p in verts]
            centroid=(sum(vx)/len(vx), sum(vy)/len(vy))
            vbbox=(min(vx), min(vy), max(vx), max(vy))
            diag=((vbbox[2]-vbbox[0])**2+(vbbox[3]-vbbox[1])**2)**0.5
            hull=convex_hull(verts)
            hbbox=(min(p[0] for p in hull), min(p[1] for p in hull),
                   max(p[0] for p in hull), max(p[1] for p in hull))
            # ordine di preferenza dei candidati: baricentro, vertici, punti medi
            const_figures.append({"ab":f['id'], "verts":verts, "vbbox":vbbox,
                                  "diag":diag, "centroid":centroid, "hull":hull,
                                  "hbbox":hbbox, "cands":[centroid]+verts+mids})
        # gli inviluppi di TUTTE le figure (per il vincolo "mai dentro un'altra
        # costellazione"): (sigla, inviluppo, riquadro dell'inviluppo per pre-filtro)
        const_hulls=[(fig["ab"], fig["hull"], fig["hbbox"]) for fig in const_figures]
        return {"enriched":enriched, "table":table, "label_siglas":labels,
                "figure_pts":fig_pts, "const_figures":const_figures,
                "const_hulls":const_hulls}

    @staticmethod
    def _messier_select(enriched, n, gruppi):
        """La REGOLA della tabella (D9). Filtro: altezza > 30 gradi. I GRUPPI
        (definiti nel catalogo, D7) sono STRUTTURALI, non competitivi: se >=
        `min_membri_sopra30` membri superano i 30 gradi, il gruppo collassa in UNA
        voce col posto GARANTITO in tabella (baricentro dei membri per la linea di
        richiamo) — non gareggia per un posto, ce l'ha. I restanti N-|gruppi|
        posti se li giocano i SINGOLI, ordinati per (notevolezza, altezza). Se un
        gruppo NON e' attivo (pochi membri sopra i 30), i suoi membri restano
        singoli come tutti gli altri. Il N e' del FILE di layout, non del codice."""
        active={}
        for key,cfg in gruppi.items():
            up=[o for o in enriched if o.get("gruppo")==key]           # sopra orizzonte
            hi=[o for o in up if o["alt"]>30]                          # sopra i 30
            if len(hi) >= cfg.get("min_membri_sopra30",3):
                gx=sum(o["x"] for o in up)/len(up); gy=sum(o["y"] for o in up)/len(up)
                active[key]={"sigla":cfg["nome"], "_group":key, "nome_it":cfg["nome"],
                    "nome_fonte":"curato", "famiglia":"galassia",
                    "notevolezza":cfg.get("merito_display",3),
                    "costellazione_it":cfg.get("costellazione_it",""),
                    "visione":cfg.get("visione","telescopio"),
                    "alt":max(o["alt"] for o in hi), "x":gx, "y":gy,
                    "_count":len(up), "_members":up}
        singles=[o for o in enriched if o["alt"]>30 and o.get("notevolezza",0)>=1
                 and o.get("gruppo") not in active]
        singles.sort(key=lambda o:(-o.get("notevolezza",0), -o["alt"]))
        groups=list(active.values())
        rows=groups + singles[: max(0, n-len(groups))]
        rows.sort(key=lambda o:(-o.get("notevolezza",0), -o["alt"]))  # ordine di stampa
        return rows

    # forme della convenzione degli atlanti (D9): copiate dal mockup del designer.
    # Tutte fill=none, stroke = token colore. `s` = raggio nominale; le proporzioni
    # sono ancorate al mockup (s=4.6 sul disco, s=5 in tabella/legenda).
    @staticmethod
    def _messier_symbol_svg(fam, x, y, s, col, sw, rot=0.0):
        if fam=="galassia":
            return (f'<ellipse cx="{x:.1f}" cy="{y:.1f}" rx="{s*1.30:.1f}" ry="{s*0.587:.1f}" '
                    f'fill="none" stroke="{col}" stroke-width="{sw}" transform="rotate({rot:.0f} {x:.1f} {y:.1f})"/>')
        if fam=="ammasso aperto":
            return (f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{s:.1f}" fill="none" '
                    f'stroke="{col}" stroke-width="{sw}" stroke-dasharray="2 2"/>')
        if fam=="ammasso globulare":
            e=s*1.24
            return (f'<g fill="none" stroke="{col}" stroke-width="{sw}">'
                    f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{s:.1f}"/>'
                    f'<line x1="{x-e:.1f}" y1="{y:.1f}" x2="{x+e:.1f}" y2="{y:.1f}"/>'
                    f'<line x1="{x:.1f}" y1="{y-e:.1f}" x2="{x:.1f}" y2="{y+e:.1f}"/></g>')
        if fam=="nebulosa diffusa":
            side=s*1.91; h=side/2
            return (f'<rect x="{x-h:.1f}" y="{y-h:.1f}" width="{side:.1f}" height="{side:.1f}" '
                    f'rx="0.9" fill="none" stroke="{col}" stroke-width="{sw}"/>')
        if fam=="nebulosa planetaria":
            r=s*0.72; o=r+s*0.6
            return (f'<g fill="none" stroke="{col}" stroke-width="{sw}">'
                    f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}"/>'
                    f'<line x1="{x:.1f}" y1="{y-r:.1f}" x2="{x:.1f}" y2="{y-o:.1f}"/>'
                    f'<line x1="{x:.1f}" y1="{y+r:.1f}" x2="{x:.1f}" y2="{y+o:.1f}"/>'
                    f'<line x1="{x-r:.1f}" y1="{y:.1f}" x2="{x-o:.1f}" y2="{y:.1f}"/>'
                    f'<line x1="{x+r:.1f}" y1="{y:.1f}" x2="{x+o:.1f}" y2="{y:.1f}"/></g>')
        return ''  # famiglie fuori dalle 5 (es. stella doppia): nessun simbolo

    @staticmethod
    def _instrument_icon_svg(kind, x, y, col, sw=1.3):
        """Icona strumento (dal mockup): binocolo = due cerchi + ponte; telescopio
        = tratto obliquo + tacca. Ancorata a (x,y)."""
        if kind=="binocolo":
            return (f'<g fill="none" stroke="{col}" stroke-width="{sw}">'
                    f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3"/><circle cx="{x+8:.1f}" cy="{y:.1f}" r="3"/>'
                    f'<line x1="{x+3:.1f}" y1="{y-1:.1f}" x2="{x+5:.1f}" y2="{y-1:.1f}"/></g>')
        return (f'<g fill="none" stroke="{col}" stroke-width="{sw}" stroke-linecap="round">'
                f'<line x1="{x:.1f}" y1="{y:.1f}" x2="{x+9:.1f}" y2="{y-6:.1f}"/>'
                f'<line x1="{x+7:.1f}" y1="{y-7:.1f}" x2="{x+10:.1f}" y2="{y-4:.1f}"/></g>')

    # un'etichetta non si scarta MAI (D9, deciso da Marco): se non trova posto
    # libero vicino al suo oggetto, si allontana e si collega con una LINEA DI
    # RICHIAMO. Oltre questa distanza (px) dall'ancora naturale scatta la linea.
    # Tarata (misura #7b) perche' un'etichetta appena nudge-ata resti muta —
    # altrimenti in una zona fitta scattano 8-9 linee = ragnatela; solo le
    # davvero lontane (~42px) prendono il richiamo.
    LEADER_GAP = 28.0

    def _render_messier_symbols(self, b, theme, mctx):
        """Simboli di TUTTI i Messier sopra l'orizzonte sul disco (43-87), col
        simbolo del tipo; etichetta 'Mxx' SOLO a chi sta in tabella (patto D9).
        L'anti-collisione conosce gli OSTACOLI: i simboli Messier e le stelle
        delle figure. Un'etichetta NON si scarta mai: se non entra vicino al suo
        oggetto si allontana finche' trova posto e si collega con una LINEA DI
        RICHIAMO (lo stesso meccanismo dell'Ammasso della Vergine, esteso a tutti).
        Espone i box calcolati (`_last_symbol_boxes`, `_last_label_boxes`) e i
        contatori (`_last_messier_dropped`, `_last_messier_leadered`) per i test."""
        cx,cy,rad = b["cx"], b["cy"], b["rad"]
        s=b.get("size",4.6); sw=b.get("stroke_width",1.15); col=theme[b.get("fill","gold")]
        lab_col=theme[b.get("label_fill","gold")]; lsz=b.get("label_size",11)
        out=[]; enriched=mctx["enriched"]; label_siglas=mctx["label_siglas"]
        symbol_boxes=[]; obstacles=[]  # simboli (ostacoli+test) + stelle-figura (solo ostacoli)
        # 1) SIMBOLI (tutti). Membri di un gruppo piu' piccoli: grappolo fitto.
        for o in enriched:
            ss = s*0.85 if o.get("gruppo") else s
            rot = (o["ra_deg"] % 180.0) - 90.0  # deterministica, non allinea le ellissi
            out.append(self._messier_symbol_svg(o["famiglia"], o["x"], o["y"], ss, col, sw, rot))
            hs=ss*1.25; box=(o["x"]-hs, o["y"]-hs, o["x"]+hs, o["y"]+hs)
            symbol_boxes.append(box); obstacles.append(box)
        for fx,fy in mctx["figure_pts"]:
            obstacles.append((fx-2.6, fy-2.6, fx+2.6, fy+2.6))
        # 2) ETICHETTE: richieste dei singoli in tabella + etichetta dei gruppi.
        #    Priorita' (pri minore = prima): i gruppi per primi (importanti e
        #    grandi), poi i singoli piu' alti (meglio piazzati).
        reqs=[]
        for o in enriched:
            if o["sigla"] in label_siglas and not o.get("gruppo"):
                reqs.append({"kind":"single", "key":o["sigla"], "text":o["sigla"],
                             "sx":o["x"], "sy":o["y"], "nx":o["x"]+s+3, "ny":o["y"]-s+1,
                             "w":len(o["sigla"])*lsz*0.62, "h":lsz, "pri":100.0-o["alt"]})
        for r in mctx["table"]:
            if r.get("_group") and ("__group__"+r["_group"]) in label_siglas:
                gx,gy=r["x"],r["y"]
                dx,dy=gx-cx,gy-cy; d=(dx*dx+dy*dy)**0.5 or 1.0
                # ancora naturale: spinta RADIALE verso l'esterno (via dal grappolo)
                nx,ny=gx+dx/d*46, gy+dy/d*46
                txt=r["nome_it"]; sub=f'{r["_count"]} galassie'
                wbox=max(len(txt)*11.5*0.55, len(sub)*9.5*0.55)  # copre la riga piu' larga
                reqs.append({"kind":"group", "key":"__group__"+r["_group"], "text":txt, "sub":sub,
                             "sx":gx, "sy":gy, "nx":nx, "ny":ny,
                             "w":wbox, "h":26, "pri":-1.0})
        # anti-collisione greedy contro OSTACOLI + etichette gia' poste
        placed_boxes=list(obstacles); label_boxes=[]; leadered=0; dropped=0
        DIRS=[(0,-1),(1,0),(0,1),(-1,0),(1,-1),(1,1),(-1,1),(-1,-1)]; STEP=6
        cands=[(0,0)]+[(dx*r*STEP, dy*r*STEP) for r in range(1,15) for dx,dy in DIRS]
        def overlaps(bb):
            return sum(1 for p in placed_boxes
                       if not(bb[2]<=p[0] or bb[0]>=p[2] or bb[3]<=p[1] or bb[1]>=p[3]))
        def mkbox(px,py,req):
            if req["kind"]=="group": return (px-req["w"]/2, py-11, px+req["w"]/2, py+16)
            return (px, py-req["h"], px+req["w"], py)
        def grid_cands(req):
            # scansione a griglia di TUTTO il disco: il gruppo ha la linea di
            # richiamo, quindi puo' stare ovunque sia libero; ordina per vicinanza
            # all'ancora naturale (il richiamo piu' corto possibile).
            g=[]
            for gxp in range(int(cx-rad+10), int(cx+rad-10), 16):
                for gyp in range(int(cy-rad+10), int(cy+rad-10), 16):
                    g.append((gxp-req["nx"], gyp-req["ny"]))
            g.sort(key=lambda o:o[0]*o[0]+o[1]*o[1])
            return g
        for req in sorted(reqs, key=lambda r:r["pri"]):
            chosen=None; best=None
            search = grid_cands(req) if req["kind"]=="group" else cands
            for ox,oy in search:
                px,py=req["nx"]+ox, req["ny"]+oy
                if (px-cx)**2+(py-cy)**2 > (rad-3)**2: continue
                bb=mkbox(px,py,req); ov=overlaps(bb)
                if ov==0: chosen=(px,py,bb,ox,oy); break
                if best is None or ov<best[4]: best=(px,py,bb,(ox*ox+oy*oy),ov)
            # non si scarta MAI: se nessun posto e' del tutto libero, si prende il
            # meno sovrapposto (con linea di richiamo). Lo scarto resta come rete di
            # sicurezza teorica (best None = nessun candidato dentro il disco).
            if chosen is None and best is not None:
                chosen=(best[0],best[1],best[2],0,0)
            if chosen is None: dropped+=1; continue
            px,py,bb,ox,oy=chosen
            placed_boxes.append(bb); label_boxes.append((bb, req["key"]))
            need_leader = (req["kind"]=="group") or (ox*ox+oy*oy) > self.LEADER_GAP**2
            if need_leader:
                leadered+=1
                out.append(f'<line x1="{req["sx"]:.1f}" y1="{req["sy"]:.1f}" x2="{px:.1f}" y2="{py-4:.1f}" '
                           f'stroke="{col}" stroke-width="0.9" stroke-opacity="0.7"/>')
            if req["kind"]=="group":
                out.append(f'<text x="{px:.1f}" y="{py:.1f}" text-anchor="middle" fill="{col}" '
                           f'font-size="11.5" font-weight="600">{req["text"]}</text>')
                out.append(f'<text x="{px:.1f}" y="{py+14:.1f}" text-anchor="middle" fill="{theme["text3"]}" '
                           f'font-size="9.5">{req["sub"]}</text>')
            else:
                out.append(f'<text x="{px:.1f}" y="{py:.1f}" fill="{lab_col}" '
                           f'font-size="{lsz}" font-weight="600">{req["text"]}</text>')
        self._last_messier_labels=len(label_boxes); self._last_messier_dropped=dropped
        self._last_messier_leadered=leadered
        self._last_symbol_boxes=symbol_boxes; self._last_label_boxes=label_boxes
        # 3) TERZO STRATO (#7d, piazzamento rivisto in #7d-bis): NOMI DELLE
        #    COSTELLAZIONI. Sfondo semantico, non contenuto: priorita' MINIMA (si
        #    piazzano DOPO simboli e sigle), tipografia subordinata, NIENTE linea
        #    di richiamo (una costellazione e' una regione), e stanno DENTRO la
        #    propria figura (candidati = punti della figura, mai deriva).
        #    OSTACOLI = simboli Messier + sigle Messier (+ i nomi gia' posti), NON
        #    le stelle della figura: un nome ETICHETTA le sue stesse stelle, e un
        #    atlante lo scrive attraverso il campo stellare. Trattare le stelle
        #    della figura come ostacolo per il nome che le nomina e' contraddittorio
        #    e scartava proprio le costellazioni piu' ricche (misura #7d-bis).
        #    Il nome puo' sfiorare una stella tenue; MAI un simbolo o una sigla.
        name_obstacles=list(symbol_boxes)+[bx for bx,_k in label_boxes]
        out.append(self._render_const_names(b, theme, mctx, cx, cy, rad,
                                            name_obstacles))
        return '\n'.join(out)

    # margine di uscita del nome dalla propria figura (#7d-ter): PICCOLO e
    # proporzionato. Inverso alla dimensione: una figura grande resta stretta
    # (una costellazione grande non ha scuse per uscire), una minuscola puo'
    # sporgere di piu' (Freccia, Scudo, Cani da Caccia escono di un passo dal
    # loro unico Messier). Tarato sui bisogni misurati (#7d-ter): il massimo
    # richiesto e' ~23px (Cani da Caccia a marzo), i grandi 0.
    @staticmethod
    def _const_margin(diag):
        return max(12.0, min(28.0, 30.0 - 0.10*diag))

    def _render_const_names(self, b, theme, mctx, cx, cy, rad, obstacles):
        """Terzo strato di etichette: i NOMI delle costellazioni (#7d, piazzamento
        #7d-bis, patto chiuso in #7d-ter). Modalita' dal FILE (`const_names`):
        'no' (com'era), 'tabella' o 'tutte' (default).

        Il nome sta DENTRO la sua figura, o al massimo la sfiora di un margine
        PICCOLO e proporzionato (`_const_margin`): mai in deriva. VINCOLO: non
        deve MAI cadere dentro la figura (inviluppo convesso) di un'ALTRA
        costellazione — scrivere "Scudo" sopra l'Aquila e' una bugia, peggio di
        un'assenza. Se l'unico posto e' dentro il vicino, SCARTA. Niente linea di
        richiamo. Le costellazioni in tabella hanno prima scelta e non devono
        scartarsi (patto D9): i loro scarti si MISURANO (`_last_const_dropped_tab`).

        Candidati, in ordine: baricentro, vertici, punti medi (dentro la figura),
        poi anelli attorno al baricentro fino a mezza-figura + margine. Il CODICE
        possiede COME piazzare; il FILE possiede QUANTE (R5/D7)."""
        self._last_const_label_boxes=[]; self._last_const_dropped=[]
        self._last_const_dropped_tab=[]; self._last_const_placed=[]
        mode=b.get("const_names","no")
        if mode not in ("tabella","principali","tutte"):
            return ''
        cfill=theme[b.get("const_fill","text4")]
        csz=b.get("const_size",10.5); ctr=b.get("const_tracking",2.2)
        cop=b.get("const_opacity",0.85)
        # NOMI: le principali (CONST_IT) + le minori (CONST_IT_MINORI, solo qui:
        # l'A4 non le vede) + i nomi VERIFICATI del catalogo (costellazione_it,
        # gia' nel repo). I nomi delle costellazioni CITATE in tabella vengono
        # dalla STESSA fonte della tabella (il testo combacia).
        name_map={**CONST_IT, **CONST_IT_MINORI}
        for o in mctx["enriched"]:
            name_map.setdefault(o["costellazione"], o["costellazione_it"])
        tab_abbr=set()
        for r in mctx["table"]:
            tab_abbr.add("Vir" if r.get("_group") else r["costellazione"])
        # QUALI figure nominare, per modo (il patto D9 - le costellazioni in
        # tabella - resta in TUTTI i modi): 'tabella' = solo quelle in tabella;
        # 'principali' = le principali (CONST_IT) + quelle in tabella (D16: sul
        # telefono le minori sui bordi sono rumore, non testo); 'tutte' = ogni
        # figura con un nome noto.
        if mode=="tabella":       allowed=set(tab_abbr)
        elif mode=="principali":  allowed=set(CONST_IT)|tab_abbr
        else:                     allowed=None  # tutte
        hulls=mctx.get("const_hulls", [])
        def in_other(px, py, ab):
            for hab, poly, hb in hulls:
                if hab==ab: continue
                if px<hb[0] or px>hb[2] or py<hb[1] or py>hb[3]: continue  # pre-filtro
                if point_in_poly(poly, px, py): return True
            return False
        DIRS=[(0,-1),(1,0),(0,1),(-1,0),(1,-1),(1,1),(-1,1),(-1,-1),
              (2,-1),(2,1),(-2,-1),(-2,1),(1,-2),(1,2),(-1,-2),(-1,2)]
        # richieste: una per FIGURA nominabile (filtrate per modo)
        reqs=[]
        for fig in mctx.get("const_figures", []):
            ab=fig["ab"]
            if allowed is not None and ab not in allowed: continue
            name=name_map.get(ab)
            if not name: continue
            text=name.upper()
            w=len(text)*csz*0.60 + ctr*max(0,len(text)-1); h=csz
            reqs.append({"ab":ab,"text":text,"w":w,"h":h,"in_tab":ab in tab_abbr,"fig":fig})
        # i CITATI in tabella hanno prima scelta (patto D9); a parita', impronta
        # piu' grande prima (piu' difficile da piazzare)
        reqs.sort(key=lambda r:(0 if r["in_tab"] else 1, -r["w"]))
        cobst=list(obstacles); out=[]
        for req in reqs:
            w,h=req["w"],req["h"]; fig=req["fig"]
            x0,y0,x1,y1=fig["vbbox"]; M=self._const_margin(fig["diag"])
            ccx,ccy=fig["centroid"]
            # candidati: prima i punti interni, poi anelli (bounded dal margine)
            cands=list(fig["cands"])
            rr=1; maxr=fig["diag"]/2.0 + M
            while rr*4.0 <= maxr:
                cands.extend((ccx+dx*rr*4.0, ccy+dy*rr*4.0) for dx,dy in DIRS)
                rr+=1
            chosen=None
            for px,py in cands:
                if (px-cx)**2+(py-cy)**2 > (rad-3)**2: continue
                ox=max(x0-px, 0.0, px-x1); oy=max(y0-py, 0.0, py-y1)
                if ox>M or oy>M: continue                     # "mai lontano"
                if in_other(px, py, req["ab"]): continue      # "mai in un'altra figura"
                bb=(px-w/2, py-h/2, px+w/2, py+h/2)
                if any(not(bb[2]<=p[0] or bb[0]>=p[2] or bb[3]<=p[1] or bb[1]>=p[3]) for p in cobst): continue
                chosen=(px,py,bb); break
            if chosen is None:
                self._last_const_dropped.append(req["ab"])
                if req["in_tab"]: self._last_const_dropped_tab.append(req["ab"])
                continue
            px,py,bb=chosen; cobst.append(bb)
            self._last_const_label_boxes.append((bb, req["ab"]))
            self._last_const_placed.append({"ab":req["ab"],"x":px,"y":py,
                                            "vbbox":fig["vbbox"],"margin":M})
            out.append(f'<text x="{px:.1f}" y="{py+h*0.34:.1f}" text-anchor="middle" '
                       f'fill="{cfill}" font-size="{csz}" opacity="{cop}" '
                       f'letter-spacing="{ctr}">{req["text"]}</text>')
        return '\n'.join(out)

    def _render_messier_table(self, b, theme, mctx):
        """Colonna destra: le righe della tabella (simbolo · Mxx — nome · tipo ·
        costellazione · strumento). Passo `step`, prima baseline `y0`."""
        out=[]; x0=b["x0"]; y0=b["y0"]; step=b["step"]
        symx=b.get("sym_dx",8); namex=b.get("name_dx",30); instx=b.get("inst_dx",398)
        s=b.get("size",5); sw=b.get("stroke_width",1.15); col=theme[b.get("sym_fill","gold")]
        for i,r in enumerate(mctx["table"]):
            y=y0+i*step
            grp=r.get("_group")=="vergine"
            # simbolo (per la Vergine: mini-grappolo di 3 ellissi)
            if grp:
                out.append('<g opacity="0.95">' +
                    self._messier_symbol_svg("galassia", x0+symx-2, y-4, s*0.7, col, sw, 20) +
                    self._messier_symbol_svg("galassia", x0+symx+2, y-2, s*0.7, col, sw, -15) +
                    self._messier_symbol_svg("galassia", x0+symx, y-3, s*0.6, col, sw, 40) + '</g>')
            else:
                rot=-22 if r["famiglia"]=="galassia" else 0
                out.append(self._messier_symbol_svg(r["famiglia"], x0+symx, y-4, s, col, sw, rot))
            # nome: "Mxx — Nome" se c'e' un nome curato, altrimenti solo "Mxx"
            if grp:
                name=(f'<text x="{x0+namex:.0f}" y="{y:.0f}" fill="{theme["text"]}" font-size="14" '
                      f'font-weight="600">{r["nome_it"]}</text>')
            elif r.get("nome_fonte")=="curato":
                name=(f'<text x="{x0+namex:.0f}" y="{y:.0f}" fill="{theme["text"]}" font-size="14" '
                      f'font-weight="600"><tspan fill="{col}">{r["sigla"]}</tspan> — {r["nome_it"]}</text>')
            else:
                name=(f'<text x="{x0+namex:.0f}" y="{y:.0f}" fill="{theme["text"]}" font-size="14" '
                      f'font-weight="600"><tspan fill="{col}">{r["sigla"]}</tspan></text>')
            out.append(name)
            # riga secondaria: Tipo · Costellazione (per la Vergine: conteggio)
            if grp:
                sec=f'{r["_count"]} galassie (Messier) · {r["costellazione_it"]}'
            else:
                sec=f'{r["famiglia"][0].upper()+r["famiglia"][1:]} · {r["costellazione_it"]}'
            out.append(f'<text x="{x0+namex:.0f}" y="{y+16:.0f}" fill="{theme["text3"]}" '
                       f'font-size="11.5">{sec}</text>')
            # strumento a destra
            kind="binocolo" if r["visione"]=="binocolo" else "telescopio"
            out.append(self._instrument_icon_svg(kind, x0+instx, y-4, theme["text3"]))
            word="Bino." if kind=="binocolo" else "Tele."
            out.append(f'<text x="{x0+instx+18:.0f}" y="{y:.0f}" fill="{theme["text2"]}" '
                       f'font-size="11.5" font-weight="500">{word}</text>')
            # divisore sottile tra le righe (non dopo l'ultima: respiro verso la legenda)
            if i < len(mctx["table"])-1:
                out.append(f'<line x1="{x0}" y1="{y+step-16:.0f}" x2="{b["x1"]}" y2="{y+step-16:.0f}" '
                           f'stroke="{theme["divider"]}" stroke-width="0.7" opacity="0.5"/>')
        return '\n'.join(out)

    def _mini_grappolo_svg(self, x, y, s, col, sw):
        """Il segno del grappolo: tre mini-ellissi quasi sovrapposte (come in
        tabella). Non e' un simbolo d'atlante ma un COMPOSITO, e va in legenda
        perche' compare sulla mappa e in tabella (sei segni usati, non cinque)."""
        return ('<g opacity="0.95">'
                + self._messier_symbol_svg("galassia", x-2, y-1, s*0.7, col, sw, 20)
                + self._messier_symbol_svg("galassia", x+2, y+1, s*0.7, col, sw, -15)
                + self._messier_symbol_svg("galassia", x, y, s*0.6, col, sw, 40) + '</g>')

    def _render_messier_legend(self, b, theme):
        """Legenda: i 5 simboli d'atlante + il segno del grappolo + la chiave
        strumenti. Senza, la mappa e' indecifrabile. Posizioni dal file."""
        out=[]; y=b["y"]; s=b.get("size",5); sw=b.get("stroke_width",1.15); col=theme[b.get("fill","gold")]
        FAMS=[("galassia","Galassia"),("ammasso aperto","Ammasso aperto"),
              ("ammasso globulare","Ammasso globulare"),("nebulosa diffusa","Nebulosa diffusa"),
              ("nebulosa planetaria","Nebulosa planetaria")]
        for (fam,label),item in zip(FAMS, b["items"]):
            x=item["x"]; rot=-22 if fam=="galassia" else 0
            out.append(self._messier_symbol_svg(fam, x, y, s, col, sw, rot))
            out.append(f'<text x="{x+16:.0f}" y="{y+4:.0f}" fill="{theme["text"]}" font-size="12.5" '
                       f'font-weight="500">{label}</text>')
        grp=b.get("gruppo")
        if grp:
            out.append(self._mini_grappolo_svg(grp["x"], y, s, col, sw))
            out.append(f'<text x="{grp["x"]+16:.0f}" y="{y+4:.0f}" fill="{theme["text"]}" font-size="12.5" '
                       f'font-weight="500">{grp.get("label","Grappolo di galassie")}</text>')
        key=b["inst_key"]
        out.append(self._instrument_icon_svg("binocolo", key["x"], y-5, theme["text3"]))
        out.append(f'<text x="{key["x"]+16:.0f}" y="{y-1:.0f}" fill="{theme["text2"]}" font-size="12" '
                   f'font-weight="500">Binocolo</text>')
        out.append(self._instrument_icon_svg("telescopio", key["x"], y+14, theme["text3"]))
        out.append(f'<text x="{key["x"]+16:.0f}" y="{y+17:.0f}" fill="{theme["text2"]}" font-size="12" '
                   f'font-weight="500">Telescopio</text>')
        return '\n'.join(out)

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
