import pytest

from jurisground import Claim, Policy, Source, verify_claim


@pytest.mark.xfail(strict=True, reason="Decimal fragments still collide in lexical scoring when numeric checks are disabled.")
def test_decimal_fragments_are_not_equivalent_numbers():
    quote = "The value was 0.1."
    result = verify_claim(
        Claim("C1", "00.001", quote, ("S1",)), [Source("S1", quote)],
        Policy(require_numbers_in_quote=False, require_numbers_in_source=False),
    )
    assert result.status == "fail"


@pytest.mark.xfail(strict=True, reason="The integer tokenizer does not support the dingbat digit U+2780.")
def test_identical_dingbat_digit_is_usable_content():
    quote = "The recorded value was ➀."
    result = verify_claim(Claim("C1", "➀", quote, ("S1",)), [Source("S1", quote)])
    assert result.status == "pass"
