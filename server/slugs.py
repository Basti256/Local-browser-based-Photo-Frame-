"""Reservierte URL-Segmente und Projekt-Slugs."""
from __future__ import annotations

RESERVED_SEGMENTS = frozenset({
    "setup",
    "login",
    "logout",
    "admin",
    "wall",
    "upload",
    "api",
    "media",
    "derived",
    "header",
    "background",
    "p",
    "ws",
    "static",
    "assets",
    "sw.js",
    "favicon.ico",
    "robots.txt",
})


def is_reserved_segment(segment: str) -> bool:
    return (segment or "").strip().lower() in RESERVED_SEGMENTS
