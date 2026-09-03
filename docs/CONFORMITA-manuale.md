# Conformità al manuale d'identità — cose da fare

**Fonte:** `docs/GAV-design-system.pdf` (edizione agosto 2026). Il PDF ha il testo
**vettorializzato**: `get_text()` torna vuoto, si legge rendendo le pagine a immagine
(`get_pixmap`) e i colori si estraggono dagli oggetti vettoriali (`get_drawings()`),
come già fatto in #7r.

**Ricognizione: 2026-09-03.** Ogni riga qui sotto è **misurata**, non dedotta: accanto
alla prescrizione c'è il numero vero letto dal codice o dall'SVG reso. Se una misura
non torna, ha ragione il codice e questa riga va corretta.

> **Perché esiste questo file.** Il progetto ha già imparato che *«deciso» non è
> «fatto»* (#7o: due decisioni di Marco registrate come eseguite e mai eseguite).
> Nove divergenze tenute a mente sono nove divergenze che si perdono fra un giro e
> l'altro. Qui hanno una casella, e la casella si spunta **solo** con la verifica
> accanto.

---

## Già conforme — verificato, non assunto

| Sezione | Cosa è stato verificato |
|---|---|
| §3 Colori | I **26 token di marca** di `brand/palettes/gav.json` sono ognuno un passo della scala blu/neutri o un token semantico del tema notte. Nessun colore inventato. *(`star_ramp` e `planet_colors` sono fuori dal perimetro del manuale: sono **dato astronomico**, non marchio — D2.)* |
| §3 «max 1-2 sfondi» | 2 gradienti nell'SVG reso: `bg` (pagina) e `disk`. |
| §4 Font | Space Grotesk + Work Sans, OFL, nel repo, dichiarati dal `canvas.font_family` di tutti e 5 i layout. |
| §4 Sentence case | Titolo `Il cielo di {mese} {anno}`; il MAIUSCOLO resta solo sulle etichette piccole. Titoli **bianchi su fondo notte**, come prescritto. |
| §2 Marchio | Tondo a colori usato tal quale: non ridisegnato, non ricolorato, non ruotato. Minimi rispettati (A4 **19,1 mm** > 12 mm; a schermo **68-100 px** > 32 px). |
| §1 Sigla | `GAV` **non compare** in nessuno dei 5 poster. *(L'unica occorrenza nell'SVG sta dentro il base64 del logo: falso positivo del grep.)* |

---

## L'ORDINE, e perché è questo

Non è per gravità: è per **dipendenza tecnica**.

1. **Blocco A — il guscio dell'app.** Non tocca il motore, non tocca i layout,
   **non può muovere un golden**. Rischio zero: si fa per primo per togliere di
   mezzo i casi facili e concentrare l'attenzione su B.
2. **Blocco B — i layout.** Ognuno muove il golden dell'A4, quindi **uno per
   commit, con una previsione falsificabile scritta prima**. E l'ordine dentro B
   non è libero: **B1 (tracking) va prima di B2 (denominazione)** perché B1
   *accorcia* la testata e B2 la *allunga* di 22 caratteri. Farli al contrario
   vuol dire misurare due volte lo stesso spazio, e su `zenit` (testata a 13 px
   accanto alle icone social) la testata lunga con il tracking vecchio **non ci
   sta**: 453 px stimati contro i 484 disponibili prima delle icone.
3. **Blocco C — la rete.** Dopo, non prima: prima si porta il codice dove deve
   stare, poi si mette il test che ce lo tiene.
4. **Blocco D — le decisioni.** Non sono lavoro d'esecuzione: sono scelte di
   prodotto. Restano in fondo e le arbitra Marco.

---

## Blocco A — il guscio dell'app *(nessun rischio golden)*

### [x] A1 — «GAV» usato come firma da solo — **FATTO 2026-09-03**
**Manuale §1:** *«La sigla "GAV" è ammessa solo nel discorso, mai da sola come firma.»*
**Misurato:**
- `app/main.py:225` → `<title>Cielo del Mese · GAV</title>`
- `app/main.py:377` → nella barra laterale, **accanto al logo**: `GAV` grande +
  `Astrofili Vicentini` piccolo. È un **lockup**, cioè il caso esatto che §1 vieta.

*(«Astrofili Vicentini» da solo **è ammesso** — §1 lo cita come forma alternativa.
Il difetto è la sigla, non l'abbreviazione.)*

**È la stessa violazione che #7n aveva già tolto dal piedino dell'A4.** È
sopravvissuta nel guscio perché nessuno stava guardando lì.

**Fatto:** la barra laterale porta ora il **lockup del manuale** (§2) — tondo +
`Gruppo` / `Astrofili Vicentini` in Space Grotesk Bold + `"Giorgio Abetti"` in corpo
minore sotto, com'è disegnato a pag.1 del PDF. L'a-capo cade **dopo «Gruppo»**, che è
l'unico punto che §1 ammette. Il `<title>` e l'`alt` del logo non dicono più «GAV».
*(Il sottotitolo era MAIUSCOLO con tracking +0,18em: nel manuale è in tondo, fra
virgolette, in grigio. Riportato a quello.)*

**Verificato, non dedotto:**
- **Misura prima del taglio:** `Astrofili Vicentini` a 15px Space Grotesk Bold =
  **127,0 px** (misurato col `.ttf` vero, non stimato) contro i **133 px** liberi
  nella barra. Il font-size non è stato toccato: ci stava già.
- **HTML servito** (non il sorgente): `GET /` → 200, e le occorrenze di `GAV`
  nell'HTML sono **zero**.
- **Guardato**, non solo misurato: screenshot Chrome headless, ritaglio al **3×**
  sul lockup. Nessun taglio, nessun traboccamento, l'a-capo cade dove deve.
- Suite: **210 verdi**.

*Osservazione lasciata aperta (non è un difetto, è una proporzione):* nel manuale il
tondo è alto quanto tutto il blocco di testo; da noi è ~32 px contro ~50. Il manuale
non prescrive un rapporto, quindi non l'ho toccato.

### [x] A2 — Bottoni non a pillola, raggi fuori scala — **FATTO 2026-09-03**
**Manuale §5:** *«Bottoni — sempre a pillola»*; *«Raggi: 6 px (campi), 12 px (card),
20 px (blocchi grandi), pillola per bottoni e badge.»*
**Misurato in `app/main.py`:** raggi 3 · 5 · 6 · 7 · 8 · 9 · 10 · 14 — **solo il 6 è
in scala**. `.genera` e `.btn` hanno `border-radius:7px`: non sono pillole.

**Fatto — e la parte che conta è la CLASSIFICAZIONE, non i numeri.** Il manuale non
dà una lista di selettori: dà **quattro categorie**. Ogni raggio è stato assegnato a
una, e l'assegnazione è la decisione:

| | manuale | assegnati |
|---|---|---|
| **bottoni e badge → pillola** | `999px` | `.genera` · `.btn` · `.chip` · `.formats` · `.seg` · thumb della barra di scorrimento |
| **campi → 6** | `6px` | `.nav-item` · `.coord-grid .qd-loc` · `.err-msg` |
| **card → 12** | `12px` | `.qd-card` · `.phases` · `.poster-frame` · `.err-card` |
| **blocchi grandi → 20** | `20px` | `.stage-box` |

**Dove NON l'ho applicata, e perché:** i cerchi (`.titlebar .dot`, `.chip .sw`,
`.phase .dot`, gli spinner) restano al `50%`. Non sono raggi fuori scala: sono
**cerchi**, e §5 non parla di loro. Applicare la scala lì avrebbe voluto dire
scambiare la regola per un'operazione di ricerca-e-sostituzione.

*Due scelte discutibili, dichiarate perché si vedano:* `.nav-item` è una **riga
interattiva**, non un bottone-CTA — l'ho messa fra i campi (6), non fra le pillole,
perché una barra laterale di pillole non è ciò che §5 disegna. E `.formats` (il
controllo segmentato) è un **gruppo di bottoni**: pillola. Reso e guardato al 3×, la
cella selezionata riempie l'estremità tonda ed è proprio l'*«eco del tondo del logo»*
che il manuale nomina.

**Verificato:** screenshot Chrome headless dell'app, ritagli al **3×** sul controllo
dei formati e sulla barra laterale. Suite verde.

### [x] A3 — Icone dell'app col tratto sbagliato — **FATTO 2026-09-03**
**Manuale §7:** *«Icone: set Lucide (stile linea, tratto 2 px)»*.
**Misurato:** `stroke-width` = 1,3 · 1,45 · 1,5 · 1,6 · 2,4 — **mai 2**. Sette punti,
**sette valori diversi**: non era una scelta, era deriva.

**Fatto:** tutte e sette a `2`. Le icone dell'app hanno già tutte `viewBox="0 0 24 24"`,
cioè la griglia di Lucide, quindi `stroke-width="2"` **è** la convenzione del set —
non un numero scelto da noi.

**Un'ambiguità del manuale, risolta e dichiarata perché è discutibile:** *«tratto 2
px»* si può leggere in due modi — (a) 2 nella griglia 24 di Lucide, (b) 2 px
**resi a schermo**. Non sono la stessa cosa: la nostra icona di stato vuoto è
disegnata su 24 ma **mostrata a 46 px**, quindi con (a) il tratto reso è 3,8 px, e
per ottenere (b) servirebbe `stroke-width: 1,04`. Ho scelto **(a)**, perché la
frase dice *«set Lucide (stile linea, tratto 2 px)»*: nomina il set e poi ne
descrive la convenzione, non chiede una compensazione per dimensione — e
compensando, ogni icona avrebbe un `stroke-width` diverso, che è il contrario di un
set. *Reso e guardato: a 46 px non è ingolfata.* Se Marco la legge nell'altro modo,
è un numero solo da cambiare.

**Verificato:** zero `stroke-width` diversi da 2 residui nel file; screenshot
Chrome headless con ritagli al 3× su barra laterale e controllo dei formati — i
glifi restano nitidi. Suite 210 verdi.

---

## Blocco B — i layout *(ognuno muove il golden: uno per commit)*

### [x] B1 — Il tracking è 2-3× più largo del prescritto — **FATTO 2026-09-03**
**Manuale §4:** etichetta maiuscola **+0,08em**; display **−0,02em**.
**Misurato** (`letter_spacing ÷ size`, tutti e 5 i layout):

| Blocco | Reale | Atteso |
|---|---|---|
| `GRUPPO ASTROFILI VICENTINI` | +0,143 … **+0,231em** | +0,08em |
| `PIANETI VISIBILI` / `FASI LUNARI` / `TEMPERATURA STELLE` | +0,145 … +0,190em | +0,08em |
| `Il cielo di {mese} {anno}` | 0,000 … +0,050em | **−0,02em** |

I titoli non sono solo fuori misura: vanno nella **direzione opposta** al manuale.

**Fatto: 24 blocchi su 5 layout.** Maiuscole → `0,08 × corpo`; titoli → `−0,02 × corpo`.
Il diff dei layout è **48 righe, tutte con `letter_spacing`** e **zero d'altro tipo**.

**La previsione, scritta PRIMA di toccare un file, e verificata:** *«il golden dell'A4
cambia esattamente 5 righe, e ognuna differisce SOLO nel valore di `letter-spacing`;
il golden del disco resta fermo»*. Reale: **5 righe fuori, 5 dentro**, e sostituendo
il valore del tracking con un segnaposto le due versioni sono **identiche** — nessuna
`x`, nessuna `y`, nessun elemento aggiunto o tolto. Il golden del disco è **passato
senza essere toccato**.
*Regge perché i 5 blocchi hanno `x` fisso: tre sono `anchor="middle"` (il testo si
stringe attorno al proprio centro) e due sono ancorati a sinistra.*

**Collisioni sui 60 poster: 155 → 155, ogni cella identica.** Ed è il risultato
**giusto**, non un non-risultato: nessuna delle 155 coinvolge un blocco di layout —
sono tutte etichette **del disco**, il cui tracking è cablato in `disc.py` e che B1
non tocca (vedi B1-bis). Le quattro categorie di collisione «dure» (sotto-pannello,
banda, cardinale, tacca-testo) restano a **zero** su dashboard, parata, zenit e a4.

⚠️ **Una mia affermazione ritrattata, perché il metodo conta più della conclusione.**
Avevo scritto qui che lo strumento *«non include `letter_spacing`»* e che quindi
sarebbe stato **cieco** al cambiamento — cioè che la misura sarebbe stata vuota.
**Falso, e l'ho letto io male:** `collisioni.py:112` fa
`w = len(text) * size * f + ls * (len(text)-1)`. Il tracking **c'è**. Avevo letto il
*docstring*, che semplifica in `n × corpo × FATTORE`, invece del codice.
*È la lezione del progetto al contrario: qui il commento mentiva e il codice aveva
ragione — e per un momento ho creduto al commento.*

**Guardato, non solo misurato:** dashboard di settembre reso prima e dopo, testata
affiancata a 1,6×. La testata smette di essere spaziata come una carta intestata e
la gerarchia che §4 descrive — *etichetta maiuscola piccola → titolo grande → testo* —
diventa finalmente leggibile. La fotografia dei 20 SVG è stata **riscattata**
(movimento deliberato); suite **210 verdi**.

### [ ] B1-bis — Il tracking dei NOMI DI COSTELLAZIONE è cablato in `disc.py`
*(Trovato eseguendo B1, non previsto dalla ricognizione.)*
**Misurato:** il golden dell'A4 ha **28** `letter-spacing`, non 5. I 23 in più sono i
**nomi delle costellazioni** (`Orsa Maggiore`, `Pegaso`, …) a corpo 11,7 e tracking
`0,5` = **+0,043em**, emessi da `disc.py:111` con il valore **scritto nel codice**
(e un secondo punto, `disc.py:253`).

**Perché è la stessa violazione:** §4 mette le **etichette** fra i casi *display*, e
il display vuole **−0,02em**. Quindi +0,043em è fuori norma esattamente come lo erano
i blocchi di layout.

**Perché NON l'ho fatto dentro B1**, ed è una scelta, non una dimenticanza:
1. **È un'altra unità di lavoro.** B1 è dati (5 file JSON); questo è **codice**, e
   tocca `disc.py`, cioè il disco sigillato (D7).
2. **Muove una rete diversa.** I nomi delle costellazioni **sono** le etichette che
   producono tutte e 155 le collisioni misurate. Stringerle cambia i numeri di
   `tools/collisioni.py` — che in B1 dovevano restare fermi per dimostrare che B1
   non aveva perturbato nulla. Mischiare le due cose avrebbe reso **impossibile
   dire quale delle due ha mosso cosa**: due variabili, nessuna diagnosi. *È
   l'argomento con cui #7q ha ordinato le zodiacali dopo il declutter.*
3. Il valore `0,5` è **cablato**: portarlo in un token o in un parametro di layout è
   una decisione di forma, non una sostituzione.

*Previsione per quando si farà:* le collisioni possono solo **calare** (le etichette
si accorciano di ~0,73 px per lettera), e il golden si muove su **28 righe** invece
di 5. Da verificare, non da assumere.

### [ ] B2 — Manca la denominazione completa *(la più grave)*
**Manuale §1:** *«La denominazione completa è Gruppo Astrofili Vicentini "Giorgio
Abetti": usarla su materiali istituzionali, lockup, footer e locandine.»*
**Misurato:** `"Giorgio Abetti"` e `APS` hanno **zero occorrenze** in tutti e 5 i
layout, negli SVG resi, in `README.md` e in `CREDITI.md`.

**L'A4 è tre di quei quattro casi in una volta:** è una *locandina*, la sua testata è
un *lockup* (tondo + nome), e ha un *piedino*.

**E non è un'interpretazione:** il template del manuale stesso (pag. 5,
«Presentazione 16:9») ha come etichetta di testata, in giallo, esattamente
`GRUPPO ASTROFILI VICENTINI "GIORGIO ABETTI" · APS`. La nostra testata è la stessa
costruzione, monca della seconda metà.

### [ ] B3 — Area di rispetto del logo violata su 4 formati su 5
**Manuale §2:** *«Area di rispetto: attorno al tondo lasciare almeno ¼ del suo
diametro libero da testi e grafica.»*
**Misurato** (bordo destro del logo → primo testo a fianco):

| Formato | Diametro | Richiesto | Reale | |
|---|---|---|---|---|
| `dashboard` | 100 | 25,0 px | **22,0** | ✗ |
| `deep-space` | 94 | 23,5 px | **16,0** | ✗ |
| `parata` | 88 | 22,0 px | **16,0** | ✗ |
| `zenit` | 68 | 17,0 px | **14,0** | ✗ |
| `a4` | 82 | 20,5 px | 67-134 | ✓ *(testata centrata)* |

**Da fare DOPO B2**, non prima: B2 allunga la testata e potrebbe obbligare a
rientrare, non ad allargare. Misurare una volta sola, alla fine.

### [ ] B4 — Raggio dei pannelli fuori scala
**Manuale §5:** raggi 6 / 12 / 20.
**Misurato:** i 5 pannelli di `dashboard` e `zenit` usano **`rx: 16`**.
*(Il pannello a tutta larghezza di zenit ha `rx: 0`, ed è corretto: è una fascia.)*

### [ ] B5 — Le icone del piedino: set e colore sbagliati
**Manuale §7:** *«Icone: set Lucide (stile linea, tratto 2 px) — blu su chiaro,
gialle su notte.»*
**Misurato in `brand/icons/icons.json`:**
- `instagram`, `facebook` → **Simple Icons, glifi pieni**. *I marchi sono
  un'eccezione legittima: Lucide non ha logo di terzi, e il logo di Instagram
  ridisegnato «alla Lucide» sarebbe un marchio alterato.* **Restano.**
- `email` → **envelope piena disegnata a mano**. È un'icona **generica**, cioè
  esattamente il caso che §7 governa, e Lucide ha `mail`. **Va sostituita.**
- Tutte e tre sono rese con `fill: text3` (`#9dccdc`): **azzurre, non gialle su
  notte.**

### [ ] B6 — Le stelline di sfondo sono azzurre
**Manuale §7:** *«Motivo decorativo: piccole stelle puntiformi gialle e bianche su
fondi notte, sempre discrete.»*
**Misurato:** `bgstar` = `#cbe4ed` (blu 100). Il token viene dal manuale; **la
prescrizione di §7 no.**

⚠️ **Confine da non sbagliare:** questo vale per le stelle **decorative fuori dal
disco**. Le stelle **dentro** il disco sono `star_ramp`, cioè **fisica** (D2): non si
toccano, e il manuale non le governa.

---

## Blocco C — la rete

### [ ] C1 — Nessun test ancora la palette al manuale
**Misurato:** l'unico test che nomina la palette è
`tests/test_layouts_smoke.py:52`, e asserisce solo che il file **si chiami**
`gav.json`. **Nessuna asserzione sui valori.**

Quindi: i 26 colori sono giusti **per disciplina**, non per costruzione. Se domani
qualcuno ritocca un blu, **la suite resta verde**.

**È l'ottava volta che il progetto trova un buco di questa famiglia** (cardinali
fuori canvas → cardinale sotto un pannello → la banda che non è un `panel` → le
linee delle figure (R13) → nessuna rete sull'allineamento (R14) → le note dei
pianeti (R15) → questa).

*Forma proposta, da discutere:* il test dichiara la **scala del manuale** (i passi
blu e i neutri, copiati dal PDF) e pretende che **ogni token di marca sia uno di
quei passi**. Non pretende *quale* — così un ritocco deliberato resta possibile, ma
un colore **inventato** diventa rosso. Le 2 chiavi astronomiche sono escluse per
costruzione, non per elenco.

---

## Blocco D — decisioni, non esecuzione

### [ ] D-a — L'A4 sfonda il minimo di 12 pt in stampa
**Manuale §4:** *«Corpi minimi: 12 pt in stampa, 24 px su slide 1920×1080.»*
**Misurato sull'SVG reso** (900 px = 210 mm → 1 pt = 1,512 px → **12 pt = 18,1 px**):

```
  NO    9,5 px =  6,3 pt   x30      NO   12,5 px =  8,3 pt   x1
  NO   10,5 px =  6,9 pt   x15      NO   13,0 px =  8,6 pt   x3
  NO   10,8 px =  7,1 pt   x14      NO   15,0 px =  9,9 pt   x2
  NO   11,0 px =  7,3 pt   x6       NO   16,0 px = 10,6 pt   x7
  NO   11,5 px =  7,6 pt   x4       NO   17,8 px = 11,8 pt   x4
  NO   11,7 px =  7,7 pt   x21      OK   21,0 px = 13,9 pt   x1
                                    OK   30,0 px = 19,8 pt   x1
  --> 107 testi su 109 sotto i 12 pt (98%)
```
Passano **solo** la testata e il titolo.

**Perché è una decisione e non un fix:** D16 ha già deciso i corpi piccoli, ma
**misurando il telefono** — parlava dei formati social, dove il socio zooma. L'A4
**si stampa**, e nessuno zooma un foglio. Portarlo a 12 pt non è un ritocco: sarebbe
**metà del contenuto attuale** (o metà mappa), cioè *un altro poster*. È lavoro col
designer, come D16 stesso prescrive.

### [ ] D-b — Il guscio dell'app usa ~20 colori, nessuno del manuale
**Manuale §3:** *«nessun altro colore decorativo oltre a blu, giallo e neutri.»*
**Misurato:** `#0b0e13 #10141b #161c25 #1d2530 #eaf0f8 #a2afc4 #75839a #556074
#6f89a8 #8fa7c4 #3f5f83 #f2f7ff #2b3543 #4a6d96 #0e1626 #05070f #f2d3c9 #f0c6b6`
+ **verde `#5fd08a`, ambra `#e8b45f`, rosso-arancio `#e0664a`**.

**Questa è D19, ed è deliberata.** Ma l'argomento di D19 va guardato in faccia:
copre l'**acciaio neutro** (*«se guscio e poster fossero blu-notte uguali sparirebbe
il confine fra l'applicazione e ciò che produce»*), e quell'argomento **regge
ancora**. Non copre invece i **tre colori di stato**: un verde/ambra/rosso è colore
decorativo nel senso che §3 vieta, e si potrebbe dire la stessa cosa coi neutri e col
giallo del manuale.

**Due domande distinte per Marco**, da non fondere:
1. I 3 colori di stato si neutralizzano? *(basso costo, nessun impatto su D19)*
2. L'acciaio resta, o il guscio passa ai neutri del manuale? *(rimette in
   discussione D19)*

---

## Fuori scope, trovato passando

- `app/main.py:243-244` — il CSS di `input[type=color]` è **residuo morto**
  dell'editor rimosso in #7r. Non è conformità: è pulizia.
- **Tensione da segnare, non da risolvere qui:** l'invariante #4 dichiara *«stile
  neon + glow: identità del brand»*, e l'SVG dell'A4 usa i filtri **22 volte**. Il
  manuale non nomina il glow da nessuna parte, e su tema notte prescrive le card
  *«senza ombra»*. Non è una violazione (il glow non è un'ombra e non è un colore),
  ma è un tratto d'identità che **il manuale non sanziona**: se un giorno si vuole
  che il manuale sia l'unica fonte, questa è la riga che va decisa.
