@echo off
rem Cielo del Mese - avvio (relocabile).
rem %~dp0 = la cartella di questo file, ovunque sia stata copiata.
rem avvia.py trova una porta libera da solo e apre il browser su quella.
rem Per chiudere l'app: chiudi questa finestra.
rem Nel pacchetto c'e' il Python portatile in .\python; nel repo no: li' si usa
rem quello di sistema. Stesso file per entrambi.
cd /d "%~dp0"
if exist ".\python\python.exe" (
    ".\python\python.exe" avvia.py
) else (
    python avvia.py
)
rem Se l'avvio fallisce la finestra resta aperta: l'errore si deve poter leggere.
if errorlevel 1 pause
