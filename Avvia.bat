@echo off
rem Cielo del Mese - avvio (relocabile).
rem %~dp0 = la cartella di questo file, ovunque sia stata copiata.
rem avvia.py trova una porta libera da solo e apre il browser su quella.
rem Per chiudere l'app: chiudi questa finestra.
cd /d "%~dp0"
".\python\python.exe" avvia.py
