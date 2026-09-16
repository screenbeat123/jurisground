import pytest

from jurisground.legal import PolishLegalCitation, parse_polish_citations


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("art. 471 § 1 k.c.", ("471", "1", None, None, None, "k.c.")),
        ("art. 160 pkt 3", ("160", None, None, "3", None, None)),
        ("art. 5 ust. 2 pkt 1", ("5", None, "2", "1", None, None)),
        ("art. 3 ust. 3 pkt 2 lit. d", ("3", None, "3", "2", "d", None)),
        ("art. 106gba ust. 2", ("106gba", None, "2", None, None, None)),
        ("Art.\u00a0471\u00a0§\u00a01 K.C.", ("471", "1", None, None, None, "k.c.")),
        ("art. 299g § 1", ("299g", "1", None, None, None, None)),
        ("art. 17a", ("17a", None, None, None, None, None)),
    ],
)
def test_parses_common_polish_citations(text, expected):
    citation = parse_polish_citations(text)[0]
    assert (
        citation.article,
        citation.paragraph,
        citation.subsection,
        citation.point,
        citation.letter,
        citation.act,
    ) == expected
    assert citation.raw == text
    assert text[citation.start:citation.end] == citation.raw


def test_finds_multiple_citations_with_original_offsets():
    text = "Stosuje się art. 471 § 1 k.c., a także art. 5 ust. 2 pkt 1."
    citations = parse_polish_citations(text)
    assert [c.raw for c in citations] == ["art. 471 § 1 k.c.", "art. 5 ust. 2 pkt 1"]
    assert [text[c.start:c.end] for c in citations] == [c.raw for c in citations]


def test_does_not_require_lower_units():
    citation = parse_polish_citations("Podstawą jest art. 471 k.c.")[0]
    assert citation.article == "471"
    assert citation.paragraph is None
    assert citation.subsection is None
    assert citation.act == "k.c."


@pytest.mark.parametrize(
    "text",
    [
        "art 471 k.c.",
        "artystyczny 471",
        "art. x",
        "ust. 2 pkt 1",
        "§ 1 k.c.",
    ],
)
def test_ignores_text_that_is_not_an_article_citation(text):
    assert parse_polish_citations(text) == []


def test_unknown_act_name_is_not_swallowed():
    text = "art. 5 ust. 2 ustawy o testach"
    citation = parse_polish_citations(text)[0]
    assert citation.raw == "art. 5 ust. 2"
    assert citation.act is None


def test_result_is_immutable():
    citation = parse_polish_citations("art. 471 k.c.")[0]
    with pytest.raises(AttributeError):
        citation.article = "5"


def test_public_shape_is_simple_dataclass():
    citation = PolishLegalCitation("art. 5", 0, 6, "5")
    assert citation.raw == "art. 5"
    assert citation.start == 0
    assert citation.end == 6


@pytest.mark.parametrize(
    ("text", "act"),
    [
        ("art. 23 k.p.c.", "k.p.c."),
        ("art. 17 k.p.k.", "k.p.k."),
        ("art. 148 k.k.", "k.k."),
        ("art. 56 k.k.s.", "k.k.s."),
        ("art. 22 k.s.h.", "k.s.h."),
        ("art. 145 p.p.s.a.", "p.p.s.a."),
    ],
)
def test_recognizes_selected_common_code_abbreviations(text, act):
    assert parse_polish_citations(text)[0].act == act


def test_paragraph_can_be_followed_directly_by_point_and_letter():
    citation = parse_polish_citations("art. 5 § 1 pkt 2 lit. a k.p.c.")[0]
    assert citation.paragraph == "1"
    assert citation.subsection is None
    assert citation.point == "2"
    assert citation.letter == "a"
    assert citation.act == "k.p.c."


@pytest.mark.parametrize(
    "text",
    [
        "art. 5-7",
        "art. 5–7",
        "art. 5 ust. 1-3",
        "art. 5 pkt 1 ust. 2",
    ],
)
def test_does_not_silently_truncate_unsupported_or_malformed_citations(text):
    assert parse_polish_citations(text) == []
