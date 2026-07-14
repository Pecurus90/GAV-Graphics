#!/usr/bin/env python3
"""
strumenti/cielo/catalog.py - i DATI e le funzioni pure del Cielo del Mese.

Cataloghi astronomici (stelle guida, pianeti), costanti di presentazione (mesi,
direzioni), il contratto dei dati (le dataclass di SkyData) e gli helper puri di
colore (B-V -> hex) e geometria (inviluppo convesso, punto-in-poligono).

Sta in fondo alla catena degli import di cielo: NON importa nessun altro modulo
di cielo (ne' i mixin, ne' engine), cosi' i mixin possono pescare di qui senza
cicli. Non conosce l'astronomia "viva" (skyfield): sono dati e matematica pura.

I nomi delle costellazioni NON vivono qui: CONST_IT sta con il disco (disc.py),
CONST_IT_MINORI con la pagina 2 (messier.py) - vedi la nota sul confine in
quei file.
"""
from dataclasses import dataclass

MONTHS_IT = ["", "gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno",
             "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"]

# rosa a 8 settori in italiano (azimut 0=Nord, 90=Est, orario): indice = round(az/45)%8
DIREZIONI_IT = ["Nord", "Nord-Est", "Est", "Sud-Est", "Sud", "Sud-Ovest", "Ovest", "Nord-Ovest"]

# Nomi italiani delle costellazioni PRINCIPALI: sono quelle che l'A4/pagina 1
# etichetta sul disco (le legge sky_disc_svg, in disc/engine). NON allargare
# questo dizionario: e' sorvegliato dai golden (l'A4 disegna un'etichetta per
# ogni voce sopra l'orizzonte). Le MINORI vivono in messier.py (CONST_IT_MINORI),
# che SOLO la pagina 2 legge: cosi' aggiungere un nome minore non puo' muovere
# l'output dell'A4 (il confine del banco-di-prova #7d-ter, ora a livello di file).
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
