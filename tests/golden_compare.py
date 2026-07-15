"""
Confronto golden a TOLLERANZA (D5) — solo per i test, non tocca il motore.

PERCHE': i golden sono generati su Windows con una certa numpy. Su un altro
OS/numpy (GitHub Actions, D4) l'ultima cifra delle coordinate cambia SENZA che
nulla sia rotto. Un confronto byte-a-byte diventerebbe ROSSO fantasma. Qui il
RIFERIMENTO resta intatto: cambia solo il MODO di confrontarlo.

Come:
- si TOKENIZZA l'SVG in parti NUMERICHE (le coordinate/%.Nf) e NON-numeriche
  (nomi di elementi/attributi, testo, e soprattutto i COLORI #hex);
- i numeri si confrontano con TOLLERANZA ASSOLUTA (`TOL`);
- tutto il resto — inclusi i colori — si confronta ESATTO.

LA TRAPPOLA (gestita): un colore come `#0c1330` contiene cifre ma NON e' un
numero-da-tollerare. Nell'alternanza del tokenizzatore `#hex` viene PRIMA dei
numeri, quindi non viene mai spezzato in cifre: resta un token unico, esatto.

LA TOLLERANZA (0.15 px) e' scelta sui FATTI dell'output, non a caso:
- le coordinate proiettate (stelle, linee delle costellazioni) — quelle che
  derivano dall'astronomia e quindi possono derivare tra piattaforme — sono
  formattate `%.1f` (una cifra: passo 0.1). Una deriva d'ultima-cifra fa saltare
  il valore di UN passo intero = 0.1 px. La tolleranza deve stare SOPRA 0.1.
- 0.15 sta sopra lo 0.1 del salto `%.1f` (con margine) e MOLTO sotto 1.0: una
  regressione di 1 px fallisce con ~7x di margine, e anche uno spostamento reale
  di 0.3 px viene preso. 0.15 px e' comunque invisibile a qualsiasi scala.
"""
import re

TOL = 0.15

# Alternanza ORDINATA: prima i colori #hex (atomici, esatti), poi i numeri
# (float o interi, con segno), poi i blocchi non-speciali, infine il singolo
# carattere di fallback. L'ordine e' cio' che impedisce a `#0c1330` di essere
# letto come cifre.
_TOKEN = re.compile(r'#[0-9a-fA-F]{3,8}|-?\d+\.\d+|-?\d+|[^#\-\d]+|.')
_NUM = re.compile(r'-?\d+\.\d+|-?\d+')


def _tokenize(s):
    """(kind, valore, testo) per ogni token. kind 'num' -> confronto a tolleranza;
    'str' (tutto il resto, #hex compresi) -> confronto esatto."""
    out = []
    for m in _TOKEN.finditer(s):
        t = m.group(0)
        if t[0] != '#' and _NUM.fullmatch(t):
            out.append(('num', float(t), t))
        else:
            out.append(('str', t, t))
    return out


def svg_diff(generated, golden, tol=TOL):
    """None se `generated` combacia col `golden` (numeri entro `tol`, tutto il
    resto ESATTO), altrimenti un messaggio che localizza la prima divergenza.
    Non solleva: chi chiama decide (pytest.fail) — cosi' il messaggio e' pulito."""
    g = _tokenize(generated)
    r = _tokenize(golden)
    if len(g) != len(r):
        return (f"struttura diversa: {len(g)} token generati vs {len(r)} golden "
                f"(un cambiamento strutturale, non deriva numerica)")
    for i, (a, b) in enumerate(zip(g, r)):
        if a[0] == 'num' and b[0] == 'num':
            d = abs(a[1] - b[1])
            if d > tol:
                return (f"numero fuori tolleranza (Δ={d:.4f} > {tol}) al token {i}: "
                        f"generato {a[2]!r} vs golden {b[2]!r}")
        elif a[2] != b[2]:
            return (f"parte non-numerica diversa al token {i} "
                    f"(nome/testo/COLORE, confronto esatto): "
                    f"generato {a[2]!r} vs golden {b[2]!r}")
    return None
