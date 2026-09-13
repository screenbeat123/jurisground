from __future__ import annotations

from .normalize import content_stems


def claim_support(claim: str, evidence: str) -> float:
    claim_tokens = content_stems(claim)
    evidence_tokens = set(content_stems(evidence))
    if not claim_tokens:
        return 0.0
    supported = sum(1 for token in claim_tokens if token in evidence_tokens)
    return supported / len(claim_tokens)
