from jurisground import Claim, Policy, Source, verify_claim
from jurisground.numbers import number_tokens
from jurisground.quotes import quote_similarity


def test_exact_quote_passes():
    source = Source("S1", "The contractor completed the roof repair on 12 May 2026 for EUR 12,500.")
    claim = Claim("C1", "The contractor completed the roof repair for EUR 12,500.", "The contractor completed the roof repair on 12 May 2026 for EUR 12,500.", ("S1",))
    result = verify_claim(claim, [source])
    assert result.status == "pass"
    assert result.quote_score == 1.0


def test_fabricated_quote_fails():
    source = Source("S1", "The court dismissed the claim because causation was not proven.")
    claim = Claim("C1", "The defendant admitted liability.", "The defendant admitted liability for all losses.", ("S1",))
    result = verify_claim(claim, [source])
    assert result.status == "fail"
    assert "quote_not_found" in {x.code for x in result.findings}


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
    source = Source("S1", "The claimant submitted invoice number 4812 for 7000 EUR.", is_ocr=True)
    claim = Claim("C1", "The claimant submitted invoice 4812 for 7000 EUR.", "The claimant subrnitted invoice number 4812 for 7000 EUR.", ("S1",))
    result = verify_claim(claim, [source], Policy(ocr_quote_threshold=0.84))
    assert result.status == "pass"


def test_claim_can_be_supported_by_source_but_not_quote():
    source = Source("S1", "The contract was signed in Warsaw. The total price was EUR 50,000.")
    claim = Claim("C1", "The contract price was EUR 50,000.", "The contract was signed in Warsaw.", ("S1",))
    result = verify_claim(claim, [source])
    assert result.source_support >= result.claim_support
    assert result.status == "fail"


def test_quote_similarity_exact_after_normalization():
    assert quote_similarity("Alpha\u00a0Beta   Gamma", "alpha beta gamma") == 1.0
