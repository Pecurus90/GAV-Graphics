#!/usr/bin/env python3
"""
compose/ - il compositore CONDIVISO (D14).

`Compositor` raccoglie cio' che QUALUNQUE strumento eredita: le primitive di
disegno generiche (testo, riga, pannello, immagine, icona, sfondo), i gradienti/
filtri di marca (`defs_svg`) e - nei prossimi movimenti - il ciclo che cammina i
blocchi di un layout. NON conosce l'astronomia: nessun riferimento a effemeridi,
proiezione, stelle o Messier. E' la meta' che "Pillole di astronomia" (D12)
riusa senza toccare strumenti/cielo/.

Un tempo tutto questo viveva dentro la classe Engine di engine/generate.py: qui
e' stato SPOSTATO tale e quale (refactor puro, output invariato), e Engine ora
lo eredita.
"""
import os, json, base64
from xml.sax.saxutils import escape as _xml_escape
import numpy as np

# Radice del progetto: <root>/compose/compositor.py -> due dirname.
_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Glifi delle icone (dati condivisi, come i font): geometria in viewBox 24.
ICONS_FILE = os.path.join(_BASE, "brand", "icons", "icons.json")


class Compositor:
    """Base condivisa: primitive di disegno generiche + scaffolding di marca.
    Nessuna dipendenza dall'astronomia (invariante del taglio D14)."""

    @staticmethod
    def _esc(s):
        """Escapa il TESTO (contenuto degli elementi, NON gli attributi) per l'XML:
        `&`, `<`, `>` diventano entita'. Serve perche' del testo puo' contenere
        caratteri speciali - su tutti il NOME DEL LUOGO, input LIBERO dell'utente
        (`--place` da CLI, parametro `place` sul web): «Bassano & Dintorni» senza
        escaping produce un SVG malformato che resvg (e minidom) rifiutano - un 500
        sul PC del socio (D4). Si applica al RISULTATO del testo, mai al template ne'
        agli attributi (quelli non ricevono input dell'utente)."""
        return _xml_escape(str(s))

    # ---- render: componenti riutilizzabili ----
    def defs_svg(self, theme, extra_gradients=""):
        """Gradienti e filtri (glow) di MARCA: lo sfondo `bg` e i due glow. Roba
        generica, la vuole qualunque strumento. `extra_gradients` e' una stringa
        di definizioni IN PIU' che uno strumento inserisce (il Cielo del Mese ci
        mette il gradiente del disco): cosi' compose/ non conosce piu' il token
        'disk' (era l'ultima venatura di cielo qui, sciolta in #7f). Vanno messi
        una volta per SVG."""
        bg = (f'<radialGradient id="bg" cx="50%" cy="38%" r="75%">'
              f'<stop offset="0%" stop-color="{theme["bg"][0]}"/>'
              f'<stop offset="55%" stop-color="{theme["bg"][1]}"/>'
              f'<stop offset="100%" stop-color="{theme["bg"][2]}"/></radialGradient>')
        glow = ('<filter id="glow" x="-60%" y="-60%" width="220%" height="220%">'
                '<feGaussianBlur stdDeviation="2.2" result="b"/><feMerge>'
                '<feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>')
        soft = ('<filter id="softglow" x="-80%" y="-80%" width="260%" height="260%">'
                '<feGaussianBlur stdDeviation="3.4"/></filter>')
        mid = (extra_gradients + "\n") if extra_gradients else ""
        return f'<defs>\n{bg}\n{mid}{glow}\n{soft}\n</defs>'

    def _render_text(self, b, theme, ctx):
        """Primitiva testo. Ordine di attributi canonico (ricavato dall'A4):
        x, y, fill, font-size, [font-weight], [text-anchor], [letter-spacing].
        `content` e' un template riempito da `ctx` (o dai campi di un item)."""
        s=(f'<text x="{b["x"]}" y="{b["y"]}" fill="{theme[b["fill"]]}" '
           f'font-size="{b["size"]}"')
        if b.get("weight"): s+=f' font-weight="{b["weight"]}"'
        if b.get("anchor"): s+=f' text-anchor="{b["anchor"]}"'
        if "letter_spacing" in b: s+=f' letter-spacing="{b["letter_spacing"]}"'
        return s+f'>{self._esc(b["content"].format(**ctx))}</text>'

    def _render_line(self, b, theme):
        s=(f'<line x1="{b["x1"]}" y1="{b["y1"]}" x2="{b["x2"]}" y2="{b["y2"]}" '
           f'stroke="{theme[b["stroke"]]}" stroke-width="{b["stroke_width"]}"')
        if b.get("filter"): s+=f' filter="url(#{b["filter"]})"'
        return s+'/>'

    def _render_panel(self, b, theme):
        """Pannello: rettangolo (arrotondato con `rx`) usato come CONTENITORE nei
        design social. Primitiva NUOVA in #6d: i tre mockup incorniciano pianeti,
        luna e colori in pannelli, e nessuna primitiva esistente disegna un
        riquadro. Fill e stroke sono TOKEN del tema (mai hex cablati).
        `fill_opacity`/`opacity` (opzionali) rendono il pannello TRANSLUCIDO: il
        vetro colorato di Zenit sopra il disco a tutto campo (niente blur, che
        resvg non ha - D7). Emessi solo se presenti: l'output di chi non li usa
        (a4/dashboard/...) NON cambia."""
        s=(f'<rect x="{b["x"]}" y="{b["y"]}" width="{b["w"]}" height="{b["h"]}" '
           f'rx="{b.get("rx",0)}" fill="{theme[b["fill"]]}"')
        if "fill_opacity" in b: s+=f' fill-opacity="{b["fill_opacity"]}"'
        if b.get("stroke"):
            s+=f' stroke="{theme[b["stroke"]]}" stroke-width="{b.get("stroke_width",1)}"'
            if "stroke_opacity" in b: s+=f' stroke-opacity="{b["stroke_opacity"]}"'
        if "opacity" in b: s+=f' opacity="{b["opacity"]}"'
        return s+'/>'

    def _render_image(self, b):
        """Incorpora un'immagine raster (es. il logo) come data URI base64: nell'
        SVG finale NON resta alcun riferimento a file esterni, quindi funziona
        offline e dentro l'.exe (D4). Posizione e dimensione FISSE dal file (non
        relative al testo: il titolo cambia lunghezza ogni mese e un logo
        agganciato al testo ballerebbe). `href` e' un percorso relativo alla
        radice del progetto."""
        with open(os.path.join(_BASE, b["href"]), "rb") as fh:
            data=base64.b64encode(fh.read()).decode("ascii")
        mime=b.get("mime", "image/png")
        return (f'<image x="{b["x"]}" y="{b["y"]}" width="{b["w"]}" height="{b["h"]}" '
                f'href="data:{mime};base64,{data}"/>')

    def _icons(self):
        """Carica (una volta) i glifi delle icone da brand/icons/icons.json."""
        if not hasattr(self, "_icons_cache"):
            with open(ICONS_FILE, encoding="utf-8") as fh:
                self._icons_cache=json.load(fh)
        return self._icons_cache

    def _render_icon(self, b, theme):
        """Glifo icona (Simple Icons/CC0 + envelope generica) posato a (x,y) e
        scalato da `size` (i glifi sono in viewBox 24). Il colore viene da un
        TOKEN del tema (mai cablato): l'icona si ricolora con la palette."""
        g=self._icons()[b["name"]]
        s=b["size"]/24.0
        col=theme[b["fill"]]
        if g.get("stroke"):
            # Icona A TRATTO (convenzione Lucide: griglia 24, tratto 2, estremi
            # tondi) - manuale sez.7. Additivo: senza la chiave "stroke" si resta
            # sul glifo pieno di prima, byte per byte.
            pen=(f'fill="none" stroke="{col}" stroke-width="2" '
                 f'stroke-linecap="round" stroke-linejoin="round"')
        else:
            pen=f'fill="{col}"'+(f' fill-rule="{g["fill_rule"]}"' if g.get("fill_rule") else "")
        return (f'<g transform="translate({b["x"]},{b["y"]}) scale({s:.5f})">'
                f'<path d="{g["d"]}" {pen}/></g>')

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

    # ---- il compositore: cammina i blocchi di un layout (D7) ----
    def _compose(self, layout, theme, ctx, out, tool_ctx=None):
        """Cammina i blocchi del layout e assembla l'SVG. Tool-AGNOSTICO: non sa
        nulla di cielo, effemeridi o Messier. Ogni strumento (oggi il Cielo del
        Mese; domani Pillole, D12) prepara `ctx` (i testi) e l'eventuale
        `tool_ctx` (i dati specifici che i suoi blocchi consumano), poi chiama
        qui. Questa e' la meta' che si eredita. L'output e' identico a prima: la
        stringa dell'SVG e' composta esattamente come faceva Engine.generate."""
        cv=layout['canvas']; cw,ch=cv['w'],cv['h']
        s=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{cw}" height="{ch}" viewBox="0 0 {cw} {ch}" font-family="{cv["font_family"]}">',
           self.defs_svg(theme)]
        for b in layout['blocks']:
            s.append(self._render_block(b, theme, ctx, cw, ch, tool_ctx))
        s.append('</svg>')
        with open(out,'w',encoding='utf-8') as fh:
            fh.write('\n'.join(s))
        return out

    def _render_block(self, b, theme, ctx, w, h, tool_ctx):
        """Dispatch di un blocco sulla primitiva giusta. Qui vivono SOLO i tipi
        generici (quelli che Pillole riuserebbe); i tipi di uno strumento sono
        gestiti dal suo override di `_render_block_tool`."""
        t=b["type"]
        if t=="background":   return self._render_background(b, theme, w, h)
        if t=="text":         return self._render_text(b, theme, ctx)
        if t=="line":         return self._render_line(b, theme)
        if t=="panel":        return self._render_panel(b, theme)
        if t=="image":        return self._render_image(b)
        if t=="icon":         return self._render_icon(b, theme)
        return self._render_block_tool(b, theme, ctx, w, h, tool_ctx)

    def _render_block_tool(self, b, theme, ctx, w, h, tool_ctx):
        """Hook per i tipi di blocco SPECIFICI di uno strumento. La base non ne
        conosce: uno strumento lo sovrascrive. Senza override, tipo sconosciuto."""
        raise ValueError(f"tipo di blocco sconosciuto nel layout: {b['type']!r}")
