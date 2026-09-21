from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class PolishLegalCitation:
    raw: str
    start: int
    end: int
    article: str
    paragraph: str | None = None
    subsection: str | None = None
    point: str | None = None
    letter: str | None = None
    act: str | None = None


_NUMBER = r"\d+[a-z]*"
_LETTER = r"[a-z]{1,2}"
_ACT = r"(?:p\.p\.s\.a\.|k\.k\.s\.|k\.p\.c\.|k\.p\.k\.|k\.r\.o\.|k\.s\.h\.|k\.c\.|k\.k\.|k\.p\.)"

_CITATION_RE = re.compile(
    rf"(?<!\w)art\.\s*(?P<article>{_NUMBER})"
    rf"(?:\s*§\s*(?P<paragraph>{_NUMBER}))?"
    rf"(?:\s+ust\.\s*(?P<subsection>{_NUMBER}))?"
    rf"(?:\s+pkt\s*(?P<point>{_NUMBER}))?"
    rf"(?:\s+lit\.\s*(?P<letter>{_LETTER}))?"
    rf"(?:\s+(?P<act>{_ACT}))?",
    re.IGNORECASE,
)

_UNSUPPORTED_CONTINUATION_RE = re.compile(
    r"\w|\s*[-–—−]\s*\d|\s*(?:§|ust\.|pkt\b|lit\.)",
    re.IGNORECASE,
)
_SUFFIX_RANGE_RE = re.compile(
    r"(?P<separator>\s*[-–—−]\s*)(?!art\.)(?P<suffix>[a-z]+)(?!\w)",
    re.IGNORECASE,
)


def parse_polish_citations(text: str) -> list[PolishLegalCitation]:
    citations: list[PolishLegalCitation] = []
    for match in _CITATION_RE.finditer(text):
        start, end = match.span()
        # Validate after matching so rejection cannot backtrack into a shorter unit.
        if _UNSUPPORTED_CONTINUATION_RE.match(text, end):
            continue
        suffix_range = _SUFFIX_RANGE_RE.match(text, end)
        if suffix_range and match.lastgroup != "act":
            unit = match.group(match.lastgroup)
            suffix_length = 2 if match.lastgroup == "letter" else sum(char.isalpha() for char in unit)
            if len(suffix_range.group("separator")) == 1 or len(suffix_range.group("suffix")) <= suffix_length:
                continue
        citations.append(
            PolishLegalCitation(
                raw=text[start:end],
                start=start,
                end=end,
                article=match.group("article").lower(),
                paragraph=_lower(match.group("paragraph")),
                subsection=_lower(match.group("subsection")),
                point=_lower(match.group("point")),
                letter=_lower(match.group("letter")),
                act=_normalize_act(match.group("act")),
            )
        )
    return citations


def _citation_fields(citation: PolishLegalCitation) -> dict[str, str | None]:
    return {
        "article": citation.article,
        "paragraph": citation.paragraph,
        "subsection": citation.subsection,
        "point": citation.point,
        "letter": citation.letter,
        "act": citation.act,
    }


def _citation_mismatches(claim: PolishLegalCitation, evidence: PolishLegalCitation) -> list[str]:
    evidence_fields = _citation_fields(evidence)
    return [
        field
        for field, expected in _citation_fields(claim).items()
        if expected is not None and expected != evidence_fields[field]
    ]


def _lower(value: str | None) -> str | None:
    return value.lower() if value else None


def _normalize_act(value: str | None) -> str | None:
    if not value:
        return None
    return value.lower().replace(" ", "")
