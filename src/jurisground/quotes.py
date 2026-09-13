from __future__ import annotations

from difflib import SequenceMatcher

from .models import Source
from .normalize import normalize_text, token_text


def quote_similarity(quote: str, source: str) -> float:
    q = normalize_text(quote)
    s = normalize_text(source)
    if len(q) < 10 or not s:
        return 0.0
    if q in s:
        return 1.0

    qt = token_text(quote).split()
    st = token_text(source).split()
    if len(qt) < 3 or not st:
        return 0.0

    anchors = sorted({t for t in qt if len(t) >= 5}, key=len, reverse=True)[:4]
    positions = [i for i, token in enumerate(st) if token in anchors]
    n = len(qt)
    candidates: list[str] = []
    for pos in positions[:120]:
        start = max(0, pos - n)
        end = min(len(st), pos + 2 * n)
        sizes = {max(3, int(n * 0.8)), n, int(n * 1.2) + 1}
        for size in sizes:
            step = max(1, n // 5)
            for off in range(start, max(start + 1, end - size + 1), step):
                candidates.append(" ".join(st[off:off + size]))
    if not candidates:
        step = max(1, n // 3)
        candidates = [" ".join(st[i:i + n]) for i in range(0, max(1, len(st) - n + 1), step)]

    target = " ".join(qt)
    best = 0.0
    for candidate in candidates[:900]:
        best = max(best, SequenceMatcher(None, target, candidate).ratio())
        if best >= 0.985:
            break
    return best


def best_quote_match(quote: str, sources: list[Source]) -> tuple[str | None, int | None, float]:
    best_source: str | None = None
    best_page: int | None = None
    best_score = 0.0
    for source in sources:
        for page_index, page_text in enumerate(source.page_texts(), start=1):
            score = quote_similarity(quote, page_text)
            if score > best_score:
                best_source = source.id
                best_page = page_index
                best_score = score
    return best_source, best_page, best_score
