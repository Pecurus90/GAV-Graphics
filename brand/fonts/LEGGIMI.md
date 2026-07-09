# Font del brand GAV

Qui vanno i file dei font (`.ttf`/`.otf`) che verranno **impacchettati nell'app**
e usati dal renderer (`resvg`) per disegnare i testi dei post. Servono i file
locali perche' l'app deve funzionare offline e dentro l'`.exe`, senza dipendere
dai font installati sul PC.

## Font proposti (gratuiti, licenza OFL — si possono ridistribuire)

- **Space Grotesk** — titoli. Geometrico, a tema "spazio", distintivo ma leggibile.
  https://fonts.google.com/specimen/Space+Grotesk
- **Inter** — testo e dati. Sans-serif pulitissimo, ottimo ai piccoli corpi.
  https://fonts.google.com/specimen/Inter

## Come aggiungerli

Scarica i `.ttf` e mettili qui, ad esempio:

```
brand/fonts/SpaceGrotesk-Bold.ttf
brand/fonts/SpaceGrotesk-Medium.ttf
brand/fonts/Inter-Regular.ttf
brand/fonts/Inter-Bold.ttf
```

Il renderer carica automaticamente questa cartella (`font_dirs`), quindi i
`font-family` usati nei template ("Space Grotesk", "Inter") verranno risolti.
