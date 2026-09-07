"""Zufallstexte für Debug-Uploads. Kein Sinn, inkl. Smileys und Symbole."""
from __future__ import annotations

import random

WORDS = (
    "Zappelbirne",
    "Mondsocke",
    "Kicherlampe",
    "Wolkenkuchen",
    "Flitzkeks",
    "Nebeltoast",
    "Glitzerstein",
    "Quatschmond",
    "Hoppeltee",
    "Funkelsuppe",
    "Knisterboot",
    "Schlummerstern",
    "Wackelpanda",
    "Bummelfloh",
    "Zitronenklang",
    "Pfannenzauber",
    "Kirmeswolke",
    "Tautropfen",
    "Rumpelkiste",
    "Sonnensalat",
)

FACES = (
    "😀",
    "😂",
    "🥳",
    "😎",
    "🤩",
    "😍",
    "🤪",
    "😜",
    "🤗",
    "😇",
)

ICONS = (
    "🎉",
    "❤️",
    "⭐",
    "🌈",
    "🚀",
    "🍀",
    "🔥",
    "🎈",
    "🌸",
    "✨",
    "🍕",
    "🐱",
    "🎵",
    "☀️",
    "💫",
    "🦄",
    "👍",
    "💖",
    "★",
    "♥",
    "♪",
    "✿",
    "☀",
    "☁",
    "⚡",
    "✓",
)


def _clip(text: str, max_len: int) -> str:
    chars = list(text or "")
    return "".join(chars[:max_len])


def generate_random_comment(max_len: int) -> str:
    try:
        max_len = int(max_len)
    except (TypeError, ValueError):
        max_len = 80
    max_len = max(1, min(500, max_len))
    tokens: list[str] = []
    for _ in range(random.randint(1, 6)):
        tokens.append(random.choice(WORDS))
    for _ in range(random.randint(1, 3)):
        tokens.append(random.choice(FACES))
    for _ in range(random.randint(1, 3)):
        tokens.append(random.choice(ICONS))
    random.shuffle(tokens)
    text = ""
    for tok in tokens:
        candidate = tok if not text else f"{text} {tok}"
        if len(list(candidate)) <= max_len:
            text = candidate
        elif not text:
            text = _clip(tok, max_len)
            break
        else:
            break
    if not text:
        text = _clip("★😀", max_len)
    return _clip(text, max_len)
