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
from .catalog import (MONTHS_IT, DIREZIONI_IT, CONST_IT, MARQUEE, STARS, PLANETS,
                      PLANET_SHAPES, CX, CY, R, MoonPhase, MoonDay, Planet,
                      SkyData, hex2rgb, rgb2hex, bv2hex, point_in_poly)

# file di layout di default: la composizione A4 come dati (D7)
# radice del progetto: <root>/strumenti/cielo/engine.py -> tre dirname.
_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_LAYOUT = os.path.join(_BASE, "brand", "layouts", "a4.json")


class Engine(Compositor, MessierMixin):
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
