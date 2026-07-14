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

```
uvicorn ► app/main.py ─┐
python cielo.py ───────┼─► engine/generate.py ──► data/stars6.json
                       │   (motore puro: solo SVG) ├─► data/const_lines.json
                       │                            └─► de421.bsp (skyfield-data)
                       └─► render.py ──► resvg_py (SVG→PNG)
                       (leggono brand/palettes/*.json + brand/layouts/*.json)

CLI: python cielo.py --format a4|post [--png]   (compone motore + render, D1)
```

| File | Ruolo |
|---|---|
| `engine/generate.py` | Il motore + compositore magro. Geometria/effemeridi → `SkyData` + disco; `generate()` cammina i blocchi di un file di layout. Libreria pura: **nessun CLI, non importa `render`**. |
| `cielo.py` | Il CLI (D1). Mappa i formati (`a4`/`post`) ai file di layout e **compone** motore + `render` (SVG, e PNG con `--png`). Vive fuori da `engine/`. |
| `brand/layouts/*.json` | La composizione come dati (canvas + blocchi). Esistono `a4.json`, `post.json` e i tre design social `dashboard.json`/`editorial.json`/`rail.json`; aggiungerne uno = aggiungere un file (il CLI li scopre dalla cartella). |
| `app/main.py` | Web app FastAPI sottile: `/`, `/preview`, `/download`. |
| `render.py` | SVG→PNG via resvg. Usato dal CLI (`cielo.py`) **e** dalla web app. |
| `validate.py` | Validazione input (R4) + contratto del tema (D2). Condiviso da CLI e web, **non** importato dal motore (invariante #1). Errori in italiano; `InputError`. |
| `brand/palettes/*.json` | I temi. **Non** in `themes/` (il README mente). |
| `data/stars6.json` | 5044 stelle GeoJSON, tutte con `mag` e `bv`. |

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
- **D14 — Il taglio di `generate.py`, e come si sa che è nel punto giusto.**
  Misurato (2026-07-13): il codice è **1621 righe**, di cui **1164 in
  `generate.py`**. Tutto il resto è già snello (`validate.py` 205, `cielo.py`
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
3. **#7e — La pulizia: il taglio di `generate.py`** (vedi **D14**).
   *Perché ora e non prima:* D3 — *prima la rete, poi l'estrazione*. La rete della
   pagina 2 adesso esiste (17 test, guasti iniettati, rosso visto).
4. **#7f — La barra laterale (D10) + il contratto del tema per-strumento (D13).**
   Una voce attiva (*Cielo del Mese*), una "prossimamente" spenta. **Non** un
   framework per plugin.
5. **Il packaging: l'`.exe` in GitHub Actions (D4).** *(Anticipato su Pillole —
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
- **R7 — Codice morto:** `render.py:DISPLAY`, `generate.py:NAKED_EYE`, param
  `obs` inutilizzato in `planet_table`, chiave `'Peg'` duplicata in `CONST_IT`.
  *(`brand/formats.py` era orfano — rimosso in #6a-riordino: il canvas vive nel
  file di layout, come deciso in R5/D7.)*

**Mai verificato:** la correttezza astronomica dell'output. Sappiamo che il
codice produce un SVG. Non sappiamo che sia giusto.

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
