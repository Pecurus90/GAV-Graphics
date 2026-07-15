#!/usr/bin/env python3
"""
strumenti/cielo/panels.py - i PANNELLI del Cielo del Mese.

Le primitive di blocco specifiche del cielo che disegnano CONTENUTO tabellare o
iconico: la tabella dei pianeti, il pannello e il calendario delle fasi lunari,
i campioni di colore delle stelle (legenda B-V). Un mixin: Engine lo eredita.

NON sono primitive generiche (quelle stanno in compose/): un pianeta con la sua
visibilita', una fase lunare, un campione di colore stellare sono roba di cielo.
"""
from .catalog import bv2hex


class PanelsMixin:
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

    def _render_planet_parade(self, b, theme, data):
        """Parata ORIZZONTALE dei pianeti (proposta B del designer, A4): una
        colonna per pianeta, pallino colorato in cima (colore REALE dal tema,
        anello per Saturno dal DATO `shape`), poi nome, alzata/tramonto e nota
        su righe centrate, con un divisore verticale fra le colonne. E' la corsia
        SUPERIORE della fascia inferiore: non condivide spazio verticale con la
        striscia lunare (corsia sotto), quindi non collidono mai (risolve R10).

        Diverso da `planet_panel` (righe verticali, un pianeta sotto l'altro):
        qui i pianeti stanno IN FILA. Il FILE possiede geometria e stile (x0,
        col_step, cy_dot, le parti di testo coi loro dy/content); il CODICE mette
        il colore del pianeta e la forma ad anello, che vengono dal dato."""
        out=[]
        x0,step,cyd,r=b["x0"],b["col_step"],b["cy_dot"],b["r"]
        planets=data.planets
        # divisori verticali fra le colonne (n-1), a meta' fra due pianeti.
        sep=b.get("sep")
        if sep:
            for i in range(len(planets)-1):
                sx=x0+step*(i+0.5)
                out.append(f'<line x1="{sx:.1f}" y1="{sep["y1"]}" x2="{sx:.1f}" y2="{sep["y2"]}" '
                           f'stroke="{theme[sep["stroke"]]}" stroke-width="{sep["width"]}"/>')
        for i,pl in enumerate(planets):
            cx=x0+i*step
            col=theme["planet_colors"][pl.name]        # colore reale per-pianeta
            out.append(f'<circle cx="{cx:.1f}" cy="{cyd}" r="{r}" fill="{col}"/>')
            if pl.shape=="ringed":                      # Saturno: l'anello dal dato
                rg=b["ring"]
                out.append(f'<ellipse cx="{cx:.1f}" cy="{cyd}" rx="{r*rg["rx"]:.2f}" '
                           f'ry="{r*rg["ry"]:.2f}" fill="none" stroke="{col}" '
                           f'stroke-width="{rg["width"]}" transform="rotate({rg["rot"]} {cx:.1f} {cyd})"/>')
            # nota su due righe, COMPATTA per la colonna stretta (~117px): la
            # riga 1 e' la CATEGORIA (la nota fino alla virgola: "Visibile
            # serale", "Telescopico", "Non osservabile"); la riga 2 e' DOVE
            # guardare (la direzione), o - per i pianeti senza direzione (muted,
            # o sotto l'orizzonte) - la CODA della nota dopo la virgola ("vicino
            # al Sole"). Nessun testo inventato: sono le stringhe del motore,
            # spezzate sulla sua stessa virgola. Deriva di PRESENTAZIONE (come
            # note_dir in planet_panel), non contenuto nuovo.
            cat, _, tail = pl.note.partition(", ")
            item={"name":pl.name,"rise":pl.rise,"set":pl.set_,
                  "note":pl.note,"direction":pl.direction,
                  "note_cat":cat,"note_where":pl.direction or tail}
            # righe di testo centrate sulla colonna: quali e come le decide il FILE
            # (name, rise, set, note1, note2). Ogni parte porta il proprio content.
            for part in ("name","rise","set","note1","note2"):
                if part not in b:
                    continue
                p=b[part]
                tb={"x":f"{cx:.1f}","y":cyd+p["dy"],"fill":p["fill"],"size":p["size"],
                    "weight":p.get("weight"),"anchor":"middle","content":p["content"]}
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
