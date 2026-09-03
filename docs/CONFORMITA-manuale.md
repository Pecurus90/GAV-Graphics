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

### [x] B2 — Manca la denominazione completa — **FATTO 2026-09-03**
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

**Fatto:** la testata di tutti e 5 i formati porta ora la stringa completa, **identica
a quella del template del manuale**, virgolette curve comprese.

**La stringa è passata da 26 a 48 caratteri, e la misura ha deciso il resto** —
larghezza calcolata col `.ttf` vero, non stimata:

| | nuova larghezza | esito |
|---|---|---|
| dashboard | 459,6 px → finisce a x=640 | OK |
| parata | 459,6 px → finisce a x=622 | OK |
| deep-space | 430,9 px → finisce a x=587 | OK |
| zenit | 373,4 px → finisce a x=483 *(icone a 594)* | OK |
| **a4** | **603,2 px** → bordo sx a x=148 | **NO: invade l'area di rispetto del logo** (serve x≥162,5) |

**Sull'A4 il corpo scende da 21 a 19**, e i due numeri che rendono la scelta
difendibile sono questi: a 19 la testata misura **545,8 px** (bordo sinistro a
x=177, cioè **34,6 px** di margine sull'area di rispetto) **e resta a 12,6 pt**,
sopra il minimo di stampa di §4. A **corpo 20 sarebbe entrata per 0,5 px** — dentro
il margine d'errore della stima, quindi scartata.
*Verificato poi sul RASTER, non sul modello:* primo pixel giallo della testata a
**x=179,0**, bordo del logo a 142 → **37,0 px liberi** contro i 20,5 richiesti.

**Una decisione presa, non subita: `· APS` c'è.** §1 lo vuole *«quando il contesto è
istituzionale»*, e un volantino diffuso dall'associazione lo è — ma soprattutto **il
manuale lo mette nel proprio template**, che è l'analogo più vicino a un poster.
*Toglierlo è una sola stringa in 5 file, se Marco legge «istituzionale» più stretto.*

**Previsione, scritta prima:** *«nel golden dell'A4 cambia UNA riga sola»*. Reale:
**1 riga sostituita**, con `x="450.0"` e `y="52"` **invariati** — cambiano solo
testo, corpo e tracking.

**Un errore mio, preso dalla rete e non da me:** avevo copiato nel golden l'A4 di
**settembre** (l'avevo reso per il ritaglio) al posto di quello di **agosto**, che è
il parametro canonico. `test_golden_svg_invariato` è diventato rosso e l'ha fermato.
*Il golden non serve solo a sorvegliare il motore: sorveglia anche chi lo rigenera.*

**Verificato:** suite **210 verdi**; collisioni sui 60 poster **155 → 155**, ogni
cella identica; fotografia dei 20 SVG riscattata; testate di A4 e zenit **guardate**
ai ritagli.

### [x] B3 — Area di rispetto del logo violata su 4 formati su 5 — **FATTO 2026-09-03**
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

**Fatto, e nell'ordine giusto: dopo B2.** *(La ragione era operativa e ha retto: B2
allunga la testata di 22 caratteri, quindi misurare lo spazio prima avrebbe voluto
dire misurarlo due volte.)*

**Ho spostato i TESTI, non rimpicciolito il tondo** — e la scelta ha un argomento:
§2 fissa anche una *dimensione minima* del marchio, e §5 chiede *«molta aria»*.
Rimpicciolire il logo avrebbe rispettato la lettera dell'area di rispetto
indebolendo il lockup; spostare la testata dà l'aria che il manuale chiede davvero.

| | richiesto | prima | dopo |
|---|---|---|---|
| dashboard | 25,0 | 22,0 | **26,0** |
| deep-space | 23,5 | 16,0 | **24,0** |
| parata | 22,0 | 16,0 | **23,0** |
| zenit | 17,0 | 14,0 | **18,0** |
| a4 | 20,5 | 67-134 | invariato *(testata centrata)* |

**Un difetto minore sanato passando:** su dashboard, deep-space e parata il **titolo
era disallineato di 2 px** rispetto a testata e sottotitolo (x=178 contro 180, 154
contro 156, 160 contro 162). Ora i tre blocchi sono **allineati sullo stesso asse**.
*Non l'avevo cercato: è saltato fuori leggendo le `x` per spostarle.*

**Il rischio vero era su zenit, e l'ho misurato:** la testata lì si sposta **verso**
la riga contatti appena rifatta in Z1. Ricontrollati i 12 mesi: lo stacco minimo
scende da 42,0 a **38,0 px** (settembre) — resta ampio.

**Previsione, verificata:** *«il golden dell'A4 non si muove — a4 non è toccato — e
nella fotografia si muovono 16 SVG su 20»*. Reale: suite **210 verdi**, e la
fotografia segnala **4 dashboard + 4 deep-space + 4 parata + 4 zenit**, con i **4
dell'A4 fermi**. Collisioni sui 60: **155 → 155**.

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

## Trovato eseguendo, NON è conformità — un difetto vero, preesistente

### [x] Z1 — Il piedino di ZENIT si scrive addosso e ESCE DAL CANVAS — **FATTO 2026-09-03**
*(Trovato il 2026-09-03 guardando il ritaglio della testata di zenit durante B2.
**Riportato, non corretto** — regola #4: il commit era a scopo unico.)*

**Non l'ho causato io, ed è dimostrato per esecuzione**, non per deduzione: ho reso
zenit col layout del commit **`a67ce4d`** (prima di questa sessione) e il difetto
c'è, **identico**.

**Misurato** (riga contatti, canvas largo 1080):

```
  x  594,0 ->  610,0   icona instagram
  x  618,0 ->  734,5   "@astrofilivicentini"
  x  734,0 ->  750,0   icona facebook          <- il testo la TOCCA (0,5 px)
  x  758,0 ->  915,8   "Gruppo Astrofili Vicentini"
  x  906,0 ->  922,0   icona email             <- SOVRAPPOSTA di 9,8 px
  x  930,0 -> 1084,4   "info@astrofilivicentini.it"
                                               <- ESCE DAL CANVAS di 4,4 px
```

Sul poster si legge letteralmente **`Gruppo Astrofili Vicentin✉`**, e l'indirizzo
email è **tagliato dal bordo**.

**La causa è quasi certamente #7s**, il cambio di font: le `x` di quelle icone furono
fissate in #7p quando il font era **Barlow Semi Condensed**, e R16 ha misurato che le
**minuscole di Space Grotesk sono ~29% più larghe** (fattore 0,400 → 0,516). Le icone
non si sono spostate; il testo si è allungato sotto di loro.

**Perché nessuna rete l'ha visto — ed è l'OTTAVA volta di questa famiglia.** Le
cinque categorie di `tools/collisioni.py` sono *sotto-pannello · banda ·
etichetta↔etichetta **del disco** · cardinale · tacca-testo*. Questo è **testo di
layout contro icona di layout**, e non è in nessuna. È esattamente la stessa forma di
**R15** (testo↔testo dentro un pannello), trovata allo stesso modo: **guardando**,
subito dopo che lo strumento aveva dato **zero**.
*E R16 aveva verificato il cambio di font proprio con quello strumento: la verifica
era buona, ma la rete non copriva questo caso.*

**Fatto — ed è solo zenit.** La stessa riga esiste su dashboard, parata, a4 e
deep-space: **misurate tutte e cinque, le altre quattro sono pulite** e con margini
larghi (su a4 la riga finisce a x=738 su 900; su dashboard a 690 su 1080). Zenit è
l'unico perché è l'unico che mette i contatti **in testata, accanto al titolo**,
invece che in un piedino a tutta larghezza.

**Il difetto vero non era «le x sono sbagliate»: la riga era IMPACCATA A GAP ZERO.**
`@astrofilivicentini` finiva a 734,5 e l'icona di Facebook cominciava a 734,0 — cioè
non c'era **nessuno spazio** da recuperare spostando le cose. Ricalcolata da zero:

```
   icon  x=552     instagram          gap icona->testo  7 px
   text  x=575     @astrofilivicentini    gap fra gruppi   18 px
   icon  x=700.5   facebook
   text  x=723.5   Gruppo Astrofili Vicentini
   icon  x=887.1   email
   text  x=910.1   info@astrofilivicentini.it
                   finisce a x=1052,6 -> 27,4 px di margine destro
```

**Il corpo scende da 13 a 12, e non è arbitrario: a 13 NON CI STA.** Misurato: a
corpo 13, con un gap fra gruppi appena decente, la riga è larga 525-534 px e
dovrebbe partire da x≤526 — ma il titolo di **settembre** arriva a x=510, quindi
resterebbero 8-16 px. A corpo 12 la riga è larga 500,6 e parte da 552: **42 px di
stacco**. *E 12 è la scala di zenit, non un'eccezione: `PIANETI VISIBILI` e
`TEMPERATURA STELLE` lì sono già a 12.*

**Verificato su tutti e 12 i mesi**, perché il titolo cambia lunghezza col mese e un
solo mese guardato non prova niente: stacco minimo **42,0 px** (settembre), massimo
121,2 (luglio), **zero collisioni**. Poi guardato al 2× su settembre, il mese
peggiore.

**Previsione, verificata:** *«il golden dell'A4 non si muove — ho toccato solo
zenit — e nella fotografia si muovono esattamente i 4 SVG di zenit»*. Reale: suite
**210 verdi** col test golden compreso, e la fotografia segnala **`zenit_02`,
`zenit_05`, `zenit_08`, `zenit_11`** e nient'altro. Collisioni sui 60: **155 → 155**.

**Quello che NON ho fatto, e resta il rimedio strutturale:** le posizioni sono ancora
**cablate**. Oggi la riga sta in 500,6 px su 528 disponibili — ma se il GAV cambiasse
l'indirizzo email con uno più lungo di ~27 px si romperebbe di nuovo, in silenzio.
Il rimedio vero è **derivare le x dalla larghezza del testo**, e qui c'è un vincolo
che va detto: **il motore non ha metriche di font** (Pillow non è in
`requirements.txt`, e aggiungerla vorrebbe dire impacchettarla nell'`.exe` — D17).
La strada praticabile è la **stima già in uso nel progetto** (`n × corpo × fattore`,
come `disc.py`), che ha ~5% d'errore: su questa riga sono ±25 px, cioè quasi tutto il
margine. **È una decisione architetturale, non un ritocco** — per questo l'ho
lasciata fuori.

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
