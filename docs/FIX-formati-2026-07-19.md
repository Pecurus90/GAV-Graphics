# Interventi sui formati — lista di lavoro

*(Dettati da Marco il 2026-07-18 guardando i cinque poster resi. Ogni punto è stato
**verificato dall'architetto sul codice e sui render**, non trascritto a fiducia: dove
c'è una misura, è misurata. Stato del repo alla stesura: `6075ec6`.)*

> **Come leggerla.** Il punto 6 e il punto 5 sono **intrecciati** e vanno fatti
> nell'ordine dato: prima si libera lo spazio, poi si rimettono le tacche. Il punto 8
> non viene da Marco: è un difetto trovato verificando, e riguarda una rete di test.

---

## 1 — «Deep Space»: il quinto formato, generato da solo

Il layout `profondo` (oggi **pagina 2 del carosello**) diventa un **modello a sé**,
chiamato **Deep Space**, generato **singolarmente e non in abbinata**.

Il set passa a **cinque**: `dashboard · parata · zenit · a4 · deep-space`.

**DECISO (Marco, 2026-07-18): il carosello a due pagine SPARISCE.** Cinque formati,
**uno alla volta**. Va tolto anche il pulsante «Genera il carosello» dalla UI e il
percorso a due PNG.
*La ragione, e non è solo semplicità:* oggi il carosello accoppia **sempre** la pagina 2
alla pagina 1 «cielo». Da formato libero, **Deep Space si abbina a quello che si vuole**
— dashboard, zenit o parata — e la scelta si fa al momento di pubblicare. Mese e luogo
restano nel modulo, quindi generare due volte non rischia disallineamenti.

---

## 2 — Dashboard: NIENTE

Marco: *«dashboard è perfetto»*. **È la fonte di verità e non si tocca.** Serve da metro
per tutti gli altri punti di questa lista.

---

## 3 — Parata: la banda dei pianeti è troppo alta

Va **ridotta** per dare più spazio al disco centrale.

**VERIFICATO — N e S sono illeggibili, non solo stretti:**

| | posizione | cosa la copre |
|---|---|---|
| **N** | `x540 y333,6` | è **dentro** il testo «Telescopico / a Est» del pannello pianeti (la banda finisce a `y343`) |
| **S** | `x540 y862,2` | cade **dentro la striscia lunare** (il divisore è a `y844`) |

Nel render la «N» si intravede come un'ombra fra due parole. *(Prova: `out/fix/_p_N.png`.)*

**Attenzione all'ordine:** ridurre la banda sposta il bordo del disco, quindi **i
cardinali vanno ricontrollati dopo**, non prima.

---

## 4 — Zenit: mancano le temperature nella legenda

**VERIFICATO:** la legenda di Zenit mostra solo i nomi dei colori — «Blu»,
«Bianco-azzurra», … — e **non le temperature**: nel blocco `swatches` il campo
`label2` **non c'è**.

| formato | cosa mostra la legenda |
|---|---|
| dashboard | `Blu` + `oltre 15.000 K` |
| parata | `Blu` + `oltre 15.000 K` |
| **zenit** | `Blu` — **manca la temperatura** |
| a4 | `oltre 15.000 K` *(solo temperatura, senza nome del colore)* |

**Nota:** anche l'A4 è disallineato, ma **al contrario** — ha le temperature e non i
nomi. Da decidere se uniformare anche quello (sull'A4 lo spazio è una riga sola, per
questo fu scelto così: vedi il punto 5, che gli ridà respiro).

---

## 5 — A4: banda pianeti troppo alta

Va **abbassata** per dare respiro a **due** cose:
- la **legenda delle stelle**, oggi schiacciata nei **16 px** fra il bordo del disco
  (`y884`) e il divisore (`y900`);
- il **cerchio, sopra e sotto**, così **N e S si leggono**.

Oggi il disco è già al suo massimo: **8 px** dalla testata sopra, **2,5 px** dalla
legenda sotto. Non è che il disco debba crescere — **è che deve respirare**.

---

## 6 — Le tacche dei gradi su tutti tranne dashboard

**VERIFICATO:** oggi le ha **solo dashboard** (`"ticks": {"minor": 10, "major": 30}`).

> ⚠️ **INTRECCIO COL PUNTO 5 — leggere prima di eseguire.**
> Le tacche erano state messe sull'A4 e **poi tolte oggi stesso**, perché la tacca
> **Sud tagliava in due la scritta «≈ 7.000 K»**: le tacche escono di **17 px** e la
> striscia libera era di **16**.
> **Il punto 5 cambia proprio quella misura.** Se la banda pianeti scende e la legenda
> respira, la striscia si allarga e le tacche potrebbero starci.
> **Ordine obbligato: prima il punto 5, poi il 6.** E dopo, **si guarda**: se la tacca
> Sud tocca ancora il testo, sull'A4 non ci vanno.

Sugli altri (parata, zenit, deep-space) le tacche non sono mai state provate: **si
mettono e si guarda**, formato per formato.

---

## 7 — Stesse etichette di dashboard: costellazioni e stelle-guida

**VERIFICATO — oggi sono tre regimi diversi:**

| formato | etichette costellazioni |
|---|---|
| **dashboard** *(riferimento)* | **22** — lista curata |
| zenit | **22** — allineato |
| **parata** | **ZERO** (`labels: false`) — il disco è muto di costellazioni |
| **a4** | `default` → **tutte le principali sopra l'orizzonte** (~27 ad agosto, varia col mese) |

Da portare **tutti a 22**, la lista di dashboard.

**Due avvertenze:**
- Le 22 sono una **lista curata** (**D16**), non «le principali disponibili». Le 44
  minori restano fuori **di proposito**.
- **Parata oggi mostra comunque 6 nomi di STELLE** (Capella, Vega, Deneb, Altair,
  Arturo, Antares): `labels: false` spegne **le costellazioni**, non le stelle. Quindi
  «carente di nomi» è vero per le costellazioni, non per le stelle.
- Riaccendere le etichette su Parata **con il disco appena ingrandito** può creare
  collisioni che prima non c'erano: **si rende e si guarda**.

---

## 8 — La rete dei cardinali ha un secondo buco *(non viene da Marco)*

`tests/test_cardinals.py` è stato esteso oggi da «cardinale dentro il canvas» a
«cardinale non sotto un pannello». **Ma cerca i blocchi di tipo `panel`, e Parata non
ne ha nessuno**: le sue bande sono delimitate da `line` (`y343`, `y844`). Quindi il
test **non trova pannelli, e passa a vuoto** — mentre N e S sono sommersi (punto 3).

**È la terza volta in un giorno che una rete ha la maglia della forma sbagliata**
(prima: cardinali fuori dal canvas; poi: cardinale tecnicamente visibile ma sotto un
pannello; ora: banda che non è un pannello).

Da estendere a **«nessun cardinale sopra altro contenuto»** — testi e bande comprese —
non solo sopra un blocco `panel`. **E, come sempre: iniettare il guasto e vedere il
rosso**, o non è una rete.

---

## Prove

Render dello stato attuale in `out/fix/` (agosto 2026, Vicenza, osservatorio):
`F-dashboard.png` · `F-parata.png` · `F-zenit.png` · `F-a4.png` · `F-profondo.png`,
più i ritagli `_p_N.png` / `_p_S.png` (i cardinali sommersi di Parata).

*(`out/` è gitignorato: i render si rigenerano con
`python cielo.py --year 2026 --month 8 --place Vicenza --format <nome> --png`.)*
