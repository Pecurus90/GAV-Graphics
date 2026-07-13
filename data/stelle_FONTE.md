# Stelle e linee delle costellazioni — fonte e licenza

`stars6.json` e `const_lines.json` provengono da **d3-celestial**, la libreria di
mappe celesti di **Olaf Frohn**.

- Fonte: <https://github.com/ofrohn/d3-celestial>
  - `data/stars6.json`      ← `data/stars.6.json` di d3-celestial (5044 stelle)
  - `data/const_lines.json` ← `data/constellations.lines.json` di d3-celestial
- Provenienza **verificata per confronto integrale** (stesso hash, non "somiglia"),
  ricognizione 2026-07-13.
- **Licenza: BSD 2-Clause** ("Simplified BSD").
- Epoca delle coordinate: **J2000**.

## Attribuzione (obbligatoria)

> Dati stellari e delle costellazioni da **d3-celestial** di Olaf Frohn
> (<https://github.com/ofrohn/d3-celestial>), distribuiti sotto licenza
> **BSD 2-Clause**.

## Cosa comporta la BSD 2-Clause, in pratica

La BSD-2 è permissiva ma pone **due condizioni** alla ridistribuzione, e questa
è quella che di solito si sbaglia:

- **Forma sorgente** (il file `.json` nel repo): va mantenuta la nota di
  copyright + le condizioni + il disclaimer. Questo file lo fa.
- **Forma binaria** (l'`.exe` di D4): la nota va **riprodotta «nella
  documentazione o negli altri materiali forniti con la distribuzione»**. Un
  `.exe` che impacchetta questi dati **è** forma binaria: deve portare i crediti
  con sé (una schermata "Informazioni", o `CREDITI.md` accanto all'eseguibile).
  Vedi `CREDITI.md` e la nota in `CLAUDE.md` sotto D4.

Non c'è share-alike (a differenza di OpenNGC): la BSD-2 non "contagia" il resto
del repo. Il codice resta MIT.

## Testo completo della licenza (BSD 2-Clause)

```
Copyright (c) 2015, Olaf Frohn
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR
ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
```
