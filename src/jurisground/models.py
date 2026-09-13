from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

Status = Literal["pass", "fail", "unverified"]


@dataclass(frozen=True)
class Source:
    id: str
    text: str = ""
    pages: tuple[str, ...] = ()
    is_ocr: bool = False

    def page_texts(self) -> tuple[str, ...]:
        return self.pages or (self.text,)


@dataclass(frozen=True)
class Claim:
    id: str
    text: str
    quote: str = ""
    source_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class Policy:
    quote_threshold: float = 0.965
    ocr_quote_threshold: float = 0.90
    min_claim_support: float = 0.42
    min_content_stems_for_support: int = 3
    max_expansion_ratio: float = 1.45
    min_expansion_support: float = 0.72
    min_quote_chars: int = 10
    require_numbers_in_quote: bool = True
    require_numbers_in_source: bool = True


@dataclass
class Finding:
    code: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class ClaimResult:
    claim_id: str
    status: Status
    matched_source_id: str | None = None
    matched_page: int | None = None
    quote_score: float = 0.0
    claim_support: float = 0.0
    source_support: float = 0.0
    claim_numbers: list[str] = field(default_factory=list)
    quote_numbers: list[str] = field(default_factory=list)
    source_numbers: list[str] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
