from __future__ import annotations

import re

_NUMBER_RE = re.compile(
    r"(?<!\w)(?:\d{1,3}(?:[ \t\u00a0\u202f]\d{3})+|\d+)(?:[.,]\d+)?(?!\w)"
)


def number_tokens(value: str) -> list[str]:
    tokens: list[str] = []
    for match in _NUMBER_RE.finditer(str(value or "")):
        token = re.sub(r"[ \t\u00a0\u202f]", "", match.group(0)).replace(",", ".")
        integer, separator, fraction = token.partition(".")
        integer = integer.lstrip("0") or "0"
        if separator:
            fraction = fraction.rstrip("0")
        tokens.append(integer + (f".{fraction}" if fraction else ""))
    return tokens
