#!/bin/sh
set -e
cd "$(dirname "$0")"
if [ ! -x "venv/bin/python" ]; then
  echo "Virtuelle Umgebung nicht gefunden unter venv/bin/python"
  echo "python3 -m venv venv && venv/bin/pip install -r requirements.txt"
  exit 1
fi
exec venv/bin/python -m server "$@"
