import pytest

from jurisground import Claim, Policy, Source, verify_claim
from jurisground.quotes import quote_matches


CUT_NUMBERS = [
    ("-100", "100", "start"),
    ("\u2212100", "100", "start"),
    ("2100", "100", "start"),
    ("1 100", "100", "start"),
    ("1\u00a0100", "100", "start"),
    ("1\u202f100", "100", "start"),
    ("1000", "100", "end"),
    ("12.500", "12.5", "end"),
    ("12,500", "12,5", "end"),
    ("12.50", "12", "end"),
    ("12,50", "12", "end"),
    ("12 500", "12", "end"),
    ("12\u00a0500", "12", "end"),
    ("12\u202f500", "12", "end"),
    ("1,234,567.89", "1,234", "end"),
    ("1.234.567,89", "1.234", "end"),
    ("AB100", "100", "start"),
    ("AB-100", "-100", "start"),
    ("100x", "100", "end"),
    ("100.000x", "100.", "end"),
]


def _sentence(number, endpoint):
    if endpoint == "start":
        return f"{number} EUR was the account balance"
    return f"The account balance was EUR {number}"


@pytest.mark.parametrize("number,partial,endpoint", CUT_NUMBERS)
@pytest.mark.parametrize("method", ["exact", "normalized", "fuzzy"])
def test_partial_number_cannot_become_evidence(number, partial, endpoint, method):
    quote = _sentence(partial, endpoint)
    source = _sentence(number, endpoint)
    if method == "normalized":
        quote = quote.upper()
    elif method == "fuzzy":
        source = source.replace("balance", "baIance")
    source += f". An unrelated fee was EUR {partial}."

    result = verify_claim(
        Claim("C", quote, quote, ("S",)), [Source("S", source, is_ocr=True)],
    )

    assert result.status == "fail", result.to_dict()
    if result.matched_text is not None:
        assert source[result.matched_start:result.matched_end] == result.matched_text
        assert result.evidence_numbers != result.quote_numbers


@pytest.mark.parametrize("method", ["exact", "normalized", "fuzzy"])
@pytest.mark.parametrize("endpoint", ["start", "end"])
def test_later_complete_occurrence_survives_an_earlier_partial_match(method, endpoint):
    quote = _sentence("100", endpoint)
    wrong = _sentence("-100" if endpoint == "start" else "1000", endpoint)
    right = quote
    if method == "normalized":
        quote = quote.upper()
        right = right.replace(" ", "\u00a0")
    elif method == "fuzzy":
        wrong = wrong.replace("balance", "baIance")
        right = right.replace("balance", "baIance")
    prefix = "Cafe\u0301. " + wrong + ". Separate entry: "
    source = prefix + right + "."

    result = verify_claim(
        Claim("C", quote, quote, ("S",)), [Source("S", source, is_ocr=True)],
    )

    assert result.status == "pass", result.to_dict()
    assert result.match_method == method
    assert result.evidence_numbers == ["100"]
    assert result.matched_text == right
    assert result.matched_start == len(prefix)
    assert result.matched_end == len(prefix) + len(right)


@pytest.mark.parametrize("method", ["exact", "normalized", "fuzzy"])
def test_boundary_protection_follows_source_number_policy(method):
    if method == "fuzzy":
        quote = "The account balance was EUR 12"
        source = "The account baIance was EUR 12.50. An unrelated fee was EUR 12."
    else:
        quote = "100 EUR was the account balance"
        source = "-100 EUR was the account balance. An unrelated fee was EUR 100."
        if method == "normalized":
            quote = quote.upper()

    result = verify_claim(
        Claim("C", quote, quote, ("S",)), [Source("S", source, is_ocr=True)],
        Policy(require_numbers_in_source=False),
    )

    assert result.status == "pass", result.to_dict()
    assert result.match_method == method
    assert result.evidence_numbers == result.quote_numbers


@pytest.mark.parametrize("number", ["-100", "\u2212100", "+100", "12.50", "12,500", "1 234.50"])
@pytest.mark.parametrize("endpoint", ["start", "end"])
def test_fuzzy_evidence_preserves_complete_signed_and_formatted_numbers(number, endpoint):
    quote = _sentence(number, endpoint)
    source = "Earlier text. " + quote.replace("balance", "baIance") + ". Later text."

    result = verify_claim(
        Claim("C", quote, quote, ("S",)), [Source("S", source, is_ocr=True)],
    )

    assert result.status == "pass", result.to_dict()
    assert result.match_method == "fuzzy"
    assert result.evidence_numbers == result.quote_numbers
    assert result.matched_text == quote.replace("balance", "baIance")
    assert source[result.matched_start:result.matched_end] == result.matched_text


def test_normalized_match_rejects_cut_number_after_expanding_unicode_character():
    quote = "STRASSE: THE ACCOUNT BALANCE WAS EUR 12.5"
    source = "Stra\u00dfe: The account balance was EUR 12.500. Other fee: EUR 12.5."
    result = verify_claim(Claim("C", quote, quote, ("S",)), [Source("S", source)])
    assert result.status == "fail", result.to_dict()


def test_a_quote_without_numbers_cannot_stop_inside_a_signed_number():
    quote = "The account balance was -"
    source = quote + "100."
    matches = quote_matches(quote, [Source("S", source)], require_numeric_boundaries=True)
    assert all(match.text != quote for match in matches)


def test_no_candidate_fallback_keeps_boundary_protection_enabled():
    quote = "Longbalance -"
    source = "Longbalance -100"
    result = verify_claim(
        Claim("C", quote, quote, ("S",)), [Source("S", source)],
        Policy(quote_threshold=0),
    )
    assert result.status == "fail", result.to_dict()


@pytest.mark.parametrize("wrong_count", [3, 20, 100])
def test_late_complete_fuzzy_number_survives_many_partial_candidates(wrong_count):
    quote = "The account balance was EUR 12"
    wrong = "The account baIance was EUR 12.50. "
    right = "The account baIance was EUR 12"
    source = wrong * wrong_count + right + "."

    result = verify_claim(
        Claim("C", quote, quote, ("S",)), [Source("S", source, is_ocr=True)],
    )

    assert result.status == "pass", result.to_dict()
    assert result.matched_text == right
    assert result.matched_start == len(wrong) * wrong_count
    assert result.evidence_numbers == ["12"]
