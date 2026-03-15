@echo off
setlocal
REM in den Projektordner wechseln (Ordner, in dem diese BAT liegt)
cd /d "%~dp0"
REM prüfen, ob venv vorhanden ist
if not exist "venv\Scripts\python.exe" (
    echo Virtuelle Umgebung nicht gefunden unter venv\Scripts\python.exe
    echo Bitte zuerst dein venv anlegen/aktivieren.
    pause
    exit /b 1
)
REM Server-GUI mit Python aus dem venv starten
"venv\Scripts\python.exe" gui\server_gui.py
REM Fenster offen halten, damit du Fehlermeldungen siehst
pause