"""Versteckte Medien: nicht in der Wall-Liste, Datei bleibt gespeichert."""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import HTTPException

from server.project import ProjectPaths, safe_join


def hidden_path(paths: ProjectPaths) -> Path:
    return paths.root / "hidden.json"


def load_hidden(paths: ProjectPaths) -> set[str]:
    path = hidden_path(paths)
    if not path.is_file():
        return set()
    try:
        with path.open(encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return set()
    names = data.get("files") if isinstance(data, dict) else data
    if not isinstance(names, list):
        return set()
    out = set()
    for raw in names:
        name = str(raw or "").strip()
        if name and name == Path(name).name and name not in (".", ".."):
            out.add(name)
    return out


def save_hidden(paths: ProjectPaths, names: set[str]) -> None:
    paths.root.mkdir(parents=True, exist_ok=True)
    payload = {"files": sorted(names)}
    with hidden_path(paths).open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
        f.write("\n")


def is_hidden(paths: ProjectPaths, original_name: str) -> bool:
    return original_name in load_hidden(paths)


def set_hidden(paths: ProjectPaths, original_name: str, hidden: bool) -> bool:
    original = safe_join(paths.media, original_name)
    if original is None or not original.is_file():
        raise HTTPException(status_code=404, detail="Datei nicht gefunden.")
    names = load_hidden(paths)
    name = original.name
    if hidden:
        names.add(name)
    else:
        names.discard(name)
        stem = Path(name).stem
        names = {n for n in names if Path(n).stem != stem}
    save_hidden(paths, names)
    return hidden


def set_hidden_many(paths: ProjectPaths, original_names: list[str], hidden: bool) -> list[str]:
    names = load_hidden(paths)
    done: list[str] = []
    for raw in original_names:
        original = safe_join(paths.media, raw)
        if original is None or not original.is_file():
            continue
        name = original.name
        if hidden:
            names.add(name)
        else:
            names.discard(name)
            stem = Path(name).stem
            names = {n for n in names if Path(n).stem != stem}
        if name not in done:
            done.append(name)
    save_hidden(paths, names)
    return done


def drop_hidden(paths: ProjectPaths, original_name: str) -> None:
    names = load_hidden(paths)
    names.discard(original_name)
    stem = Path(original_name).stem
    names = {n for n in names if Path(n).stem != stem}
    save_hidden(paths, names)
