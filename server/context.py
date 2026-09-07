"""Aktuelles Projekt für die laufende Anfrage (Listen-Port oder Pfad-Prefix)."""
from contextvars import ContextVar, Token

current_project: ContextVar[str | None] = ContextVar("current_project", default=None)
url_prefix: ContextVar[str] = ContextVar("url_prefix", default="")


def set_current_project(name: str | None) -> Token:
    return current_project.set(name)


def reset_current_project(token: Token) -> None:
    current_project.reset(token)


def get_current_project() -> str | None:
    return current_project.get()


def set_url_prefix(prefix: str) -> Token:
    return url_prefix.set(prefix or "")


def reset_url_prefix(token: Token) -> None:
    url_prefix.reset(token)


def get_url_prefix() -> str:
    return url_prefix.get() or ""
