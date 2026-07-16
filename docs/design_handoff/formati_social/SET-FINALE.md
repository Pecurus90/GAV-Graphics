# Il set finale dei formati quadrati — DECISO

*(Designer via claude.ai/design, `Formati - Set Finale.dc.html`. Mappatura
approvata da Marco, 2026-07-16. Supera la nota "decisione rimandata" del README
di questa cartella.)*

## Il set: QUATTRO quadrati, quattro assi di lettura

| Formato | Esito | Al posto di | Disposizione |
|---|---|---|---|
| **dashboard** | **TENUTO** (intatto) | — | griglia modulare · l'àncora |
| **Parata** | **NUOVO** | ← colonna | corsie orizzontali |
| **Cornice** | **NUOVO** | ← editoriale | poster incorniciato verticale |
| **Zenit** | **NUOVO** | ← post | immersivo, disco a tutto campo |

**Ritirati: `post`, `editorial`, `rail`.** Ogni ritirato ha un erede; nessuna
coppia condivide la disposizione.

## Perché `post` esce — verificato dall'architetto, ed è peggio di come il designer l'ha detto

Il designer: *«post è l'unico che salta un blocco di contenuto (niente legenda
colori stelle) e rompe la regola stesso-contenuto»*. **Vero, e c'è di più**
(contato sui layout):

| | `swatches` (legenda stelle) | luna |
|---|---|---|
| **post** | **0** ❌ | `moon_panel` (le vecchie 4 fasi) |
| dashboard · editorial · rail | 1 ✓ | `moon_calendar` (striscia 1→31) |

`post` usa ancora **il vecchio pannello lunare a 4 fasi** che tutti gli altri hanno
abbandonato. **Non è "il minimale per scelta": è quello che nessuno ha aggiornato.**
Debito tecnico con un nome. Il suo ruolo ("pulito, senza cornice") passa a **Zenit**,
che però ha *tutto* il contenuto.

## Conseguenza: il DEFAULT cambia

`post` era il default in `app/main.py` **e il render della CI** (`ci.yml`).

**ESITO (#7i, 2026-07-16): il default è `dashboard`, non Zenit.**
La regola era: il default si sposta **solo dopo** aver visto Zenit reso — e se non
convince, si ripiega su `dashboard`. **Zenit è stato costruito, reso e guardato:
Marco ha scelto `dashboard`.** Zenit resta nel set, non è il default.
*(Questo paragrafo diceva «il nuovo default è ZENIT»: corretto dopo la prova.
Il cancello "prima vederlo reso" ha funzionato — è servito a questo.)*

## Costo (verificato)

- **Parata, Cornice: costo zero** — blocchi già esistenti (`planet_parade` dall'A4,
  `moon_calendar` regge sia striscia 31 sia griglia 8×4, `swatches` ha `label2`).
- **Zenit: fattibile**, ma il "vetro sfocato" è reso come **pannello translucido**
  (il backdrop-blur non esiste in resvg; niente finta-sfocatura, D7). Il disco a
  tutto campo è scala+posizione del frammento sigillato: lecito.
