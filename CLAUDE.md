# CLAUDE.md — Cielo del Mese (Gruppo Astrofili Vicentini)

Questo file descrive **il progetto come è**, non come vorremmo fosse.
Se trovi una divergenza fra questo file e il codice, **il codice ha ragione** e
questo file va corretto. Segnalala invece di adattarti in silenzio.

> Il `README.md` è **storicamente inaffidabile** (ricognizione 2026-07-09: 8
> divergenze dal disco). Usa questo file come fonte di verità. Il README verrà
> riallineato; finché non lo è, non fidarti dei suoi comandi d'esempio.

---

## Cos'è

Genera il volantino **"Cielo del Mese"** per il Gruppo Astrofili Vicentini:
mappa del cielo notturno per un dato mese/anno/località, con fasi lunari,
pianeti e stelle nei loro colori reali. Output attuale: **SVG A4**, con
conversione PNG.

**Direzione (decisa 2026-07-09):** il valore dei prossimi mesi è la
**pubblicazione social** — post 1080×1080 e storie 1080×1920 generati ogni mese
dallo stesso motore. L'A4 resta, non è più il fuoco.

**Nessuna scadenza esterna.** Costruiamo le fondamenta prima di ristrutturare.

---

## Architettura reale (verificata, non dichiarata)

*(Riscritta dopo il taglio #7e, 2026-07-14. Prima c'era un file solo da 1393
righe: `engine/generate.py`. Non esiste più.)*

```
uvicorn ► app/main.py ─┐
python cielo.py ───────┤
                       ├─► strumenti/cielo/  ──► data/stars6.json, const_lines,
                       │   (SOLO astronomia)     messier · de421.bsp (skyfield)
                       │        │
                       │        └─ eredita ─► compose/compositor.py
                       │                       (CONDIVISO: cammina i blocchi
                       │                        del layout, le primitive SVG)
                       └─► render.py ──► resvg_py (SVG→PNG)

           (tutti leggono brand/palettes/*.json + brand/layouts/*.json)

La freccia "eredita" ha UN SOLO VERSO: compose/ non importa nulla di
strumenti/ (verificato). È ciò che permetterà a Pillole (D12) di ereditare
il compositore senza toccare il cielo.
```

| File | Righe | Ruolo |
|---|---|---|
| `compose/compositor.py` | 143 | **CONDIVISO.** Il compositore: cammina i blocchi di un file di layout ed è **tool-agnostico** (hook `_render_block_tool` per i blocchi propri di uno strumento). Le primitive: testo, riga, pannello, **immagine (base64)**, icona, sfondo. **È ciò che Pillole eredita.** |
| `strumenti/cielo/messier.py` | 518 | Il profondo cielo (pagina 2): simboli, tabella, anti-collisione a tre strati, nomi delle costellazioni. Ospita `CONST_IT_MINORI` (vedi il confine, D14). |
| `strumenti/cielo/disc.py` | 219 | Il disco sigillato (D7). Legge `CONST_IT`, **non** `CONST_IT_MINORI`. |
| `strumenti/cielo/panels.py` | 193 | Pannelli: luna, pianeti, colori. |
| `strumenti/cielo/catalog.py` | 193 | Dati + funzioni pure: cataloghi, `SkyData`, `bv2hex`, geometria. Ospita `CONST_IT`. |
| `strumenti/cielo/ephemeris.py` | 184 | Effemeridi, proiezione. **Il cuore astronomico.** |
| `strumenti/cielo/engine.py` | 102 | L'assemblaggio: init + `generate()` + dispatch. |
| `engine/generate.py` | 17 | **Un ponte**, non il motore: re-esporta `Engine`/`bv2hex`/`STARS` perché `cielo.py` e `app/main.py` importavano da lì. Si potrà togliere aggiornando quei due import. |
| `cielo.py` | 101 | Il CLI (D1). Mappa i formati ai file di layout e **compone** motore + `render`. |
| `validate.py` | 205 | Validazione input (R4) + contratto del tema (D2). Condiviso da CLI e web, **non** importato dal motore (invariante #1). |
| `render.py` | 53 | SVG→PNG via resvg. Usato dal CLI **e** dalla web app. |
| `app/main.py` | 98 | Web app FastAPI sottile: `/`, `/preview`, `/download`. **Attenzione:** l'HTML è dentro il `.py` (f-string), non in template. E **la UI espone solo l'A4**: niente selettore di formato, PNG sempre a 1800 px. Tutto il lavoro social (post, pagina 2, i quattro design) è raggiungibile **solo dal CLI**. Da sanare in #7f. |
| `brand/layouts/*.json` | — | La composizione come dati. `a4`, `post`, `profondo` (pagina 2), + i tre design social `dashboard`/`editorial`/`rail`. Aggiungerne uno = aggiungere un file. |
| `brand/palettes/*.json` | — | I temi. **Non** in `themes/`. |
| `data/stars6.json` | — | 5044 stelle GeoJSON, tutte con `mag` e `bv`. |

**Nessun file supera 520 righe.** Il problema "apro un file e devo leggere
migliaia di righe" non esiste più.

---

## La regola delle case — dove vive un file

Il criterio **non** è "è roba di design?", è **"il motore lo legge a runtime?"**.

| Cartella | Cosa contiene | Criterio |
|---|---|---|
| `brand/` | palette, layout, font, logo | ciò che il **motore LEGGE a runtime** |
| `docs/`  | spec di design, mockup, riferimenti visivi | ciò che serve agli **UMANI** |
| `out/`   | SVG/PNG generati | ciò che il programma **PRODUCE**: usa e getta, **mai** in git |

Ragione operativa: `brand/` è esattamente ciò che verrà **impacchettato
nell'`.exe`** (D4). Un mockup nell'exe sarebbe peso morto; una palette no.

**Eccezione (documentazione degli asset):** un `LEGGIMI`/`README` che documenta
una cartella vive **dentro** quella cartella, anche se è per umani —
`brand/fonts/LEGGIMI.md` resta in `brand/fonts/`. La regola governa gli **asset**,
non la documentazione che li accompagna: staccare il LEGGIMI dai file che
descrive lo fa scollare al primo cambiamento.

---

## Invarianti — non violare senza chiedere

1. **Il motore non conosce la UI.** `engine/generate.py` non importa nulla di
   `app/` né di `render.py`.
2. **La palette non è mai hardcoded.** *(Sanato in #4b: `#cdd6ee` è ora il token
   di tema `moon_label`, letto con accesso diretto che spacca se manca.)*
3. **Orientamento della mappa:** N in alto, E a sinistra. Proiezione azimutale
   equidistante, zenit al centro. È identità visiva: non cambiarlo.
4. **Stile neon + glow:** identità del brand.
5. **Tutti i testi rivolti all'utente sono in italiano.** Anche gli errori.
6. **Il codice del motore è puro:** stesse coordinate + stessa data ⇒ stesso
   output. Nessuna I/O nascosta, nessun orologio di sistema.

---

## Decisioni architetturali prese

- **D1 — Il PNG si genera anche da CLI.** `render.py` resta un modulo separato
  che il CLI *compone*; non viene fuso nel motore. Un solo percorso d'uscita
  SVG→PNG, testabile headless. *(Fatto, giro #5d: `cielo.py` compone motore +
  `render`; `--png` produce il PNG accanto all'SVG, larghezza per formato.)*
- **D2 — Il tema è un contratto validato, non un dict libero.** Una palette a
  cui manca una chiave deve dare un errore leggibile, non un `KeyError`.
  Motivazione: stiamo per moltiplicare le palette. *(FATTO, #6n: `validate.py`
  dice QUALE chiave manca e in QUALE file. Distingue STILE — colori liberi — da
  FISICA: `star_ramp` deve avere B-V crescente e rosso↑/blu↓ al crescere di B-V,
  monotonia DEBOLE — i canali saturano a 255; `planet_colors` coi 7 pianeti e
  Marte rossastro/Nettuno bluastro. Una palette può cambiare un blu, non mentire
  sull'astronomia.)*
- **D3 — Prima la rete di sicurezza, poi l'estrazione del layout social.** Il
  layout va estratto dal metodo `generate()` (oggi le coordinate A4 sono fuse
  nel metodo, `R5`). Quel refactor tocca la geometria: si fa **dopo** i test.
- **D4 — Distribuzione: repo pubblico su GitHub + `.exe` in Release.** I soci
  scaricano ed eseguono sul proprio PC. Niente NAS, niente server.
  Conseguenze vincolanti:
  - La build dell'`.exe` si fa in **GitHub Actions**, mai a mano. Ambiente
    pulito e riproducibile.
  - `de421.bsp` (da `skyfield-data`) e `resvg_py` (libreria nativa) vanno
    dichiarati esplicitamente al bundler e risolti a runtime: dentro un exe
    `__file__` non funziona come credi. È il punto in cui il packaging fallisce.
  - L'exe non firmato attiva **SmartScreen**. Va documentato nel README, o si
    compra un certificato.
  - **R4 (validazione input) diventa bloccante**: un HTTP 500 sul PC di un socio
    è "il programma non funziona", e non hai i log.
  - Prima di rendere pubblico il repo: `LICENSE` (senza, nessuno ha diritto di
    usarlo) e README riallineato alla realtà. *(Fatto #7c: `LICENSE` MIT,
    `CREDITI.md`, `data/stelle_FONTE.md`, README riscritto ed eseguito.)*
  - **`CREDITI.md` va IMPACCHETTATO nell'`.exe`** *(#7c)*: BSD-2 e OFL obbligano
    la nota di copyright anche in forma binaria (vedi sotto). L'`.exe` deve
    portarsi `CREDITI.md` accanto e/o in una schermata "Informazioni". È lavoro
    del giro di packaging (D4), non prima: qui resta scritto perché è il punto
    che si dimentica e che rende l'`.exe` non distribuibile finché manca.
  - **La provenienza dei dati è nota e verificata** *(2026-07-13, per confronto
    integrale: stesso hash, non "somiglia")*:
    | Dato | Fonte | Licenza |
    |---|---|---|
    | `data/stars6.json` (5044 stelle) | **d3-celestial**, Olaf Frohn | **BSD-2** |
    | `data/const_lines.json` (89 cost.) | **d3-celestial**, Olaf Frohn | **BSD-2** |
    | `data/messier.json` | OpenNGC, Mattia Verga | CC-BY-SA-4.0 *(attribuita)* |
    | `brand/fonts/*.ttf` | Google Fonts | OFL *(licenze nel repo)* |
    | `de421.bsp` | JPL/NASA | pubblico dominio |
    **La BSD-2 obbliga anche la FORMA BINARIA**: la nota di copyright va
    riprodotta «nella documentazione o negli altri materiali forniti con la
    distribuzione» — cioè **l'`.exe` di D4 deve portare i crediti con sé** (una
    schermata "Informazioni", o un file di note accanto all'eseguibile). Non è un
    cavillo: è la condizione a cui abbiamo il diritto di usare quei dati.
  - **Font del brand (decisi dal designer, 2026-07-12): Barlow Semi Condensed**
    (testata, titoli, etichette, cardinali) **+ Instrument Sans** (corpo: nomi,
    orari, note, date). Entrambi **SIL Open Font License**: ridistribuibili nel
    repo e nell'`.exe`. *Superano* la proposta precedente (Inter / Space
    Grotesk), che resta citata in `render.py` (`SANS = "Inter"`) e in
    `cielo-del-mese_struttura.md`: **da riallineare**. *(Corretto 2026-07-13:
    questo punto diceva ancora «i `.ttf` non sono nel repo». Non è più vero — ci
    sono, ed è verificato: vedi R6.)*
- **D10 — L'app è un contenitore di strumenti, non un generatore singolo.**
  *(Deciso da Marco, 2026-07-13.)* La UI ha una **barra laterale**: oggi una voce
  attiva (*Cielo del Mese*), domani altre (*Pillole di astronomia*, e ciò che
  verrà).
  **Disciplina vincolante:** si costruisce **la barra laterale**, NON
  un'infrastruttura per plugin. Una voce attiva + una "prossimamente" costano un
  pomeriggio; un'astrazione generica per strumenti mai progettati è lavoro
  speculativo su un'ipotesi. Quando il secondo strumento esisterà davvero,
  sapremo *cosa gli serve* e l'astrazione la scriveremo sui fatti.
  *(Precedente che lo dimostra: `brand/formats.py`, scritto in anticipo per il
  layer di composizione, che poi prese tutt'altra strada. È stato cancellato.)*
- **D11 — La barra di avanzamento dice il vero.** Il motore ha **quattro fasi
  reali** (effemeridi → proiezione → composizione → rendering PNG): la UI le
  riporta man mano. *Niente barra finta*: una barra che arriva al 100% e poi resta
  lì è il modo peggiore di far aspettare qualcuno, e mente al socio.
- **D9 — La seconda mappa: il profondo cielo (Messier).** *(Decisa 2026-07-12,
  da fare.)* Il post diventa **due pagine**: (1) costellazioni, stelle, Luna e
  pianeti — quella attuale, che resta il default; (2) **profondo cielo**, con
  meno stelle (solo quelle delle figure) e sopra gli **oggetti Messier**.
  - **Simboli: usa la convenzione degli atlanti**, non icone inventate.
    Galassia = ellisse · ammasso aperto = cerchio tratteggiato · ammasso
    globulare = cerchio con croce · nebulosa diffusa = quadrato · nebulosa
    planetaria = cerchio con quattro punte. Serve una **legenda** dei tipi.
  - **LA MAPPA MOSTRA, LA TABELLA RACCONTA.** *(Deciso da Marco, 2026-07-12.)*
    - La **mappa** disegna **tutti** i Messier sopra l'orizzonte (~50 in un mese),
      col simbolo del tipo. È il cielo com'è: togliendo la gran parte delle stelle
      il disco si svuota e il catalogo intero ci sta.
    - Una **tabella** (come il pannello dei pianeti) elenca quelli che vale la
      pena cercare **questo mese**: 15-20 righe, non 50 — cinquanta righe non
      entrano in un 1080 più di quanto ci entrino cinquanta etichette.
    - **Il criterio della tabella è una REGOLA, non una lista curata** *(Marco,
      2026-07-12)*: gli oggetti **sopra i 30° di altezza** quel mese. Sotto quella
      quota estinzione atmosferica e inquinamento luminoso dell'orizzonte
      ammazzano il profondo cielo — è la regola pratica di chiunque osservi. Si
      aggiorna da sola ogni mese.
      Conseguenza corretta e voluta: da Vicenza (45°N) **Sagittario e Scorpione
      culminano bassi**, quindi M8/M20/M22 (il cuore della Via Lattea) restano
      fuori. Sono genuinamente difficili da lì: meglio non prometterli.
      **DA MISURARE:** in primavera, con l'Ammasso della Vergine alto, i Messier
      sopra i 30° potrebbero essere 30-40 — troppi per la tabella. Rimedio:
      **ordinare per altezza e prendere i primi N** (i più alti = i meglio
      piazzati). La regola resta automatica e la tabella non sfonda mai.
    - **L'etichetta sulla mappa ce l'ha solo chi sta in tabella.** Mappa e tabella
      si guardano l'un l'altra: nessun nome sulla mappa senza spiegazione sotto.
      **E il patto vale nei due sensi** *(precisato 2026-07-13)*: chi sta in
      tabella **deve** avere il nome sulla mappa, o il socio legge una riga e non
      trova nulla nel disco. Quindi **un'etichetta non si scarta mai**: se non
      entra vicino al suo oggetto, si allontana e si collega con una **linea di
      richiamo** — la stessa tecnica già approvata per l'Ammasso della Vergine,
      estesa a tutti. *(Deciso da Marco, 2026-07-13.)* Un'etichetta scartata
      significherebbe che è la tipografia a decidere il contenuto editoriale.
      **La superficie di collisione include i SIMBOLI**, non solo le altre
      etichette: è il difetto trovato il 2026-07-13 — `placed_boxes` conteneva
      solo etichette, quindi un nome non aveva alcun motivo di evitare un
      simbolo, e ci finiva sopra.
    - Colonne: *simbolo · M31 — Galassia di Andromeda · galassia · in Andromeda ·
      binocolo*.
  - **L'Ammasso della Vergine è UNA voce, non sedici.** M49, M58-61, M84-91,
    M98-100 stanno in un fazzoletto di cielo. Sedici *simboli* fitti sono
    informazione ("qui ci sono un sacco di galassie" — è ciò che fanno gli atlanti
    veri); sedici *etichette* sono **impossibili** (l'anti-collisione ne
    scarterebbe a caso). Sulla mappa **una sola etichetta** appoggiata al
    grappolo; in tabella **una sola riga** che li elenca.
    *(Corretto 2026-07-13: **M104 NON fa parte del gruppo.** È a dec −11,6°,
    ~24° a sud del nucleo dell'ammasso: sta nella costellazione della Vergine,
    non nell'ammasso. Ed è un gioiello a sé — il Sombrero — che collassato fra i
    sedici sarebbe sepolto.)*
    Il gruppo ha **notevolezza T3**, per coerenza col patto mappa↔tabella: se il
    grappolo è etichettato sulla mappa ma non compare in tabella, il lettore vede
    un nodo fitto di simboli con un nome e **nessuna spiegazione sotto**.
  - **L'ORDINE della tabella è il MERITO, non l'altezza.** *(Deciso 2026-07-13,
    dopo misura.)* Il filtro resta l'altezza (>30°); l'**ordine** usa un campo
    `notevolezza` (0-3) **curato nel catalogo**. Misurato: ordinare per altezza
    metterebbe in testa a marzo M108/M109/M106 — galassie di 10ª magnitudine —
    mentre col merito la testa è M81/M82/M51/M63/M64/M97/M44/M3, i gioielli di
    primavera. La regola mensile resta **automatica**; il merito è una
    **proprietà curata dell'oggetto** (decisa una volta), non una **lista curata**
    (decisa ogni mese) — è la distinzione che salva D9.
    **Il 3 dev'essere RARO** *(corretto 2026-07-13, dopo misura sull'output di
    marzo)*: con **otto** oggetti a `notevolezza: 3` il merito non ordina più
    niente, il pareggio lo rompe l'altezza, e in testa alla tabella finisce
    **M97** (Civetta, mag 9.9, solo telescopio) sopra **M44** (Presepe, mag 3.1)
    e M81. Cioè: **l'altezza travestita da merito** — esattamente ciò che D9
    voleva escludere. Il 3 lo tengono solo gli oggetti che un divulgatore mette
    in **prima riga davanti a un principiante**. La prima riga è la vetrina del
    poster: se promette un telescopio dove poteva promettere un binocolo, ha
    sbagliato bersaglio. *(Deciso da Marco, 2026-07-13.)*
    *(Applicato #7b: da 28 oggetti a tier-3 a **11**. La vetrina di marzo passa da
    M97 Civetta — mag 9.9, telescopio — a **M44 Presepe**, binocolo.)*
  - **OSSERVAZIONE, non un'azione — la coda della tabella.** Misurato a marzo: le
    righe 5-15 sono **undici galassie di fila, quasi tutte da telescopio, sette
    senza nome proprio** (M108, M109, M106, M94, M105, M96, M95…). È **onesto**:
    sopra i 30°, in primavera, il cielo di Vicenza è davvero quello. E la regola
    automatica è ciò che salva D9 dalla lista curata. **Non si tocca.** Se un
    giorno darà fastidio, il rimedio è nel **dato** (la notevolezza), non nel
    codice. Scritto qui perché non venga "scoperto" fra due mesi e corretto da
    qualcuno che non sa che era una scelta.
  - **"Cosa serve per vederlo": due categorie (binocolo / telescopio), e NON si
    calcolano dalla magnitudine.** *(Le due categorie le propone Marco; il vincolo
    è dell'architetto.)* La magnitudine misura la luce **totale**: un oggetto
    grande la spalma su un'area vasta e sparisce pur essendo "luminoso" sulla
    carta. Conta la **brillanza superficiale**.
    I bugiardi sono pochi ma sono proprio i famosi: **M33** (mag 5.7 — sulla carta
    più luminosa di M31; col binocolo da Vicenza **non la vedi**), **M101**,
    **M74**, **M1**. Scrivere "binocolo" accanto a M33 manda un socio a cercare il
    nulla e a concludere che il programma sbaglia: peggio che non scrivere niente.
    Quindi: **stima iniziale dalla magnitudine, ma il catalogo porta il valore
    vero come DATO**, e i bugiardi li corregge il GAV (una dozzina, non 110).
    Stesso principio della direzione tolta ai pianeti sotto l'orizzonte: mai
    mandare l'osservatore a cercare il nulla.
  - **Il test è gratis:** ogni Messier appartiene a una costellazione nota. M31
    deve cadere in Andromeda, M42 in Orione, M13 in Ercole. Verifica incrociata,
    come per pianeti e Luna.
  - Costo reale: **un catalogo** (fonte pubblica, verificata — non copiata a
    fiducia), **una primitiva** per i simboli, **un file di layout**. Il motore
    non va rifattorizzato: la proiezione è già scritta e già testata.
- **D6 — Si mette mano all'input, mai all'output.** Un SVG generato non si
  ritocca a mano: la correzione muore alla rigenerazione successiva. Se ti
  ritrovi a voler cambiare sempre la stessa cosa, quella cosa era un parametro
  mancante. Eccezione unica e legittima: il ritocco irripetibile per un'occasione
  singola. *Claude Code non deve mai proporre di correggere l'output.*
- **D7 — Il disco è sigillato, la composizione è dati.**
  - Il **disco del cielo** (geometria, astronomia) è la parte fissa. Esce dal
    motore come frammento SVG auto-contenuto, in coordinate proprie: chi compone
    lo scala e lo posiziona, non lo ridisegna mai.
  - Il motore restituisce **disco + dati strutturati** (pianeti, fasi, data),
    distinti. Oggi i valori sono infilati direttamente nel testo dell'A4: vanno
    separati, altrimenti un file di layout non ha con cosa riempire i blocchi.
  - **Composizione, tema e contenuto sono file, non codice.** Titolo, posizioni,
    dimensioni, gerarchia tipografica: modificabili senza toccare Python.
  - `docs/cielo-del-mese_struttura.md` è la spec di design. Non va abbassata al
    codice: è il codice che deve salire fino a lei.
  - **Niente browser headless** per comporre (HTML/CSS→PNG): impacchettare
    Chromium nell'`.exe` (D4) è insostenibile. Si resta su SVG + `resvg`.
- **D8 — L'app produce il file, non pubblica.** L'output è il PNG del post; la
  pubblicazione su Instagram è manuale, la fa Marco (o chi gestisce il profilo
  GAV). *Niente* pubblicazione automatica via API: richiederebbe account
  business, app Meta, token OAuth e revisione — incompatibile con un `.exe`
  offline distribuito ai soci (D4), che non può contenere le credenziali del
  profilo. Il confine dell'app è l'immagine pronta. Non proporre di superarlo.
- **D5 — Il golden ha una data di scadenza.** *(Corretto 2026-07-09: il
  confronto NON era byte-a-byte come credevamo. Il test legge in modalità testo,
  con newline universali: normalizzava i fine-riga su entrambi i lati. La mina
  era innescata — blob LF, output Windows CRLF — e non era esplosa per caso. Il
  `.gitattributes` ora impone LF ovunque.)* Regge finché gira solo
  su questa macchina. Su GitHub Actions (altro OS, altra numpy) l'ultima cifra
  dei `%.2f` cambierà e il test fallirà **senza che nulla sia rotto**.
  Va convertito a confronto con tolleranza numerica *quando si accende la CI*,
  non prima: adesso serve esatto, per sorvegliare il refactor del layout.
  Inoltre, per D7, andrà **ristretto al solo disco**: se sorveglia anche la
  composizione, fallirà a ogni ritocco estetico legittimo — e un test che è
  sempre rosso viene ignorato, che è il modo in cui una rete di sicurezza muore.
  **FATTO (#8 Milestone 2/A, 2026-07-15):** convertito a **tolleranza** in vista
  della CI. `tests/golden_compare.py::svg_diff` tokenizza l'SVG: i numeri con
  **tolleranza assoluta 0,15 px**, il resto (nomi, testo, **colori `#hex`**) esatto.
  I `.svg` golden **non toccati** (solo il confronto cambia); motore intatto.
  **TOL=0,15 e non 0,05** — l'architetto suggeriva 0,05 su premessa sbagliata
  («ultima cifra dei `%.2f` = 0,01»); l'esecutore ha **misurato**: la maggioranza
  delle coordinate è **`%.1f`** (contate dall'architetto: 4333 vs 2057 `%.2f`),
  dove un salto d'ultima-cifra fra piattaforme è **0,1 px** — quindi 0,05 avrebbe
  rifiutato il rumore normale. 0,15 sta sopra lo 0,1 e ~7× sotto una regressione da
  1 px (prende anche 0,3). **Rete viva, non placebo** (dimostrato): tollera 0,1 px,
  fallisce a 0,3 e 1,0, fallisce se cambia un `#hex`. *Se in CI emergesse una deriva
  > 0,15, NON si alza la tolleranza (annacquerebbe la rete): è un caso da guardare
  in faccia.* Nota per la CI (passo B): **fissare le versioni** (numpy compreso) per
  ridurre la deriva cross-OS e per riproducibilità (D4).
- **D12 — Il secondo strumento è NOTO, e questo sblocca il refactor.**
  *(Marco, 2026-07-13.)* "Pillole di astronomia" non è più un'ipotesi: è un post
  1080×1080 con **un'immagine caricata dall'utente** (trascinata e posizionata),
  **un testo**, **3-4 layout** e le palette. Esce un PNG.
  - La lezione *"non costruire l'astrazione prima del secondo caso"* **non si
    applica più**: il secondo caso c'è, e si può misurare. Il taglio di
    `generate.py` (D14) ha finalmente un bersaglio.
  - **Il rischio tecnico di Pillole è già risolto** — verificato, non dedotto: la
    primitiva `image` incorpora un raster nell'SVG come **data URI base64**. È
    quella che disegna il logo del GAV nella testata di *ogni* poster, ed è
    testata (`test_image_icon.py`). Sopravvive nell'`.exe` perché l'immagine
    finisce **dentro** l'SVG. L'upload dell'utente è quella primitiva con un href
    diverso.
  - Resta da fare, quando ci arriveremo: il **ritaglio** nel riquadro (maschera +
    offset: l'utente trascina) e i 3-4 file di layout.
  - **NON si creano cartelle o file di Pillole in anticipo.** Una cartella vuota
    attira decisioni prese al buio. Si scrive quando si scrive.
- **D13 — Una palette sola per tutti gli strumenti; ciò che varia è il CONTRATTO.**
  Una palette ha ~20 chiavi **di marca** (`bg`, `text`, `panel`, `neon`, `gold`,
  `border`, `status`…) e 2 chiavi che sono **astronomia pura** (`star_ramp`,
  `planet_colors`). Le prime le vuole qualunque strumento, le seconde solo chi
  disegna un cielo.
  Quindi **non** si spezzano le palette in un file per strumento: sarebbe
  duplicare il marchio, e cambiare l'oro del GAV vorrebbe dire cambiarlo in
  quattro posti e dimenticarsene uno. Una palette resta **un file**, valida per
  tutti; **ogni strumento dichiara di quali chiavi ha bisogno**, e `validate.py`
  (D2) valida contro quella dichiarazione, non contro una lista globale.
  Necessario, non speculativo: senza, la prima voce "prossimamente" della barra
  laterale (D10) rompe la validazione.
  **Il SET di palette (deciso 2026-07-15, dopo consolidamento col designer): SEI,
  nessuna gemella.** osservatorio (default/golden, **intatta**), luce-rossa
  (funzionale, **intatta**), + 4 nuove del designer armonizzate col logo: **Aurora
  Boreale** (verde polare), **Nebulosa** (viola magenta), **Ottone Antico** (caldo
  ottone), **Cielo di Ghiaccio** (blu-argento). **Ritirate** `notte-blu` (gemella
  di osservatorio, distanza 26,4) e `petrolio` (teal assorbito da Aurora). Le 4
  nuove: 20 token di marca dal designer + `star_ramp`/`planet_colors` innestati da
  osservatorio (fisica, uguale per tutte). **Verificate dall'architetto: passano
  `validate.py` e rendono sul cielo vero.** Le stelle restano coi colori reali in
  ogni palette (onestà astronomica intatta anche su fondo ottone/viola).
- **D14 — Il taglio di `generate.py`. FATTO (#7e, 2026-07-14).**
  **Riuscito su entrambi i criteri, verificati dall'architetto e non sulla parola:**
  - **(a) Output identico byte per byte.** I golden non sono stati toccati in
    nessuno degli 8 commit (verificato sulla storia). E poiché **i golden NON
    coprono la pagina 2** — buco scoperto dall'esecutore stesso, quando un `import`
    dimenticato lasciò i golden verdi e fece arrossire 106 test — l'architetto ha
    **rigenerato la pagina 2 col codice nuovo e confrontata con quella di prima del
    taglio: stesso hash**, agosto e luglio. Il refactor è puro su *tutto* l'output,
    non solo su ciò che una rete copriva.
  - **(b) Pillole descrivibile su carta senza nominare un file di
    `strumenti/cielo/`:** riuscito. Unico residuo dichiarato: `defs_svg` (in
    `compose/`) legge ancora il token `theme['disk']` — è una chiave di tema, non
    una dipendenza di file, e la scioglie **D13**.
  - **Il confine è STRUTTURALE, non una disciplina.** `CONST_IT` (l'A4) vive in
    `catalog.py`; `CONST_IT_MINORI` (solo pagina 2) in `messier.py`, che `disc.py`
    **non importa**. Il bug del 13/07 — allargare un dizionario e far muovere i
    golden dell'A4 — oggi è **impossibile per costruzione**.
  - **Metodo:** 8 movimenti, un commit ciascuno, suite verde dopo ognuno; i blocchi
    grossi spostati con uno slice esatto via script, **non ricopiati a mano** — così
    una virgola non può cambiare di nascosto.
  *(Testo originale della decisione, per memoria:)*
  Misurato (2026-07-13): il codice era **1621 righe**, di cui **1164 in
  `generate.py`** — *cifra poi rivelatasi stale: al momento del taglio erano
  **1393**, cresciute coi giri della pagina 2.* Tutto il resto è già snello (`validate.py` 205, `cielo.py`
  101, `app/main.py` 98, `render.py` 53) e **non va toccato**: il problema "apro
  un file e devo leggere migliaia di righe" è **un file solo**.
  Il taglio separa **ciò che Pillole eredita** da **ciò che non erediterà mai**:
  ```
  brand/       palette, font, logo, layout                      — condiviso
  compose/     il compositore (cammina i blocchi), le primitive,
               render.py, il contratto del tema                 — condiviso
  strumenti/
    cielo/     effemeridi, proiezione, disco sigillato, Messier — SOLO cielo
  app/         la barra laterale
  ```
  **Doppio criterio di riuscita** — servono entrambi:
  - **(a)** i golden restano **identici byte per byte**. Un refactor puro non
    cambia l'output: se un golden si muove, non hai rifattorizzato — hai cambiato
    qualcosa senza accorgertene.
  - **(b)** si riesce a descrivere Pillole **su carta**, senza nominare un solo
    file di `strumenti/cielo/`. Se (b) non riesce, il taglio è nel punto sbagliato
    e si rifà. È il modo di **verificare l'astrazione prima di costruirla** — la
    cosa che non facemmo con `brand/formats.py`, e che ci costò il file.
  **Un accoppiamento accidentale già trovato, da usare come banco di prova** *(#7d-ter)*:
  `CONST_IT` è letto **sia dal disco dell'A4 (pagina 1) sia dalla pagina 2**.
  Estenderlo coi 44 nomi minori **ha fatto muovere i golden dell'A4** — l'A4 si è
  messo a disegnare 44 etichette in più, senza che nessuno gliel'avesse chiesto.
  Rimedio tampone: un secondo dizionario (`CONST_IT_MINORI`) letto solo dalla
  pagina 2. **Il taglio deve rendere esplicito questo confine**: se dopo #7e un
  dato può ancora cambiare l'output di uno strumento mentre se ne modifica un
  altro, il taglio non ha fatto il suo lavoro.

- **D16 — IL MEZZO È IL TELEFONO. E la pagina 2 è una CARTA DA STUDIARE, non un
  cartello da leggere di sfuggita.** *(Deciso da Marco, 2026-07-14, dopo misura.)*
  **La misura, prima della decisione** *(corpi del layout ÷ 1080 × 65 mm = la
  larghezza di un telefono da 6")*:
  | Elemento | Corpo | Sul telefono |
  |---|---|---|
  | Titolo | 50 | **3,0 mm** ✓ |
  | Righe della tabella | 15 | 0,90 mm |
  | Sigle Messier (M51…) | 11 | 0,66 mm |
  | Nomi delle costellazioni | 10,5 | 0,63 mm |
  | Legenda | 5 | 0,30 mm |
  Sotto ~1,5 mm un occhio normale, a distanza di braccio, **non legge**. Quindi nel
  feed **si legge SOLO il titolo**. La tabella — il contenuto editoriale su cui
  abbiamo speso quattro giri — è invisibile **quanto** i nomi. *(Correzione onesta:
  la prima stesura di D16 dava la colpa ai nomi delle costellazioni. Era falso: sono
  innocenti quanto tutto il resto. La misura è arrivata dopo la frase.)*
  **La decisione:** il post è un **richiamo**; il socio vede il titolo e un disco di
  cielo che incuriosisce, **apre e fa zoom** per leggere. È la norma per le
  infografiche dense, ed è coerente col pubblico: un astrofilo che vede "Il cielo di
  agosto" zooma. **Non si insegue la leggibilità nel feed gonfiando i corpi**: per
  portare la tabella a 1,5 mm servirebbero corpi quasi doppi, quindi **6-8 righe
  invece di 15** e metà mappa. Non sarebbe un ritocco tipografico: sarebbe **un
  altro poster**, con meno contenuto. Se un giorno lo si vorrà, è un lavoro col
  designer — non un ritocco dell'esecutore.
  **Conseguenza che resta valida:** ciò che nel feed non si legge **e** che nessuno
  cerca nemmeno zoomando è comunque **sporcizia**. È il motivo per cui le 44
  costellazioni minori restano fuori (sotto): non perché illeggibili — lo è tutto —
  ma perché **nessun principiante le cerca** e affollano i bordi bassi del disco.
  **Per Pillole (D12) il criterio si ribalta:** è una pagina di testo, non una
  carta. Lì il feed conta, e i corpi vanno dimensionati per essere letti **senza
  zoom**.
  Applicazione (nomi delle costellazioni, #7d): si nominano le **35 principali +
  tutte quelle citate in tabella** (il patto D9 resta chiuso). Le **44 minori**
  (Lince, Lucertola, Cavallino, Microscopio, Sestante…) restano **fuori**: nessun
  principiante le cerca, affollano i bordi del disco — dove per giunta il cielo è
  basso e nessuno osserva — e sul telefono sono illeggibili.
  Il dizionario dei 44 nomi **resta scritto** (`CONST_IT_MINORI`, fonte UAI): si
  riaccende con una parola nel file di layout. È un dato, non codice.
- **D17 — Distribuzione: Python PORTATILE per-OS, non PyInstaller. E deve girare
  su Windows E Mac.** *(Deciso da Marco, 2026-07-15: «deve funzionare su windows e
  mac». Modello scelto dall'architetto sotto quel vincolo.)*
  Non un `.exe` PyInstaller, ma **una cartella** per OS con dentro un **Python
  portatile** (Windows: embeddable; Mac: python-build-standalone) + **tutte le
  librerie già installate** (pip prende il wheel nativo giusto per OS: resvg_py
  Windows su Windows, macOS su Mac) + il nostro repo + un launcher (`Avvia.bat` /
  `Avvia.command`) che avvia uvicorn e apre il browser (D15).
  **Perché batte PyInstaller per il NOSTRO caso** *(verificato, non dedotto)*:
  - **Aggira R9 su DUE fronti.** (1) I binari nativi non vengono reimpacchettati:
    `resvg_py.pyd`/`.so` sta in `site-packages` e si carica normale. (2) `__file__`
    funziona: l'app gira dai `.py` veri nella loro cartella vera, quindi **le sei
    basi di percorso NON vanno rifatte** — niente `resource_path`, niente
    `_MEIPASS`. È *più semplice* del `.exe`.
  - **Cross-platform verificato**: `resvg-py 0.3.3` (la nostra) pubblica wheel
    `macosx_11_0_arm64` **e** `macosx_10_12_x86_64` per cp312, oltre a `win_amd64`;
    numpy/skyfield idem; `de421.bsp` è dato puro. *(Fonti: PyPI JSON API, 2026-07-15.)*
  - **NON esiste un artefatto unico per i due OS**: `resvg_py` è nativo per
    piattaforma. Stessa ricetta, **due pacchetti**, costruiti su runner Windows e
    macOS in **GitHub Actions** (D4).
  Prezzi accettati: **~100 MB a pacchetto** (Python + numpy); **non firmato** →
  SmartScreen (Windows) e **Gatekeeper** (Mac, più severo: «tasto destro → Apri»
  la prima volta). Da documentare nel README.
  **VERIFICATO su Windows (Milestone 1, vedi R9).** Ricetta che ha funzionato:
  **python-build-standalone** (astral-sh, variante `install_only` — evita il
  pasticcio del file `._pth` dell'embeddable ufficiale, `pip install` diretto) +
  `pip install -r requirements.txt` dentro. Peso reale del bundle: **~251 MB** (più
  dei 100 stimati). **Il bundle DEVE includere `engine/`** — omesso dalla prima
  lista, ma `cielo.py` e `app/main.py` fanno `from engine.generate import Engine`
  (il ponte di #7e); senza, l'import spacca. Lista bundle completa: `app/`,
  `compose/`, `strumenti/`, `engine/`, `brand/`, `data/`, `cielo.py`, `render.py`,
  `validate.py`, `CREDITI.md`, + il launcher. **Launcher da rifinire (Milestone
  2):** `Avvia.bat` oggi fissa la porta 8000; renderla configurabile (se un socio
  ha la 8000 occupata, oggi fallirebbe il bind).
- **D15 — L'`.exe` apre il browser; e cosa manca DAVVERO per averlo.**
  *(Deciso da Marco, 2026-07-14.)* Doppio clic ⇒ il programma parte in silenzio e
  **apre il browser** sull'interfaccia dell'app. Niente terminale, niente Python
  da installare. Il socio non deve sapere cos'è una riga di comando: un `.exe` da
  CLI che metà dei soci non sa aprire non è "leggero", è **inutile**.
  Prezzo accettato: l'exe si porta FastAPI/uvicorn, e Windows chiederà il permesso
  del **firewall** al primo avvio — a un socio poco pratico *sembra un virus*: va
  spiegato nel README, accanto a SmartScreen.
  **Cosa manca, misurato sul codice (2026-07-14) — non dedotto:**
  - **I percorsi sono il punto che si rompe.** Oggi ci sono **quattro basi
    indipendenti** calcolate da `__file__`: `engine/generate.py:94`
    (`_BASE = dirname(dirname(abspath(__file__)))` → `brand/layouts`, `brand/icons`,
    il logo), `cielo.py:27`, `render.py:15`, e i template della web app. Dentro un
    exe `__file__` non è dove credi (PyInstaller scompatta in una cartella
    temporanea). Quattro basi = quattro modi diversi di sbagliare. Si sana con
    **una funzione sola** che sappia se sta girando congelata — non con quattro
    toppe.
  - **`de421.bsp` non è un file nostro:** arriva da
    `skyfield_data.get_skyfield_data_path()` (`generate.py:21,173`), vive dentro un
    pacchetto installato. Va dichiarato esplicitamente al bundler.
  - **`resvg_py` è nativo davvero:** `resvg_py.cp312-win_amd64.pyd`, un binario
    compilato. Va raccolto esplicitamente.
  - **Da imbarcare:** `brand/` (palette, layout, font, logo, icone), `data/`, e
    **`CREDITI.md`** (obbligo BSD-2, non un optional). *(Corretto 2026-07-14:
    questo punto elencava anche `app/templates/`. **Non esiste**: l'HTML è scritto
    dentro `app/main.py`, in una f-string. Se #7f introdurrà dei template veri,
    andranno aggiunti qui.)*
  - **Build in GitHub Actions**, mai a mano: ambiente sporco = exe irriproducibile.
  - **Niente di tutto questo dipende da #7e o #7f.** L'`.exe` si potrebbe fare
    subito; Marco ha scelto di farlo **dopo**, per consegnare ai soci un prodotto
    con la barra laterale invece di un assaggio. *Rischio residuo accettato
    consapevolmente:* se `resvg_py` o `de421.bsp` non si lasciassero impacchettare,
    non sarebbe un bug ma **una scelta architetturale da rifare**, e la si
    scoprirebbe con due giri di lavoro costruiti sopra.

---

## Roadmap

Ordinata. Il *perché ora* è la parte che conta: senza, l'ordine si perde al primo
imprevisto.

1. **#7c — Il repo pubblicabile.** *(FATTO, 2026-07-13.)* Storia riscritta
   (`docs/riferimenti/` e `brand/logo/logo-white.png` purgati: il PDF era peso
   morto, il logo bianco aveva **provenienza ignota**), `LICENSE` MIT,
   `CREDITI.md`, `data/stelle_FONTE.md`, README riscritto **eseguendo** ogni
   comando, `design_handoff_*` in `docs/`, ramo `main`.
   Il repo GitHub è stato **cancellato e ricreato** per essere certi che i vecchi
   blob non sopravvivessero da nessuna parte: verificato dal remoto, non dal
   locale. Repo: `Pecurus90/GAV-Graphics` (privato).
2. **#7d — I nomi delle costellazioni sulla pagina 2.** *(Marco, 2026-07-13.)*
   Oggi il socio vede **dove** sono i Messier ma non **in che costellazione** sta
   guardando — mentre la tabella gliela dice ("Galassia · Cani da Caccia"). Mappa
   e tabella devono guardarsi, come per le etichette (D9).
   *Perché prima del refactor:* è lavoro **nel motore com'è**. Farlo dopo il
   taglio significherebbe scriverlo in un codice appena spostato, con due
   variabili in ballo: se si rompe qualcosa, non sapresti se è colpa dei nomi o
   dello spostamento. *Additivo prima, distruttivo dopo.*
   *Attenzione:* i nomi sono il **terzo strato** di etichette, dopo i simboli
   Messier e le sigle. L'anti-collisione oggi ne conosce due. La rete di
   `tests/test_messier_page2.py` va **estesa**, non aggirata: senza, si torna
   esattamente al difetto del 13/07 (etichette sopra i simboli, e nessun test che
   lo dica).
2b. **#7d-bis/ter/quater — I nomi delle costellazioni.** *(FATTO.)* Tre giri, e
   **tre regole dell'architetto cadute sotto la misura dell'esecutore**: il
   baricentro (sepolto nei propri Messier), le stelle-figura come ostacolo
   (contraddittoria: i candidati *stanno* sulle stelle), il divieto di uscire dalla
   figura (impossibile per Freccia e Scudo, più piccole della propria etichetta).
   La regola giusta è **«mai lontano», non «mai fuori»** — e **mai dentro il
   vicino** (inviluppo convesso). Default: modo `principali` (D16). 198 test.
3. **#7e — La pulizia: il taglio di `generate.py`.** *(FATTO, 2026-07-14 — vedi
   **D14**.)* Da un file di 1393 righe a sette file, il maggiore di 518.
   `compose/` (condiviso) + `strumenti/cielo/` (solo astronomia), dipendenza a
   senso unico. Output identico byte per byte, **verificato anche sulla pagina 2**,
   che i golden non coprono.
4. **#7f — La barra laterale (D10) + il contratto del tema per-strumento (D13).**
   Una voce attiva (*Cielo del Mese*), una "prossimamente" spenta. **Non** un
   framework per plugin.
5. **Il packaging: l'`.exe` in GitHub Actions (D4 + D15).** *(Anticipato su Pillole —
   deciso da Marco, 2026-07-14: «prima l'exe che funziona e lo condivido, poi
   progettiamo Pillole».)*
   *Perché prima:* è il punto dove questi progetti falliscono — `de421.bsp` e
   `resvg_py` **non si fanno trovare da soli** dentro un eseguibile. Se la strada
   non esistesse, non sarebbe un bug da correggere ma **una scelta architetturale
   da rifare**: meglio scoprirlo con quattro file da spostare che con uno
   strumento in più addosso. E un `.exe` in mano ai soci è l'unico modo di sapere
   davvero cosa manca: Pillole progettata *dopo* si progetta sui fatti.
   `CREDITI.md` va impacchettato con l'exe (obbligo BSD-2).
   **Mina già innescata:** accendere la CI fa diventare **rosso il golden** (D5) —
   altro OS, altra numpy, ultima cifra dei `%.2f` diversa — **senza che nulla sia
   rotto**. Il golden va convertito a **tolleranza numerica** in questo giro, non
   prima (finché sorveglia il taglio #7e serve esatto).
6. **Pillole di astronomia** (D12), quando Marco vorrà pensarci — **dopo** aver
   visto l'`.exe` in mano a un socio.

---

## Debito tecnico noto (ricognizione 2026-07-09)

Ordinato per rischio reale.

- **R1 — Nessun git.** Ogni modifica è irreversibile. *Prerequisito di tutto.*
- **R2 — Zero test su matematica non ispezionabile a occhio.** `altaz`,
  `project`, `sky_context` (tempo siderale), `bv2hex` producono risultati
  *plausibili* anche quando sono sbagliati. Una mappa storta di 5° non la nota
  nessuno. **È il rischio più grave del progetto.**
- **R3 — Contratto del tema implicito.** ~15 chiavi piatte + `bg[0..2]`,
  `disk[0..2]`, `status.{ok,info,warn,muted}`, `star_ramp`. Zero validazione.
- **R4 — RISOLTO (#6n).** La validazione vive in `validate.py`, un modulo a sé
  condiviso da CLI e web (non nel motore: invariante #1; non duplicato). Mese
  1-12, anno in copertura de421, lat/lon numerici e in range, formato/palette
  esistenti + contratto del tema (D2). Errore = messaggio in italiano; il CLI
  esce con exit 1, la web risponde **HTTP 400** (non più 500, non più 200
  incoerente).
- **R5 — RISOLTO (#5b).** Il layout A4 non è più fuso in `generate()`: vive in
  `brand/layouts/a4.json`. `generate()` è un compositore che cammina i blocchi.
  Il confine è: il **file** possiede cosa/dove/quale-dato; il **codice** possiede
  "come disegnare" per 5 primitive (background procedurale, disco sigillato,
  forma della fase lunare, colore da `bv2hex`, pallino da `status`) + la
  derivazione di presentazione (`MONTHS_IT`, `[:3]`, `{:.1f}`).
- **R6 — RISOLTO (2026-07-12).** I `.ttf` del brand sono in `brand/fonts/`
  (Barlow Semi Condensed SemiBold/ExtraBold + Instrument Sans
  Regular/Medium/SemiBold, con le licenze OFL). **Verificato**, non dedotto:
  `render._font_dirs()` restituisce la cartella e `resvg` carica i font — la
  tipografia di `docs/mockups/dashboard.svg` non è più il fallback di sistema.
  *Resta*: `a4.json` e `post.json` dichiarano ancora
  `Helvetica,Arial,sans-serif` nel canvas. Cambiarlo **muove i golden**: si fa
  nel giro deliberato (#6e), insieme alla rimozione di `moon_panel`. (I tre
  design social nuovi dichiarano gia' i font del brand: non hanno golden.)
- **R7 — RISOLTO (prima di quanto credessimo).** Dichiarava codice morto:
  `render.py:DISPLAY`, `NAKED_EYE`, il param `obs` di `planet_table`. **Andato a
  cercarlo in #7e: non esiste più niente di tutto ciò** — era già stato tolto in
  giri precedenti, e il debito è rimasto scritto per inerzia. *(`brand/formats.py`
  era orfano — rimosso in #6a-riordino.)*
  *(**Corretto 2026-07-14, #7d:** R7 dichiarava anche una chiave `'Peg'`
  **duplicata** in `CONST_IT`. **Non esiste**: contate con `ast.literal_eval` +
  `Counter`, 35 chiavi, 0 duplicati. Il debito era immaginario, o sanato senza
  aggiornare il file. Terza volta che una riga di questo file viene smentita dalla
  misura: quando il file e il codice divergono, ha ragione il codice.)*
- **R8 — I nomi italiani delle costellazioni sono incompleti.** *(Scoperto #7d.)*
  `const_lines.json` ha **88 sigle** (89 figure: `Ser` compare due volte —
  Serpente Caput e Cauda, due regioni distinte: è corretto, e produce due
  etichette). `CONST_IT` ne nomina **35**; altri 9 si recuperano dal catalogo
  Messier. **44 costellazioni restano mute** sulla mappa. Non si inventano: si
  propongono e si approvano.

- **R9 — DUBBIO APERTO: nessuno ha mai verificato che l'`.exe` sia possibile.**
  *(Registrato 2026-07-14, su richiesta di Marco: «quando è ora vediamo, segna il
  dubbio».)* Sappiamo che `resvg_py` è un **binario nativo** (`.pyd`) e che
  `de421.bsp` vive dentro un pacchetto installato (vedi D15). **Non sappiamo** che
  sopravvivano dentro un eseguibile: è dedotto dalla documentazione, non
  **eseguito**. Se uno dei due non si lasciasse impacchettare, non sarebbe un bug
  da correggere ma **la tecnica di rendering da rifare** — e a quel punto ci
  saranno #7e e #7f costruiti sopra.
  L'architetto ha proposto uno **spike usa-e-getta** (un exe scemo che carica le
  effemeridi e sputa un PNG, in una cartella temporanea, fuori dal repo) per
  rispondere alla domanda *prima*. Marco ha deciso di **non anticiparlo**: si
  affronta al giro del packaging. La proposta resta scritta qui perché la
  decisione sia una **scelta**, non una dimenticanza.
  **AGGIORNAMENTO 2026-07-15 — si affronta ORA (giro #8, il packaging).** Marco,
  messo davanti al bivio spike-prima / build-diretta, ha scelto la **build
  diretta** (l'architetto raccomandava lo spike). *Rischio accettato
  consapevolmente.* Mitigazione strutturale, non uno spike travestito: la build
  vera è ordinata in **milestone**, e il **Milestone 1 è il pezzo rischioso** — un
  exe onefile del CLI che carica de421 e chiama resvg e sputa un PNG. Usa il
  codice VERO (non throwaway) e resta come fondazione; ma se non si impacchetta, lo
  scopri al primo milestone, non dopo aver scritto lo spec + il workflow Actions.
  **Misura aggiornata post-#7e (2026-07-15): NON quattro basi di percorso, ma SEI**
  (`cielo.py:27`, `validate.py:19`, `compose/compositor.py:20`, `app/main.py:34`,
  `strumenti/cielo/engine.py:36`, `render.py:15`). Il taglio ha aggiunto
  annidamento, quindi altri modi di sbagliare. Si sanano con **una funzione sola**
  (`resource_path`) che conosce `sys._MEIPASS`.
  **RISOLTO — SÌ, su Windows (Milestone 1, 2026-07-15). ESEGUITO, non dedotto.**
  Col modello portatile (D17) R9 ha risposta **SÌ**, e le sei basi di percorso
  **NON sono state toccate**: `git diff` = solo `.gitignore`, zero `.py` cambiati —
  nel bundle portatile `__file__` funziona, quindi `resource_path`/`_MEIPASS`
  **non servono**. Prova di rilocabilità: bundle copiato in `%TEMP%\prova_socio\`,
  lontano dal repo, e da lì CLI+web+`Avvia.bat` funzionano. Font del brand
  verificati in modo **non falsificabile**: dashboard reso dal bundle spostato =
  **sha256 IDENTICO** al rendering in-repo coi font del brand (un ripiego sul font
  di sistema avrebbe cambiato i byte). Restano da verificare **su Mac** (Milestone
  2) — lì i binari nativi e Gatekeeper sono un'altra prova, non ancora eseguita.
  *Nota: il rischio temuto (deps native) è filato liscio; l'unico attrito è stato
  ambientale (porta 8000 occupata da un server fantasma) — non un difetto del
  bundle.*
- **R10 — L'A4 ha una COLLISIONE, congelata nel golden da dieci giri.**
  *(Trovata 2026-07-15, aprendo l'immagine — NON un test.)* Nel volantino A4 il
  pannello delle **fasi lunari** (4 fasi a tutta larghezza) si sovrappone al
  pannello dei **pianeti** (cresciuto a 7 voci, che invade la metà destra): "Primo
  Quarto" finisce sopra "Saturno", la Luna Piena copre l'elenco, la legenda si
  accavalla a "Giove". **I formati quadrati (dashboard/post/editorial/rail/profondo)
  sono PULITI** — il dashboard ha già la soluzione elegante (striscia lunare mensile
  in basso, pianeti in un pannello a lato). L'A4 è rimasto indietro.
  **La lezione, in diretta:** il golden è passato **verde per dieci giri**. Nessun
  test l'ha vista, perché *il golden confronta i byte, non i pixel*: dice "l'output
  non è cambiato", non "l'output è giusto". Si è vista solo **aprendo l'immagine**.
  È il motivo della regola «GUARDA L'IMMAGINE, NON IL REPORT».
  **Decisione (Marco, 2026-07-15):** la resa dell'A4 stampato la rivede il
  **designer** (brief autonomo), non una toppa copiata dal quadrato — proporzioni
  portrait diverse. Fix in `a4.json` (dati, D6), che **muoverà di nuovo il golden**:
  movimento deliberato e contato, come per il logo (#7g). Non blocca il video ai
  soci: quello usa il carosello quadrato, che è pulito.
  **ESITO (#7h, in preparazione):** il designer ha consegnato due proposte — vedi
  il progetto claude.ai/design «Infografica cielo del mese», file
  `A4 - Fascia inferiore.html`. **La struttura risolutiva: due CORSIE ORIZZONTALI**
  (pianeti sopra, fasi lunari sotto, un divisore in mezzo): non condividono mai lo
  spazio verticale, quindi non collidono nemmeno con 7+ pianeti. **Verificato
  dall'architetto renderizzando gli SVG del designer col NOSTRO `render.py`
  (resvg + font del brand): rendono, usano i token del tema (`data-token`), fasi
  come archi vettoriali.** Marco ha scelto la **proposta B — "Schieramento"**
  (i 7 pianeti in fila unica, coerente col dashboard). **Sgonfia il lavoro:** la
  striscia lunare 1→31 è il blocco `moon_calendar` che il dashboard **già usa** —
  si riusa, non si riscrive.
  *Ordine:* prima si CHIUDE #7g (logo A4 + golden +1 `<image>`, già contato),
  poi #7h (la fascia, secondo movimento deliberato del golden).
  **#7h fatto e verificato dall'architetto** (render aperto, collisione sparita,
  disco identico): la parata dei pianeti è il blocco `planet_parade` (`panels.py`);
  le note usano le **parole del motore** ("Telescopico", "Non osservabile"), non i
  segnaposto del designer (D6). **Due code lasciate aperte apposta:**
  - **La legenda "colore stelle = temperatura" è stata TOLTA dall'A4** (la proposta
    B occupava quello spazio). Il **post quadrato la tiene** (pannello "COLORI DELLE
    STELLE"): incoerenza. *(Marco, 2026-07-15:)* si **rimette nel giro di revisione
    dei design**, chiedendo al designer di trovarle posto — non una toppa.
  - **Margine di stampa in basso ~2,8 mm** (footer a y1258 su 1273): identico al
    mockup, ma **da verificare in tipografia** (di solito vogliono 3-5 mm). Si alza
    con un numero in `a4.json`.

**Mai verificato:** la correttezza astronomica dell'output. Sappiamo che il
codice produce un SVG. Non sappiamo che sia giusto.
*(Da riverificare: esistono ora `tests/test_correctness.py`, `test_planets.py`,
`test_moon.py`, `test_planet_direction.py`, ancorati a riferimenti esterni.
Questa riga potrebbe essere debito già pagato di cui il file non si è accorto —
va letta contro i test veri, non lasciata marcire.)*

---

## Metodo di lavoro

Tre ruoli. Un ciclo: `prompt → esecuzione → report → allineamento → prompt`.

- **Architetto** (Claude, altra sessione): scrive i prompt, decide, mantiene
  questo file.
- **Esecutore** (Claude Code, tu): esegue, **verifica**, riporta. Non decide
  l'architettura. Se un task richiede una scelta architetturale non coperta qui,
  **fermati e proponi 2-3 opzioni con il trade-off reale.**
- **Product owner** (Marco): arbitra le scelte irreversibili o estetiche.

### Regole di ingaggio — sempre attive

1. **Se non l'hai verificato, scrivi che non l'hai verificato.** Mai
   "dovrebbe funzionare". Distingui sempre *eseguito* da *dedotto*.
2. **Contesta le istruzioni sbagliate o ambigue** invece di eseguirle.
   Un'istruzione contraddittoria va segnalata, non aggirata in silenzio.
3. **Non compiacere.** Un report che dice "tutto a posto" quando non lo è costa
   più di una verità scomoda.
4. **Non allargare lo scope.** Se noti un bug fuori dal task, **riportalo, non
   correggerlo.** Le correzioni opportunistiche rendono i diff illeggibili.
5. **Un commit per unità di lavoro logica**, messaggio in italiano.
6. Se ritratti una tua affermazione precedente, **dillo esplicitamente.**

### Formato del report di fine task

- **Fatto** — cosa è cambiato, file per file.
- **Verificato** — comandi eseguiti e loro **output reale**. Non parafrasato.
- **Non verificato** — e perché.
- **Sorprese** — cosa hai trovato che non ti aspettavi.
- **Decisioni per l'architetto** — dove hai dovuto scegliere, o dove ti sei
  fermato.

---

## Comandi (verificati su Windows/PowerShell, 2026-07-09)

```powershell
# NB: non esiste una .venv nel repo. Oggi gira sul Python globale (3.12.2),
# che ha già le dipendenze. Un venv + lockfile diventeranno utili al packaging
# (D4, giro #9), non prima. Per crearne uno ora, se lo vuoi isolato:
#   python -m venv .venv ; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# CLI (D1): A4 in SVG (default)
python cielo.py --year 2026 --month 8 --place Vicenza
# A4 in SVG + PNG (larghezza 1800)
python cielo.py --year 2026 --month 8 --place Vicenza --png
# post quadrato 1080 in SVG + PNG (larghezza 1080)
python cielo.py --year 2026 --month 8 --format post --png

# web app
python -m uvicorn app.main:app --reload --port 8000
```

Il tema di default è già `brand/palettes/osservatorio.json`: non passare
`--theme themes/...` (quel percorso non esiste).
