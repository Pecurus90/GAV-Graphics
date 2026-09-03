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

**L'identità visiva esiste, ed è UNA (2026-09-02, D20).** Il GAV ha un manuale
d'identità (`docs/GAV-design-system.pdf`): blu notte, giallo stella, neutri. Da lì
viene l'unica palette del progetto, `brand/palettes/gav.json`. Non si sceglie e non
si compone: è il marchio. *Le stelle e i pianeti restano coi colori reali — sono
fisica, non gusto (D2).*

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
| `compose/compositor.py` | 171 | **CONDIVISO.** Il compositore: cammina i blocchi di un file di layout ed è **tool-agnostico** (hook `_render_block_tool` per i blocchi propri di uno strumento). Le primitive: testo, riga, pannello, **immagine (base64)**, icona, sfondo. **È ciò che Pillole eredita.** |
| `strumenti/cielo/messier.py` | 518 | Il profondo cielo (pagina 2): simboli, tabella, anti-collisione a tre strati, nomi delle costellazioni. Ospita `CONST_IT_MINORI` (vedi il confine, D14). |
| `strumenti/cielo/disc.py` | 297 | Il disco sigillato (D7). Legge `CONST_IT`, **non** `CONST_IT_MINORI`. |
| `strumenti/cielo/panels.py` | 223 | Pannelli: luna, pianeti, colori. |
| `strumenti/cielo/catalog.py` | 195 | Dati + funzioni pure: cataloghi, `SkyData`, `bv2hex`, geometria. Ospita `CONST_IT`. |
| `strumenti/cielo/ephemeris.py` | 184 | Effemeridi, proiezione. **Il cuore astronomico.** |
| `strumenti/cielo/engine.py` | 126 | L'assemblaggio: init + `generate()` + dispatch. |
| `engine/generate.py` | 17 | **Un ponte**, non il motore: re-esporta `Engine`/`bv2hex`/`STARS` perché `cielo.py` e `app/main.py` importavano da lì. Si potrà togliere aggiornando quei due import. |
| `cielo.py` | 84 | Il CLI (D1). Mappa i formati ai file di layout e **compone** motore + `render`. |
| `validate.py` | 246 | Validazione input (R4) + contratto del tema (D2). Condiviso da CLI e web, **non** importato dal motore (invariante #1). *(355 → 246 in #7r: via l'editor e la cartella delle palette utente. **Non c'è più un nome di palette da validare**: `carica_palette()` non prende argomenti.)* |
| `render.py` | 68 | SVG→PNG via resvg. Usato dal CLI **e** dalla web app. |
| `app/main.py` | 512 | Web app FastAPI: `/`, `/preview`, `/download`. *(814 → 510 in #7r: via i due endpoint dell'editor, la sua modale, il suo CSS/JS, e la riga di scelta della palette — che con **una palette sola** non ha più nulla da scegliere.)* **L'HTML sta dentro il `.py`**, non in template (debito `#7f`) — ma è una **raw string** `PAGINA = r"""…"""` riempita con `.replace()`, **NON una f-string**: le graffe del CSS non sono un problema, il CSS si riscrive libero. **La UI ESPONE i formati** (`<button class="fmt" data-fmt=…>`, riga ~309) + la barra laterale (D10). *(Riga riscritta 2026-07-16: diceva «98 righe» (erano 811), «f-string» (è `r"""`) e «espone solo l'A4, niente selettore di formato» (il selettore c'è). **Tre errori in una riga**: quinta smentita di questo file per misura.)* |
| `brand/layouts/*.json` | — | La composizione come dati. Il set è **`a4` · `dashboard` · `parata` · `zenit` · `deep-space`**. Aggiungerne uno = aggiungere un file. *(Riga corretta 2026-09-03: diceva ancora `profondo` — rinominato `deep-space` — e `cornice`, **ritirato in #7m**. Nominava cioè un file che non esiste e un formato che non esiste.)* |
| `brand/palettes/gav.json` | — | **LA** palette: una sola, l'identità visiva del GAV (D20). **Non** in `themes/`. |
| `data/stars6.json` | — | 5044 stelle GeoJSON, tutte con `mag` e `bv`. |

**Nessun file supera 520 righe** *(max: `messier.py`, 518 — ricontato 2026-09-03).* Il problema "apro un file e devo leggere
migliaia di righe" non esiste più.

> ⚠️ **OTTAVA SMENTITA PER MISURA, ED È LA STESSA DELLA SETTIMA.** #7q corresse questi
> conteggi il 2026-07-19 chiamandolo *«il caso più imbarazzante»*, e **sei settimane
> dopo 5 righe su 12 erano di nuovo sbagliate** — `panels.py` dato 247 quando erano
> 223, `cielo.py` 90 quando erano 84 — **prima** che questa sessione toccasse
> qualsiasi cosa. Più due righe che nominavano **file inesistenti**.
> *Il conteggio delle righe è la parte di questo file che marcisce per prima: cambia
> a ogni commit e nessuno lo guarda.* Ricontarlo costa una riga, e va fatto **prima**
> di fidarsi della tabella:
> ```powershell
> Get-ChildItem compose,strumenti,engine,app -Filter *.py -Recurse |
>   Where-Object { $_.Name -ne '__init__.py' } |
>   ForEach-Object { "{0,5}  {1}" -f (Get-Content $_.FullName).Count, $_.Name } | Sort-Object -Descending
> ```
> *Due trappole, entrambe prese ESEGUENDO il comando prima di scriverlo qui:* dentro
> `ForEach-Object` serve **`$_.FullName`** (con `$_` PowerShell passa il **nome** e
> `Get-Content` non trova il file), e serve **`.Count`** — **`Measure-Object -Line`
> NON conta le righe vuote** e dà 496 dove `wc -l` dà 518.

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
   *(Violato in silenzio fino al 2026-07-15, scoperto dalla CI — #8 M2/B1.)*
   `disc.py:75` ordinava le stelle con `np.argsort(-smag)` (quicksort **instabile**),
   e il **98% delle 5044 stelle è in pareggio di magnitudine** (411 magnitudini
   distinte, gruppo max 72). Il tie-break varia per CPU/build numpy → **ordine delle
   stelle diverso su ogni piattaforma** (Windows-CI e Windows locale davano valori
   diversi: 180,6 vs 532,6 per la stessa coordinata). Non era rumore d'ultima-cifra:
   un riordino. **La CI l'ha stanato, il golden a tolleranza l'ha giustamente
   respinto** (non si alza la tolleranza per un bug). Fix: `kind='stable'` (tie-break
   per indice originale, identico ovunque) + rigenerazione deliberata dei golden.
   *Lezione: "puro" su una macchina sola è un caso fortunato, non una prova.*

---

## Decisioni architetturali prese

- **D1 — Il PNG si genera anche da CLI.** `render.py` resta un modulo separato
  che il CLI *compone*; non viene fuso nel motore. Un solo percorso d'uscita
  SVG→PNG, testabile headless. *(Fatto, giro #5d: `cielo.py` compone motore +
  `render`; `--png` produce il PNG accanto all'SVG, larghezza per formato.)*
- **D2 — Il tema è un contratto validato, non un dict libero.** Una palette a
  cui manca una chiave deve dare un errore leggibile, non un `KeyError`.
  Motivazione *(originale, 2026: «stiamo per moltiplicare le palette» — **premessa
  caduta con D20**, il contratto no)*: oggi la palette è **una**, e il contratto
  vale ancora — anzi vale **di più**, perché è l'unico cancello fra il manuale
  d'identità e l'output. Se qualcuno traducesse male un token del manuale, D2 lo
  fa diventare **rosso** invece che sbagliato in silenzio. *(FATTO, #6n: `validate.py`
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
  - **⚠️ FONT DEL BRAND — SUPERATI (2026-09-02, vedi R16 e D20).** Oggi sono
    **Space Grotesk + Work Sans**, quelli del manuale d'identità: Marco, messo
    davanti alla divergenza, ha deciso che *«il manuale ha ragione»*. Barlow Semi
    Condensed e Instrument Sans sono stati **rimossi dal repo**. *(Testo originale,
    per memoria:)*
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
- **D13 — ⚠️ SUPERATA DA D20 (2026-09-02): il SET di sei palette non esiste più.**
  Ciò che **sopravvive** di D13, e che resta vero: la palette è **un file solo**
  (non si spezza per strumento — duplicare il marchio vuol dire cambiare l'oro del
  GAV in quattro posti e dimenticarsene uno), e la distinzione fra i **token di
  marca** e le **2 chiavi di astronomia pura**. Ciò che **cade**: le sei palette, la
  scelta fra loro, e l'idea che il valore stesse nella varietà.
  *(Testo originale, per memoria:)*
  **D13 — Una palette sola per tutti gli strumenti; ciò che varia è il CONTRATTO.**
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
- **D17 — Distribuzione: Python PORTATILE per-OS, non PyInstaller.**
  **⚠️ REVISIONE 2026-07-18 — SOLO WINDOWS, per ora.** *(Marco: «facciamo solo per
  Windows intanto; se ci sarà necessità faremo per Mac».)* Il **pacchetto Mac è
  sospeso**, non cancellato: la ricetta è già provata (R9 chiuso su Mac), riaccenderla
  costerà un pomeriggio, non un giro di scoperta.
  **MA la CI su macOS RESTA** (`ci.yml` ha `matrix.os: [windows-latest, macos-latest]`,
  e non si tocca). **Spedire su Mac e TESTARE su Mac sono due cose diverse:** quel
  runner è ciò che ha stanato l'`argsort` instabile — il bug che rendeva il motore
  **non deterministico fra macchine** e che su Windows da solo non sarebbe mai emerso.
  È la rete dell'invariante #6. Si toglie il pacchetto, non la prova.
  Decadono col pacchetto Mac: Gatekeeper, la firma Apple, l'`Avvia.command`, e la
  verifica della cartella-dati OS-condizionale (D18) — che resta **non provata** su Mac.
  *(Testo originale, per memoria: «E deve girare su Windows E Mac», deciso da Marco
  2026-07-15: «deve funzionare su windows e mac». Modello scelto dall'architetto sotto
  quel vincolo.)*
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
- **D18 — ⚠️ DECADUTA E RIMOSSA DAL CODICE (2026-09-02, commit `80ed047`).**
  L'editor esisteva per una ragione esplicita: *«Marco ha piena autonomia sui colori
  senza passare dal designer»*. **Con il manuale d'identità quella ragione non c'è
  più — si rovescia.** Il manuale ammette solo blu, giallo e neutri: uno strumento
  che permette a un socio di inventarsi i colori lavora **contro** l'identità.
  Notare che D18 conteneva **già l'argomento della propria fine** e nessuno l'aveva
  letto così: *«trenta soci, trenta identità visive»* era la ragione per cui il
  ricolore per-poster fu vietato. Il passo successivo — **una sola palette** — era
  la stessa frase portata fino in fondo.
  Ciò che **sopravvive** di D18: il principio che le **2 chiavi astronomiche non si
  toccano**, che oggi è strutturale invece che sorvegliato (non c'è più nessun
  cliente che possa mandarle).
  *(Testo originale, per memoria:)*
  **D18 — L'editor dei colori è un EDITOR DI PALETTE, non un ricolore del poster.**
  *(Marco, 2026-07-15: «slider sui colori come un programma di fotoritocco, per ogni
  elemento». Forma decisa con l'architetto.)*
  **Cosa produce, e perché conta:** l'output dell'editor è **una palette nuova
  salvata e validata**, NON "questo poster è colorato così". Due ragioni:
  - **Le 2 chiavi astronomiche restano BLOCCATE** (`star_ramp`, `planet_colors`):
    sono fisica, non gusto. Mai sullo slider, mai esposte — si **innestano** da
    osservatorio al salvataggio. È D2: *una palette può cambiare un blu, non può
    mentire sull'astronomia*. Non negoziabile.
  - **L'exe va a TUTTI i soci.** Ricolore libero per-poster = trenta soci, trenta
    identità visive, e le sei palette appena consolidate (D13) diventano carta
    straccia. Con l'editor-di-palette Marco ha **piena autonomia sui colori senza
    passare dal designer**, ma **la palette resta l'unità** e il socio continua a
    scegliere da una lista coerente.
  **Struttura:** slider/selettori sui **20 token di marca** + anteprima **sul cielo
  vero** + "salva come palette" (nome + descrizione → JSON in `brand/palettes/`,
  chiavi astronomiche innestate, `validate.py` come cancello). Appare nella lista
  come le altre.
  **Timing (Marco):** **PRIMA dell'exe** — la prima versione che arriva ai soci lo
  avrà dentro. Sposta il rilascio, consegna un'app più completa.
  **FATTO e verificato dall'architetto (2026-07-16).** Il cancello regge: iniettando
  un client malizioso (`Marte:#0000ff`) l'astro viene **innestato da osservatorio e
  il valore del client ignorato** — dimostrato col rosso. Nell'editor `star_ramp` e
  `planet_colors` sono **irraggiungibili**, e il vincolo è **detto all'utente** nel
  sottotitolo: *«Componi i colori del brand · le stelle restano coi loro colori
  reali»*. Poster reso con una palette creata a mano: bellissimo, e **le stelle
  mantengono i colori veri** (Arturo arancione, Antares rosso) su fondo viola.
  **Correzioni dell'esecutore, accettate:**
  - **I colori editabili sono 26, non 20** (16 piatti + `bg`×3 + `disk`×3 +
    `status`×4). L'architetto confondeva "20 chiavi" con "20 colori" (e
    `descrizione` non è un colore). Contato e confermato.
  - **`disk` è EDITABILE, non innestato:** non è fisica, è lo sfondo del disco =
    identità visiva. Prova: **le 6 palette di serie hanno `disk` diversi**.
    *(Wart segnalata, non corretta: `validate.py` lo classifica sotto "astronomia"
    pur senza vincolo fisico — raggruppamento fuorviante, funziona lo stesso.)*
  - **Il CLI legge dall'unione** (di-serie + utente): una palette dell'editor si usa
    anche da riga di comando. Era un bug introdotto dall'unione stessa.
  **Misura dell'anteprima (smonta l'ipotesi dell'architetto):** effemeridi **~0 ms**
  → non c'è geometria da cachare; il costo è il **raster** (932 ms @1080, 538 @600),
  che dipende dal tema e quindi **non è cacheabile**. Anteprima ~0,8 s a 600 px,
  aggiornata al rilascio del cursore, spinner onesto (nessuna live-preview promessa).
  **Dove vivono le palette utente:** cartella **dati dell'OS** (non nel bundle) →
  **sopravvivono all'aggiornamento** del pacchetto. Prezzo accettato: non viaggiano
  se il socio copia la cartella su un altro PC.
  **Non verificato:** su **Mac** la cartella dati e il render con palette utente non
  sono provati (codice OS-condizionale, eseguito solo su Windows) — da coprire in B2.
- **D19 — La palette è del POSTER, non dell'APP.** *(Marco, 2026-07-18; forma con
  l'architetto.)* Le sei palette (D13) vestono l'**output**. Il **guscio**
  dell'applicazione è un'altra cosa e **non** si veste col tema del poster: sarebbe
  assurdo che cambiare l'oro del GAV ripitturasse la UI.
  **L'argomento non è estetico, è strutturale:** dentro il guscio vive l'**anteprima
  del poster**, e l'editor (D18) mostra **cieli di sei colori diversi** — verde
  aurora, viola nebulosa, ottone, blu-argento. Un guscio dipinto con **uno** dei sei
  **litiga con gli altri cinque**. Un'interfaccia neutra non è gusto: è l'unica che
  non combatte col contenuto che deve ospitare.
  *Applicato in #7l: guscio acciaio (`--acc #6f89a8`), zero token del poster nel
  chrome. I due colori del poster compaiono solo COME CONTENUTO — i pallini delle
  palette e i campioni dell'editor.*
  **⚠️ L'ARGOMENTO DI D19 È CADUTO CON D20, LA CONCLUSIONE NO — e vale la pena
  saperlo, perché la domanda tornerà.** «Un guscio dipinto con uno dei sei litiga
  con gli altri cinque» non ha più senso: di cieli ce n'è **uno**, e in teoria il
  guscio *potrebbe* indossarlo. **Resta neutro lo stesso**, per una ragione diversa
  e più semplice: dentro il guscio c'è l'**anteprima del poster**, e se guscio e
  poster fossero blu-notte uguali **sparirebbe il confine fra l'applicazione e ciò
  che l'applicazione produce** — il socio non saprebbe più dove finisce la UI e
  dove comincia il suo volantino. *(E i due esempi che D19 citava come «contenuto»
  — i pallini delle palette e i campioni dell'editor — non esistono più: erano
  proprio le due cose rimosse in #7r.)*
  **CODA APERTA (#7t, 2026-09-03).** L'audit di conformità ha misurato che il guscio usa
  **19 colori che non stanno nel manuale** (tutti i suoi hex distinti). Metà della questione **si è chiusa da
  sola**: il verde `#5fd08a` e l'ambra `#e8b45f` erano **dichiarati e mai usati** — zero
  occorrenze di `var(--ok)`/`var(--warn)` — cioè codice morto, tolto.
  Resta il rosso `#e0664a` degli errori, e la **raccomandazione è di tenerlo**: il
  manuale dichiara il proprio perimetro alla prima riga — *«sito web, slide, social,
  locandine e brochure»* — non descrive **stati d'interfaccia** e non definisce un
  colore d'errore. Un errore in giallo sarebbe indistinguibile da un accento. *È lo
  stesso confine per cui `star_ramp` è fuori dal perimetro: il manuale governa ciò che
  governa.*
  **La domanda che resta è di Marco, ed è quella di D19:** l'acciaio resta, o il guscio
  passa ai neutri del manuale?
- **D20 — L'IDENTITÀ È UNA: una sola palette, e non è una scelta dell'utente.**
  *(Marco, 2026-09-02: «abbiamo un'identità ora ben distinta, quindi rimuovere le
  varie palette e la possibilità di crearle e farne una standard seguendo il
  foglio». Forma con l'architetto, dopo lettura del manuale.)*
  La fonte è il **manuale d'identità visiva del GAV** (edizione agosto 2026, copia
  in `docs/GAV-design-system.pdf` — **committato apposta**: così la provenienza dei
  colori è *verificabile*, non asserita). Dice: blu GAV `#024f6d`, giallo stella
  `#fde875`, grigio luna, blu notte `#01141d`, una scala blu 50→950 e dei neutri —
  e **«nessun altro colore decorativo oltre a blu, giallo e neutri»**.
  **Il ribaltamento rispetto a D13/D18, ed è il punto:** sei palette erano una
  ricchezza finché l'identità non c'era. Con un manuale in mano diventano
  un'**ambiguità** — e l'editor, che serviva a comporne altre, diventa uno strumento
  che lavora *contro* il marchio. Non è una semplificazione per pigrizia: è che la
  premessa è cambiata.
  - **`brand/palettes/gav.json`** — i 26 colori di marca, ognuno un passo della scala
    del manuale o un suo token semantico del «tema notte». Nessun colore inventato.
  - **Due token li ha decisi Marco perché il manuale non li copre:** il **neon**
    (`#9dccdc`, blu 200 = il `--link` del tema notte — il manuale non ha un «neon»,
    e l'invariante #4 lo pretende) e i quattro **`status`**, **neutralizzati** dentro
    la tavolozza (via il verde e l'ambra: erano il quinto e il sesto colore).
  - **DUE token li ha decisi il RENDER, non la carta**, ed è la parte che vale:
    `border` da blu 400 a **600** (a 400 la cornice del disco era la cosa più satura
    del poster e **rubava l'occhio alle costellazioni**) e `grid` da blu 800 a **700**
    (a 800 i cerchi d'altezza **sparivano** sotto `opacity .7`). Nessuna delle due si
    poteva vedere sulla tavolozza: si vedono **guardando il poster ritagliato al 3×**.
  - **`star_ramp` e `planet_colors` NON cambiano — copiate verbatim.** Il divieto del
    manuale governa il **marchio**, non il **dato**: Antares rossa non è decorazione,
    è il contenuto. Questa è D2, e non è negoziabile.
  - **La palette non è più un PARAMETRO in nessun entry point**: via `--palette` dal
    CLI, via `?theme=` dai tre endpoint, via la riga dalla barra laterale. *L'input
    più sicuro è quello che non esiste* — ed è R4/D4, non estetica: un parametro che
    può avere un valore solo è superficie d'errore a costo zero di beneficio.
  - **Prezzo accettato, e sappilo:** `luce-rossa` **è persa**, e non era un gusto —
    portava una **funzione** (`nota: "si guarda stando al telescopio"`: il poster che
    non rovina l'adattamento al buio). Marco l'ha scelto sapendolo. Resta nella
    storia: `git show 80ed047^:brand/palettes/luce-rossa.json`.
  **SECONDO GIRO, 2026-09-02 — «allinea tutto al documento» (Marco).** Il primo giro
  aveva lasciato **3 colori su 26 fuori dal manuale**: gli stop dei gradienti, che
  l'esecutore aveva **interpolato** fra due passi della scala invece di usare i passi.
  Verificato **estraendo i colori dagli oggetti vettoriali del PDF** (non letti da uno
  screenshot: `page.get_drawings()` dà i valori veri) e confrontandoli uno per uno.
  **Ora 26 su 26 vengono dal manuale.** E la distinzione trovata misurando vale oltre
  il caso: due dei tre (`disk[0]`, `disk[2]`) erano **punti interni** al segmento fra
  due passi — cioè colori che il gradiente **attraversa comunque**, scritti come stop
  o no. Solo `bg[2]` usciva davvero (più scuro del blu 950 su tutti i canali). *«Non è
  nel manuale» e «esce dalla tavolozza» non sono la stessa cosa.*
  **E il disallineamento peggiore non era un colore.** Controllando *tutte* le
  prescrizioni, non solo §3:
  - **Il TITOLO era tutto maiuscolo su tutti e 5 i formati** (`IL CIELO DI AGOSTO
    2026`, corpo 30-56). Il §4 dice *«testo in sentence case, MAIUSCOLO solo per
    piccole etichette»*, e i mockup del manuale stesso scrivono i titoli in sentence
    case (*«Il cielo dei Colli Berici»*). Tre conferme indipendenti nello stesso
    documento. Ora è `Il cielo di {month_name} {year}`, e la gerarchia è finalmente
    quella che il §4 descrive: **etichetta maiuscola piccola → titolo grande → testo**.
    *Le etichette (`FASI LUNARI · AGOSTO`, `PIANETI VISIBILI`, corpo 11-15) restano
    maiuscole: il manuale le ammette. La regola non è «via il maiuscolo», è «il
    maiuscolo solo dove è piccolo».*
  - **`GAV · Vicenza` nel piedino di deep-space**: il §1 vieta la sigla *«da sola come
    firma»*. Tolta — stessa ragione per cui #7n l'aveva già tolta dall'A4 (ripete la
    testata, che porta la denominazione per esteso).
  **La leggibilità non è peggiorata, ed è stato MISURATO prima di consigliare:** il
  fondo pagina si schiarisce di 11-22 livelli, ma il contrasto stelle↔cielo dentro il
  disco resta identico (196,4 → 198,3) — perché ciò che cambia è il fondo *pagina*,
  dove di stelle vere non ce n'è. *L'architetto aveva sconsigliato la variante chiara
  temendo la leggibilità: **ritrattato dopo la misura**.*
  **Golden mosso, e la previsione era diversa per i due:** il **disco** solo colori
  (scheletro identico, il titolo non ci sta dentro); l'**A4** colori **+ UNA sola riga
  non-colore**, e stessa `x`, stessa `y`, stesso corpo — solo il testo. Verificato
  prima di rigenerare.
  **✅ E DAL 2026-09-03 D20 HA UNA RETE, non più solo la disciplina** (#7t):
  `tests/test_identita_manuale.py` pretende che **ogni** colore di marca sia un passo
  della tavolozza del manuale — i cui valori sono **estratti dagli oggetti vettoriali
  del PDF**, non letti a schermo. Sorveglia il colore **inventato**, non *quale* passo:
  ritarare `border` da blu 400 a 600 (ciò che D20 stesso ha fatto guardando il poster)
  resta legittimo. `star_ramp`/`planet_colors` sono esclusi **strutturalmente**, e un
  test dimostra che l'esclusione **non è vacua**. C'è una **guardia**: un token nuovo
  non può scivolare fuori dalla rete, va classificato a mano.
  *Prima di questo, ritoccare un blu lasciava la suite verde.*
  **⚠️ IL MANUALE E IL REPO NON SONO ALLINEATI SUI FONT — vedi R16.** Il giro dei
  colori si è fermato lì apposta: è il disallineamento **più visibile che resta**
  (la tipografia si riconosce prima del colore), ma costa un giro intero.
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
    dentro `app/main.py`. Se #7f introdurrà dei template veri, andranno aggiunti
    qui.)* *(Corretto 2026-07-16: diceva «in una f-string». È una **raw string**
    `r"""…"""` riempita con `.replace()`.)*
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
4b. **#7i — Il set finale dei quadrati.** *(FATTO, 2026-07-16.)* Il set è
   **a4 · dashboard · parata · cornice · zenit · profondo**. Ritirati `post`,
   `editorial`, `rail` (ognuno con un erede; `post` portava ancora il vecchio
   `moon_panel` a 4 fasi: debito, non minimalismo). **Default: `dashboard`** —
   Marco ha visto Zenit reso e ha scelto dashboard; il cancello «prima vederlo
   reso» è servito a questo. Unica aggiunta di codice: il pannello accetta
   `fill_opacity`/`opacity`/`stroke_opacity` **opzionali** (il vetro di Zenit),
   emessi solo se presenti → golden fermi. Il pannello dei colori si chiama ora
   **«TEMPERATURA STELLE»** su tutti i quadrati.
   **DUE DIFETTI APERTI, misurati dall'architetto sull'output reso** (prossimo
   giro, dopo R11):
   - **Zenit non aveva i punti cardinali. RISOLTO (2026-07-16, commit `6fb4448`).**
     Esistevano nell'SVG ma cadevano **fuori dal canvas** e resvg li tagliava:
     `rad=560` su canvas 1080 e `disc.py:124` aveva `rr=rad+22` **cablato** → N a
     y −42, S a 1122, E a x −42, O a 1122. **Era una carta del cielo senza
     orientamento** (invariante #3). Solo Zenit.
     Fix: `+22` è ora `cardinal_gap`, **parametro opzionale** del blocco `disc`
     (additivo come `fill_opacity`: assente ⇒ identico); `zenit.json` usa
     `"cardinal_gap": -27` e li mette **dentro** il bordo, restando a tutto campo.
     Coordinate reali dopo il fix: **N(540, 28.1) · E(19.4, 548.8) ·
     S(540, 1069.4) · O(1060.6, 548.8)** — tutte dentro. Altri formati: **0 righe
     cambiate** (verificato diffando prima/dopo via `git stash`, non dedotto).
     **E ora c'è una RETE, non un'occhiata**: `tests/test_cardinals.py` pretende i
     quattro cardinali dentro il canvas **per ogni formato**; iniettato il guasto
     → `FAILED [zenit]` con `assert 0 <= -43.3`, ripristinato → 5 verdi.
   - **⚠️ CORNICE È STATO RITIRATO (2026-07-18).** Vedi **#7m**: la ricognizione lo
     mette **primo fra i difetti**, con quattro problemi sommati. Marco: *«ritirarlo»*.
     Il set finale è **`dashboard · parata · zenit · a4`** (+ `profondo`). Il paragrafo
     qui sotto resta come **storia della diagnosi** — è il ragionamento che ha portato
     al ritiro, e vale più della conclusione.
   - **Cornice: il pallino di Marte è verde. (Chiuso col ritiro.)**
     Usa `"dot": {"fill_status": true}`; dashboard/zenit usano `fill_planet`,
     parata usa `planet_parade`. **Ereditato fedelmente da `editorial`** — non un
     errore dell'esecutore — ma ora Cornice è **l'unico**, ed è *la stessa forma di
     debito* per cui `post` è stato ritirato. Sullo stesso poster c'è la legenda
     «TEMPERATURA STELLE» che insegna *pallino = colore fisico*: un Marte verde lì
     sotto è ciò che **D2** esiste per impedire.
     **L'architetto aveva ordinato `fill_planet`. L'esecutore si è FERMATO, e aveva
     ragione** *(settima correzione, misurata contro una deduzione)*: in Cornice
     l'osservabilità **vive solo nel colore del pallino** — Cornice mostra nome e
     orari, **non la nota** che i tre fratelli hanno. Con `fill_planet` liscio
     Urano/Nettuno (`info` = *«Telescopico»*, `ephemeris.py:135`) perderebbero
     l'unico segno che servono un telescopio.
     **Gerarchia dei due mali, ed è ciò che decide:** Marte verde è
     un'**incoerenza** (nessuno ci rimette una serata); «Telescopico» che sparisce
     **manda un socio a cercare Urano a occhio nudo** e a concludere che il
     programma sbaglia — il peccato che il progetto nomina più volte (*«mai mandare
     l'osservatore a cercare il nulla»*: è la ragione per cui M33 non dice
     «binocolo»). L'istruzione dell'architetto, presa alla lettera, avrebbe
     **peggiorato** il poster.
     **La diagnosi vera non è «token sbagliato»: Cornice ha perso la COLONNA DELLE
     NOTE** che dashboard/Zenit/Parata hanno, e usa il pallino come surrogato. Il
     `status_ring` (che `panels.py:52` già supporta) sarebbe lo stesso difetto
     travestito: un secondo linguaggio sullo stesso pallino, **senza legenda**.
     Dove entrano le note è una domanda di **spazio e gerarchia** = designer.
     *Marco (2026-07-16): si tiene `fill_status` — male minore e reversibile — e il
     Task 2 si chiude dentro il giro di design.*
   **LA LEZIONE, che vale più dei due difetti:** l'esecutore ha scritto «PNG 1080,
   **guardati**» — e li aveva guardati davvero. **Guardare trova solo ciò che stai
   cercando.** È identico a R10 (una collisione grossolana sopravvissuta a dieci
   giri di gente che guardava). La conclusione non è «guarda meglio»: è che quel
   controllo va reso **una rete** — un test che pretenda i cardinali **dentro il
   canvas**, con l'iniezione del guasto.
4c. **#7l — Il GUSCIO dell'app rifatto (design «1c Scheda tecnica»).**
   *(FATTO, 2026-07-18.)* Marco, guardando l'app: *«la sidebar e tutto lo stile sono
   da rivedere, da app più seria. Non deve usare una palette colori come quella dei
   post»*. **Aveva ragione su una cosa che nessuno aveva visto: il guscio indossava
   l'identità del CONTENUTO** — `--oro #e4ac4a` e `--neon #45c8ff`, i colori del
   poster, erano i colori della UI. E non era una nostra deriva: **l'aveva disegnato
   così il designer** (verificato: valori identici fra il suo file e l'app).
   **Perché è sbagliato per costruzione, non «meno bello»:** dentro il guscio c'è
   l'anteprima del poster, e l'editor mostra **cieli di sei colori diversi**. Un
   guscio dipinto con uno dei sei **litiga con gli altri cinque**.
   → **D19.** Il designer ha consegnato **tre direzioni** (Console · Editoriale ·
   Scheda tecnica); Marco ha scelto **1c**. Guscio ora **acciaio neutro**
   (`--acc #6f89a8`, `--prim #3f5f83`): zero oro/neon nel chrome.
   **Il riordino (l'altra metà della richiesta):** la toolbar con «Genera» è salita
   **in cima** al pannello — prima l'azione principale stava **in fondo a uno scroll**.
   Formato = controllo segmentato con glifi; palette = riga con 4 pallini (token veri).
   **La regola che ha salvato l'implementazione:** *«prendi il suo CSS, NON il suo
   JavaScript»*. Il mockup ha logica **simulata** (`setInterval` a 850 ms per le fasi,
   anteprima fatta di `div`); l'app ha logica **vera**. Importarla sarebbe stata
   un'app più bella che **mente** — ciò che D11 vieta. Verificato sull'HTML servito:
   niente `setInterval`, niente switcher da mockup, niente Google Fonts.
   **Tre correzioni al designer, obbligatorie perché non vede il repo:** i colori di
   stelle/pianeti nella sua anteprima erano **hex cablati e non i nostri** (invariante
   #2); la sua anteprima è uno **schema CSS** mentre la nostra è il **cielo vero**
   (implementarla sarebbe stata una **regressione**); mancava il campo **descrizione**.
   *Poi (`4ee6825`): anteprima del poster molto più grande — tolto il cap
   `min(64vh,640px)`, +36% lineare sul singolo. Il carosello resta ~metà per geometria:
   due pagine affiancate si dividono la larghezza.*
4d. **#7m — La RICOGNIZIONE dei formati, e cosa ne è uscito.** *(2026-07-18.)*
   Marco, guardando i poster: *«dashboard funziona e non si tocca, è la fonte di verità
   — il disco ha le tacche dei gradi, gli altri no. Son tutti da ritoccare tranne
   dashboard.»* Da lì una **ricognizione** (diagnosi, **non** ridisegno) chiesta al
   designer sui **render veri**, tutti allo stesso cielo (agosto 2026, osservatorio).
   **Le divergenze, misurate:**
   | | dashboard | parata | cornice | zenit | a4 |
   |---|---|---|---|---|---|
   | Tacche gradi | **sì** 10°/30° | no | no | no | no |
   | Icone social | 3 | 3 | **0** | **0** | 2 *(manca email)* |
   | Pianeti | 5 | **7** | 5 | 5 | **7** |
   | Colore pallino | reale | reale | **osservabilità** | reale | reale |
   **DECISIONI DI MARCO:**
   - **`cornice` RITIRATO.** Quattro difetti sommati (Marte verde · niente colonna
     note · zero icone · testata accorciata): **stesso profilo di `post`** — debito
     accumulato, non bruttezza. Set finale: **`dashboard · parata · zenit · a4`**
     (+ `profondo`). Default: `dashboard`.
   - **SETTE pianeti ovunque, con «Non osservabile».** Era metà e metà (5 filtrati su
     dashboard/cornice/zenit, 7 su parata/a4): **due scelte editoriali opposte che
     nessuno aveva mai preso.** La regola scelta: dire *«Giove c'è, ma non stanotte»* è
     informazione utile; il filtro nasconde e basta.
     **⚠️ ATTENZIONE ESEGUENDOLO: è la mossa che ha generato R10** — *«il pannello
     delle fasi si sovrappone a quello dei pianeti, **cresciuto a 7 voci**»*. Il
     pannello cresce di `2 × step`: va **calcolato prima e GUARDATO dopo**, non
     affidato alla suite (il golden confronta i byte, non i pixel).
   - **Le tacche dei gradi restano una domanda aperta** (su Zenit il disco è a tutto
     campo e non ha un bordo su cui appoggiarle: è geometria, non un interruttore).
   **⚠️ DIFETTO NUOVO, CONFERMATO SUI PNG — le etichette di ZENIT collidono.**
   Col disco a tutto campo i nomi delle costellazioni finiscono **sotto i pannelli**
   («Orsa Maggiore» tagliata a metà dal riquadro pianeti; Thuban/Mizar sul bordo) e
   **sopra la striscia lunare** («Sagittario» attraversa il pannello; un'etichetta si
   sovrappone a «20 Primo Q.»; «Scorpione»/«Antares» finiscono sul testo dei contatti).
   **La causa è ARCHITETTURALE, ed è il punto da ricordare:** il **disco è sigillato
   (D7) e non sa cosa gli sta sopra** — le etichette le disegna `disc.py`, i pannelli
   il compositore, e **non si parlano**. Negli altri formati non si vede perché il disco
   è piccolo e i pannelli stanno fuori; in Zenit il disco è full-bleed e i pannelli ci
   stanno **sopra**. **Stessa famiglia del bug dei cardinali.** Non si tappa con una
   toppa: è un giro a sé.
   **LA LEZIONE, la terza volta che il progetto la impara:** Zenit l'avevano **guardato
   in tre** — esecutore, Marco, architetto — e nessuno l'aveva vista. Serve un occhio
   che confronta **cinque poster affiancati**. *Guardare trova solo ciò che stai
   cercando* (come R10, dieci giri; come i cardinali).
   **E una lezione sul METODO, pagata cara:** il primo giro di ricognizione è stato
   **buttato** perché il designer aveva misurato il proprio mockup — l'unica fonte che
   può vedere — e quel mockup era **più vecchio del programma**. Vedi *«Il confine col
   designer»* nel Metodo di lavoro.
4e. **#7n — FASE 1: il contenuto unificato fra i formati.** *(FATTO, 2026-07-18.)*
   Marco: *«dashboard ok, non c'è da fare nulla»* — **fonte di verità, intatto**; gli
   altri si allineano. **Prima il contenuto, poi la geometria**, e la ragione è
   operativa: fissato cosa deve starci dentro, si sa **quanto spazio resta al disco**.
   Al contrario si ingrandisce la mappa e poi si scopre che il contenuto non ci sta.
   - **Testata** allineata su Zenit (diceva «Nord Italia…», ora «Cielo visibile dal
     Nord Italia…» come gli altri tre).
   - **Legenda «TEMPERATURA STELLE» rimessa sull'A4** — la coda di #7h, chiusa.
   - **Piedino A4**: aggiunta l'email, tolto «GAV · Vicenza» (ripeteva la testata) →
     `instagram · facebook · email`, identico a dashboard e parata.
   - **Icone di Zenit: RIMANDATE, deliberatamente.** Il contenuto **c'è già** (entrambi
     i contatti in una riga); manca solo lo *stile* a icone. E quella riga sta **dentro
     la zona che collide** con Scorpione/Antares: si rifà **una volta sola**, nel giro
     delle etichette. *(L'architetto aveva detto «tre icone ovunque, è meccanico»:
     sbagliato, corretto dalla misura dell'esecutore.)*
   **Il golden dell'A4 si è mosso, DELIBERATO E CONTATO:** 15 aggiunte, 1 rimozione,
   leggibili riga per riga (i 13 della legenda + icona email `<g><path>` + indirizzo,
   meno «GAV · Vicenza»). **Disco intatto.** I sei colori vengono da
   `bv2hex(star_ramp, bv)` — **nessun hex cablato** (invariante #2).
   *È la differenza fra un golden **mosso** e uno **rigenerato perché era rosso**.*
   **Nona correzione dell'esecutore:** l'architetto prevedeva `+1 <image>` per l'icona
   email — sono **glifi `<path>` inline** (Simple Icons via `_render_icon`), non raster.
   Il golden ha **un solo `<image>`, il logo**. Non è un cavillo: cercare un `<image>`
   in più e non trovarlo avrebbe fatto concludere che il fix non era entrato.
   *Principio confermato: ci si ferma quando **non torna il conto**, non quando torna
   per una strada diversa da quella prevista.*
4f. **#7o — FASE 2: la GEOMETRIA.** *(FATTO, 2026-07-18.)* Marco: *«portare la mappa
   il più grande possibile negli altri; Zenit perde leggibilità con le stelle e i
   pianeti sopra»*. **Un solo problema visto da due lati:** più il disco cresce, più i
   pannelli gli finiscono **sopra** invece che **accanto**. Le due disposizioni che non
   collidono mai — dashboard **affianca**, a4 **impila** — non mettono **mai** pannelli
   sul disco.
   **Il principio, dal designer:** *il 50% di dashboard è il tetto di **una
   disposizione**, non un numero universale.*
   | | prima | dopo |
   |---|---|---|
   | dashboard | 50% | **50%** *(fonte di verità, disco intatto)* |
   | parata | 36% | **46%** (r250) |
   | zenit | 104% | **82%** (r445) |
   | a4 | 85% | **85%** — *già al massimo, misurato* |
   - **Via gli orari da TUTTI** (`↑10:23`/`↓21:50`): restano nota e direzione. Il poster
     è **mensile**, gli orari valgono per il ~15 e **derivano di ore** lungo il mese —
     falsa precisione. *(L'architetto voleva tenerli sull'A4: incoerente, corretto da
     Marco.)* **Due conseguenze impreviste, trovate dall'esecutore:** la didascalia
     «alzata ↑ / tramonto ↓» diventava **una legenda di simboli inesistenti** (tolta), e
     restava un **buco di ~62 px** fra nome e nota (chiuso, e lo spazio è andato al disco).
   - **Zenit: direzione A del designer, ma solo in parte — e il taglio l'ha deciso la
     misura.** Disco a r445 + etichette 31→22 **hanno chiuso due collisioni su tre da
     sole**. I **pannelli agli angoli no**: i suoi rettangoli **non contengono il
     contenuto** (sottotitolo che sfora di 75 px, sei campioni in 180 px), e farceli
     stare significa decidere **corpi e trattamenti** = progettare. *Lui stesso aveva
     avvisato: «anche a 82% gli angoli restano stretti».* Si è fatto il **tocco leggero**:
     pannello pianeti spostato quanto basta a liberare «Orsa Maggiore», e `cardinal_gap`
     ritarato — **col segno opposto**: a r445 il disco **rientra nel canvas**, quindi i
     cardinali vanno spinti **fuori** (`-27` → **`+65`**). La stima del designer (−21) li
     tirava **sotto i pannelli**.
   - **A4: FERMATO al 90%.** Misurato: 8 px dalla testata sopra, **2,5 px dalla legenda
     sotto**; per il 90% servirebbero 32 px inesistenti. **La legenda vince** — è quella
     appena rimessa (coda #7h), barattarla per +1,4% di disco è un cattivo affare.
   - **Tacche dei gradi: sì dashboard, NO a4.** Il designer aveva detto sì a entrambi;
     rendendo, la tacca **Sud taglia in due «≈ 7.000 K»** — le tacche escono di **17 px**
     e la striscia libera è di **16**. Ritirate dall'A4; il golden è tornato
     **byte-identico** a prima (aggiunta e rimozione, giro esatto).
   - **Riequilibrio del dashboard:** coi 7 pianeti il pannello andava a passo 30 mentre
     la legenda restava a 36 — **stessa altezza di contenuto (180 px), ritmo diverso**.
     La legenda cede spazio ai pianeti: la griglia torna uniforme.
   **⚠️ SCOPERTA GRAVE — due decisioni di Marco erano DOCUMENTATE ma MAI ESEGUITE.**
   `cornice` risultava ritirato e i pianeti «sette per tutti» **solo in questo file**: sul
   disco `cornice.json` c'era ancora, e dashboard/zenit filtravano a 5. Il prompt che le
   conteneva si era perso fra un giro e l'altro, e **l'architetto ha registrato l'esito
   senza verificare l'esecuzione**. *Lezione, ed è dell'architetto: **«deciso» non è
   «fatto»**. Questo file deve registrare ciò che è **verificato nel codice**; una
   decisione presa e non eseguita va segnata come tale, o il file diventa il README
   inaffidabile contro cui mette in guardia alla prima riga.* *(Entrambe poi eseguite:
   `cbe87ba` cornice, `6b277eb`+`3faaecb` i sette pianeti.)*
   **DUE LEZIONI SUL METODO, che valgono oltre questo giro:**
   1. **«Conta il golden» e «guarda l'immagine» NON sono ridondanti: sono reti con
      maglie di forma diversa.** La tacca dentro «≈ 7.000 K» è sfuggita all'occhio
      dell'esecutore (che cercava collisioni *sul bordo del disco*) ed è stata presa
      dall'architetto **leggendo le coordinate del golden** (`y884→901` attraversa
      `y891`), con l'immagine a confermare **dopo**. Serviva l'incrocio.
   2. **Il designer risponde su un bersaglio che si muove.** Due sue risposte sbagliate
      — «a4 può salire al 90%» e «sì tacche sull'A4» — avevano **la stessa causa**: la
      legenda dell'A4 **non c'era** quando le ha date, l'abbiamo rimessa noi in Fase 1.
      Non è un suo errore: è l'effetto del lavorare in parallelo. *Quando gli si chiede
      qualcosa, va detto cosa è cambiato da ieri.*
   **La rete dei cardinali è stata ESTESA** (`test_cardinals.py`): non più solo «dentro
   il canvas», ma **«non sotto un pannello»** — perché a r445 la `S` finiva **sopra la
   striscia lunare** e il test **passava lo stesso**. *Il buco aveva la stessa forma del
   bug che la rete doveva sorvegliare.* Iniettato il guasto → rosso su **N**, ripristinato
   → verde. *(Proposta non fatta, giro a sé: una rete che pretenda che nessuna tacca
   attraversi un blocco di testo. Difficoltà nota: la larghezza del testo non sta
   nell'SVG.)*
4g. **#7p — LA RICOGNIZIONE SISTEMATICA (60 poster) e l'A4 sull'anti-collisione.**
   *(2026-07-19.)* Marco: *«genera le 12 immagini per i 5 formati, analizzale e fammi
   un report generale»* — per chiudere le collisioni **una volta per tutte**, invece di
   rammendare il mese che si sta guardando.
   **Lo strumento, non l'occhio:** `tools/collisioni.py` (committato) legge i layout e
   i 60 SVG di `out/sweep/` e misura cinque categorie. **È diagnosi, non un test**, e non
   corregge nulla. Il punto duro dichiarato: *la larghezza del testo non sta nell'SVG* —
   stimata `n_char × corpo × fattore`, col fattore **calibrato rendendo stringhe isolate
   e misurandole dal raster** (0,40 per le etichette — Barlow è condensato; ~0,50 per il
   tutto-maiuscolo). Errore ±1 px su soglie di 3-4 px: le collisioni grosse sono robuste,
   i quasi-contatti si confermano a occhio (ed è ciò che si è fatto).
   **Calibrato su tre difetti VERI e ritrovati tutti e tre** (Auriga↔Capella, zenit-nov,
   parata N/S pre-fix): *se non li avesse ritrovati, lo strumento era rotto.*
   | | sotto-pann. | banda | etich↔etich | cardin. | tacca-testo |
   |---|---|---|---|---|---|
   | dashboard | 0 | 0 | 31 *(quasi)* | 0 | 2 |
   | parata | 0 | 0 | 18 *(quasi)* | 0 | 2 |
   | **zenit** | **56** | 0 | 7 | 0 | 0 |
   | a4 | 0 | 0 | 19 *(**15 VERE**)* | 0 | 2 |
   | deep-space | 0 | 0 | 9 *(quasi)* | 0 | 15 *(lievi)* |
   **I fix di ieri hanno TENUTO su un anno intero**, non solo sul mese guardato: banda e
   cardinali sono **0 su tutti e 60**. È la prima volta che il progetto lo sa invece di
   sperarlo.
   **Due problemi strutturali, di natura diversa — ed è la scoperta che conta:**
   - **zenit (56/anno) — il D7 puro.** Il disco full-bleed passa sotto i pannelli e
     **non sa che ci sono**. *Prova numerica che il rammendo è morto:* **Mizar è pulito
     ad agosto — il mese su cui era stato rammendato (`4090986`) — e sepolto al 100% a
     novembre**; le etichette sepolte oscillano **3/32 (9%) ad agosto → 11/33 (33%) a
     novembre**. I colpevoli di novembre non sono quelli di agosto. **Giro a sé, aperto.**
   - **a4 — 15 sovrapposizioni VERE, ed erano CONGELATE NEL GOLDEN.** L'A4 era l'unico
     formato **senza anti-collisione**. E la cosa da ricordare è che *il codice lo diceva
     a voce alta* (`disc.py:88`: «*le etichette sono piazzate ingenuamente (le
     sovrapposizioni restano); è ciò che il golden A4 sorveglia*») e **nessuno l'aveva
     letto come un difetto per dieci giri**. È **R10 nella stessa identica forma**: il
     golden dice che l'output non è cambiato, non che è giusto.
   **FATTO (`805cfe1`): l'A4 passa a `declutter` — UNA RIGA nel layout.** 15 → **0** su
   tutti i 12 mesi. Le stelle-guida **non spariscono** (senza `star_names` il declutter
   ripiega su `MARQUEE`, come parata): Capella/Vega/Antares/Deneb/Altair/Arturo restano.
   **Il golden mosso, contato dall'architetto per una strada indipendente:** 17 `<text>`
   fuori / 17 dentro, **zero elementi non-testo** → disco intatto. **Ma delle 17 solo
   DUE si sono spostate davvero** — `Auriga` (y188,9→194,5, si stacca da Capella a
   y181,5) e `Scorpione` (y751,6→740,3, si stacca da Antares a y752,5): le altre 15 hanno
   **coordinate identiche**, il declutter le emette solo in **ordine** diverso nel file.
   *L'esecutore aveva riportato «34 righe, TUTTE riposizionate»: **il conto tornava, la
   spiegazione no**.* E la strada vera è **una prova migliore** di quella portata: agosto
   ha **esattamente 2** collisioni nella ricognizione e il declutter ha mosso
   **esattamente 2** etichette, che sono **i difetti calibratori**. *Principio confermato
   (già scritto in #7n): ci si ferma quando **non torna il conto**, non quando torna per
   una strada diversa da quella prevista — e qui fermarsi ha fatto emergere la prova
   forte.*
   **La rete che seguiva il cambiamento è VIVA, provata dall'architetto e non
   sull'asserzione dell'esecutore:** `test_disc_e_fetta_dell_a4` è stato aggiornato a
   `declutter=True` (obbligato: il frammento deve restare una **fetta verbatim** dell'A4,
   D7). Iniettato il guasto — frammento rimesso naive — → **rosso** con l'asserzione vera
   («*Il disco non è più una fetta VERBATIM dell'A4, invariante D7*»), ripristinato →
   verde, repo pulito. *Il test insegue la realtà; non è stato annacquato per passare.*
   **⚠️ E GUARDANDO IL PNG è uscita una SESTA categoria che lo strumento non può vedere
   — vedi R13.**
   **ZENIT — le tre strade misurate e CHIUSE, e il vincolo geometrico che le governa.**
   *(2026-07-19. Misure pure: nessun commit su layout/motore/golden.)*
   - **(a) le etichette schivano i pannelli — MORTA.** Simulazione calibrata contro l'SVG
     vero (scarto max **0,06 px**). Non c'è **un solo mese** in cui entrino tutte: ne
     restano fuori da 1 a 8 (novembre 8/33). E le scartate non sono «appena fuori»: per
     entrare dovrebbero allontanarsi **76-139 px** dal proprio oggetto — *Sirio a 139 px
     da Sirio indica la stella sbagliata*.
     **⚠️ Ma la premessa del prompt era INCOMPLETA, ed è colpa dell'architetto:** D9 ha
     già deciso che *«un'etichetta non si scarta mai: si allontana e si collega con una
     **linea di richiamo**»*, e la tecnica **è già implementata** (`messier.py`:
     `LEADER_GAP`, `_last_messier_leadered`). Quindi (a) è morta **solo nella variante
     "sposta e basta"**; la variante **con richiamo resta viva**, al prezzo di ~8 linee
     di richiamo a novembre e del portare la tecnica da `messier.py` a `disc.py`.
     *Registrata come viva perché non venga «riscoperta» fra due mesi.*
   - **(b) rimpicciolire il disco — MORTA, e guardata.** Curva misurata: rad 445→56
     sepolte/anno, 360→11, 300→4, **220→0**. Il raggio a zero è **220 = 41% del canvas**
     (oggi 82%): il disco diventa **più piccolo del dashboard** (50%) e galleggia nel
     vuoto. *L'architetto ha aperto il PNG: confermato, Zenit smette di essere sé stesso.*
   - **(c) spostare gli stessi pannelli negli angoli — NON BASTA.** Anche a filo
     d'angolo, i due colpevoli restano a ~300-340 px dal centro, sotto i **>360** che
     servirebbero. Sono **troppo grandi** (300×300 e 270×320 in un canvas 1080).
   **IL VINCOLO GEOMETRICO, trovato dall'architetto verificando il brief prima di
   spedirlo — e che stava per far progettare al designer una cosa impossibile:**
   **un pannello d'ANGOLO può stare fuori dal cielo; una FASCIA A TUTTA LARGHEZZA no.**
   La fascia passa **sopra il centro**, quindi la sua distanza dal disco **è la sua
   altezza**: con disco all'82% (serve >445) nessuna fascia più alta di **~95 px** può
   stare fuori — e oggi la **testata è 150** e le **fasi lunari 120**. Un riquadro
   d'angolo 220×140, invece, sta a **~510 px**: ampiamente fuori.
   *L'esecutore aveva scritto nel brief che «pannelli bassi e distesi» permettono disco
   all'82% **e** zero collisioni: **vero per gli angoli, falso per le fasce**. Il numero
   era giusto, la generalizzazione no — e sarebbe stato il **quarto giro bruciato per un
   numero sbagliato dato al designer**.*
   **STATO: brief depositato nel progetto design (2026-07-19)** con i tre PNG veri
   (Zenit-novembre, dashboard di riferimento, la variante rimpicciolita scartata). Al
   designer si chiede di sciogliere il compromesso fra **fasce ≤95 px**, **disco a un
   valore intermedio**, e **accettare che le fasce coprano il cielo basso** (l'orizzonte,
   dove nessuno osserva — ma a novembre lì ci stanno Mizar e Thuban). **Zenit resta
   com'è** finché non risponde: funziona, ha le collisioni, e nessuno ci stampa.
   **Restano bloccate su questo giro** le due feature mancanti di Zenit (**tacche** e
   **icone social**): entrambe dipendono da dove finiscono i pannelli.
   **🏁 CHIUSO (2026-07-19, `6b90896` + `b3b6690` + `966dc49`).** Il designer ha proposto
   la **direzione B portata fino in fondo**: testata compatta in cima, **tutto** il
   contenuto in una fascia in fondo, il disco **fra** le due senza toccarle → **zero
   etichette sepolte PER COSTRUZIONE**, non per statistica. *Marco ha trovato il 66%
   troppo piccolo*; misurando si è arrivati a **71%** (rad 384) comprimendo i **34 px di
   spazio morto** dentro la fascia — il tetto vero, oltre il quale le **etichette delle
   fasi lunari escono dal canvas** *(difetto trovato dall'esecutore rendendo a −38 px, non
   dedotto)*.
   **La leva 3 (disco 80%) è stata misurata e scartata da Marco**, ma il suo costo è
   registrato perché la domanda tornerà: costa **Scorpione + Antares** (estate),
   **Sagittario**, **Fomalhaut** (autunno) — tutti a dec −17°…−30°, la fascia d'orizzonte
   che **D9 già sacrifica**. *E ha smontato un sospetto dell'architetto:* a novembre i
   gioielli invernali **non** sono in basso — **sorgono a Est**, sopra la fascia. Avevo
   dedotto «inverno = basso» senza guardare l'ora.
   **IL DIFETTO CHE HO APPROVATO GUARDANDO, E LA LEZIONE.** Ho dato il via libera al
   render 71% **senza vedere che la «N» era scritta sopra «Boote»** — si leggeva
   letteralmente **«BoNte»**, due testi illeggibili al posto di due leggibili. L'avevo
   guardato **ridotto a 560 px**, chiedendomi *«il disco riempie la tela?»*: e a **quella**
   domanda la risposta era sì. **L'esecutore si è fermato e non ha committato**, citando
   il mio stesso «fermati se lo trovi». *È la quarta volta che questo progetto impara che
   **guardare trova solo ciò che stai cercando** — e stavolta a cascarci è stato
   l'architetto, che la regola l'aveva scritta.* **Conseguenza operativa, non morale: i
   render si guardano RITAGLIATI AL 3× sulle zone critiche**, non interi e rimpiccioliti.
   **IL FIX, e perché NON tocca D7** *(l'argomento che rende la modifica dovuta invece che
   un'estensione di scope)*: **cardinali e tacche li disegna `disc.py` — sono PARTE del
   disco**. Insegnare all'anti-collisione a schivarli non è «il disco che impara cosa gli
   sta sopra» (quello sarebbe stato il caso dei pannelli, ed è la ragione per cui l'abbiamo
   scartato): è **il disco che smette di scriversi addosso**. Un bug in casa propria.
   **Due commit, due previsioni falsificabili, entrambe verificate:**
   - **cardinali** → golden A4 **fermo di un byte**, come previsto: sui 4 formati stanno a
     `rad+22`, **fuori** dalla zona delle etichette (`rad−3`) — non si incontrano mai.
   - **tacche** → **l'architetto prevedeva che il golden si MUOVESSE** (l'A4 ha 2
     tacca-testo nella ricognizione). **Sbagliato, e l'esecutore l'ha corretto con la
     misura:** quelle due tacche sono a **febbraio e aprile**, e **il golden è agosto** —
     dove l'etichetta più esterna (Antares) sta 10 px dentro il bordo. *Previsione
     dell'architetto smentita da una domanda che non si era posto: «in QUALE mese?».*
   **Risultato sui 60 poster** — e va oltre Zenit: **sotto-pannello, banda, cardinale e
   tacca-testo sono ZERO su dashboard, parata, zenit e a4**. Zenit passa da **63 a 14**
   collisioni l'anno, **tutte quasi-contatti** etichetta↔etichetta. Il fix delle tacche ha
   chiuso **anche i 2+2+2 degli altri tre formati** — cioè **parte di R13 su tre formati**,
   che non era nemmeno l'obiettivo.
   **Riga pianeti:** il riquadro è stato allargato a 784 px (opzione 1, rubando al riquadro
   colori) — «Telescopico, a fine notte» ha ora **9 px di margine**, e le note **non sono
   state accorciate** (D6).
   **DUE CODE APERTE, dichiarate:**
   - **`deep-space` ha ancora 15 tacca-testo**: i suoi nomi li disegna **`messier.py`**,
     che non passa dal declutter — **altro percorso di codice, giro a sé**. Da decidere:
     fix in `messier.py`, oppure togliere le tacche da deep-space (aggiunte in #6).
   - ~~**Le icone social di Zenit**~~ **FATTO (2026-07-19).** Le 3 icone (instagram ·
     facebook · email) col **trattamento copiato** da dashboard/parata/a4 — *copiato, non
     reinventato*, perché lo scopo era **l'allineamento**, non «Zenit ha delle icone».
     Stanno in testata a destra (la fascia bassa è piena): misurato che ci stanno anche
     col titolo più lungo (SETTEMBRE → 94 px di margine), verificato **rendendo settembre**
     e non solo novembre. Collisioni di Zenit: **tutte le categorie restano a zero**.
   **🟩 LA MATRICE DI ALLINEAMENTO È TUTTA VERDE** — è ciò che Marco aveva chiesto col
   «check completo» (*«tutti i formati, anche in modo diverso, devono avere le stesse
   feature»*). I quattro formati «cielo» hanno gli stessi 23 nomi di stelle, le stesse 22
   costellazioni, tacche, legenda, luna, pianeti e **3 icone social**. Deep Space resta
   diverso **dove è giusto** (è il formato Messier).
   **⚠️ Ma l'allineamento è garantito dalla DISCIPLINA, non da una rete: vedi R14.** È
   stato disallineato per mesi senza che nessun test lo dicesse, e oggi lo è di nuovo per
   scelta di nessuno — solo perché qualcuno ha costruito la matrice a mano. *La prossima
   volta che si aggiunge un formato o una feature, il buco si riapre in silenzio.*
   **SEGUITO — l'ALLINEAMENTO dei nomi di stelle (Marco, 2026-07-19): «*valutiamo di
   aggiungere qualche nome in più… poi un check completo: tutti i formati, anche in modo
   diverso, devono avere le stesse feature*».**
   La **matrice feature × formato**, costruita a mano dall'architetto, ha trovato un
   difetto che nessuno cercava: **`parata` e `a4` mostravano 14 nomi di stelle invece di
   23**, perché non dichiarano `star_names` e il declutter ripiegava su **`MARQUEE`, una
   lista CABLATA in `disc.py`**. E la lista cablata era **peggiore**: conteneva *Deneb
   Kaitos* (β Ceti, sconosciuta) e **non conteneva SIRIO** — la stella più luminosa del
   cielo notturno **non aveva il nome sul volantino stampato**. Vedi **R14**.
   **FATTO:** le quattro liste sono ora **identiche** (23, verificato campo per campo, non
   sulla parola). Golden A4 mosso e contato **per strada indipendente dall'architetto**:
   `+22/−4 <circle>` e `+11/−2 <text>` = **netto +18 cerchi (9 stelle × 2) + 9 nomi**, i
   6 tolti sono riordini; **zero righe di disco**. Previsione dell'esecutore (+27) contro
   reale (+27): **il conto torna**, e stavolta anche la strada.
   **I quasi-contatti raddoppiano (parata 18→36) ED È CORRETTO, non un difetto** — la
   causa è geometrica e l'architetto l'ha verificata sull'immagine al 3×: i dieci più
   stretti sono **tutti** *nome-di-stella contro nome-della-SUA costellazione*
   (Schedar↔Cassiopea 1,8 px, Mirach↔Andromeda 1,7, Aldebaran↔Toro, Polare↔Orsa Minore).
   La stella **sta dentro** la sua costellazione e l'etichetta della costellazione sta al
   baricentro: ogni stella nominata **porta con sé** un quasi-contatto strutturale.
   **E a 1,8 px sono LEGGIBILI**: la gerarchia di colore (azzurro la costellazione, bianco
   la stella) li separa meglio della distanza. *Guardato, non dedotto.*
   **Ordine deciso da Marco:** (1) allineamento ✅ · (2) il giro di Zenit · (3) **solo
   dopo** le 7 costellazioni **zodiacali** mancanti (Ariete, Cancro, Vergine, Bilancia,
   Capricorno, Acquario, Pesci — il nome è già in `CONST_IT`, è una riga di layout).
   *La ragione dell'ordine è del progetto, non del gusto:* aggiungere etichette a Zenit
   mentre ne seppellisce 11 vuol dire non sapere più se un difetto è **dei nomi** o
   **della struttura**. Due variabili, nessuna diagnosi.
4h. **#7q — L'AUDIT DI PULIZIA, e la RETE che ne è il vero prodotto.** *(2026-07-19,
   chiesto da Marco: «rimuovere codice, ottimizzare, portare DRY le funzioni».)*
   **Il verdetto è che non c'era un audit da fare: c'era mezz'ora di lavoro.** Registrato
   perché la domanda tornerà, e la risposta misurata vale più di una seconda ricognizione.
   **PRIMA la rete, poi il refactor** — stesso criterio di #7e (*output identico byte per
   byte*), e per la stessa ragione: **un refactor non aggiunge niente, quindi se rompe
   qualcosa non c'è nessuna funzione nuova da provare che lo riveli.**
   `tools/fotografia.py` (+ `fotografia_sha256.txt`): **20 SVG = 5 formati × 4 mesi**, uno
   per stagione. **Copre deliberatamente il buco dei golden**, che sorvegliano solo
   **l'A4 di agosto** — lo stesso buco che in #7e lasciò i test verdi con un `import`
   dimenticato. *Resta come rete permanente per ogni giro futuro.*
   **Cosa è stato tolto — poco, ed è il punto:**
   - **`moon_panel`** (~22 righe): l'unico **morto davvero** (nessun layout, nessun test).
   - **una formula sola per cardinali e tacche**: la duplicazione era *giusta da unire*
     perché i due usi **cambierebbero insieme** (posizione disegnata ↔ box-ostacolo). *E
     qui la fotografia si è guadagnata lo stipendio:* su Zenit i cardinali stanno **dentro**
     il disco, quindi una fattorizzazione sbagliata avrebbe mosso le etichette — e
     **nessun test se ne sarebbe accorto**. 20 hash identici lo escludono.
   - **3 commenti che il codice smentiva** (l'A4 non è più naive, `moon_panel` non esiste,
     `MARQUEE` è test-only).
   **Cosa NON è stato toccato, e la ragione che vale oltre questo giro:** `MARQUEE` e il
   percorso naive sono **test-only, non morti** — la distinzione che salva dal churn
   («non chiamato» ≠ «morto»); le **6 basi di percorso** non si unificano perché il
   coupling **non esiste ancora** (D17 ha reso `resource_path` inutile, R9 è chiuso) — è
   l'astrazione-troppo-presto che è già costata `brand/formats.py`; il **ponte**
   `engine/generate.py` è indirezione voluta (D14) e tocca 8 import.
   **⚠️ IL PRODOTTO PIÙ UTILE DELL'AUDIT NON È CODICE: È CHE QUESTO FILE ERA SBAGLIATO.**
   La **tabella dell'architettura era stale su 8 file su 12** — `validate.py` dichiarato
   205 righe, ne ha **355**. Cioè: *la tabella che esiste per descrivere il codice* era la
   cosa più divergente dal codice. **Settima smentita di questo file per misura**, e la
   più imbarazzante. Corretta, e ora la riga dice **quando** è stata ricontata, così la
   prossima deriva si vede invece di marcire.
   **Nessun bug funzionale trovato.** *Lezione da tenere: la risposta «il codice è già
   abbastanza pulito» è un risultato valido, e l'esecutore ha avuto ragione a darla invece
   di trovarsi qualcosa da fare.*
   **CODA DELLO STESSO GIORNO — tre lavori chiesti da Marco, tutti chiusi:**
   - **Deep Space riconoscibile nella UI.** *Il tasto c'era già* (il layout ha la sua
     scheda): mancava il **glifo**, quindi ripiegava su `_GLYPH_GEN` — **due cerchi
     concentrici, cioè quasi lo stesso disegno di Zenit**. Ora ha ellisse inclinata
     (galassia) + cerchio tratteggiato (ammasso aperto): **i simboli d'atlante che il
     formato già usa**, non un'icona inventata. *Diagnosi utile oltre il caso: «non c'è il
     pulsante» voleva dire «non si riconosce».*
   - **Le 7 costellazioni ZODIACALI** (Ariete · Cancro · Vergine · Bilancia · Capricorno ·
     Acquario · Pesci) sui quattro formati cielo: 22 → **29** etichette. Motivo (D16): *un
     principiante non cerca la Lince, ma cerca il **proprio segno** — spesso l'unica
     costellazione che sa di dover cercare.*
     **IL RISULTATO CHE VALE LA PENA RICORDARE: 28 etichette in più e le collisioni NON si
     sono mosse di un'unità** (29 · 34 · 14 · 18, identiche prima e dopo, verificate
     dall'architetto). *Non è fortuna: è l'anti-collisione. Se le zodiacali fossero state
     aggiunte **prima** del declutter sull'A4 — cioè stamattina — l'A4 sarebbe peggiorato.
     L'ordine dei giri ha protetto il risultato.*
     Golden A4: **+6 `<text>`, non 7 — Cancro ad agosto è sotto l'orizzonte**. È la
     verifica incrociata che il conto torna **per la ragione giusta**.
   - **La rete sull'allineamento**: vedi **R14, risolta**.
   *(E l'ultimo residuo del carosello — una regola CSS morta — è sparito: Marco aveva
   chiesto «l'eliminazione del carosello», quindi era **dentro** la richiesta.)*
4i. **#7r — UNA SOLA PALETTE: l'identità GAV dal manuale.** *(2026-09-02, chiesto da
   Marco. Vedi **D20**; D13 e D18 cadono.)* Due commit, `80ed047` (via l'editor) e
   `458f2b0` (la palette). `validate.py` 355→246, `app/main.py` 814→510, sei palette →
   una, e la palette smette di essere un parametro.
   **IL GOLDEN SI È MOSSO, E LA PREVISIONE ERA FALSIFICABILE:** *«ogni differenza è un
   colore, zero coordinate»*. Verificata per **due strade indipendenti** — (a)
   sostituendo ogni `#hex` con un segnaposto, il nuovo output e il golden congelato
   sono **byte-identici** (idem per i 5 formati resi con la vecchia e la nuova
   palette); (b) il diff del golden A4 è **536 righe cambiate su 536** e **ogni riga
   contiene un `#hex`**. *È la differenza fra un golden **mosso** e uno rigenerato
   perché era rosso.*
   **E il conto torna per la RAGIONE giusta**, che è la verifica che vale davvero: sul
   golden del disco cambiano **85 hex su 1130** — gli altri **1045 sono le STELLE**,
   che non devono cambiare colore. Se fossero cambiati tutti, avremmo mentito
   sull'astronomia senza accorgercene. *(Rifatta anche la fotografia dei 20 SVG.)*
   **Le reti non sono state annacquate ma RIESPRESSE**, ed è la parte da imitare:
   `test_icona_colorata_dal_tema` sorvegliava *«il colore viene dal token, non è
   cablato»* usando **due palette su disco** — con una palette sola sarebbe stato
   comodo cancellarlo; invece costruisce il secondo tema **in memoria** variando UN
   token. *La rete guarda il difetto, non il numero di file.* E
   `test_layouts_smoke` ora pretende **una** palette **e che sia `gav.json`**: se ne
   ricompare una seconda dev'essere una decisione, non una ricaduta.
   **Suite 244 → 210, e il calo è CONTATO, non subìto:** −8 (i test dell'editor
   rimosso), −25 (`test_layouts_smoke` parametrizza formati × palette: 5×6=30 casi →
   5×1=5), −1 (`?theme=arcobaleno` non è più un input possibile). Torna.
   **Coda: due difetti trovati GUARDANDO e non corretti** (regola #4) — vedi **R15**
   e la riconferma di **R13**.
4j. **#7s — I FONT DEL MANUALE.** *(2026-09-02. Marco: «il manuale ha ragione».)*
   Chiude **R16** e la coda di **R6**; apre **R17**. Space Grotesk + Work Sans (OFL,
   statici) al posto di Barlow + Instrument, che sono stati rimossi dal repo.
   Toccati: i 5 layout, `render.py` (`SANS`), i `@font-face` e le due variabili del
   guscio dell'app, `tools/collisioni.py` (ricalibrato), `brand/fonts/LEGGIMI.md`
   (riscritto: diceva ancora che i `.ttf` non erano nel repo e citava un
   `SANS = "Inter"` che non esisteva più).
   **L'ordine ha fatto il giro:** prima la misura che decideva se era fattibile
   (0,516 contro lo 0,55 del motore), poi la baseline delle collisioni sui 60, poi il
   cambio, poi la rimisura, poi l'occhio al 4× sull'unico caso sospetto. *Se la
   misura iniziale avesse dato > 0,55, il giro sarebbe stato un altro — e lo si
   sarebbe saputo prima di toccare un file.*
   **Curiosità che vale come promemoria sul metodo:** la primissima proposta di font
   del progetto era *Space Grotesk + Inter*; fu superata dal designer a luglio
   (Barlow + Instrument); il manuale d'identità ha poi prescritto *Space Grotesk +
   Work Sans*. **Il cerchio si è chiuso sulla proposta iniziale, per la strada più
   lunga** — e non era tempo perso: senza il manuale nessuno avrebbe saputo *quale*
   delle due avesse ragione.
4k. **#7t — LA CONFORMITÀ AL MANUALE, voce per voce.** *(2026-09-03, chiesto da Marco:
   «controlla se il progetto è conforme al manuale in tutto e per tutto», poi «fixare i
   problemi uno a uno».)* 15 commit. Piano e verifiche in
   **`docs/CONFORMITA-manuale.md`**, una casella per divergenza con la misura accanto.
   **Nove divergenze trovate, nove chiuse** *(§1 denominazione · §1 sigla nel guscio ·
   §2 area di rispetto · §4 tracking · §5 raggi e pillole · §5 raggio dei pannelli · §7
   set e colore delle icone · §7 motivo decorativo · la rete mancante)*, **più un bug
   vero e più il tracking delle etichette di mappa**.
   - **Il PDF del manuale ha il testo VETTORIALIZZATO:** `get_text()` torna **vuoto**.
     Si legge rendendo le pagine (`get_pixmap`) e i colori si estraggono dagli oggetti
     vettoriali (`get_drawings()`). *Chi ci riprova senza saperlo conclude che il PDF è
     illeggibile.*
   - **§1 era la più grave: `"Giorgio Abetti"` e `APS` avevano ZERO occorrenze** in tutti
     e 5 i layout, negli SVG resi, nel README e in `CREDITI.md`. E l'A4 è **tre** dei
     quattro casi che §1 nomina in una volta: è una *locandina*, la sua testata è un
     *lockup*, e ha un *piedino*. Il template del manuale (pag.5) ha esattamente
     `GRUPPO ASTROFILI VICENTINI "GIORGIO ABETTI" · APS`.
     Sull'A4 il corpo scende 21→19: a 21 la stringa completa **invade l'area di
     rispetto del logo**, a 19 restano 34,6 px di margine **e** 12,6 pt (sopra il minimo
     di stampa). *A corpo 20 entrava per 0,5 px: dentro il margine d'errore, scartata.*
   - **⚠️ Z1 — UN BUG VERO, TROVATO GUARDANDO UN RITAGLIO, NON CERCANDOLO.** Il piedino
     di **zenit** stampava `Gruppo Astrofili Vicentin✉` (icona email sovrapposta di
     **9,8 px**) e `info@astrofilivicentini.it` **tagliato dal canvas** di 4,4 px.
     **Preesistente, dimostrato per esecuzione** rendendo col layout di `a67ce4d`.
     Causa: **#7s** — le `x` furono fissate in #7p con **Barlow condensato**, e R16 ha
     misurato che le minuscole di Space Grotesk sono **~29% più larghe**. Le icone non
     si sono mosse: il testo si è allungato sotto di loro.
     Ed è **solo zenit** (misurate tutte e cinque le righe contatti): è l'unico che
     mette i contatti **in testata accanto al titolo** invece che in un piedino a tutta
     larghezza. La riga era **impaccata a gap ZERO**, quindi non c'era nulla da
     recuperare spostando: ricalcolata, corpo 13→12 *(a 13 non ci sta: il titolo di
     settembre arriva a x=510 e servirebbe partire da x≤526)*. **Verificata sui 12
     mesi**, non su quello guardato: stacco minimo 38 px.
     **È l'OTTAVA volta che una rete ha un buco della forma del bug** — le cinque
     categorie di `tools/collisioni.py` non contengono *testo di layout contro icona di
     layout*.
   - **Il rimedio strutturale a Z1 NON è stato fatto, e la ragione è un vincolo:** le
     posizioni restano **cablate**. Derivarle dalla larghezza del testo richiederebbe
     **metriche di font, che il motore non ha** — Pillow non è in `requirements.txt` e
     aggiungerla vorrebbe dire impacchettarla (D17). La stima già in uso nel progetto
     (`n × corpo × fattore`) ha ~5% d'errore, cioè ±25 px su quella riga: quasi tutto il
     margine. **Decisione architetturale, non un ritocco.**
   - **Le collisioni sono rimaste a 155 per undici voci su dodici, ed era il segno
     giusto:** nessuna di quelle toccava le etichette del disco. Sono calate solo con
     l'ultima (il tracking delle etichette di mappa): **155 → 134**, e con esse **6
     `tacca-testo` di deep-space**, cioè un pezzo di **R13** che nessuno stava cercando.
   - **`docs/CONFORMITA-manuale.md` resta come registro**, con le due decisioni aperte
     (R18 e la coda di D19) e le misure per riaprirle senza rifarle.

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
  **⚠️ RISOLTO NON VUOL DIRE COMPLETO — `place` NON è validato** *(scoperto
  2026-07-16, vedi R11)*: è **testo libero** da CLI (`cielo.py:41`) **e dal web**
  (parametro di `/preview`, `/download`, `/genera`), e finisce **grezzo** nel testo
  dell'SVG. Quarta volta che una riga di questo file viene smentita dalla misura.
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
  **CODA CHIUSA (2026-09-02, #7s).** Per un mese e mezzo `a4.json` ha continuato a
  dichiarare `Helvetica,Arial,sans-serif`: cioè **il volantino che si STAMPA era
  l'unico dei cinque a non avere una tipografia d'associazione** — usava il font di
  sistema. Nessuno se n'era accorto perché la coda era registrata come «si fa nel
  giro deliberato», e il giro deliberato non arrivava mai. *(`post.json` nel
  frattempo era stato ritirato del tutto.)* Ora tutti e cinque dichiarano i font
  del manuale. **Il golden si è mosso di UNA riga**, quella del canvas.
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
  di sistema avrebbe cambiato i byte).
  **CHIUSO ANCHE SU MAC (#8 M2/B1, 2026-07-15) — CI verde su entrambi.** Su
  `macos-latest` (arm64): wheel `resvg_py` macOS + `de421` installati senza build da
  sorgente, render eseguito, **PNG scaricato e GUARDATO** (414 KB, 1080×1080, poster
  vero — disco, ~5000 stelle, logo). Suite **230 verde su macOS E Windows** (numpy
  2.3.5). **Il motore è deterministico su entrambi** (dopo il fix dell'argsort).
  **Due code aperte, dichiarate:**
  - **I font del brand su Mac NON sono ancora provati**: il render R9 usa `post`,
    che dichiara Helvetica/Arial. Barlow/Instrument su Mac si provano rendendo un
    formato del brand (dashboard) in CI — B2.
  - **Gatekeeper NON è provato dalla CI**: il runner esegue senza chiedere permessi;
    il socio che fa doppio clic su un'app non firmata sì. Serve un **Mac vero** +
    la decisione firma/notarizzazione.
  *Nota: il rischio temuto (deps native) è filato liscio; l'unico attrito è stato
  ambientale (porta 8000 occupata da un server fantasma) — non un difetto del
  bundle.*
  **🏁 CHIUSA DEL TUTTO — il pacchetto è stato COSTRUITO DA ACTIONS E USATO DA MARCO
  (2026-07-18).** Non più «la CI è verde»: workflow `package-windows.yml` eseguito su
  runner pulito → artefatto `.zip` scaricato → aperto → **poster generati e PNG
  salvati**. Cioè `de421.bsp` si carica e `resvg` rasterizza **dentro il bundle**,
  che era *la* domanda di R9. **La distribuzione ai soci è tecnicamente possibile: non
  è più un dubbio.**
  *(Non riverificato su questo bundle: la **rilocabilità** — Marco non ha confermato
  dove l'ha scompattato. Fu provata in Milestone 1 copiando in `%TEMP%\prova_socio\`,
  quindi il rischio è basso, ma **dedotto ≠ eseguito**.)*
  **La porta non è più cablata** (`a787545`): il launcher ne cerca una libera da solo e
  apre il browser su quella. Non era teoria — **la 8000 era occupata sul PC di Marco**
  da un'altra sua app, e un socio avrebbe visto solo una pagina bianca, *senza log*:
  lo scenario che D4 dichiara bloccante.
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
  soci: quello usa il carosello quadrato, che è pulito. *(Nota 2026-07-19: **il carosello
  non esiste più** — ritirato in #7m, Deep Space è un formato libero. La frase resta come
  cronologia della decisione di allora, non come descrizione del programma di oggi.)*
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
    **VERIFICATA E PRONTA (2026-07-16), da eseguire.** Vedi
    `docs/design_handoff/a4_legenda_stelle/`. Il designer (2º giro, dopo che il 1º
    fu rimandato indietro con la geometria vera) la mette nella **striscia fra il
    bordo del disco e il divisore**, col divisore come linea di base. **L'architetto
    ha verificato sul NOSTRO render, non sul mockup**: disco reale `cx450 cy500
    r384` → bordo a **y884**, divisore **y900**, «S» **y912**; la striscia è libera,
    i campioni stanno a r≥400 e l'alone (blur σ3,4 su r384) sfuma a ~395 — nessuna
    collisione. *(L'architetto aveva segnalato una collisione con l'alone: **ritratta**,
    l'aveva calcolata sulla geometria del mockup.)*
    **Due correzioni al designer, trovate RENDENDO:** (1) le sue spaziature (64 px)
    **fanno scavallare i testi**, perché misurate sulle sue temperature corte e non
    sulle nostre, ancorate al B-V — i numeri che reggono sono `x0=222 step=106 r=4.5`
    corpo 11, resi e guardati; (2) i **sei hex cablati si buttano** (invariante #2):
    i colori vengono dal `star_ramp` via `bv2hex`, e anche le **sue temperature si
    buttano** perché contraddicono quelle del quadrato.
    **Il lavoro si sgonfia: è DATI, zero Python.** Il blocco `swatches`
    (`panels.py:226`) **sa già fare la fila orizzontale** — il commento dice che
    *era proprio l'A4*; #7h l'aveva solo rimosso da `a4.json` (`385af71`). Stessa
    economia di `moon_calendar`.
    **Marco ha scelto le TEMPERATURE** (viste rese, contro le **parole** storiche
    «calde·bianche·gialle·arancioni·rosse»): un pallino giallo con scritto "gialle"
    dice il colore, non la temperatura — e «colore = temperatura» è *il messaggio*.
    **Il titolo è `TEMPERATURA STELLE`**, non «COLORI DELLE STELLE»: #7i ha
    rinominato il pannello su tutti i quadrati, e l'A4 segue.
    **Muoverà il golden dell'A4**: movimento deliberato e contato (+6 `<circle>`,
    +7 `<text>`, disco intatto).
  - **Margine di stampa in basso ~2,8 mm** (footer a y1258 su 1273): identico al
    mockup, ma **da verificare in tipografia** (di solito vogliono 3-5 mm). Si alza
    con un numero in `a4.json`.

- **R11 — L'escaping XML dei testi. RISOLTO (2026-07-16), con un RESIDUO
  dichiarato.** *(Trovato dall'esecutore in #7i, riportato e **non corretto** —
  regola #4; riprodotto dall'architetto, non dedotto.)*
  Era: `_render_text` emetteva `b["content"].format(**ctx)` **grezzo**. Con
  `place="Bassano & Dintorni"` l'SVG **non passava** `parseString` (la `&` cruda
  nel sottotitolo). Aveva già morso in casa: è ciò che ha fatto crashare `cornice`
  con un `</>` in un'etichetta.
  **Fix e prova:** golden `diff` **vuoto** e — prova forte — **a4 rigenerato con
  sha256 IDENTICO al golden** (non «non vedo differenze»: *è lo stesso file*). La
  previsione del no-op ha retto byte-per-byte. Suite 238→242. Il test guarda
  `parseString`, cioè **il difetto**, non `'&amp;' in svg`, che sarebbe la toppa;
  iniettato il guasto → **4 rossi** con l'`ExpatError` vero, ripristinato → verdi.
  **Il choke point è la parte elegante:** `panels.py` instrada *tutto* il suo testo
  attraverso `_render_text` (pianeti, parata, luna, calendario, campioni), quindi
  **un punto solo** protegge pannelli e layout. Ed è dove entra `place`.
  **Scelta dell'esecutore, confermata dall'architetto:** ha escapato **tutti** i
  punti-testo, non solo `place`. Ragione migliore della mia: **i nomi Messier sono
  dati che il GAV modifica** — una `&` lì è plausibile, non ipotetica. Escapare solo
  `place` avrebbe tappato *un ingresso*, non *la classe*. Ha evitato la trappola
  giusta: in `messier.py` escapa **i valori** e lascia `<tspan>` e `—` (escapare
  tutta la stringa avrebbe stampato `&lt;tspan&gt;`).
  **⚠️ RESIDUO — undici `_esc()` A MANO, non coperti da test.** I bypass di
  `_render_text` sono `disc.py` (4: stella-guida, costellazione, cardinale,
  etichetta anti-collisione) e `messier.py` (7). Il test passa **solo `place`**, che
  arriva al sottotitolo — **non** ai nomi Messier né alle stelle. Quindi: se domani
  qualcuno aggiunge la dodicesima etichetta e scorda `_esc`, **nessun test lo dice**.
  Un choke point difeso da una rete, e undici punti difesi dalla **disciplina** — che
  in questo progetto è già fallita tre volte. *Registrato, non corretto: il commit
  era pulito e a scopo unico, allargarlo è ciò che vietiamo.*
  **Non è latente: è l'input dell'utente** (vedi il buco di R4 sopra), ed è
  precisamente ciò che **D4 dichiara bloccante** — *«un HTTP 500 sul PC di un socio
  è "il programma non funziona", e non hai i log»*. Va chiuso **prima del rilascio**.
  *Il fix è golden-safe e la previsione è falsificabile:* i golden hanno **zero `&`
  grezze** e **nessun layout/dato/palette contiene `&`** → l'escaping deve essere un
  **no-op sull'output attuale**. Se un golden si muove, una premessa è falsa: si
  guarda in faccia, non si rigenera.
  **Attenzione al confine:** `_render_text` **potrebbe non essere l'unico** punto
  d'emissione di testo (campioni, pianeti, stelle, Messier, costellazioni). Vanno
  trovati tutti.
  *Deciso da Marco (2026-07-16): si chiude **solo l'escaping**; la validazione di
  `place` è un giro a parte, perché «cosa sia un nome-luogo lecito» è una domanda
  di prodotto, non di codice.*

- **R12 — Gli asset di `docs/` non sono in git: la documentazione di design è
  committata a metà.** *(Trovato 2026-07-16, verificato con `git ls-files`.)*
  `.gitignore` ha `*.svg` e `*.png` **globali** — scritti per l'output del motore
  (`out/`), ma sono pattern globali e si mangiano anche `docs/`. Contraddice **la
  regola delle case** scritta in questo file: `docs/` è *ciò che serve agli UMANI*
  e sta nel repo; `out/` è *usa e getta, mai in git*. L'ignore tratta il primo come
  il secondo.
  Conseguenze **misurate, non temute**:
  - **`docs/mockups/dashboard.svg` non è in git** — cioè *la prova* che R6 cita per
    dire che i font del brand funzionano **esiste solo sul PC di Marco**. Se cambia
    computer, la prova sparisce e resta l'affermazione.
  - Gli **handoff HTML del designer sono tracciati, i loro `assets/*.png` no**: chi
    clona apre l'HTML e vede le immagini rotte.
  - **Nessuna PNG, in tutto `docs/`, è tracciata.**
  Rimedio (non applicato): restringere l'ignore con un'eccezione per `docs/`.
  Costo ~1-2 MB. **`.gitignore` non è né CLAUDE.md né `docs/`: non è roba
  dell'architetto** — va nel prompt dell'esecutore.
  *Marco (2026-07-16): «fermati, ne parliamo dopo» — si decide a coda vuota.*

- **R13 — LE LINEE DELLE COSTELLAZIONI ATTRAVERSANO LE ETICHETTE. La sesta categoria,
  che nessuna rete vede.** *(Trovata 2026-07-19 dall'architetto **guardando il PNG**
  dell'A4 di marzo, subito dopo che `tools/collisioni.py` aveva dichiarato quel poster
  privo di sovrapposizioni.)* Sull'A4 di marzo la linea della figura passa **in mezzo
  alla parola** «Cassiopea» e «Cefeo». Non è testo↔testo, non è testo↔pannello, non è
  tacca↔testo: **è una linea di costellazione contro un'etichetta**, e sta fuori da
  tutte e cinque le categorie dello strumento.
  **NON è una regressione del declutter, ed è dimostrato dal diff del golden**, non
  dedotto: `Cassiopea` è fra le 15 etichette a **coordinate identiche** prima/dopo — non
  si è mossa. Il difetto **c'era già**, congelato nel golden come le 15 sovrapposizioni.
  **Quarta volta che il progetto impara la stessa cosa** *(dopo i cardinali fuori dal
  canvas → il cardinale sotto un pannello → la banda che non è un `panel`)*: **le reti
  hanno buchi della stessa forma del bug**. Lo strumento modella *testi e rettangoli*;
  le linee delle figure attraversano tutto il disco e non erano nel modello. E le due
  reti si sono comportate esattamente come previsto: *«conta il golden» e «guarda
  l'immagine» non sono ridondanti* — lo strumento ha dato 0, l'occhio ha trovato il
  difetto, e **il golden ha poi provato che non l'avevamo introdotto noi**.
  **Non corretto** (regola #4: riportare, non correggere): il commit dell'A4 era pulito
  e a scopo unico. Prima di decidere un fix va **misurata l'estensione** sui 60 poster —
  una linea che sfiora il bordo di un'etichetta non è «Cassiopea tagliata in due», e
  senza quella distinzione si finisce a inseguire rumore. *Costo noto della misura: le
  linee delle figure sono già nell'SVG (`<polyline>`/`<path>`), quindi è geometria
  segmento↔bbox — la stessa che cat.5 fa già per le tacche.*
  **LA CAUSA, trovata il 2026-07-19 guardando `parata` dopo l'allineamento dei nomi:
  sono le figure CONCAVE.** Le vittime non sono casuali — su parata-agosto sono di nuovo
  **«Cassiopea» e «Cefeo»**, *gli stessi due nomi* trovati sull'A4 di marzo: formato
  diverso, mese diverso, **stesse vittime**. L'etichetta di una costellazione è piazzata
  al **baricentro** delle sue stelle; per una figura concava (la **W** di Cassiopea, la
  casetta di Cefeo) il baricentro cade **dentro la figura**, cioè **sulle linee**. Non è
  sfortuna: è geometria, e rende R13 **prevedibile e circoscritto** invece che diffuso —
  si può misurare quali figure sono concave prima ancora di rendere.

- **R14 — RISOLTA (2026-07-19): `tests/test_allineamento_formati.py`.** Cinque test:
  stesse feature · stessi `star_names` · stesse costellazioni · stesse icone sui quattro
  formati «cielo», **+ una guardia** che pretende che *ogni* layout sia classificato
  «cielo» **oppure eccezione motivata** — così un formato nuovo non può scivolare fuori
  dalla rete per distrazione. **L'eccezione `deep-space` è dichiarata in UN SOLO POSTO,
  con scritto il perché** (è il formato Messier): era il punto che distingueva una rete da
  un placebo. **Iniezione del guasto rifatta dall'architetto**, non presa sulla parola:
  tolto Sirio da `parata.json` → **rosso** su `test_star_names_allineati` con il messaggio
  che nomina formato e feature; ripristinato → 5 verdi.
  **Limite dichiarato, ed è quello GIUSTO:** confronta le liste **fra loro** (unione), non
  contro un contenuto assoluto. Se un giorno si togliesse Sirio da **tutti e quattro**, la
  rete resterebbe verde — perché è una rete di **allineamento**, non di **contenuto**. Un
  presidio «Sirio obbligatorio» proteggerebbe una scelta editoriale con un test, e il
  giorno che il GAV vuole cambiare le stelle da nominare troverebbe un rosso senza capire
  perché. *(Proposto dall'esecutore, accettato: la distinzione è sua.)*
  *(Testo originale del debito, per memoria:)*
  **R14 — NESSUNA RETE SORVEGLIAVA L'ALLINEAMENTO FRA I FORMATI.** *(2026-07-19. Il buco
  previsto dall'architetto e **confermato dall'esecutore**; e prima ancora è il modo in
  cui il difetto era entrato.)*
  Per mesi **due formati hanno usato 23 nomi di stelle e due ne hanno usati 14** — con
  **Sirio, la stella più luminosa del cielo, assente dal volantino stampato** — e
  **nessun test se n'è accorto**. Non l'ha trovato una rete: l'ha trovato l'architetto
  **costruendo a mano una matrice feature × formato**.
  Oggi esiste `test_star_names_dei_layout_sono_nel_catalogo` (becca i **refusi**: provata
  rossa con «Mizzar»), ma **nulla asserisce che le liste COMBACINO fra i formati**. L'A4 è
  protetto di rimbalzo dal proprio golden; **parata non ha golden**: se domani qualcuno
  togliesse Sirio da parata, **la suite resterebbe verde** e il disallineamento
  rientrerebbe dalla porta di servizio.
  **È il QUINTO buco della stessa famiglia** (cardinali fuori canvas → cardinale sotto un
  pannello → la banda che non è un `panel` → le linee delle figure → questo). E stavolta
  il buco non ha la forma del bug: **non c'era proprio la rete**.
  *Rimedio proposto, non fatto (è un giro a sé): la matrice di allineamento diventa un
  TEST invece di una tabella che qualcuno rifà a mano ogni volta. Andrebbe scritta come
  «questi formati dichiarano le stesse feature», con le eccezioni **dichiarate** (zenit
  senza tacche, deep-space che è il formato Messier) — così un'eccezione nuova va scritta
  apposta, e non si insinua.*
  **Coda dello stesso giro:** `MARQUEE` (in `disc.py`) è ora il fallback di **nessun**
  formato — tutti e cinque dichiarano `star_names`. È codice morto come fallback, e
  contiene ancora «Deneb Kaitos» (β Ceti, la stella sconosciuta che stava sull'A4 al posto
  di Sirio). **Non rimossa** (regola #4): resta viva per il ramo naive e per un test.

- **R15 — LE NOTE DEI PIANETI SI SCRIVONO ADDOSSO SU ZENIT. La SETTIMA categoria,
  che lo strumento non può vedere.** *(Trovata 2026-09-02 guardando il render di
  Zenit al 4×, subito dopo che `tools/collisioni.py` aveva dato **zero** su tutte e
  cinque le sue categorie per quel poster.)* Nel riquadro dei pianeti si legge
  letteralmente `…ne notteNon osservabile, vicino al Sole` **sovrapposto** a
  `Non osservabile, vicino al Sole`: la nota di Nettuno tocca quella di Mercurio, e
  quella di Mercurio finisce **sopra** quella di Giove. **Due testi illeggibili al
  posto di due leggibili.**
  **È PREESISTENTE, e per esecuzione non per deduzione:** in #7r è stato dimostrato
  che lo scheletro SVG (tolti i `#hex`) è **byte-identico** prima e dopo il cambio di
  palette — quindi quelle coordinate erano già lì. Il cambio di colori non muove un
  testo.
  **Perché nessuna rete lo vede, ed è il punto:** le cinque categorie dello strumento
  sono *sotto-pannello · banda · etichetta↔etichetta **del disco** · cardinale ·
  tacca-testo*. Questo è **testo↔testo DENTRO un pannello** — non è in nessuna. **È la
  SETTIMA volta** che questo progetto trova un buco **della stessa forma del bug**
  (cardinali fuori canvas → cardinale sotto un pannello → la banda che non è un
  `panel` → le linee delle figure (R13) → nessuna rete sull'allineamento (R14) →
  questa). *La lezione non è «aggiungi la settima categoria»: è che l'occhio trova
  ciò che lo strumento non modella, e va usato **insieme**, non dopo.*
  **Non corretta** (regola #4: il commit era a scopo unico). Prima di un fix va
  **misurata l'estensione sui 60 poster**: sospetto che Zenit sia l'unico colpito
  perché è il formato dove il riquadro pianeti è più stretto, ma è un sospetto, non
  una misura.

- **R16 — RISOLTO (2026-09-02, #7s): il repo è passato a Space Grotesk + Work Sans.**
  Marco: *«il manuale ha ragione, il file PDF ha tutto quello che serve per
  decidere»*. `.ttf` **statici** (non variable: `resvg` con gli statici è
  verificato, coi variabili no — e non è una cosa da scoprire a metà giro), OFL,
  dai repository degli autori.
  **LA DOMANDA CHE DECIDEVA IL GIRO ERA UNA SOLA, ED È STATA MISURATA PRIMA DI
  TOCCARE QUALSIASI COSA:** il motore stima la larghezza del testo con un fattore
  **0,55 cablato** (`disc.py:259`), che **non dipende dal font**. Se Space Grotesk
  fosse stato più largo di 0,55 il motore avrebbe iniziato a **sottostimare** e le
  collisioni sarebbero esplose. Misurato sul raster: **0,516** — il motore resta
  conservativo, margine 0,034 (era 0,15 con Barlow). **Non è stato toccato.**
  *È la misura che ha reso il giro fattibile invece che un salto nel buio.*
  **Costo reale, misurato sui 60 poster** — non stimato: i quasi-contatti
  etichetta↔etichetta salgono da **104 a 155** (dashboard 29→46, parata 34→49,
  zenit 14→23, a4 18→28, deep-space 9→9). **Sotto-pannello, banda, cardinale e
  tacca-testo restano TUTTI a zero.** Le sovrapposizioni *vere* (distanza negativa)
  sono **2 su 60**, entrambe a −0,3 px, cioè **dentro il margine d'errore ±1 px
  dello strumento** — e guardate al 4× («Ercole» / «Corona Boreale» su parata-agosto)
  **non si sovrappongono affatto**: sono affiancate, entrambe leggibili. *Lo
  strumento aveva torto e l'occhio l'ha smentito, esattamente come il suo stesso
  manuale d'uso prescrive.*
  **Lo strumento è stato RICALIBRATO con la tecnica originale** (stringhe vere rese
  isolate e misurate sul raster, non un rapporto stimato): `F_MISTO` 0,40 → **0,52**;
  `F_MAIUSC` 0,50 → **0,50**, praticamente invariato. *Scoperta controintuitiva: le
  minuscole di Space Grotesk sono ~29% più larghe, le MAIUSCOLE no — Barlow è
  condensato ma ha maiuscole relativamente larghe.* Aggiornata anche la riga di
  esempi nel commento, che altrimenti restava a mentire coi numeri di Barlow.
  **Il golden si è mosso di UNA riga per file**, quella del canvas — previsione
  fatta prima e verificata: *il font non entra nel calcolo delle posizioni*.
  **E qui c'è la lezione:** il golden è cambiato di **una riga** mentre il poster
  cambiava **dappertutto**. È R10 in forma pura — *il golden sorveglia l'SVG, non i
  pixel*. La rete che ha visto il cambiamento vero è stata `tools/collisioni.py`,
  non il golden. Due reti, maglie di forma diversa, e serviva quella giusta.
  *(Testo originale del debito, per memoria:)*
  **R16 — IL MANUALE D'IDENTITÀ E IL REPO NON SONO D'ACCORDO SUI FONT.**
  *(Registrato 2026-09-02 con D20.)* Il manuale prescrive **Space Grotesk** (display)
  **+ Work Sans** (corpo). Il repo ha **Barlow Semi Condensed + Instrument Sans**,
  scelti dal designer il 2026-07-12 e presenti in `brand/fonts/` (vedi D4/R6).
  **Uno dei due è sbagliato, e va riconciliato** — non lasciato divergere: è
  esattamente il modo in cui questo file è stato smentito sette volte.
  **Ma NON è un ritocco, ed è la ragione per cui il giro dei colori si è fermato
  qui.** Barlow Semi Condensed è **condensato**; Space Grotesk **no**. Tutta
  l'anti-collisione portata a zero in #7p/#7q è calibrata su un fattore di larghezza
  **0,40** che viene *proprio* da quello (`tools/collisioni.py:23-27`). Con un font
  più largo **ogni etichetta cresce** e il lavoro delle collisioni si riapre su tutti
  e 60 i poster.
  Il fix, quando si farà: **ricalibrare il fattore rendendo stringhe isolate** (la
  tecnica di #7p) **prima** di guardare i risultati, o si misurerà rumore. E prima
  ancora, decidere **chi ha ragione**: è una domanda per Marco e per il designer, non
  per l'esecutore.

- **R17 — LA «COPPIA DI FONT» DEL BRAND NON È MAI ESISTITA: il poster usa UN FONT
  SOLO.** *(Trovato 2026-09-02 mentre si cambiavano i font, cercando dove assegnare
  il display e dove il corpo.)* Il compositore emette **un solo `font-family`**, sul
  tag `<svg>` radice (`compositor.py:146`), preso da `canvas.font_family`. Nessun
  blocco può dichiararne uno proprio. E poiché quel valore è una **lista CSS**, vince
  il primo che esiste: il poster è **interamente** nel primo font.
  **Non è una regressione di oggi — era già così con Barlow.** `"Barlow Semi
  Condensed, Instrument Sans, …"` significava «tutto Barlow», e **Instrument Sans non
  è mai stato disegnato una sola volta** in nessun poster, in nessun mese. Cioè: D4
  dichiarava dal 2026-07-12 una coppia *«Barlow (testate) + Instrument Sans (corpo)»*
  che il codice non ha mai implementato, e per un mese e mezzo il file lo ha ripetuto
  senza che nessuno lo verificasse. **Nona smentita di questo file per misura.**
  Oggi vale identicamente per `"Space Grotesk, Work Sans, …"`: tutto Space Grotesk.
  **Perché conta davvero, e non è pignoleria tipografica:** il manuale (sez.4) assegna
  ruoli **diversi** — Space Grotesk al *display* (titoli, numeri, etichette), Work Sans
  al *testo corrente* (note, sottotitoli, crediti). Con un font solo stiamo seguendo
  **metà** della prescrizione. Sul poster il danno è piccolo (è quasi tutto display);
  **su Pillole (D12) sarebbe grosso** — è una pagina di testo, dove il corpo è il
  contenuto.
  **Rimedio, non fatto (giro a sé):** un `font_family` **opzionale per blocco** nel
  compositore, additivo esattamente come `fill_opacity` e `cardinal_gap` (assente ⇒
  output identico, golden fermi). Poi i blocchi di testo corrente lo dichiarano.
  ⚠️ **Non basta il compositore:** le note dei pianeti e le righe Messier le genera
  `panels.py`/`messier.py`, che dovrebbero ereditare il font dal blocco — è lì che il
  lavoro smette di essere di due righe.
  *Non corretto in #7s (regola #4): il commit era a scopo unico, e il difetto è
  preesistente di un mese e mezzo, non introdotto dal cambio di font.*

- **R18 — L'A4 SFONDA IL MINIMO DI 12 pt IN STAMPA: 111 testi su 113.**
  *(Misurato in #7t, 2026-09-03. **Decisione aperta, non un fix.**)*
  **Manuale §4:** *«Corpi minimi: 12 pt in stampa, 24 px su slide 1920×1080.»*
  Misurato **sull'SVG reso** (900 px = 210 mm → 12 pt = **18,1 px**): passano **solo**
  la testata (12,6 pt) e il titolo (19,8 pt): **111 testi su 113 sono sotto (98%)**, e il
  grosso sta fra **6,3 e 7,7 pt** — 31 a 6,3, 23 a 7,7, 15 a 6,9, 15 a 7,1.
  **Perché è una decisione e non lavoro d'esecuzione:** D16 ha già deciso i corpi
  piccoli, ma **misurando il telefono** — parlava dei formati social, dove il socio
  zooma. **L'A4 si stampa, e un foglio non si zooma.** Portarlo a 12 pt significa
  **metà del contenuto o metà mappa**: è *un altro poster*, cioè lavoro col designer,
  esattamente come D16 stesso prescrive per questo caso.
  *Nessun altro formato è toccato: sono social, e lì il minimo del manuale è «24 px su
  slide 1920×1080», che non è la nostra unità.*

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
- **Designer** (Claude Design, progetto `claude.ai/design` «Infografica cielo del
  mese»): **NON vede il repo.** Riceve brief autonomi e consegna proposte.

### Il confine col designer — pagato caro il 2026-07-18

**Il designer può misurare SOLO ciò che sta nel progetto design.** L'architetto gli
ha chiesto di verificare dei conteggi che vivono in `brand/layouts/*.json`, e lui —
non potendo — ha misurato l'unica fonte a sua disposizione: il proprio mockup
(`Cielo Post.dc.html`). Che era **più vecchio del programma**.
Ne è uscita una tabella sbagliata su tre punti (icone di Cornice e Parata, e un
«disco segnaposto» che **da noi non esiste**: gli SVG veri hanno ~1350 stelle e
~360 linee di costellazione). Se fosse partita, avremmo chiesto una diagnosi su una
**realtà immaginaria** — il terzo giro bruciato per numeri sbagliati.
**La colpa era del brief, non di lui**: aveva perfino marcato le divergenze con ⚠ e
scritto «da confermare insieme, non è una sentenza». *(L'architetto in prima battuta
ha incolpato l'esecutore, e ha dovuto ritrattare: l'output era del designer.)*

**Le regole che ne discendono:**
1. **La verità è ciò che il motore GENERA** (i PNG/SVG in `out/`) **e ciò che il
   motore LEGGE** (`brand/layouts/`). Tutto ciò che sta nel progetto design è **una
   proposta**, mai una misura.
2. **Al designer non si chiede MAI di misurare il repo**: i numeri glieli si porta
   già contati, insieme ai **render veri**.
3. **Il materiale stale nel progetto design è una MINA**, non disordine: lui lo tratta
   come verità perché non ha modo di sapere che è vecchio. *(Pulito il 2026-07-18:
   rimossi il mockup col disco segnaposto, le palette ritirate `notte-blu`/`petrolio`
   — che lui aveva appena usato per rendere —, i formati morti `editorial`/`rail`, e
   `logo-white.png`, il logo di **provenienza ignota** già purgato da git in #7c.
   Depositati al loro posto i cinque render veri + `LEGGIMI-fonte-di-verita.md`.)*
4. **Prima il sostituto, poi la cancellazione**: mai un momento senza riferimento.

### «Deciso» non è «fatto», e «fatto» non è «ARRIVATO» — 2026-07-19

Il progetto aveva già imparato la prima metà (#7o: due decisioni di Marco registrate
come fatte e mai eseguite). Oggi ha imparato la seconda, e **l'ha pagata Marco**.

Marco ha rilanciato il workflow del pacchetto e nel bundle **non c'era il pulsante Deep
Space**. Diagnosi, in ordine di quanto era sbagliata:
1. *«sarà l'app»* — no: `deep-space.json` ha la sua scheda, il tasto c'è.
2. *«sarà la cartella vecchia sul suo PC»* — plausibile (`dist/CieloDelMese` era del 15/07,
   con `editorial`/`post`/`rail` e senza Zenit), ma **non era quella**: lo zip nuovo era in
   `Downloads`, scompattato quel giorno.
3. **La causa vera: 29 commit mai pushati.** Il pacchetto conteneva `profondo.json` — il
   nome *prima* del rename a Deep Space. **GitHub Actions aveva impacchettato
   fedelmente ciò che c'era su GitHub**, cioè il codice di quattro giorni prima.

**Il workflow era sano. Erano sani i commit, i test, le verifiche.** Mancava un `git push`.

**La catena ha TRE anelli, e ognuno può rompersi in silenzio:**
`deciso` → `committato` → **`pushato`** → `impacchettato`.
Un lavoro verificato, con la suite verde e i golden fermi, **può essere invisibile al
prodotto** perché il terzo anello non è stato toccato da nessuno.

**Di chi era la colpa, per non impararla storta:** *dell'architetto*. L'esecutore ha fatto
la cosa giusta a non pushare di sua iniziativa (le regole dicono di committare e basta,
salvo richiesta). L'architetto ha detto a Marco *«rigenera il pacchetto»* **senza
verificare che ci fosse qualcosa da rigenerare** — cioè ha dato per scontato l'unico
anello che nessuno aveva controllato.

**Regola operativa che ne discende:** prima di dire a Marco *«ricostruisci il pacchetto»*,
si esegue **`git status -sb`** e si guarda `ahead/behind`. Se il ramo è **ahead**, il
pacchetto che uscirà **non conterrà il lavoro**. E il push, che è l'unica azione che esce
dal computer di Marco, **si chiede** — non si fa di iniziativa.

### Un numero può MIGLIORARE mentre stai sbagliando — 2026-09-03

Il progetto sapeva già che *«guardare trova solo ciò che stai cercando»* (R10, i
cardinali, R13, R15). #7t ha trovato il rovescio, ed è peggio: **una metrica che ti dà
ragione mentre sbagli.**

Applicando il tracking del manuale alle etichette di mappa, avevo messo **−0,02em**
anche su `deep-space`. Le collisioni sui 60 poster scendevano da 24 a **13**: il
numero più basso della sessione. Ma su deep-space i nomi sono **MAIUSCOLI**
(`messier.py:398` fa `.upper()`, `disc.py` no), e §4 dà al maiuscolo **+0,08em** —
comprimere delle maiuscole è proprio ciò che quella riga esiste per impedire. Col
valore **giusto** le collisioni scendono a **17**, non a 13.

**Guardando solo la tabella avrei tenuto il valore sbagliato, perché "dava un
risultato migliore".** L'ho preso confrontando due render affiancati.

*La lezione operativa:* `tools/collisioni.py` misura la **sovrapposizione**, non la
**correttezza tipografica**. Un miglioramento del suo numero **non è** una prova che
la modifica sia giusta — è solo una prova che non hai rotto la spaziatura. Le due
domande sono diverse e vogliono due strumenti diversi.

### Strumenti di MISURA, fuori dal motore

Nessuno dei tre è dipendenza di `requirements.txt`: servono a **decidere prima** e a
**verificare dopo**, non a girare in produzione.

- **Il PDF del manuale ha il testo vettorializzato:** `page.get_text()` torna
  **vuoto**. Si legge rendendo (`page.get_pixmap(dpi=…)`) e i **colori veri** si
  prendono da `page.get_drawings()`, mai da uno screenshot.
- **Pillow misura la larghezza vera** col `.ttf` del brand
  (`ImageFont.truetype(...).getlength(s)`): serve **prima** di toccare un layout, per
  sapere se una stringa ci sta. In #7t ha deciso tre volte il valore da scrivere
  (lockup a 127 px su 133; testata A4 a corpo 19; riga contatti di zenit a corpo 12).
  *Il motore invece stima (`n × corpo × fattore`) perché non può caricare font.*
- **Chrome headless fotografa il guscio dell'app** quando l'estensione del browser non
  è connessa:
  `chrome.exe --headless=new --disable-gpu --window-size=1400,900 --screenshot=out.png --virtual-time-budget=4000 http://127.0.0.1:PORTA/`
  Con un confronto pixel-per-pixel (`ImageChops.difference(...).getbbox() is None`)
  diventa una **prova** che un refactor del CSS non ha cambiato nulla.

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

## Comandi (rieseguiti su Windows, 2026-09-02)

*Ogni comando qui sotto è stato **eseguito**, non ricopiato. La versione
precedente di questa sezione citava `--format post` (formato ritirato da mesi) e
un `--theme themes/...` che non è mai esistito: **ottava smentita di questo file
per misura**, e proprio nella sezione che serve a essere copiata e incollata.*

```powershell
# NB: non esiste una .venv nel repo. Oggi gira sul Python globale (3.12.2),
# che ha già le dipendenze. Un venv + lockfile diventeranno utili al packaging
# (D4), non prima. Per crearne uno ora, se lo vuoi isolato:
#   python -m venv .venv ; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# CLI (D1). Il FORMATO si sceglie; la PALETTE no: è una sola (D20).
# Formati: dashboard (default della UI) · parata · zenit · a4 · deep-space
python cielo.py --year 2026 --month 8 --place Vicenza                        # A4, SVG
python cielo.py --year 2026 --month 8 --place Vicenza --png                  # A4, SVG + PNG (1800px)
python cielo.py --year 2026 --month 8 --format dashboard --png               # quadrato 1080
python cielo.py --year 2026 --month 3 --format deep-space --png              # i Messier

# web app (poi apri http://localhost:8000)
python -m uvicorn app.main:app --reload --port 8000

# LE DUE RETI. La suite copre tutto; la fotografia copre il buco dei golden,
# che sorvegliano SOLO l'A4 di agosto (vedi #7q).
python -m pytest -q                    # 216 verdi
python tools/fotografia.py             # 20 SVG (5 formati x 4 mesi), byte per byte
python tools/fotografia.py --scatta    # SOLO dopo un cambiamento DELIBERATO
```

**`--palette` non esiste più** (D20): la palette è `brand/palettes/gav.json` e
basta. Nemmeno la web app la espone — `?theme=` è stato tolto dai tre endpoint.
