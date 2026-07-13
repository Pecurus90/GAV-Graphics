# Catalogo di Messier — fonte e licenza

`messier.json` è derivato da **OpenNGC**, database NGC/IC mantenuto da
**Mattia Verga**.

- Fonte: <https://github.com/mattiaverga/OpenNGC>
  (file `database_files/NGC.csv` e `database_files/addendum.csv`).
- **Licenza dei dati: CC-BY-SA-4.0** (`.reuse/dep5` del repo OpenNGC dichiara
  `Files: *  License: CC-BY-SA-4.0`).
- Epoca delle coordinate: **J2000**.

## Attribuzione (obbligatoria)

> Dati degli oggetti Messier derivati da **OpenNGC** di Mattia Verga
> (<https://github.com/mattiaverga/OpenNGC>), distribuiti sotto licenza
> **Creative Commons Attribuzione-Condividi allo stesso modo 4.0** (CC-BY-SA-4.0).

Questa attribuzione va mantenuta ovunque il catalogo (o un suo derivato) venga
ridistribuito: nel repo, nella Release e — se compaiono i nomi/dati Messier —
nel volantino o nel post.

## Cosa comporta la share-alike (CC-BY-SA), in pratica

- **I fatti astronomici non sono protetti** (posizione, magnitudine, tipo di un
  oggetto sono dati di natura). A essere protetta dal diritto d'autore — e in UE
  anche dal *diritto sui generis sulle banche dati* — è la **compilazione**: la
  selezione, la verifica e l'arrangiamento di OpenNGC.
- `messier.json` è un **derivato** di quella compilazione (l'ho estratta e
  trasformata): quindi **questo file** eredita CC-BY-SA-4.0 e va attribuito.
- La share-alike **si ferma al file di dati**. Il codice del motore che *legge*
  il catalogo non è un'opera derivata del catalogo: dati e programma sono un
  *aggregato*, non una fusione. Marco resta **libero di scegliere la licenza del
  resto del repo** (es. MIT), a patto che `messier.json` continui a portare
  CC-BY-SA-4.0 + attribuzione.
- L'`.exe` che **impacchetta** il catalogo insieme al programma è un aggregato,
  non un adattamento: il catalogo resta CC-BY-SA, il programma resta sotto la sua
  licenza. L'attribuzione deve però comparire (README/Release).

**Da decidere prima di rendere pubblico il repo (D4):** aggiungere `LICENSE` per
il codice GAV e citare OpenNGC nel README. Se il GAV **modifica** i valori
(campo `visione`, nomi italiani), quelle modifiche restano sotto CC-BY-SA (sono
adattamenti del catalogo): va bene, basta che la licenza del file non cambi.
