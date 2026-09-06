"""Aktuelles Projekt für die laufende Anfrage (Listen-Port)."""
from contextvars import ContextVar, Token

current_project: ContextVar[str | None] = ContextVar("current_project", default=None)


def set_current_project(name: str | None) -> Token:
    return current_project.set(name)


def reset_current_project(token: Token) -> None:
    current_project.reset(token)


def get_current_project() -> str | None:
    return current_project.get()
