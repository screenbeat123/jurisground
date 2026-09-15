import json
import subprocess
import sys

import pytest

from jurisground import Claim, Policy, Source, verify_batch, verify_claim


SOURCE_TEXT = "The court dismissed the claim because causation was not proven."


@pytest.mark.parametrize("text", ["", " \t\r\n\u00a0", "\u00ad"])
def test_empty_claim_is_unverified(text):
    result = verify_claim(Claim("C1", text, SOURCE_TEXT, ("S1",)), [Source("S1", SOURCE_TEXT)])
    assert result.status == "unverified"
    assert {finding.code for finding in result.findings} == {"empty_claim"}
    assert result.matched_text is None


@pytest.mark.parametrize("text", ["...", "the and of", "UK"])
def test_claim_without_usable_tokens_is_unverified(text):
    result = verify_claim(Claim("C1", text, SOURCE_TEXT, ("S1",)), [Source("S1", SOURCE_TEXT)])
    assert result.status == "unverified"
    assert {finding.code for finding in result.findings} == {"no_claim_content"}


@pytest.mark.parametrize("text", ["Liability.", "Liability remains.", "The liability remains."])
@pytest.mark.parametrize("threshold", [0.42, 0.0])
def test_zero_overlap_never_passes(text, threshold):
    result = verify_claim(
        Claim("C1", text, SOURCE_TEXT, ("S1",)),
        [Source("S1", SOURCE_TEXT)],
        Policy(min_claim_support=threshold),
    )
    assert result.status == "fail"
    assert result.claim_support == 0.0
    assert "claim_not_supported" in {finding.code for finding in result.findings}


@pytest.mark.parametrize("text", ["Dismissed.", "Claim dismissed.", "The claim was dismissed."])
def test_supported_short_claim_passes(text):
    result = verify_claim(Claim("C1", text, SOURCE_TEXT, ("S1",)), [Source("S1", SOURCE_TEXT)])
    assert result.status == "pass"
    assert result.claim_support == 1.0
    assert result.findings == []


def test_numeric_claim_is_not_treated_as_empty():
    quote = "The invoice total was 100 EUR."
    result = verify_claim(Claim("C1", "100", quote, ("S1",)), [Source("S1", quote)])
    assert result.status == "pass"
    assert result.claim_numbers == ["100"]


def test_empty_claim_makes_otherwise_valid_batch_unverified():
    claims = [
        Claim("valid", "Claim dismissed.", SOURCE_TEXT, ("S1",)),
        Claim("empty", "", SOURCE_TEXT, ("S1",)),
    ]
    result = verify_batch(claims, [Source("S1", SOURCE_TEXT)])
    assert result["status"] == "unverified"
    assert result["summary"] == {"total": 2, "pass": 1, "fail": 0, "unverified": 1}


def test_failed_claim_takes_precedence_over_unverified():
    claims = [
        Claim("empty", "", SOURCE_TEXT, ("S1",)),
        Claim("unsupported", "Liability remains.", SOURCE_TEXT, ("S1",)),
    ]
    result = verify_batch(claims, [Source("S1", SOURCE_TEXT)])
    assert result["status"] == "fail"
    assert result["summary"] == {"total": 2, "pass": 0, "fail": 1, "unverified": 1}


@pytest.mark.parametrize(
    ("text", "status", "exit_code"),
    [("", "unverified", 2), ("Liability remains.", "fail", 2), ("Claim dismissed.", "pass", 0)],
)
def test_cli_returns_status_and_exit_code(tmp_path, text, status, exit_code):
    path = tmp_path / "claims.json"
    path.write_text(json.dumps({
        "sources": [{"id": "S1", "text": SOURCE_TEXT}],
        "claims": [{"id": "C1", "text": text, "quote": SOURCE_TEXT, "source_ids": ["S1"]}],
    }), encoding="utf-8")
    process = subprocess.run(
        [sys.executable, "-m", "jurisground.cli", str(path)],
        capture_output=True, text=True, timeout=10,
    )
    assert process.returncode == exit_code, process.stderr
    result = json.loads(process.stdout)
    assert result["status"] == status
    assert result["claims"][0]["status"] == status


def test_removed_length_bypass_is_not_silently_accepted():
    with pytest.raises(TypeError, match="min_content_stems_for_support"):
        Policy(min_content_stems_for_support=3)


@pytest.mark.parametrize("argument_count", range(4, 10))
def test_old_positional_policy_calls_are_rejected(argument_count):
    old_arguments = (.965, .90, .42, 3, 1.45, .72, 10, False, True)
    with pytest.raises(TypeError):
        Policy(*old_arguments[:argument_count])


def test_first_three_policy_arguments_and_named_options_keep_their_meaning():
    policy = Policy(.965, .90, .42, require_numbers_in_quote=False)
    assert policy.quote_threshold == .965
    assert policy.ocr_quote_threshold == .90
    assert policy.min_claim_support == .42
    assert policy.max_expansion_ratio == 1.45
    assert policy.min_expansion_support == .72
    assert policy.min_quote_chars == 10
    assert policy.require_numbers_in_quote is False
    assert policy.require_numbers_in_source is True

    result = verify_claim(
        Claim("C1", "9900 EUR", "The invoice total was 9900 EUR.", ("S1",)),
        [Source("S1", "The invoice total was 1900 EUR.")],
        policy,
    )
    assert result.status == "fail"
    assert "number_not_in_source" in {finding.code for finding in result.findings}


@pytest.mark.parametrize("text", ["---", "___", "_-_", "－－－"])
def test_separator_only_claim_is_unverified_even_when_quoted(text):
    quote = f"Recorded {text} in this document."
    result = verify_claim(Claim("C1", text, quote, ("S1",)), [Source("S1", quote)])
    assert result.status == "unverified"
    assert {finding.code for finding in result.findings} == {"no_claim_content"}


def test_separator_tokens_cannot_supply_overlap():
    quote = "Recorded --- in this document."
    result = verify_claim(
        Claim("C1", "--- Liability remains.", quote, ("S1",)),
        [Source("S1", quote)],
        Policy(min_claim_support=0),
    )
    assert result.status == "fail"
    assert result.claim_support == 0
    assert "claim_not_supported" in {finding.code for finding in result.findings}


def test_hyphenated_word_is_still_content():
    quote = "The well-known rule was applied."
    result = verify_claim(Claim("C1", "Well-known", quote, ("S1",)), [Source("S1", quote)])
    assert result.status == "pass"
    assert result.claim_support == 1


@pytest.mark.parametrize(
    ("text", "amount", "canonical"),
    [
        ("00100", "100", "100"),
        ("100", "00100", "100"),
        ("000", "0", "0"),
        ("0", "000", "0"),
        ("Invoice 00100", "100", "100"),
        ("Invoice 100", "00100", "100"),
    ],
)
def test_integer_overlap_uses_numeric_normalization(text, amount, canonical):
    quote = f"Invoice {amount} was submitted."
    result = verify_claim(
        Claim("C1", text, quote, ("S1",)),
        [Source("S1", quote)],
        Policy(min_claim_support=1),
    )
    assert result.status == "pass"
    assert result.claim_support == result.source_support == 1
    assert result.claim_numbers == result.quote_numbers == [canonical]


@pytest.mark.parametrize(("text", "amount"), [("00101", "100"), ("100", "00101")])
@pytest.mark.parametrize("check_numbers", [True, False])
def test_different_integers_have_no_overlap(text, amount, check_numbers):
    quote = f"The invoice total was {amount}."
    result = verify_claim(
        Claim("C1", text, quote, ("S1",)),
        [Source("S1", quote)],
        Policy(
            min_claim_support=0,
            require_numbers_in_quote=check_numbers,
            require_numbers_in_source=check_numbers,
        ),
    )
    assert result.status == "fail"
    assert result.claim_support == 0
    assert "claim_not_supported" in {finding.code for finding in result.findings}
