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
import json, argparse, calendar
from datetime import datetime
import numpy as np
import pytz
from skyfield_data import get_skyfield_data_path
from skyfield.api import Loader, wgs84
from skyfield import almanac

MONTHS_IT = ["", "gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno",
             "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"]

# nomi italiani costellazioni principali da etichettare
CONST_IT = {'Aql':'Aquila','Boo':'Boote','CrB':'Corona Boreale','Cas':'Cassiopea',
 'Cep':'Cefeo','Cyg':'Cigno','Del':'Delfino','Dra':'Dragone','Her':'Ercole',
 'Lyr':'Lira','Oph':'Ofiuco','Peg':'Pegaso','Sgr':'Sagittario','Sco':'Scorpione',
 'Ser':'Serpente','UMa':'Orsa Maggiore','UMi':'Orsa Minore','Vir':'Vergine',
 'Lib':'Bilancia','Cap':'Capricorno','And':'Andromeda','Aqr':'Acquario',
 'CVn':'Cani da Caccia','Ori':'Orione','Tau':'Toro','Gem':'Gemelli','Leo':'Leone',
 'Cnc':'Cancro','Per':'Perseo','Aur':'Auriga','CMi':'Cane Minore','CMa':'Cane Maggiore',
 'Peg':'Pegaso','Cet':'Balena','Psc':'Pesci','Ari':'Ariete'}

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
NAKED_EYE = {"Mercurio","Venere","Marte","Giove","Saturno"}

# canvas
W, Hpx = 900, 1273
CX, CY, R = 450.0, 500.0, 384.0


def hex2rgb(h): return tuple(int(h[i:i+2],16) for i in (1,3,5))
def rgb2hex(r): return '#%02x%02x%02x'%tuple(int(max(0,min(255,x))) for x in r)

def bv2hex(ramp, bv):
    xs=[p[0] for p in ramp]; bv=max(xs[0],min(xs[-1],bv))
    for i in range(len(ramp)-1):
        if ramp[i][0]<=bv<=ramp[i+1][0]:
            f=(bv-ramp[i][0])/(ramp[i+1][0]-ramp[i][0]+1e-9)
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

    def planet_table(self, year, month, tz, obs, loc):
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
            # best night altitude and when
            best_alt=-90; best_h=None
            for h in hours:
                dd=day+(1 if h<12 else 0)
                tt=self.ts.from_datetime(tz.localize(datetime(year,month,dd,h,0)))
                alt=(earth+loc).at(tt).observe(tgt).apparent().altaz()[0].degrees
                if alt>best_alt: best_alt=alt; best_h=h
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
            rows.append((label,rise or '--',set_ or '--',note,status))
        # ordine: osservabili prima
        order={'ok':0,'info':1,'warn':2,'muted':3}
        rows.sort(key=lambda r:order[r[4]])
        return rows

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

    # ---- render: volantino A4 ----
    def generate(self, year, month, lat, lon, place, theme, out,
                 hour_local=23, tzname='Europe/Rome'):
        lst, lat_rad, tz = self.sky_context(year,month,lat,lon,hour_local,tzname)
        loc=wgs84.latlon(lat,lon,elevation_m=50)
        obs=self.eph['earth']+loc

        phases=self.moon_phases(year,month,tz)
        planets=self.planet_table(year,month,tz,obs,loc)
        ramp=theme['star_ramp']
        s=[]; a=s.append
        a(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{Hpx}" viewBox="0 0 {W} {Hpx}" font-family="Helvetica,Arial,sans-serif">')
        a(self.defs_svg(theme))
        a(f'<rect width="{W}" height="{Hpx}" fill="url(#bg)"/>')
        rng=np.random.default_rng(7)
        for x,y in zip(rng.uniform(0,W,240),rng.uniform(0,Hpx,240)):
            a(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{rng.uniform(0.3,1.0):.2f}" fill="{theme["bgstar"]}" opacity="{rng.uniform(0.15,0.5):.2f}"/>')
        # disco cielo (componente riutilizzabile, a misura A4)
        a(self.sky_disc_svg(CX, CY, R, lst, lat_rad, theme, ramp))
        # header
        a(f'<text x="{CX}" y="52" fill="{theme["gold"]}" font-size="21" font-weight="bold" text-anchor="middle" letter-spacing="3">GRUPPO ASTROFILI VICENTINI</text>')
        a(f'<text x="{CX}" y="86" fill="{theme["text"]}" font-size="30" font-weight="bold" text-anchor="middle" letter-spacing="1.5">IL CIELO DI {MONTHS_IT[month].upper()} {year}</text>')
        a(f'<text x="{CX}" y="108" fill="{theme["text3"]}" font-size="12.5" text-anchor="middle">Cielo visibile dal Nord Italia · {place} · valido ~15 {MONTHS_IT[month]}, ore {hour_local}:00</text>')
        # moon phases
        py=960
        a(f'<text x="60" y="{py}" fill="{theme["text"]}" font-size="16" font-weight="bold" letter-spacing="1">FASI LUNARI</text>')
        mr=24; startx=90; gap=200; my=py+58
        for i,(nm,ph,dt) in enumerate(phases[:4]):
            mx=startx+i*gap
            a(f'<circle cx="{mx}" cy="{my}" r="{mr}" fill="{theme["panel"]}" stroke="{theme["border2"]}" stroke-width="1"/>')
            if ph=='full': a(f'<circle cx="{mx}" cy="{my}" r="{mr}" fill="{theme["moon_lit"]}"/>')
            elif ph=='first': a(f'<path d="M{mx},{my-mr} A{mr},{mr} 0 0 1 {mx},{my+mr} Z" fill="{theme["moon_lit"]}"/>')
            elif ph=='last': a(f'<path d="M{mx},{my-mr} A{mr},{mr} 0 0 0 {mx},{my+mr} Z" fill="{theme["moon_lit"]}"/>')
            a(f'<text x="{mx}" y="{my+mr+20}" fill="#cdd6ee" font-size="12.5" text-anchor="middle">{nm}</text>')
            a(f'<text x="{mx}" y="{my+mr+37}" fill="{theme["text3"]}" font-size="12" text-anchor="middle">{dt}</text>')
        # planets
        px0=470
        a(f'<text x="{px0}" y="{py}" fill="{theme["text"]}" font-size="16" font-weight="bold" letter-spacing="1">PIANETI · alzata / tramonto (15 {MONTHS_IT[month][:3]})</text>')
        ry=py+34
        for nm,al,tr,note,st in planets:
            a(f'<circle cx="{px0+6}" cy="{ry-4}" r="4" fill="{theme["status"][st]}"/>')
            a(f'<text x="{px0+20}" y="{ry}" fill="{theme["text"]}" font-size="13.5" font-weight="bold">{nm}</text>')
            a(f'<text x="{px0+115}" y="{ry}" fill="{theme["text2"]}" font-size="12.5">{al} / {tr}</text>')
            a(f'<text x="{px0+20}" y="{ry+15}" fill="{theme["text3"]}" font-size="11.5">{note}</text>')
            ry+=38
        # legend
        ly=1235
        a(f'<line x1="60" y1="{ly-40}" x2="{W-60}" y2="{ly-40}" stroke="{theme["divider"]}" stroke-width="1"/>')
        a(f'<text x="60" y="{ly-16}" fill="{theme["text3"]}" font-size="11.5">Colore stelle = temperatura reale:</text>')
        leg=[(bv2hex(ramp,-0.2),"calde"),(bv2hex(ramp,0.3),"bianche"),(bv2hex(ramp,0.8),"gialle"),(bv2hex(ramp,1.3),"arancioni"),(bv2hex(ramp,1.9),"rosse")]
        lx=290
        for c,lab in leg:
            a(f'<circle cx="{lx}" cy="{ly-20}" r="4.5" fill="{c}"/>')
            a(f'<text x="{lx+9}" y="{ly-16}" fill="{theme["text3"]}" font-size="11.5">{lab}</text>'); lx+=100
        a(f'<line x1="60" y1="{ly}" x2="86" y2="{ly}" stroke="{theme["neon"]}" stroke-width="2" filter="url(#glow)"/>')
        a(f'<text x="94" y="{ly+4}" fill="{theme["text3"]}" font-size="11.5">linee = figure delle costellazioni</text>')
        a(f'<text x="{W-60}" y="{ly+4}" fill="{theme["text4"]}" font-size="10.5" text-anchor="end">Effemeridi per {place} ({lat:.1f}°N, {lon:.1f}°E)</text>')
        a('</svg>')
        with open(out,'w',encoding='utf-8') as fh:
            fh.write('\n'.join(s))
        return out


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--year',type=int,required=True)
    p.add_argument('--month',type=int,required=True)
    p.add_argument('--lat',type=float,default=45.5455)
    p.add_argument('--lon',type=float,default=11.5353)
    p.add_argument('--place',default='Vicenza')
    p.add_argument('--theme',default='brand/palettes/osservatorio.json')
    p.add_argument('--out',default='cielo.svg')
    args=p.parse_args()
    theme=json.load(open(args.theme,encoding='utf-8'))
    eng=Engine()
    out=eng.generate(args.year,args.month,args.lat,args.lon,args.place,theme,args.out)
    print("scritto",out)

if __name__=='__main__':
    main()
