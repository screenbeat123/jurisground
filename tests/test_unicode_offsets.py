import unicodedata

import pytest

from jurisground import Claim, Policy, Source, verify_claim
from jurisground.normalize import normalize_text
from jurisground.quotes import _normalized_with_spans


@pytest.mark.parametrize(
    "text",
    [
        "Café déjà vu",
        "Cafe\u0301 de\u0301ja\u0300 vu",
        "Alpha\u00a0Beta   Gamma",
        "The ofﬁce balance was −100 EUR.",
        "\u1100\u1161",
    ],
)
def test_normalized_text_with_spans_matches_public_normalizer(text):
    normalized, spans = _normalized_with_spans(text)

    assert normalized == normalize_text(text)
    assert len(spans) == len(normalized)


def test_nfc_quote_matches_nfd_source_with_exact_original_span():
    fragment = unicodedata.normalize("NFD", "Sąd zasądził kwotę na rzecz powoda.")
    source = f"Header. {fragment} Footer."
    quote = "Sąd zasądził kwotę na rzecz powoda."

    result = verify_claim(Claim("C1", quote, quote, ("S1",)), [Source("S1", source)])

    assert result.status == "pass"
    assert result.match_method == "normalized"
    assert result.matched_text == fragment
    assert source[result.matched_start:result.matched_end] == fragment


def test_nfd_quote_matches_nfc_source():
    source = "Sąd zasądził kwotę na rzecz powoda."
    quote = unicodedata.normalize("NFD", source)

    result = verify_claim(Claim("C1", source, quote, ("S1",)), [Source("S1", source)])

    assert result.status == "pass"
    assert result.match_method == "normalized"
    assert result.matched_text == source
    assert source[result.matched_start:result.matched_end] == source


def test_compatibility_character_keeps_original_source_span():
    source = "The ofﬁce recorded the payment."
    quote = "The office recorded the payment."

    result = verify_claim(Claim("C1", quote, quote, ("S1",)), [Source("S1", source)])

    assert result.status == "pass"
    assert result.match_method == "normalized"
    assert result.matched_text == source
    assert source[result.matched_start:result.matched_end] == source


def test_casefold_expansion_keeps_original_source_span():
    source = "Die Straße wurde vollständig gesperrt."
    quote = "Die STRASSE wurde vollständig gesperrt."

    result = verify_claim(Claim("C1", quote, quote, ("S1",)), [Source("S1", source)])

    assert result.status == "pass"
    assert result.match_method == "normalized"
    assert result.matched_text == source
    assert source[result.matched_start:result.matched_end] == source


def test_fuzzy_match_with_decomposed_text_keeps_combining_mark_in_span():
    clean = "The café submitted invoice 4812 for 7000 EUR."
    source = unicodedata.normalize("NFD", clean)
    quote = "The café subrnitted invoice 4812 for 7000 EUR."

    result = verify_claim(
        Claim("C1", clean, quote, ("S1",)),
        [Source("S1", source, is_ocr=True)],
        Policy(ocr_quote_threshold=0.84),
    )

    assert result.status == "pass"
    assert result.match_method == "fuzzy"
    assert source[result.matched_start:result.matched_end] == result.matched_text
    assert unicodedata.normalize("NFC", result.matched_text) == clean[:-1]


def test_normalized_match_does_not_start_inside_compatibility_expansion():
    source = "The ofﬁce recorded the payment."
    quote = "ICE recorded the payment."

    result = verify_claim(
        Claim("C1", quote, quote, ("S1",)),
        [Source("S1", source)],
    )

    assert result.match_method != "normalized"


def test_normalized_match_skips_partial_expansion_and_uses_later_full_span():
    source = "The ofﬁce recorded the payment. Later the ice recorded the payment."
    quote = "ICE recorded the payment."

    result = verify_claim(
        Claim("C1", quote, quote, ("S1",)),
        [Source("S1", source)],
    )

    assert result.status == "pass"
    assert result.match_method == "normalized"
    assert result.matched_text == "ice recorded the payment."
    assert source[result.matched_start:result.matched_end] == result.matched_text
