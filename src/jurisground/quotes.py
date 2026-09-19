from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher

from .models import Source
from .normalize import normalize_text, token_text
from .numbers import number_tokens


_MAX_WINDOWS = 900
_REFINEMENT_BUDGET = 160
_MAX_ANCHOR_POSITIONS = 120
_NUMERIC_WINDOW_BUDGET = _MAX_WINDOWS // 3


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


def _sample_evenly(values: list[int] | list[tuple[int, int]], limit: int):
    if limit <= 0 or not values:
        return []
    if len(values) <= limit:
        return list(values)
    if limit == 1:
        return [values[len(values) // 2]]

    sampled = []
    seen = set()
    for index in range(limit):
        position = round(index * (len(values) - 1) / (limit - 1))
        value = values[position]
        if value not in seen:
            sampled.append(value)
            seen.add(value)
    return sampled


def _canonical_integer_token(token: str) -> str | None:
    if not token.isdigit():
        return None
    values = number_tokens(token)
    return values[0] if len(values) == 1 else None


def _numeric_candidate_windows(quote_tokens: list[str], source_tokens: list[str]) -> list[tuple[int, int]]:
    quote_positions: dict[str, list[int]] = {}
    for index, token in enumerate(quote_tokens):
        value = _canonical_integer_token(token)
        if value is not None:
            quote_positions.setdefault(value, []).append(index)

    if not quote_positions:
        return []

    source_positions: dict[str, list[int]] = {value: [] for value in quote_positions}
    for index, token in enumerate(source_tokens):
        value = _canonical_integer_token(token)
        if value in source_positions:
            source_positions[value].append(index)

    groups = [
        (len(positions), value, positions)
        for value, positions in source_positions.items()
        if positions
    ]
    groups.sort(key=lambda item: item[0])

    windows: list[tuple[int, int]] = []
    group_count = max(1, len(groups))
    for _, value, positions in groups:
        quote_indices = quote_positions[value]
        per_quote_limit = max(1, _NUMERIC_WINDOW_BUDGET // (group_count * len(quote_indices)))
        for quote_index in quote_indices:
            for source_index in _sample_evenly(positions, per_quote_limit):
                first = source_index - quote_index
                last = first + len(quote_tokens)
                if first < 0 or last > len(source_tokens) or last - first < 3:
                    continue
                windows.append((first, last))

    deduped = list(dict.fromkeys(windows))
    return deduped[:_NUMERIC_WINDOW_BUDGET]


def _fuzzy_match(source: str, source_spans, source_tokens, target: str, first: int, last: int, score: float) -> _QuoteMatch:
    start = source_spans[first][1]
    end = source_spans[last - 1][2]
    return _QuoteMatch(score=score, start=start, end=end, text=source[start:end], method="fuzzy")


def _boundary_adjustments(radius: int) -> list[int]:
    values = {0, -1, 1}
    step = radius
    while step > 1:
        values.update((-step, step))
        step //= 2
    return sorted(values, key=lambda value: (abs(value), value))


def _refine_fuzzy_match(
    source: str,
    source_spans,
    source_tokens,
    target: str,
    first: int,
    last: int,
    score: float,
    quote_token_count: int,
    budget: int,
) -> tuple[_QuoteMatch, int]:
    best = _fuzzy_match(source, source_spans, source_tokens, target, first, last, score)
    used = 0
    radius = max(2, quote_token_count // 5)
    adjustments = _boundary_adjustments(radius)

    for move_first in (True, False, True, False):
        if used >= budget:
            break
        if move_first:
            choices = adjustments if used < budget // 2 else [-2, -1, 1, 2]
            for delta in choices:
                if delta == 0 or used >= budget:
                    continue
                candidate_first = first + delta
                if candidate_first < 0 or last - candidate_first < 3:
                    continue
                candidate = " ".join(source_tokens[candidate_first:last])
                candidate_score = SequenceMatcher(None, target, candidate).ratio()
                used += 1
                if candidate_score > best.score:
                    first = candidate_first
                    best = _fuzzy_match(source, source_spans, source_tokens, target, first, last, candidate_score)
        else:
            choices = adjustments if used < budget // 2 else [-2, -1, 1, 2]
            for delta in choices:
                if delta == 0 or used >= budget:
                    continue
                candidate_last = last + delta
                if candidate_last > len(source_spans) or candidate_last - first < 3:
                    continue
                candidate = " ".join(source_tokens[first:candidate_last])
                candidate_score = SequenceMatcher(None, target, candidate).ratio()
                used += 1
                if candidate_score > best.score:
                    last = candidate_last
                    best = _fuzzy_match(source, source_spans, source_tokens, target, first, last, candidate_score)

    return best, used


def _fuzzy_matches(quote: str, source: str, limit: int | None) -> list[_QuoteMatch]:
    quote_tokens = token_text(quote).split()
    source_spans = _token_spans(source)
    if len(quote_tokens) < 3 or not source_spans:
        return []

    source_tokens = [token for token, _, _ in source_spans]
    anchor_candidates = {token for token in quote_tokens if len(token) >= 5}
    anchors = sorted(
        anchor_candidates,
        key=lambda token: (source_tokens.count(token), -len(token), token),
    )[:4]
    all_positions = [i for i, token in enumerate(source_tokens) if token in anchors]
    positions = _sample_evenly(all_positions, _MAX_ANCHOR_POSITIONS)
    n = len(quote_tokens)

    priority_candidates = _numeric_candidate_windows(quote_tokens, source_tokens)
    coverage_candidates: list[tuple[int, int]] = []

    for pos in positions:
        lo = max(0, pos - n)
        hi = min(len(source_spans), pos + 2 * n)
        sizes = {max(3, int(n * 0.8)), n, int(n * 1.2) + 1}
        for size in sizes:
            step = max(1, n // 5)
            for off in range(lo, max(lo + 1, hi - size + 1), step):
                coverage_candidates.append((off, min(len(source_spans), off + size)))

    if not coverage_candidates:
        step = max(1, n // 3)
        coverage_candidates = [
            (i, min(len(source_spans), i + n))
            for i in range(0, max(1, len(source_spans) - n + 1), step)
        ]

    priority_candidates = list(dict.fromkeys(priority_candidates))
    priority_set = set(priority_candidates)
    coverage_candidates = [
        bounds for bounds in dict.fromkeys(coverage_candidates)
        if bounds not in priority_set
    ]

    priority_candidates = priority_candidates[:_NUMERIC_WINDOW_BUDGET]
    remaining = _MAX_WINDOWS - len(priority_candidates)
    selected_candidates = priority_candidates + _sample_evenly(coverage_candidates, remaining)

    target = " ".join(quote_tokens)
    scored: list[tuple[float, int, int]] = []
    for first, last in selected_candidates:
        candidate = " ".join(source_tokens[first:last])
        score = SequenceMatcher(None, target, candidate).ratio()
        scored.append((score, first, last))
        if limit == 1 and score >= 0.985:
            break

    if not scored:
        return []

    separation = max(2, n // 2)
    seeds: list[tuple[float, int, int]] = []
    for score, first, last in sorted(scored, reverse=True):
        if any(abs(first - seed_first) < separation for _, seed_first, _ in seeds):
            continue
        seeds.append((score, first, last))
        if limit is not None and len(seeds) >= limit:
            break

    remaining_budget = _REFINEMENT_BUDGET
    refined: list[_QuoteMatch] = []
    refine_count = min(len(seeds), 8)
    for index, (score, first, last) in enumerate(seeds):
        if index < refine_count:
            seed_count_left = refine_count - index
            budget = remaining_budget // seed_count_left if seed_count_left else 0
            match, used = _refine_fuzzy_match(
                source, source_spans, source_tokens, target, first, last, score, n, budget,
            )
            remaining_budget -= used
        else:
            match = _fuzzy_match(source, source_spans, source_tokens, target, first, last, score)
        refined.append(match)

    return sorted(refined, key=lambda match: match.score, reverse=True)


def _match_texts(quote: str, source: str, limit: int | None = 1) -> list[_QuoteMatch]:
    q = normalize_text(quote)
    s = normalize_text(source)
    if len(q) < 10 or not s:
        return []

    start = source.find(quote)
    if start >= 0:
        end = start + len(quote)
        return [_QuoteMatch(score=1.0, start=start, end=end, text=source[start:end], method="exact")]

    normalized_source, offsets = _normalized_with_offsets(source)
    pos = normalized_source.find(q)
    if pos >= 0:
        start = offsets[pos]
        end = offsets[pos + len(q) - 1] + 1
        return [_QuoteMatch(score=1.0, start=start, end=end, text=source[start:end], method="normalized")]

    return _fuzzy_matches(quote, source, limit)


def _match_text(quote: str, source: str) -> _QuoteMatch:
    matches = _match_texts(quote, source)
    return matches[0] if matches else _QuoteMatch()


def quote_similarity(quote: str, source: str) -> float:
    return _match_text(quote, source).score


def quote_matches(quote: str, sources: list[Source], per_page_limit: int | None = 1) -> list[_QuoteMatch]:
    matches: list[_QuoteMatch] = []
    for source in sources:
        for page_index, page_text in enumerate(source.page_texts(), start=1):
            for match in _match_texts(quote, page_text, per_page_limit):
                if match.text is None:
                    continue
                matches.append(_QuoteMatch(
                    source_id=source.id,
                    page=page_index,
                    score=match.score,
                    start=match.start,
                    end=match.end,
                    text=match.text,
                    method=match.method,
                ))
    return sorted(matches, key=lambda match: match.score, reverse=True)


def best_quote_match(quote: str, sources: list[Source]) -> _QuoteMatch:
    matches = quote_matches(quote, sources)
    return matches[0] if matches else _QuoteMatch()
