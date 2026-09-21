import json
import subprocess
import sys

import pytest

from jurisground import Claim, ClaimResult, Policy, Source, verify_batch, verify_claim
from jurisground.models import Finding


REPAIR = "The contractor completed the roof repair on 12 May 2026 for EUR 1900."
ALTERED = REPAIR.replace("1900", "9900")
OTHER = "A separate unrelated invoice was EUR 9900."


@pytest.mark.parametrize("location", ["same_page", "other_page", "other_source"])
def test_amount_elsewhere_does_not_validate_an_altered_quote(location):
    if location == "same_page":
        sources = [Source("S1", REPAIR + " " + OTHER)]
    elif location == "other_page":
        sources = [Source("S1", pages=(REPAIR, OTHER))]
    else:
        sources = [Source("S1", REPAIR), Source("S2", OTHER)]
    result = verify_claim(
        Claim("C1", ALTERED, ALTERED, tuple(source.id for source in sources)), sources,
    )
    assert result.status == "fail"
    assert result.quote_score >= Policy().quote_threshold
    assert "quote_number_mismatch" in {f.code for f in result.findings}
    assert "number_not_in_evidence" in {f.code for f in result.findings}
    assert result.evidence_numbers == ["12", "2026", "1900"]
    assert "9900" in result.source_numbers
    assert "1900" in result.matched_text


def test_altered_quote_is_checked_even_when_claim_has_no_numbers():
    result = verify_claim(
        Claim("C1", "The contractor completed the roof repair.", ALTERED, ("S1",)),
        [Source("S1", REPAIR + " " + OTHER)],
    )
    assert result.status == "fail"
    assert result.claim_numbers == []
    assert {f.code for f in result.findings} == {"quote_number_mismatch"}


def test_number_in_corpus_is_not_enough_when_quote_number_check_is_disabled():
    result = verify_claim(
        Claim("C1", "The contractor completed the roof repair for EUR 9900.", REPAIR, ("S1",)),
        [Source("S1", REPAIR + " " + OTHER)],
        Policy(require_numbers_in_quote=False),
    )
    assert result.status == "fail"
    assert {f.code for f in result.findings} == {"number_not_in_evidence"}
    assert result.evidence_numbers == ["12", "2026", "1900"]


def test_quote_check_alone_does_not_claim_source_number_integrity():
    result = verify_claim(
        Claim("C1", ALTERED, ALTERED, ("S1",)),
        [Source("S1", REPAIR + " " + OTHER)],
        Policy(require_numbers_in_source=False),
    )
    assert result.status == "pass"
    assert result.evidence_numbers == ["12", "2026", "1900"]
    assert result.quote_numbers == ["12", "2026", "9900"]


@pytest.mark.parametrize(
    ("text", "quote"),
    [
        ("The invoice total was PLN 92250.", "The invoice total was PLN 92 250,00."),
        ("The balance was 100 EUR.", "The balance was 00100 EUR."),
        ("The balance was 00100 EUR.", "The balance was 100 EUR."),
        ("The invoice total was EUR 7000.", "The invoice total was EUR 7\u00a0000.00."),
    ],
)
def test_existing_number_equivalences_still_pass(text, quote):
    result = verify_claim(Claim("C1", text, quote, ("S1",)), [Source("S1", quote)])
    assert result.status == "pass"
    assert result.evidence_numbers == result.quote_numbers


def test_fuzzy_typo_with_unchanged_numbers_passes():
    quote = REPAIR.replace("completed", "cornpleted")
    result = verify_claim(Claim("C1", REPAIR, quote, ("S1",)), [Source("S1", REPAIR, is_ocr=True)])
    assert result.status == "pass"
    assert result.match_method == "fuzzy"
    assert result.evidence_numbers == result.quote_numbers == ["12", "2026", "1900"]


@pytest.mark.parametrize("kind", ["order", "multiplicity", "missing_number"])
def test_quote_number_sequence_must_match_the_fragment(kind):
    source = "The schedule records invoice 1900 followed by invoice 9900 for the completed roofing works."
    if kind == "order":
        quote = source.replace("1900", "TEMP").replace("9900", "1900").replace("TEMP", "9900")
    elif kind == "multiplicity":
        quote = source.replace("1900", "9900")
    else:
        quote = source.replace("1900", "")
    result = verify_claim(
        Claim("C1", "The schedule records the completed roofing works.", quote, ("S1",)),
        [Source("S1", source)], Policy(quote_threshold=0.8),
    )
    assert result.status == "fail"
    assert result.matched_text is not None
    assert "quote_number_mismatch" in {f.code for f in result.findings}


def test_claim_may_mention_only_one_number_from_the_quote():
    quote = "Invoice 4812 had a total of EUR 7000."
    result = verify_claim(Claim("C1", "The invoice total was EUR 7000.", quote, ("S1",)), [Source("S1", quote)])
    assert result.status == "pass"
    assert result.evidence_numbers == ["4812", "7000"]


def test_verified_match_without_numbers_returns_empty_list():
    quote = "The court dismissed the claim."
    result = verify_claim(Claim("C1", "Claim dismissed.", quote, ("S1",)), [Source("S1", quote)])
    assert result.status == "pass"
    assert result.evidence_numbers == []


def test_missing_quote_match_does_not_report_evidence_numbers():
    result = verify_claim(
        Claim("C1", "The defendant admitted liability for EUR 9900.", "The defendant admitted liability for EUR 9900.", ("S1",)),
        [Source("S1", REPAIR)],
    )
    assert result.status == "fail"
    assert result.evidence_numbers is None
    assert "quote_not_found" in {f.code for f in result.findings}
    assert "number_not_in_source" in {f.code for f in result.findings}


def test_empty_claim_does_not_report_evidence_numbers():
    result = verify_claim(Claim("C1", "", REPAIR, ("S1",)), [Source("S1", REPAIR)])
    assert result.status == "unverified"
    assert result.evidence_numbers is None


def test_zero_threshold_does_not_turn_no_candidate_into_a_match():
    result = verify_claim(
        Claim("C1", "The invoice total was 9900.", "The invoice total was 9900.", ("S1",)),
        [Source("S1", "")], Policy(quote_threshold=0, require_numbers_in_source=False),
    )
    assert result.status == "fail"
    assert "quote_not_found" in {f.code for f in result.findings}
    assert result.evidence_numbers is None


def test_numeric_mismatch_blocks_batch_and_serializes_evidence():
    result = verify_batch(
        [Claim("valid", REPAIR, REPAIR, ("S1",)), Claim("altered", ALTERED, ALTERED, ("S1",))],
        [Source("S1", REPAIR + " " + OTHER)],
    )
    assert result["status"] == "fail"
    assert result["summary"] == {"total": 2, "pass": 1, "fail": 1, "unverified": 0}
    assert result["claims"][1]["evidence_numbers"] == ["12", "2026", "1900"]


def test_cli_blocks_amount_borrowed_from_another_invoice(tmp_path):
    path = tmp_path / "claims.json"
    path.write_text(json.dumps({
        "sources": [{"id": "S1", "text": REPAIR + " " + OTHER}],
        "claims": [{"id": "C1", "text": ALTERED, "quote": ALTERED, "source_ids": ["S1"]}],
    }), encoding="utf-8")
    process = subprocess.run(
        [sys.executable, "-m", "jurisground.cli", str(path)],
        capture_output=True, text=True, timeout=10,
    )
    assert process.returncode == 2, process.stderr
    result = json.loads(process.stdout)
    assert result["status"] == "fail"
    assert result["claims"][0]["evidence_numbers"] == ["12", "2026", "1900"]


def test_evidence_is_taken_from_the_selected_source_and_page():
    sources = [Source("S1", OTHER), Source("S2", pages=(OTHER, REPAIR))]
    result = verify_claim(Claim("C1", REPAIR, REPAIR, ("S1", "S2")), sources)
    assert result.status == "pass"
    assert (result.matched_source_id, result.matched_page) == ("S2", 2)
    assert result.evidence_numbers == ["12", "2026", "1900"]
    assert result.matched_text == sources[1].pages[1][result.matched_start:result.matched_end]


def test_same_number_in_another_sentence_does_not_override_claim_mismatch():
    result = verify_claim(
        Claim("C1", ALTERED, REPAIR, ("S1",)),
        [Source("S1", REPAIR + " " + OTHER)],
    )
    assert result.status == "fail"
    assert {f.code for f in result.findings} == {"number_not_in_quote", "number_not_in_evidence"}


def test_lexical_failure_can_still_report_matched_numbers():
    result = verify_claim(
        Claim("C1", "The defendant admitted liability.", REPAIR, ("S1",)), [Source("S1", REPAIR)],
    )
    assert result.status == "fail"
    assert {f.code for f in result.findings} == {"claim_not_supported"}
    assert result.evidence_numbers == ["12", "2026", "1900"]


def test_result_fields_do_not_share_mutable_number_lists():
    result = verify_claim(Claim("C1", REPAIR, REPAIR, ("S1",)), [Source("S1", REPAIR)])
    result.evidence_numbers.append("999")
    assert "999" not in result.source_numbers
    assert "999" not in result.quote_numbers


def test_no_candidate_cannot_pass_with_both_number_checks_disabled():
    result = verify_claim(
        Claim("C1", "The invoice total was 9900.", "The invoice total was 9900.", ("S1",)),
        [Source("S1", "")],
        Policy(quote_threshold=0, require_numbers_in_quote=False, require_numbers_in_source=False),
    )
    assert result.status == "fail"
    assert result.evidence_numbers is None


def test_ocr_match_does_not_include_adjacent_number_when_tighter_window_is_better():
    quote = REPAIR.replace("completed", "cornpleted")
    source = "2025. " + REPAIR
    result = verify_claim(
        Claim("C1", REPAIR, quote, ("S1",)),
        [Source("S1", source, is_ocr=True)],
    )
    assert result.status == "pass"
    assert result.quote_score == pytest.approx(0.978, abs=0.001)
    assert result.evidence_numbers == ["12", "2026", "1900"]
    assert result.matched_text == REPAIR[:-1]


def test_valid_numeric_ocr_match_can_beat_higher_scoring_wrong_amount():
    wrong_amount = REPAIR.replace("1900", "9900")
    correct_ocr = REPAIR.replace("completed", "cornpleted")
    sources = [Source("wrong", wrong_amount), Source("right", correct_ocr, is_ocr=True)]
    result = verify_claim(Claim("C1", REPAIR, REPAIR, ("wrong", "right")), sources)
    assert result.status == "pass"
    assert result.matched_source_id == "right"
    assert result.evidence_numbers == ["12", "2026", "1900"]
    assert result.quote_score < 0.985


def test_valid_numeric_match_on_later_page_is_not_masked_by_wrong_amount():
    wrong_amount = REPAIR.replace("1900", "9900")
    correct_ocr = REPAIR.replace("completed", "cornpleted")
    source = Source("S1", pages=(wrong_amount, correct_ocr), is_ocr=True)
    result = verify_claim(Claim("C1", REPAIR, REPAIR, ("S1",)), [source])
    assert result.status == "pass"
    assert result.matched_page == 2
    assert result.evidence_numbers == ["12", "2026", "1900"]


def test_disabling_source_number_checks_keeps_similarity_first_selection():
    wrong_amount = REPAIR.replace("1900", "9900")
    correct_ocr = REPAIR.replace("completed", "cornpleted")
    sources = [Source("wrong", wrong_amount), Source("right", correct_ocr, is_ocr=True)]
    result = verify_claim(
        Claim("C1", REPAIR, REPAIR, ("wrong", "right")),
        sources,
        Policy(require_numbers_in_source=False),
    )
    assert result.status == "pass"
    assert result.matched_source_id == "wrong"
    assert result.evidence_numbers == ["12", "2026", "9900"]

@pytest.mark.parametrize("separator", [" ", "\n", " | "])
def test_valid_numeric_ocr_match_on_same_page_is_not_masked(separator):
    wrong_amount = REPAIR.replace("1900", "9900")
    correct_ocr = REPAIR.replace("completed", "cornpleted")
    source = Source("S1", wrong_amount + separator + correct_ocr, is_ocr=True)
    result = verify_claim(Claim("C1", REPAIR, REPAIR, ("S1",)), [source])
    assert result.status == "pass"
    assert result.matched_source_id == "S1"
    assert result.matched_page == 1
    assert result.evidence_numbers == ["12", "2026", "1900"]
    assert "cornpleted" in result.matched_text


def test_valid_numeric_ocr_match_survives_multiple_wrong_same_page_candidates():
    wrong_amount = REPAIR.replace("1900", "9900")
    correct_ocr = REPAIR.replace("completed", "cornpleted")
    source = Source("S1", " ".join([wrong_amount, wrong_amount, correct_ocr, wrong_amount]), is_ocr=True)
    result = verify_claim(Claim("C1", REPAIR, REPAIR, ("S1",)), [source])
    assert result.status == "pass"
    assert result.evidence_numbers == ["12", "2026", "1900"]
    assert "cornpleted" in result.matched_text


def test_fuzzy_refinement_has_a_fixed_similarity_budget(monkeypatch):
    import jurisground.quotes as quotes_module

    original = quotes_module.SequenceMatcher
    calls = 0

    def counting_matcher(*args, **kwargs):
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(quotes_module, "SequenceMatcher", counting_matcher)
    sentence = "The contractor completed the roof repair and recorded the invoice amount."
    quote = " ".join([sentence] * 25)
    source = quote.replace("completed", "cornpleted").replace("recorded", "rec0rded")
    result = verify_claim(Claim("C1", quote, quote, ("S1",)), [Source("S1", source, is_ocr=True)])
    assert result.status == "fail"
    assert calls <= 1100


def test_valid_numeric_ocr_match_is_not_lost_after_many_wrong_same_page_candidates():
    wrong_amount = REPAIR.replace("1900", "9900")
    correct_ocr = REPAIR.replace("completed", "cornpleted")
    parts = [wrong_amount] * 12
    parts.insert(6, correct_ocr)
    result = verify_claim(
        Claim("C1", REPAIR, REPAIR, ("S1",)),
        [Source("S1", " ".join(parts), is_ocr=True)],
    )
    assert result.status == "pass"
    assert result.evidence_numbers == ["12", "2026", "1900"]
    assert "cornpleted" in result.matched_text


def test_claim_result_extensions_preserve_v020_positional_findings():
    finding = Finding("legacy", "kept")
    result = ClaimResult(
        "C", "fail", "S1", 1, 1.0, "text", 0, 4, "exact",
        1.0, 1.0, [], [], [], [finding],
        claim_legal_citation={"article": "471"},
        evidence_legal_citation={"article": "472"},
    )
    assert result.claim_legal_citation == {"article": "471"}
    assert result.evidence_legal_citation == {"article": "472"}
    assert result.findings == [finding]
    assert result.evidence_numbers is None


@pytest.mark.parametrize("fragment_count", [3, 10, 20])
def test_late_numeric_ocr_candidate_is_not_starved_by_window_budget(fragment_count):
    quote = "The contractor completed the roof repair on the apartment building for the agreed amount of EUR 1900."
    wrong = quote.replace("1900", "9900")
    right = quote.replace("completed", "cornpleted")
    source = " ".join([wrong] * (fragment_count - 1) + [right])

    result = verify_claim(
        Claim("C1", quote, quote, ("S1",)),
        [Source("S1", source, is_ocr=True)],
    )

    assert result.status == "pass"
    assert result.evidence_numbers == ["1900"]
    assert "cornpleted" in result.matched_text
