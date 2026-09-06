@echo off
setlocal
cd /d "%~dp0"
if not exist "venv\Scripts\python.exe" (
  echo Virtuelle Umgebung nicht gefunden unter venv\Scripts\python.exe
  echo python -m venv venv
  echo venv\Scripts\pip install -r requirements.txt
  pause
  exit /b 1
)
"venv\Scripts\python.exe" -m server %*
if errorlevel 1 pause
