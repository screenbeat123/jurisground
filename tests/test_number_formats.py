import json
import subprocess
import sys

import pytest

from jurisground import Claim, Source, verify_claim
from jurisground.numbers import number_tokens


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("-100 EUR", ["-100"]),
        ("−100 EUR", ["-100"]),
        ("+100 EUR", ["100"]),
        ("100 EUR", ["100"]),
        ("-000", ["0"]),
        ("−0.00", ["0"]),
        ("92 250,00", ["92250"]),
        ("92\u00a0250.00", ["92250"]),
        ("092250", ["92250"]),
        ("1,234,567", ["1234567"]),
        ("1.234.567", ["1234567"]),
        ("1,234,567.89", ["1234567.89"]),
        ("1.234.567,89", ["1234567.89"]),
        ("12,500.00", ["12500"]),
        ("12.500,00", ["12500"]),
    ],
)
def test_number_token_normalization(raw, expected):
    assert number_tokens(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("12,500", ["12,500"]),
        ("12.500", ["12.500"]),
        ("0.125", ["0.125"]),
        ("0,125", ["0,125"]),
    ],
)
def test_single_three_digit_separator_is_preserved_as_format_sensitive(raw, expected):
    assert number_tokens(raw) == expected


def test_sign_change_is_not_silently_accepted():
    source = "The account balance was -100 EUR."
    result = verify_claim(
        Claim("C1", "The account balance was 100 EUR.", source, ("S1",)),
        [Source("S1", source)],
    )
    codes = {finding.code for finding in result.findings}

    assert result.status == "fail"
    assert result.claim_numbers == ["100"]
    assert result.quote_numbers == ["-100"]
    assert result.evidence_numbers == ["-100"]
    assert {"number_not_in_quote", "number_not_in_source", "number_not_in_evidence"} <= codes


def test_unicode_minus_matches_ascii_minus_without_losing_source_offsets():
    source = "The account balance was −100 EUR."
    quote = "The account balance was -100 EUR."
    result = verify_claim(Claim("C1", quote, quote, ("S1",)), [Source("S1", source)])

    assert result.status == "pass"
    assert result.quote_numbers == result.evidence_numbers == ["-100"]
    assert result.matched_text == source
    assert source[result.matched_start:result.matched_end] == source


def test_explicit_plus_is_compatible_with_unsigned_positive_value():
    source = "The account balance was +100 EUR."
    claim = "The account balance was 100 EUR."
    result = verify_claim(Claim("C1", claim, source, ("S1",)), [Source("S1", source)])

    assert result.status == "pass"
    assert result.claim_numbers == result.quote_numbers == result.evidence_numbers == ["100"]


def test_ambiguous_separator_does_not_equal_decimal_value():
    source = "The invoice total was EUR 12,500."
    result = verify_claim(
        Claim("C1", "The invoice total was EUR 12.5.", source, ("S1",)),
        [Source("S1", source)],
    )

    assert result.status == "fail"
    assert result.claim_numbers == ["12.5"]
    assert result.quote_numbers == result.evidence_numbers == ["12,500"]
    assert "number_not_in_quote" in {finding.code for finding in result.findings}


def test_identical_format_sensitive_number_still_passes():
    text = "The invoice total was EUR 12,500."
    result = verify_claim(Claim("C1", text, text, ("S1",)), [Source("S1", text)])

    assert result.status == "pass"
    assert result.claim_numbers == result.quote_numbers == result.evidence_numbers == ["12,500"]


@pytest.mark.parametrize("source_number", ["12,500.00", "12.500,00"])
def test_unambiguous_mixed_grouping_matches_plain_integer(source_number):
    source = f"The invoice total was EUR {source_number}."
    claim = "The invoice total was EUR 12500."
    result = verify_claim(Claim("C1", claim, source, ("S1",)), [Source("S1", source)])

    assert result.status == "pass"
    assert result.claim_numbers == result.quote_numbers == result.evidence_numbers == ["12500"]


def test_signed_numeric_fallback_selects_matching_ocr_evidence():
    quote = "The account balance was -100 EUR after adjustment."
    wrong = quote.replace("-100", "100")
    right = quote.replace("adjustment", "adjustrnent")
    sources = [
        Source("wrong", wrong),
        Source("right", right, is_ocr=True),
    ]

    result = verify_claim(Claim("C1", quote, quote, ("wrong", "right")), sources)

    assert result.status == "pass"
    assert result.matched_source_id == "right"
    assert result.evidence_numbers == ["-100"]


def test_cli_rejects_lost_numeric_sign(tmp_path):
    source = "The account balance was -100 EUR."
    path = tmp_path / "input.json"
    path.write_text(json.dumps({
        "sources": [{"id": "S1", "text": source}],
        "claims": [{
            "id": "C1",
            "text": "The account balance was 100 EUR.",
            "quote": source,
            "source_ids": ["S1"],
        }],
    }), encoding="utf-8")

    process = subprocess.run(
        [sys.executable, "-m", "jurisground.cli", str(path)],
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert process.returncode == 2, process.stderr
    payload = json.loads(process.stdout)
    assert payload["status"] == "fail"
    assert payload["claims"][0]["evidence_numbers"] == ["-100"]
