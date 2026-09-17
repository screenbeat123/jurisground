from __future__ import annotations

from .claims import claim_support
from .legal import _citation_fields, _citation_mismatches, parse_polish_citations
from .models import Claim, ClaimResult, Finding, Policy, Source
from .normalize import content_stems, normalize_text
from .numbers import number_tokens
from .quotes import best_quote_match


def _source_map(sources: list[Source]) -> dict[str, Source]:
    return {source.id: source for source in sources}


def verify_claim(claim: Claim, sources: list[Source], policy: Policy | None = None) -> ClaimResult:
    policy = policy or Policy()
    source_by_id = _source_map(sources)
    findings: list[Finding] = []

    if not normalize_text(claim.text):
        findings.append(Finding("empty_claim", "Claim text is empty after normalization."))
        return ClaimResult(claim.id, "unverified", findings=findings)
    if not content_stems(claim.text):
        findings.append(Finding("no_claim_content", "Claim has no usable tokens for lexical comparison."))
        return ClaimResult(claim.id, "unverified", findings=findings)

    if not claim.source_ids:
        findings.append(Finding("missing_source_ids", "Claim has no cited source IDs."))
        return ClaimResult(claim.id, "unverified", findings=findings)

    cited = [source_by_id[source_id] for source_id in claim.source_ids if source_id in source_by_id]
    missing = [source_id for source_id in claim.source_ids if source_id not in source_by_id]
    if missing:
        findings.append(Finding("unknown_source_id", "One or more cited source IDs are unavailable.", details={"ids": missing}))
    if not cited:
        return ClaimResult(claim.id, "unverified", findings=findings)

    if len(claim.quote.strip()) < policy.min_quote_chars:
        findings.append(Finding("quote_too_short", "Quote is missing or too short to verify."))
        return ClaimResult(claim.id, "unverified", findings=findings)

    match = best_quote_match(claim.quote, cited)
    matched_source = source_by_id.get(match.source_id or "")
    quote_threshold = policy.ocr_quote_threshold if (matched_source and matched_source.is_ocr) else policy.quote_threshold
    quote_verified = match.score >= quote_threshold
    if not quote_verified:
        findings.append(Finding(
            "quote_not_found",
            "The quoted text could not be verified in the cited source material.",
            details={"score": round(match.score, 3), "threshold": quote_threshold},
        ))

    claim_legal_citation = None
    evidence_legal_citation = None
    if policy.require_legal_citation_match and quote_verified:
        claim_citations = parse_polish_citations(claim.text)
        if not claim_citations:
            findings.append(Finding(
                "legal_citation_missing",
                "The claim has no supported Polish statutory citation to bind to evidence.",
            ))
        elif len(claim_citations) > 1:
            findings.append(Finding(
                "legal_citation_ambiguous",
                "The claim contains more than one Polish statutory citation.",
                details={"citations": [citation.raw for citation in claim_citations]},
            ))
        else:
            claim_citation = claim_citations[0]
            claim_legal_citation = _citation_fields(claim_citation)
            if not matched_source or not matched_source.legal_citation:
                findings.append(Finding(
                    "legal_evidence_citation_missing",
                    "The matched source has no legal-citation metadata.",
                ))
            else:
                evidence_citations = parse_polish_citations(matched_source.legal_citation)
                if len(evidence_citations) != 1:
                    findings.append(Finding(
                        "legal_evidence_citation_invalid",
                        "The matched source legal-citation metadata must contain exactly one supported citation.",
                        details={"value": matched_source.legal_citation},
                    ))
                else:
                    evidence_citation = evidence_citations[0]
                    evidence_legal_citation = _citation_fields(evidence_citation)
                    mismatches = _citation_mismatches(claim_citation, evidence_citation)
                    if mismatches:
                        findings.append(Finding(
                            "legal_citation_mismatch",
                            "The claim citation does not match the legal unit attached to the evidence.",
                            details={
                                "fields": mismatches,
                                "claim": claim_legal_citation,
                                "evidence": evidence_legal_citation,
                            },
                        ))

    source_corpus = "\n".join("\n".join(source.page_texts()) for source in cited)
    quote_support = claim_support(claim.text, claim.quote)
    source_support = claim_support(claim.text, source_corpus)

    claim_numbers = number_tokens(claim.text)
    quote_numbers = number_tokens(claim.quote)
    source_numbers = number_tokens(source_corpus)
    quote_number_set = set(quote_numbers)
    source_number_set = set(source_numbers)

    if policy.require_numbers_in_quote:
        missing_quote_numbers = [n for n in claim_numbers if n not in quote_number_set]
        if missing_quote_numbers:
            findings.append(Finding(
                "number_not_in_quote",
                "A numeric fact in the claim is not present in the supporting quote.",
                details={"numbers": missing_quote_numbers},
            ))
    if policy.require_numbers_in_source:
        missing_source_numbers = [n for n in claim_numbers if n not in source_number_set]
        if missing_source_numbers:
            findings.append(Finding(
                "number_not_in_source",
                "A numeric fact in the claim is not present in the cited source material.",
                details={"numbers": missing_source_numbers},
            ))

    if quote_support == 0.0 or quote_support < policy.min_claim_support:
        findings.append(Finding(
            "claim_not_supported",
            "The claim has insufficient lexical support in the cited quote.",
            details={"support": round(quote_support, 3), "threshold": policy.min_claim_support},
        ))

    if (
        len(claim.text) > max(120, len(claim.quote) * policy.max_expansion_ratio)
        and quote_support < policy.min_expansion_support
    ):
        findings.append(Finding(
            "claim_expands_quote",
            "The claim materially expands beyond the cited quotation.",
            details={"support": round(quote_support, 3)},
        ))

    status = "fail" if findings else "pass"
    return ClaimResult(
        claim_id=claim.id,
        status=status,
        matched_source_id=match.source_id,
        matched_page=match.page,
        quote_score=round(match.score, 3),
        matched_text=match.text if quote_verified else None,
        matched_start=match.start if quote_verified else None,
        matched_end=match.end if quote_verified else None,
        match_method=match.method if quote_verified else None,
        claim_support=round(quote_support, 3),
        source_support=round(source_support, 3),
        claim_numbers=claim_numbers,
        quote_numbers=quote_numbers,
        source_numbers=source_numbers,
        claim_legal_citation=claim_legal_citation,
        evidence_legal_citation=evidence_legal_citation,
        findings=findings,
    )


def verify_batch(claims: list[Claim], sources: list[Source], policy: Policy | None = None) -> dict:
    if not claims:
        return {
            "status": "unverified",
            "summary": {"total": 0, "pass": 0, "fail": 0, "unverified": 0},
            "claims": [],
        }

    results = [verify_claim(claim, sources, policy) for claim in claims]
    if any(result.status == "fail" for result in results):
        status = "fail"
    elif any(result.status == "unverified" for result in results):
        status = "unverified"
    else:
        status = "pass"
    return {
        "status": status,
        "summary": {
            "total": len(results),
            "pass": sum(result.status == "pass" for result in results),
            "fail": sum(result.status == "fail" for result in results),
            "unverified": sum(result.status == "unverified" for result in results),
        },
        "claims": [result.to_dict() for result in results],
    }
