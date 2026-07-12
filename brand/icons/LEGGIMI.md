# Icone del piè di pagina

Glifi vettoriali incorporati nei post (piè di pagina: profilo Instagram, pagina
Facebook, email). Stanno qui come **dati** (`icons.json`, solo il tracciato in
viewBox 24×24): il **colore** non è nel file, lo mette il tema al render (`fill`
da token), così le icone si ricolorano con la palette e non c'è mai un hex
cablato. Sono incorporati come tracciato nell'SVG (nessun download a runtime):
funzionano offline e dentro l'`.exe` (D4).

## Provenienza e licenze

- **instagram**, **facebook** — [Simple Icons](https://simpleicons.org),
  licenza **CC0 1.0** (dominio pubblico): ridistribuibili nel repo e nell'`.exe`.
  I marchi Instagram/Facebook restano dei rispettivi titolari; qui servono solo
  a indicare i profili del GAV.
- **email** — envelope **generica disegnata a mano** (nessun marchio, nessuna
  licenza da citare).

Aggiungere un'icona = aggiungere una voce a `icons.json` (nome → `{d, fill_rule?}`).
