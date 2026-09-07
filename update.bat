@echo off
setlocal
cd /d "%~dp0"

git rev-parse --is-inside-work-tree >nul 2>&1
if errorlevel 1 (
  echo Kein Git-Arbeitsverzeichnis.
  pause
  exit /b 1
)

git fetch origin
git checkout main
git pull --ff-only origin main
if errorlevel 1 (
  echo git pull fehlgeschlagen. Keine lokalen Commits auf dem Live-System mischen.
  pause
  exit /b 1
)

if not exist "venv\Scripts\pip.exe" (
  echo venv nicht gefunden.
  echo python -m venv venv
  echo venv\Scripts\pip install -r requirements.txt
  pause
  exit /b 1
)

"venv\Scripts\pip.exe" install -r requirements.txt
if errorlevel 1 (
  echo pip install fehlgeschlagen.
  pause
  exit /b 1
)

echo Code und Abhaengigkeiten sind aktuell. data/ und projects/ bleiben unveraendert.
echo Server neu starten: laufenden Prozess beenden, dann start.bat
pause
