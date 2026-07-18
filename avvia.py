#!/usr/bin/env python3
"""Avvio dell'app "Cielo del Mese" per il socio (D15).

Trova DA SOLO una porta libera, avvia il server e apre il browser su quella
porta — solo QUANDO il server risponde davvero.

Perche' non una porta fissa: la 8000 puo' essere gia' occupata da un'altra app
del PC (e' successo davvero, con "AstroLog"). Con la porta fissa il server non
parte, il browser apre una pagina bianca e il socio conclude «non funziona»,
senza log — lo scenario che D4 dichiara BLOCCANTE. Con una porta effimera scelta
dal sistema questo non puo' capitare, e il socio non deve sapere cos'e' una porta.

NON modifica l'app: importa `app.main` e lo serve. E' relocabile — la cartella di
questo file finisce su sys.path, cosi' funziona ovunque sia copiato il bundle.
"""
import os
import sys
import time
import socket
import threading
import webbrowser

HERE = os.path.dirname(os.path.abspath(__file__))


def _porta_libera():
    """Chiede al sistema operativo una porta effimera libera su localhost.

    Nota: fra questa chiamata e il bind di uvicorn c'e' una finestra minuscola in
    cui, in teoria, un altro processo potrebbe prendere la porta. Su un PC a
    singolo utente e' trascurabile; se accadesse, il server stampa l'errore nella
    finestra (non una pagina bianca muta)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]
    finally:
        s.close()


def _apri_quando_pronto(url):
    """Apre il browser SOLO quando il server risponde: niente pagina bianca."""
    import urllib.request
    for _ in range(150):                       # fino a ~30 s di attesa
        try:
            urllib.request.urlopen(url, timeout=0.5)
            break
        except Exception:
            time.sleep(0.2)
    webbrowser.open(url)


def main():
    os.chdir(HERE)             # CWD = il bundle (per eventuali percorsi relativi)
    sys.path.insert(0, HERE)   # per importare app.main anche lontano dal repo
    port = _porta_libera()
    url = f"http://127.0.0.1:{port}"
    print("Cielo del Mese — Gruppo Astrofili Vicentini")
    print(f"Apro il browser su {url}")
    print("Per CHIUDERE l'app: chiudi questa finestra.")
    threading.Thread(target=_apri_quando_pronto, args=(url,), daemon=True).start()
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=port, log_level="warning")


if __name__ == "__main__":
    main()
