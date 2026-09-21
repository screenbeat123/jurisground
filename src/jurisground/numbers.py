from __future__ import annotations

import re


_SPACE = r"[ \t\u00a0\u202f]"
_SPACE_RE = re.compile(_SPACE)
_NUMBER_RE = re.compile(
    rf"(?<![\w+\-\u2212])(?P<sign>[+\-\u2212]?)(?P<body>"
    rf"(?:\d{{1,3}}(?:{_SPACE}\d{{3}})+(?:[.,]\d+)?"
    rf"|\d{{1,3}}(?:,\d{{3}})+\.\d+"
    rf"|\d{{1,3}}(?:\.\d{{3}})+,\d+"
    rf"|\d{{1,3}}(?:,\d{{3}}){{2,}}"
    rf"|\d{{1,3}}(?:\.\d{{3}}){{2,}}"
    rf"|\d+(?:[.,]\d+)?"
    rf"))(?![\w]|[.,]\d)"
)


def _with_sign(value: str, negative: bool) -> str:
    digits = [char for char in value if char.isdigit()]
    nonzero = any(char != "0" for char in digits)
    return ("-" if negative and nonzero else "") + value


def _canonical_number(sign: str, body: str) -> str:
    negative = sign in {"-", "\u2212"}
    had_space_groups = bool(_SPACE_RE.search(body))
    compact = _SPACE_RE.sub("", body)
    commas = compact.count(",")
    dots = compact.count(".")

    if commas and dots:
        decimal_sep = "," if compact.rfind(",") > compact.rfind(".") else "."
        group_sep = "." if decimal_sep == "," else ","
        integer_part, fraction = compact.rsplit(decimal_sep, 1)
        integer = integer_part.replace(group_sep, "").lstrip("0") or "0"
        fraction = fraction.rstrip("0")
        value = integer + (f".{fraction}" if fraction else "")
        return _with_sign(value, negative)

    separator = "," if commas else "." if dots else None
    if separator is None:
        integer = compact.lstrip("0") or "0"
        return _with_sign(integer, negative)

    if compact.count(separator) > 1:
        integer = compact.replace(separator, "").lstrip("0") or "0"
        return _with_sign(integer, negative)

    integer_part, fraction = compact.split(separator, 1)
    integer = integer_part.lstrip("0") or "0"

    if had_space_groups or len(fraction) != 3:
        fraction = fraction.rstrip("0")
        value = integer + (f".{fraction}" if fraction else "")
        return _with_sign(value, negative)

    # A single punctuation separator followed by exactly three digits is
    # locale-sensitive (for example 12,500 or 12.500). Keep the separator
    # instead of guessing whether it is a decimal or thousands marker.
    if integer == "0" and not any(char != "0" for char in fraction):
        return "0"
    value = f"{integer}{separator}{fraction}"
    return _with_sign(value, negative)


def number_tokens(value: str) -> list[str]:
    tokens: list[str] = []
    for match in _NUMBER_RE.finditer(str(value or "")):
        tokens.append(_canonical_number(match.group("sign"), match.group("body")))
    return tokens


def _number_spans(value: str) -> list[tuple[int, int]]:
    return [match.span() for match in _NUMBER_RE.finditer(value)]
