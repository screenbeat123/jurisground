import pytest

from jurisground import ClaimResult
from jurisground.models import Finding


def test_v020_positional_result_preserves_fields_and_serialized_findings():
    finding = Finding("number_not_in_source", "Missing number", {"numbers": ["200"]})
    result = ClaimResult(
        "C", "fail", "S", 2, 0.98, "Amount 100", 4, 14, "fuzzy",
        0.8, 0.7, ["200"], ["100"], ["100", "300"], [finding],
    )

    assert result.findings == [finding]
    assert result.to_dict() == {
        "claim_id": "C",
        "status": "fail",
        "matched_source_id": "S",
        "matched_page": 2,
        "quote_score": 0.98,
        "matched_text": "Amount 100",
        "matched_start": 4,
        "matched_end": 14,
        "match_method": "fuzzy",
        "claim_support": 0.8,
        "source_support": 0.7,
        "claim_numbers": ["200"],
        "quote_numbers": ["100"],
        "source_numbers": ["100", "300"],
        "findings": [{
            "code": "number_not_in_source",
            "message": "Missing number",
            "details": {"numbers": ["200"]},
        }],
        "claim_legal_citation": None,
        "evidence_legal_citation": None,
        "evidence_numbers": None,
    }


def test_unreleased_17_argument_layout_is_rejected():
    # PR #15 inserted legal fields before findings; v0.2.0 never had that layout.
    with pytest.raises(TypeError):
        ClaimResult(
            "C", "fail", "S", 1, 1.0, "text", 0, 4, "exact",
            1.0, 1.0, [], [], [],
            {"article": "471"}, {"article": "472"}, [Finding("legacy", "kept")],
        )


def test_extension_fields_accept_keywords_and_serialize_with_findings():
    result = ClaimResult(
        "C", "fail",
        findings=[Finding("legal_citation_mismatch", "Wrong article")],
        claim_legal_citation={"article": "471"},
        evidence_legal_citation={"article": "472"},
        evidence_numbers=["471"],
    )
    payload = result.to_dict()

    assert payload["claim_legal_citation"] == {"article": "471"}
    assert payload["evidence_legal_citation"] == {"article": "472"}
    assert payload["evidence_numbers"] == ["471"]
    assert payload["findings"] == [{
        "code": "legal_citation_mismatch", "message": "Wrong article", "details": {},
    }]
