"""Startet Uvicorn mit Host/Port aus Runtime oder CLI."""
from __future__ import annotations

import argparse
import os

import uvicorn

from server.paths import BASE_DIR, ensure_data_dir
from server.restart import clear_skip_restart, set_listen
from server.runtime import load_runtime


def main() -> None:
    clear_skip_restart()
    ensure_data_dir()
    os.chdir(BASE_DIR)
    rt = load_runtime()
    parser = argparse.ArgumentParser(description="Local-browser-based-Photo-Frame")
    parser.add_argument("--host", default=None, help="Bind-Adresse. Default 0.0.0.0 aus Runtime.")
    parser.add_argument("--port", type=int, default=None, help="TCP-Port. Default aus Runtime.")
    args = parser.parse_args()
    host = args.host or rt.get("bind_host") or "0.0.0.0"
    port = args.port or int(rt.get("port", 8000))
    set_listen(host, port, cli_host=args.host)
    print(f"Listening on http://{host}:{port}")
    uvicorn.run("server.main:app", host=host, port=port)


if __name__ == "__main__":
    main()
