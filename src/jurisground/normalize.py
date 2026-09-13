from __future__ import annotations

import re
import unicodedata

_GENERIC_STOPWORDS = {
    "and", "the", "that", "this", "with", "from", "into", "than", "then", "for", "are", "was",
    "were", "has", "have", "had", "not", "but", "or", "of", "to", "in", "on", "a", "an", "is",
    "oraz", "który", "która", "które", "tego", "tej", "tych", "jest", "był", "była", "było",
    "został", "została", "zostało", "przez", "dla", "jako", "jego", "jej", "wobec", "zgodnie",
    "należy", "może", "powinien", "powinna", "brak", "danych", "informacji", "przy", "albo", "jednak",
}


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKC", value or "")
    value = value.replace("\u00ad", "").replace("\u00a0", " ").replace("\u202f", " ")
    return re.sub(r"\s+", " ", value.casefold()).strip()


def token_text(value: str) -> str:
    value = normalize_text(value)
    chars = []
    for ch in value:
        chars.append(ch if (ch.isalnum() or ch in "_-") else " ")
    return re.sub(r"\s+", " ", "".join(chars)).strip()


def content_tokens(value: str) -> list[str]:
    out: list[str] = []
    for token in token_text(value).split():
        if token in _GENERIC_STOPWORDS:
            continue
        if token.isdigit():
            out.append(token)
        elif len(token) >= 3:
            out.append(token)
    return out


def content_stems(value: str) -> list[str]:
    out = []
    for token in content_tokens(value):
        out.append(token if token.isdigit() else (token[:5] if len(token) >= 5 else token))
    return out
