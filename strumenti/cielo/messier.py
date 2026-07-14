#!/usr/bin/env python3
"""
strumenti/cielo/messier.py - il PROFONDO CIELO (pagina 2, D9).

Catalogo Messier, geometria dei simboli d'atlante, tabella "meglio piazzati",
e il TERZO strato di etichette (i nomi delle costellazioni, #7d/bis/ter/quater).
E' un mixin: la classe Engine lo eredita, cosi' i metodi trovano via self la
proiezione e le effemeridi (altaz/project) senza importarle.

Il vocabolario dei nomi minori (CONST_IT_MINORI) vive QUI e non in catalog: e' il
confine del banco-di-prova #7d-ter reso file. Il disco dell'A4 legge solo
CONST_IT (catalog) e non ha modo di vedere queste voci.
"""
import json
import numpy as np

from .catalog import CONST_IT, convex_hull, point_in_poly


# Le costellazioni MINORI: le 44 restanti, aggiunte in #7d-ter (approvate da
# Marco), cosi' la PAGINA 2 in modo "tutte" puo' nominare ogni figura sopra
# l'orizzonte. Vivono QUI, nella pagina 2, e NON in catalog con CONST_IT: il
# disco dell'A4 (sky_disc_svg) non le vede, quindi aggiungerne una non puo'
# muovere il golden dell'A4. E' il confine del banco-di-prova (#7d-ter), reso
# esplicito a livello di file. FONTE: Wikipedia in italiano, "Lista delle
# costellazioni" (https://it.wikipedia.org/wiki/Lista_delle_costellazioni), nomi
# UAI. Con UNA eccezione VOLUTA: Norma -> "Squadra" (NON "Regolo": collide con la
# stella Regolo/Regulus, gia' in STARS). DATO curato: per cambiarne uno, una riga.
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


class MessierMixin:
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
