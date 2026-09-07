#!/bin/sh
set -e
cd "$(dirname "$0")"

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "Kein Git-Arbeitsverzeichnis."
  exit 1
fi

git fetch origin
git checkout main
git pull --ff-only origin main

if [ -x "venv/bin/pip" ]; then
  venv/bin/pip install -r requirements.txt
elif [ -x "venv/bin/pip3" ]; then
  venv/bin/pip3 install -r requirements.txt
else
  echo "venv nicht gefunden. python3 -m venv venv && venv/bin/pip install -r requirements.txt"
  exit 1
fi

echo "Code und Abhängigkeiten sind aktuell. data/ und projects/ bleiben unverändert."

if command -v systemctl >/dev/null 2>&1; then
  if systemctl is-active --quiet photo-frame 2>/dev/null \
      || sudo -n systemctl is-active --quiet photo-frame 2>/dev/null; then
    if systemctl restart photo-frame 2>/dev/null \
        || sudo -n systemctl restart photo-frame 2>/dev/null; then
      echo "Dienst photo-frame neu gestartet."
    else
      echo "Dienst konnte nicht neu gestartet werden. Manuell: sudo systemctl restart photo-frame"
    fi
  else
    echo "Server neu starten: laufenden Prozess beenden, dann ./start.sh"
  fi
else
  echo "Server neu starten: laufenden Prozess beenden, dann ./start.sh"
fi
