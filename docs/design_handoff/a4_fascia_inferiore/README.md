# Handoff — A4, ridisegno della fascia inferiore

*(Designer via claude.ai/design, 2026-07-15. Consegna in risposta al brief
`BRIEF-A4-fascia-inferiore.md`. Verificata dall'architetto renderizzando gli SVG
col nostro `render.py`: rendono in resvg, usano i `data-token` del tema, fasi
lunari come archi vettoriali. Traducibile, non solo bella in un browser.)*

## Il problema che risolve

Nell'A4 (l'unico formato mai passato dal designer) il pannello **fasi lunari**
(4 fasi a tutta larghezza) si sovrapponeva al pannello **pianeti** (7 voci, metà
destra). Vedi **R10** in `CLAUDE.md`.

## La soluzione — DUE CORSIE ORIZZONTALI

Pianeti sopra, fasi lunari sotto, un divisore in mezzo: **non condividono mai lo
spazio verticale**, quindi non collidono nemmeno con 7+ pianeti. Lo spazio
verticale è assegnato una volta sola.

## Scelta di Marco: **PROPOSTA B — "Schieramento"**

I 7 pianeti in **fila unica** (parata), ciascuno con alzata ↑ / tramonto ↓ e nota;
sotto, la **striscia lunare 1→31** a tutta larghezza con le 4 fasi principali
evidenziate. Coerente col dashboard del carosello.
Vedi `PROPOSTA-B-scelta.png` (render col nostro motore) e la proposta B dentro
`A4 - Fascia inferiore.html`.

## Note per la traduzione (#7h)

- **La striscia lunare 1→31 è il blocco `moon_calendar`** che `dashboard.json`
  **già usa**: si riusa, non si riscrive.
- Il designer ha **hardcoded** i colori (es. i pallini dei pianeti) ma ha
  annotato ogni elemento con `data-token`: in traduzione i colori vengono dalla
  **palette**, non dagli hex del mockup. In particolare `planet_colors` deve
  restare per-pianeta (onestà astronomica: Marte rossastro, Nettuno bluastro).
- Il disco nell'SVG è un **segnaposto** ("DISCO DEL CIELO · resta invariato"): non
  si tocca, viene dal motore. #7h cambia **solo la fascia inferiore** (sotto il
  disco) + il logo in testata (che arriva già da #7g).
