from jurisground import Claim, Policy, Source, verify_claim
from jurisground.numbers import number_tokens
from jurisground.quotes import quote_similarity


def test_exact_quote_passes():
    source_text = "The contractor completed the roof repair on 12 May 2026 for EUR 12,500."
    source = Source("S1", source_text)
    claim = Claim("C1", "The contractor completed the roof repair for EUR 12,500.", source_text, ("S1",))
    result = verify_claim(claim, [source])
    assert result.status == "pass"
    assert result.quote_score == 1.0
    assert result.match_method == "exact"
    assert result.matched_text == source_text
    assert source_text[result.matched_start:result.matched_end] == result.matched_text


def test_fabricated_quote_fails():
    source = Source("S1", "The court dismissed the claim because causation was not proven.")
    claim = Claim("C1", "The defendant admitted liability.", "The defendant admitted liability for all losses.", ("S1",))
    result = verify_claim(claim, [source])
    assert result.status == "fail"
    assert "quote_not_found" in {x.code for x in result.findings}
    assert result.matched_text is None
    assert result.matched_start is None
    assert result.matched_end is None
    assert result.match_method is None


def test_changed_number_fails():
    source = Source("S1", "The invoice total was PLN 92 250,00.")
    claim = Claim("C1", "The invoice total was PLN 98 250.", "The invoice total was PLN 92 250,00.", ("S1",))
    result = verify_claim(claim, [source])
    codes = {x.code for x in result.findings}
    assert result.status == "fail"
    assert "number_not_in_quote" in codes
    assert "number_not_in_source" in codes


def test_number_normalization_equivalence():
    assert number_tokens("92 250,00") == ["92250"]
    assert number_tokens("92\u00a0250.00") == ["92250"]
    assert number_tokens("092250") == ["92250"]


def test_missing_source_id_is_unverified():
    result = verify_claim(Claim("C1", "A claim", "A sufficiently long quotation.", ()), [])
    assert result.status == "unverified"


def test_unknown_source_id_is_unverified():
    result = verify_claim(Claim("C1", "A claim", "A sufficiently long quotation.", ("MISSING",)), [])
    assert result.status == "unverified"


def test_quote_across_pages_selects_page():
    source = Source("S1", pages=("Page one has unrelated text.", "Page two states the payment was rejected due to missing evidence."))
    claim = Claim("C1", "The payment was rejected due to missing evidence.", "the payment was rejected due to missing evidence", ("S1",))
    result = verify_claim(claim, [source])
    assert result.status == "pass"
    assert result.matched_page == 2


def test_ocr_threshold_can_be_relaxed():
    source_text = "The claimant submitted invoice number 4812 for 7000 EUR."
    source = Source("S1", source_text, is_ocr=True)
    claim = Claim("C1", "The claimant submitted invoice 4812 for 7000 EUR.", "The claimant subrnitted invoice number 4812 for 7000 EUR.", ("S1",))
    result = verify_claim(claim, [source], Policy(ocr_quote_threshold=0.84))
    assert result.status == "pass"
    assert result.match_method == "fuzzy"
    assert source_text[result.matched_start:result.matched_end] == result.matched_text


def test_claim_can_be_supported_by_source_but_not_quote():
    source = Source("S1", "The contract was signed in Warsaw. The total price was EUR 50,000.")
    claim = Claim("C1", "The contract price was EUR 50,000.", "The contract was signed in Warsaw.", ("S1",))
    result = verify_claim(claim, [source])
    assert result.source_support >= result.claim_support
    assert result.status == "fail"


def test_quote_similarity_exact_after_normalization():
    assert quote_similarity("Alpha\u00a0Beta   Gamma", "alpha beta gamma") == 1.0


def test_normalized_match_keeps_source_offsets():
    source_text = "Header. Alpha\u00a0Beta   Gamma is recorded here. Footer."
    claim = Claim("C1", "Alpha Beta Gamma is recorded here.", "alpha beta gamma is recorded here.", ("S1",))
    result = verify_claim(claim, [Source("S1", source_text)])
    assert result.status == "pass"
    assert result.match_method == "normalized"
    assert source_text[result.matched_start:result.matched_end] == result.matched_text
    assert result.matched_text == "Alpha\u00a0Beta   Gamma is recorded here."


def test_claim_support_threshold_is_configurable():
    quote = "The roof was fixed."
    claim = Claim("C1", "The roof was repaired.", quote, ("S1",))
    source = Source("S1", quote)
    at_threshold = verify_claim(claim, [source], Policy(min_claim_support=0.5))
    below_threshold = verify_claim(claim, [source], Policy(min_claim_support=0.51))
    assert at_threshold.claim_support == 0.5
    assert at_threshold.status == "pass"
    assert below_threshold.status == "fail"
    assert "claim_not_supported" in {finding.code for finding in below_threshold.findings}


def test_expansion_support_threshold_is_configurable():
    quote = "The contractor repaired the roof after the storm and replaced damaged tiles."
    source = Source("S1", quote)
    claim = Claim(
        "C1",
        "The contractor repaired the roof after the storm and replaced damaged tiles, and the work also included extensive additional structural repairs that were allegedly required throughout the entire building.",
        quote,
        ("S1",),
    )
    permissive = verify_claim(claim, [source], Policy(min_expansion_support=0.0, min_claim_support=0.0))
    strict = verify_claim(claim, [source], Policy(min_expansion_support=1.0, min_claim_support=0.0))
    assert "claim_expands_quote" not in {x.code for x in permissive.findings}
    assert "claim_expands_quote" in {x.code for x in strict.findings}
