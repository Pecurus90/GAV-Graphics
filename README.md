# Cielo del Mese — generatore

Genera un volantino del cielo notturno (SVG/PNG/PDF) per un dato **mese, anno e
località**, con **fasi lunari** e **pianeti** calcolati automaticamente e stelle
nei loro **colori reali**. I colori del volantino arrivano da un **file di tema**
intercambiabile, così la palette si cambia senza toccare il codice.

Sviluppato a partire da un prototipo; questo README serve anche da **briefing per
Claude Code** (vedi ultima sezione).

---

## Cosa c'è già (funziona)

- `engine/generate.py` — il **motore**. Proietta un catalogo stellare reale sul
  cielo di quella data/località, disegna costellazioni (linee neon) e stelle
  (colore per indice B‑V), calcola fasi lunari e alzata/tramonto dei pianeti,
  classifica la visibilità e produce un **SVG A4**.
- `data/` — catalogo stelle (`stars6.json`) e linee costellazioni
  (`const_lines.json`). L'effemeride planetaria (`de421.bsp`) arriva dal pacchetto
  `skyfield-data`, nessun download runtime.
- `themes/osservatorio.json` — la palette come **token**. Per una nuova palette:
  copia il file, cambia i valori, passala con `--theme`.
- `app/main.py` — **scheletro** di web app (FastAPI): form → anteprima → download
  SVG/PNG/PDF.

## Avvio rapido

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 1) solo motore, da riga di comando:
python engine/generate.py --year 2026 --month 8 --place Vicenza \
    --lat 45.5455 --lon 11.5353 --theme themes/osservatorio.json --out cielo.svg

# 2) web app:
uvicorn app.main:app --reload --port 8000
# apri http://localhost:8000
```

## Come cambiare palette

Duplica `themes/osservatorio.json`, modifica i colori (i più incisivi: `neon`,
`bg`, `gold`, `text`, `star_ramp`) e rigenera con `--theme themes/tua.json`.
L'effetto "neon sfumato" = colore `neon` + glow: nel SVG è un blur gaussiano;
se porti la grafica sul web usa `filter: drop-shadow(0 0 6px <neon>)`.

---

## Limiti noti / scelte oneste

- **Visibilità pianeti = euristica.** La classificazione ok/telescopico/difficile/
  non-osservabile usa elongazione dal Sole + altezza notturna massima. È
  ragionevole ma semplificata: niente magnitudine reale, niente crepuscolo
  preciso. Da rifinire se serve rigore.
- **Etichette fisse.** I nomi di costellazioni/stelle sono posizionati al
  centroide/accanto al punto: mese per mese possono **sovrapporsi**. Manca un
  algoritmo anti-collisione (è il pezzo di ingegneria più corposo per
  l'automazione).
- **Orario di riferimento** fisso: giorno 15 del mese, 23:00 locali. Gli orari di
  alzata/tramonto valgono per quel giorno.
- **Proiezione** azimutale equidistante (zenit al centro, N in alto, E a sinistra).

---

## Architettura (come è pensato)

```
[dati statici: stelle, costellazioni] + [effemeridi skyfield]
                     │
                 engine/generate.py  ──(tema JSON)──►  SVG
                     │
        ┌────────────┴────────────┐
     app/main.py              (futuro) scheduler
    form web + download       job mensile → cartella/NAS/mail
```

- **Motore puro** (nessuna UI dentro): facile da testare e riusare.
- **Tema disaccoppiato**: la grafica è dati, non codice.
- **UI sottile** sopra il motore.
- **Deploy consigliato**: container Docker sul NAS (stesso ambiente del sito
  dell'associazione).

---

## Cosa costruire con Claude Code (briefing)

Apri Claude Code **in questa cartella** e parti da qui. Priorità suggerite:

1. **Rifinire la web app** (`app/main.py`): validazione input, scelta formato,
   anteprima PNG oltre a SVG, gestione errori, pagina più curata col tema.
2. **Anti-collisione etichette**: spostare i nomi che si sovrappongono (forza di
   repulsione o griglia occupata). È il miglioramento di qualità più visibile.
3. **Visibilità pianeti più seria**: usare magnitudine, crepuscolo astronomico,
   e una nota "dove guardare" (azimut/altezza).
4. **Multi-formato social**: oltre all'A4, un layout **1080×1080** (Instagram) e
   **1080×1920** (storia) che riusano lo stesso motore con canvas diverso.
5. **Automazione**: job mensile (cron/systemd/Docker) che genera il mese
   successivo e lo salva in una cartella condivisa o lo invia via mail.
6. **Dockerfile** per il deploy sul NAS.

Vincoli da rispettare:
- Tenere **motore** e **tema** disaccoppiati (la palette non va mai hardcoded).
- L'orientamento della mappa (N alto, E sinistra) e lo stile neon+glow sono
  identità del brand: non alterarli senza motivo.
- Tutti i testi in **italiano**.

> Contesto extra utile da incollare a Claude Code all'avvio: "Questo progetto
> genera il volantino "Cielo del Mese" per il Gruppo Astrofili Vicentini. Il
> motore è già funzionante e parametrico. Voglio [obiettivo del momento].
> Rispetta l'architettura del README."
