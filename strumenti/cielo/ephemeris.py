#!/usr/bin/env python3
"""
strumenti/cielo/ephemeris.py - le EFFEMERIDI e la proiezione.

La parte "viva" dell'astronomia (skyfield): posizione di stelle/pianeti nel cielo
(altaz), proiezione azimutale equidistante sul disco (project), tempo siderale
(sky_context), fasi e illuminazione della Luna, alzate/tramonti e visibilita' dei
pianeti, e l'assemblaggio di SkyData. Un mixin di Engine: i dati (self.ts,
self.eph, self.stars) li prepara Engine.__init__.

E' il codice piu' PESANTE in dipendenze (skyfield, pytz): tenerlo separato rende
esplicito che Pillole non lo eredita.
"""
import calendar
from datetime import datetime
import numpy as np
import pytz
from skyfield.api import wgs84
from skyfield import almanac

from .catalog import (CX, CY, R, DIREZIONI_IT, PLANETS, PLANET_SHAPES,
                      MoonPhase, MoonDay, Planet, SkyData)


class EphemerisMixin:
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
