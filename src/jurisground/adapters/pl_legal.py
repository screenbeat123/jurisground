from __future__ import annotations

import re

from ..normalize import normalize_text

LEGAL_CODE_REPLACEMENTS = (
    (r"\bk\s*\.\s*p\s*\.\s*c\s*\.?", " kpc "),
    (r"\bk\s*\.\s*c\s*\.?", " kc "),
    (r"\bk\s*\.\s*k\s*\.?", " kk "),
    (r"\bk\s*\.\s*p\s*\.?", " kp "),
    (r"\bp\s*\.\s*z\s*\.\s*p\s*\.?", " pzp "),
    (r"§+", " paragraf "),
)


def normalize_polish_legal_text(value: str) -> str:
    value = normalize_text(value)
    for pattern, replacement in LEGAL_CODE_REPLACEMENTS:
        value = re.sub(pattern, replacement, value, flags=re.I)
    return re.sub(r"\s+", " ", value).strip()
