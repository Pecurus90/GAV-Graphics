#!/usr/bin/env python3
"""
strumenti/cielo/disc.py - il DISCO SIGILLATO del cielo.

La geometria del disco notturno (D7): cornice, stelle nei loro colori reali,
linee delle costellazioni, etichette (stelle guida + nomi delle costellazioni
PRINCIPALI), tacche di azimut, cardinali; piu' l'anti-collisione delle etichette
del percorso social. Esce come frammento SVG auto-contenuto, in coordinate
proprie: chi compone lo scala e lo posiziona, non lo ridisegna. Un mixin di Engine.

Legge CONST_IT (le costellazioni PRINCIPALI) da catalog: e' il vocabolario di
etichette dell'A4. NON conosce CONST_IT_MINORI (vive in messier.py): il confine
del banco-di-prova #7d-ter e' qui, a livello di file.
"""
import numpy as np

from .catalog import CONST_IT, MARQUEE, STARS, bv2hex, R


class DiscMixin:
    @staticmethod
    def _disk_gradient(theme):
        """Il gradiente radiale del DISCO cielo (token 'disk'): e' roba di cielo,
        non di marca, quindi vive qui e non in compose/defs_svg (#7f, D13). Engine
        lo inserisce nel <defs> tramite il suo override di defs_svg."""
        return (f'<radialGradient id="disk" cx="50%" cy="46%" r="55%">'
                f'<stop offset="0%" stop-color="{theme["disk"][0]}"/>'
                f'<stop offset="80%" stop-color="{theme["disk"][1]}"/>'
                f'<stop offset="100%" stop-color="{theme["disk"][2]}"/></radialGradient>')

    def sky_disc_svg(self, cx, cy, rad, lst, lat_rad, theme, ramp=None,
                     cardinals=True, labels=True, marquee=True, ticks=None,
                     star_names=None, declutter=False, clip_id='dclip',
                     figure_stars=False, cardinal_gap=22):
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
            # kind='stable': il 98% delle stelle e' in pareggio di magnitudine e un
            # sort instabile rompe il pareggio in modo diverso per CPU/build numpy
            # -> ordine di disegno diverso su ogni piattaforma (invariante #6 violato,
            # stanato dalla CI). 'stable' fissa il tie-break all'indice originale.
            for i in np.argsort(-self.smag, kind='stable'):
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
                    a(f'<text x="{x+7*k:.1f}" y="{y-5*k:.1f}" fill="{theme["text"]}" font-size="{11.5*k:.1f}" opacity="0.95">{self._esc(nm)}</text>')
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
                    a(f'<text x="{x.mean():.1f}" y="{y.mean():.1f}" fill="{theme["label"]}" font-size="{12.5*k:.1f}" opacity="0.82" text-anchor="middle" letter-spacing="0.5">{self._esc(CONST_IT[ab])}</text>')
        else:
            # PERCORSO SOCIAL: dischi delle stelle nominate + etichette con
            # ANTI-COLLISIONE deterministica (vedi _disc_labels_declutter).
            # I CARDINALI sono OSTACOLI per l'anti-collisione: il disco non si
            # scrive addosso. Box calcolato qui (i cardinali si DISEGNANO piu'
            # sotto, invariati). Quando i cardinali stanno FUORI dal bordo
            # (cardinal_gap>0, come A4/dashboard/parata) il box cade oltre la zona
            # delle etichette (rad-3) e non cambia NESSUN piazzamento; conta solo
            # dove i cardinali stanno DENTRO (gap negativo, Zenit rientrato).
            # Ostacoli dell'anti-collisione: cardinali + TACCHE (anch'esse le
            # disegna il disco: una tacca sopra un nome e' il disco che si scrive
            # addosso). Le tacche stanno FUORI dal bordo (rad..rad+len): contano
            # solo per le etichette che arrivano fin li' col loro riquadro.
            avoid = (self._cardinal_boxes(cx, cy, rad, k, cardinals, cardinal_gap)
                     + self._tick_boxes(cx, cy, rad, k, ticks))
            a(self._disc_labels_declutter(cx, cy, rad, k, lst, lat_rad, theme,
                                          ramp, labels, marquee, star_names, avoid))
        # tacche di azimut (corona SOLO tacche, niente numeri: a 1080 i numeri
        # sono rumore). Default SPENTA -> l'A4 non la disegna. `ticks` e' un dict
        # {"minor":10,"major":30}: una tacca ogni `minor` gradi, piu' lunga ogni
        # `major`. Geometria del disco (D7), stessa proiezione dei cardinali.
        if ticks:
            a(self._disc_ticks(cx, cy, rad, k, theme, ticks))
        # punti cardinali
        if cardinals:
            # `cardinal_gap` (default 22): quanto FUORI dal bordo cadono le lettere,
            # in unita' del disco di riferimento (scalate da k). Additivo - assente
            # -> +22 come sempre. Zenit, col disco che SBORDA il canvas (rad 560),
            # lo mette NEGATIVO per portarle appena DENTRO il canvas (invariante #3:
            # N in alto, E a sinistra = orientamento, identita' visiva). Non tocca
            # la proiezione: solo dove finisce la lettera.
            for lab,ang in (('N',0),('E',90),('S',180),('O',270)):
                rr=rad+cardinal_gap*k; ax=cx-rr*np.sin(np.radians(ang)); ay=cy-rr*np.cos(np.radians(ang))
                a(f'<text x="{ax:.1f}" y="{ay+6*k:.1f}" fill="{theme["cardinal"]}" font-size="{19*k:.1f}" font-weight="bold" text-anchor="middle">{self._esc(lab)}</text>')
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

    @staticmethod
    def _cardinal_boxes(cx, cy, rad, k, cardinals, cardinal_gap):
        """I riquadri (x0,y0,x1,y1) dei 4 cardinali, alle STESSE coordinate a cui
        li disegna sky_disc_svg (ancora middle, corpo 19k, baseline a ay+6k). Servono
        all'anti-collisione come ostacoli: cosi' le etichette non finiscono sotto
        N/E/S/O. Vuoto se `cardinals` e' spento."""
        if not cardinals:
            return []
        s = 19 * k; hw = s * 0.55          # mezza larghezza: lettera + margine
        boxes = []
        for ang in (0, 90, 180, 270):
            rr = rad + cardinal_gap * k
            ax = cx - rr * np.sin(np.radians(ang)); ay = cy - rr * np.cos(np.radians(ang))
            by = ay + 6 * k
            boxes.append((ax - hw, by - s * 0.85, ax + hw, by + s * 0.15))
        return boxes

    @staticmethod
    def _tick_boxes(cx, cy, rad, k, ticks, margin=2.0):
        """I riquadri delle tacche (dai loro estremi in _disc_ticks), con un piccolo
        margine, per l'anti-collisione. Vuoto se non ci sono tacche. Stanno FUORI
        dal bordo (rad..rad+len): toccano solo le etichette che arrivano al bordo."""
        if not ticks:
            return []
        minor = ticks.get("minor", 10); major = ticks.get("major", 30)
        minl = ticks.get("minor_len", 9.0) * k; majl = ticks.get("major_len", 17.0) * k
        boxes = []
        for az in range(0, 360, minor):
            t = majl if az % major == 0 else minl
            ar = np.radians(az)
            x1 = cx - rad * np.sin(ar); y1 = cy - rad * np.cos(ar)
            x2 = cx - (rad + t) * np.sin(ar); y2 = cy - (rad + t) * np.cos(ar)
            boxes.append((min(x1, x2) - margin, min(y1, y2) - margin,
                          max(x1, x2) + margin, max(y1, y2) + margin))
        return boxes

    def _disc_labels_declutter(self, cx, cy, rad, k, lst, lat_rad, theme, ramp,
                               labels, marquee, star_names, card_boxes=()):
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
        placed=list(card_boxes); dropped=0; dropped_labels=[]; STEP=6*k
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
                       f'font-size="{req["size"]:.1f}" opacity="{req["opacity"]}"{anc}{req["extra"]}>{self._esc(req["text"])}</text>')
        self._last_dropped=dropped; self._last_dropped_labels=dropped_labels
        return '\n'.join(out)

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
                                 figure_stars=b.get("figure_stars", False),
                                 cardinal_gap=b.get("cardinal_gap", 22))
