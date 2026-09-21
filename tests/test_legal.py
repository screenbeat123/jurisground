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


@pytest.mark.parametrize(
    "reference",
    [
        "art. 471",
        "art. 106gba",
        "art. 471 § 12a",
        "art. 471 ust. 12ab",
        "art. 471 pkt 12abc",
        "art. 471 lit. aa",
    ],
)
@pytest.mark.parametrize("continuation", ["-472", " – 472", "—472", "−472"])
def test_rejects_ranges_without_shortening_numbers_or_suffixes(reference, continuation):
    assert parse_polish_citations(reference + continuation) == []


@pytest.mark.parametrize(
    "text",
    [
        "art. 17a-c",
        "art. 17a-bb",
        "art. 106gba-gbc",
        "art. 5 § 12a-bb",
        "art. 5 ust. 12a-bb",
        "art. 5 pkt 12a-bb",
        "art. 5 lit. a-c",
        "art. 5 lit. aa-ab",
        "art. 5 lit. a - aa",
        "art. 471 pkt 12 ust. 2",
        "art. 471 pkt 12§2",
        "art. 471§12§2",
        "art. 471 ust. 12 § 2",
        "art. 471 lit. ab pkt 2",
        "art. 471 k.c. ust. 2",
        "art. 471 ust.",
        "art. 471 pkt",
        "art. 471 lit.",
        "art. 471 lit. abc",
        "art. 471 lit. a2",
        "art. 471a2",
        "art. 471 pkt 12a2",
        "art. 471_2",
    ],
)
def test_rejects_malformed_continuations_without_returning_a_prefix(text):
    assert parse_polish_citations(text) == []


@pytest.mark.parametrize(
    "reference",
    [
        "art. 471",
        "art. 106gba",
        "art. 471§12a",
        "art. 471 § 12a ust. 12ab pkt 12abc lit. aa k.p.c.",
        "ART. 471 § 12A UST. 12AB PKT 12ABC LIT. AA K.P.C.",
    ],
)
def test_complete_citations_keep_their_original_span(reference):
    text = f"Stosuje się {reference}, zgodnie z umową."
    citations = parse_polish_citations(text)
    assert len(citations) == 1
    citation = citations[0]
    assert citation.raw == reference
    assert text[citation.start:citation.end] == reference


def test_rejected_citation_does_not_hide_a_later_valid_reference():
    text = "Odrzucono art. 471-472; zastosowano art. 106gba pkt 12a."
    citations = parse_polish_citations(text)
    assert [citation.raw for citation in citations] == ["art. 106gba pkt 12a"]
    citation = citations[0]
    assert text[citation.start:citation.end] == citation.raw


@pytest.mark.parametrize(
    ("reference", "prose"),
    [
        ("art. 471", "– przepis o odpowiedzialności"),
        ("art. 471", "— to podstawa odpowiedzialności"),
        ("art. 17a", "– przepis szczególny"),
        ("art. 106gba", "— określa obowiązki"),
        ("art. 5 lit. a", "— określa obowiązki"),
        ("art. 5 lit. aa", "— określa obowiązki"),
        ("art. 471 k.c.", "— a nie art. 472"),
    ],
)
def test_dash_before_prose_does_not_make_a_complete_citation_a_range(reference, prose):
    text = f"Stosuje się {reference} {prose}."
    citation = parse_polish_citations(text)[0]
    assert citation.raw == reference
    assert text[citation.start:citation.end] == reference


@pytest.mark.parametrize("separator", ["-", " - ", " — "])
def test_explicit_article_after_a_dash_preserves_both_citations(separator):
    text = f"art. 106gba{separator}art. 106gbc"
    assert [citation.raw for citation in parse_polish_citations(text)] == ["art. 106gba", "art. 106gbc"]
