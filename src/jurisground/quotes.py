from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher

from .models import Source
from .normalize import normalize_text, token_text


@dataclass(frozen=True)
class _QuoteMatch:
    source_id: str | None = None
    page: int | None = None
    score: float = 0.0
    start: int | None = None
    end: int | None = None
    text: str | None = None
    method: str | None = None


def _normalized_with_offsets(value: str) -> tuple[str, list[int]]:
    chars: list[str] = []
    offsets: list[int] = []
    pending_space: int | None = None

    for index, char in enumerate(value):
        piece = unicodedata.normalize("NFKC", char)
        piece = piece.replace("\u00ad", "").replace("\u00a0", " ").replace("\u202f", " ").casefold()
        for out in piece:
            if out.isspace():
                if chars and chars[-1] != " " and pending_space is None:
                    pending_space = index
                continue
            if pending_space is not None:
                chars.append(" ")
                offsets.append(pending_space)
                pending_space = None
            chars.append(out)
            offsets.append(index)

    return "".join(chars), offsets


def _token_spans(value: str) -> list[tuple[str, int, int]]:
    spans: list[tuple[str, int, int]] = []
    for match in re.finditer(r"[\w-]+", value, flags=re.UNICODE):
        for token in token_text(match.group(0)).split():
            spans.append((token, match.start(), match.end()))
    return spans


def _match_text(quote: str, source: str) -> _QuoteMatch:
    q = normalize_text(quote)
    s = normalize_text(source)
    if len(q) < 10 or not s:
        return _QuoteMatch()

    start = source.find(quote)
    if start >= 0:
        end = start + len(quote)
        return _QuoteMatch(score=1.0, start=start, end=end, text=source[start:end], method="exact")

    normalized_source, offsets = _normalized_with_offsets(source)
    pos = normalized_source.find(q)
    if pos >= 0:
        start = offsets[pos]
        end = offsets[pos + len(q) - 1] + 1
        return _QuoteMatch(score=1.0, start=start, end=end, text=source[start:end], method="normalized")

    quote_tokens = token_text(quote).split()
    source_spans = _token_spans(source)
    if len(quote_tokens) < 3 or not source_spans:
        return _QuoteMatch()

    source_tokens = [token for token, _, _ in source_spans]
    anchors = sorted({token for token in quote_tokens if len(token) >= 5}, key=len, reverse=True)[:4]
    positions = [i for i, token in enumerate(source_tokens) if token in anchors]
    n = len(quote_tokens)
    candidates: list[tuple[int, int]] = []

    for pos in positions[:120]:
        lo = max(0, pos - n)
        hi = min(len(source_spans), pos + 2 * n)
        sizes = {max(3, int(n * 0.8)), n, int(n * 1.2) + 1}
        for size in sizes:
            step = max(1, n // 5)
            for off in range(lo, max(lo + 1, hi - size + 1), step):
                candidates.append((off, min(len(source_spans), off + size)))

    if not candidates:
        step = max(1, n // 3)
        candidates = [(i, min(len(source_spans), i + n)) for i in range(0, max(1, len(source_spans) - n + 1), step)]

    target = " ".join(quote_tokens)
    best = _QuoteMatch()
    for first, last in candidates[:900]:
        candidate = " ".join(source_tokens[first:last])
        score = SequenceMatcher(None, target, candidate).ratio()
        if score > best.score:
            start = source_spans[first][1]
            end = source_spans[last - 1][2]
            best = _QuoteMatch(score=score, start=start, end=end, text=source[start:end], method="fuzzy")
        if best.score >= 0.985:
            break
    return best


def quote_similarity(quote: str, source: str) -> float:
    return _match_text(quote, source).score


def best_quote_match(quote: str, sources: list[Source]) -> _QuoteMatch:
    best = _QuoteMatch()
    for source in sources:
        for page_index, page_text in enumerate(source.page_texts(), start=1):
            match = _match_text(quote, page_text)
            if match.score > best.score:
                best = _QuoteMatch(
                    source_id=source.id,
                    page=page_index,
                    score=match.score,
                    start=match.start,
                    end=match.end,
                    text=match.text,
                    method=match.method,
                )
    return best
