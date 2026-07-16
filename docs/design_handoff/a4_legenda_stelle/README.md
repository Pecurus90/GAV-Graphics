# La legenda «colori delle stelle» rimessa sull'A4 — VERIFICATA

*(Coda aperta da #7h: la proposta B occupava lo spazio della legenda, che fu
tolta dall'A4 mentre il post quadrato la teneva. R10 la rimandava «al giro di
revisione dei design, non una toppa». Questo è quel giro.)*

**Fonte:** designer via claude.ai/design, file `A4 - Legenda stelle.html` nel
progetto «Infografica cielo del mese». Secondo giro: il primo fu rimandato
indietro perché progettato su un disco che finiva a y870
(`BRIEF-a4-legenda-CORREZIONE.md` + `A4-fascia-VERA.png`).

## L'idea del designer, ACCETTATA

La legenda vive nella **striscia fra il bordo inferiore del disco e il divisore**,
e usa **il divisore come propria linea di base**. Sei campioni su **una riga**,
dal più caldo al più freddo. Parata dei pianeti e striscia lunare **non toccate**.

## Verificato dall'architetto sul NOSTRO render, non sul mockup

Numeri estratti da `out/cielo_a4.svg` vero, non dedotti:

| | Valore reale | Il mockup del designer diceva |
|---|---|---|
| Disco | `cx=450 cy=500 r=384` → bordo inferiore **y884** | `cy=520 r=364` → stesso y884 |
| Divisore | **y900** | y900 ✓ |
| «S» cardinale | **y912**, *sotto* il divisore | y912 ✓ |
| Alone | blur gaussiano σ 3,4 su tratto r=384 → sfuma a ~395 | anello finto r=378 sp.10 |

**La striscia è libera nel disco vero** (verificato ritagliando la banda dal PNG
reso: solo il pulviscolo di stelle procedurali del fondo). I campioni stanno a
**r ≥ 400** dal centro: fuori dall'alone. *Nessuna collisione.*

*(Ritrattazione dell'architetto: avevo segnalato un campione dentro l'anello di
alone. Falso — avevo calcolato sulla geometria del mockup, non sulla nostra.)*

## Due correzioni al designer — trovate RENDENDO, non calcolando

1. **Le spaziature non sopravvivono alle nostre etichette.** Il designer spazia i
   primi tre campioni a **64 px**, misurati sulle *sue* temperature corte
   («> 10 000 K»). Le **nostre** sono lunghe («oltre 15.000 K») perché ancorate
   al B-V vero: a 64 px **i testi si scavallano**. Verificato a schermo.
   **Numeri che funzionano** (resi e guardati): `x0=222`, `step=106`, `r=4.5`,
   corpo 11, ultimo campione a x752 → tutto dentro gli 820 px utili.
2. **I sei hex cablati si buttano.** Violerebbero l'invariante #2 e D18: i colori
   delle stelle sono **fisica**, vengono dal `star_ramp` via `bv2hex`. Il
   designer non lo sa (non vede il repo): non è un suo errore, è il nostro
   confine.
   **Anche le sue temperature si buttano**: propone
   «>10.000 · ≈8.000 · ≈6.500 · ≈5.800 · ≈4.500 · <3.500», che **contraddicono**
   quelle del quadrato. Le nostre sono ancorate ai `bv` veri e restano.

## Il lavoro si sgonfia: è DATI, non codice

Il blocco **`swatches` esiste già** (`strumenti/cielo/panels.py:226`) e il suo
commento dice che la **fila orizzontale era proprio l'A4**. #7h l'aveva
semplicemente **rimosso** da `a4.json` (commit `385af71`). Rimetterlo è un blocco
di dati — **zero righe di Python**. Stessa economia di `moon_calendar` in #7h.

Storicamente l'A4 mostrava **parole** («calde · bianche · gialle · arancioni ·
rosse», 5 campioni, step 100). **Marco ha scelto le TEMPERATURE** (2026-07-16),
viste rese entrambe: le parole accanto a un pallino colorato dicono il colore,
non la temperatura — e «colore = temperatura» è *il messaggio* che R10 voleva
rimettere. Le temperature sono anche coerenti col quadrato.

## Il blocco, con i valori verificati

```json
{"type": "swatches", "from": "ramp", "x0": 222, "cy": 891, "step": 106, "r": 4.5,
 "_titolo": "TEMPERATURA STELLE (occhiello a parte, x40 y895, token gold)",
 "label": {"dx": 9, "dy": 4, "fill": "text3", "size": 11},
 "items": [{"bv": -0.33, "label": "oltre 15.000 K"},
           {"bv": 0.0,   "label": "≈ 10.000 K"},
           {"bv": 0.4,   "label": "≈ 7.000 K"},
           {"bv": 0.65,  "label": "≈ 5.800 K"},
           {"bv": 1.3,   "label": "≈ 4.000 K"},
           {"bv": 3.3,   "label": "sotto 3.000 K"}]}
```

più il testino d'occhiello **`TEMPERATURA STELLE`** (x40, y895, `gold`, corpo
10.5, `letter-spacing` 2). I `bv` sono **gli stessi** che usa il quadrato: la
fisica non cambia col formato.

⚠️ **Il titolo è `TEMPERATURA STELLE`, non `COLORI DELLE STELLE`.** #7i ha
rinominato il pannello su **tutti** i quadrati (dashboard · parata · cornice ·
zenit): l'A4 deve seguire, o rimetterebbe il vecchio nome proprio nel giro in cui
gli altri lo abbandonano.

**Muove il golden dell'A4**: movimento **deliberato e contato** — +6 `<circle>`,
+7 `<text>`, il resto identico. Il disco non si tocca.

## La prova

La legenda **è stata resa dal nostro motore e guardata** — non calcolata. La prova
è `LEGENDA-verificata.png`, in questa cartella **ma NON versionata**: `.gitignore`
ha `*.png` globale (scritto per `out/`, si mangia anche gli asset di `docs/`).
Vedi **R12**. Se non la trovi, si rigenera: si innesta il blocco qui sopra in
`a4.json` e si rende `--format a4 --png`.

*Resa prima del rename #7i: mostra ancora l'occhiello «COLORI DELLE STELLE».
Vale per la **geometria**, che è ciò che verifica — non per il testo.*
