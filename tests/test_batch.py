from jurisground import Claim, Source, verify_batch


def test_batch_fail_closed():
    source = Source("S1", "The source says the payment was PLN 10 000.")
    claims = [
        Claim("C1", "The payment was PLN 10 000.", "The source says the payment was PLN 10 000.", ("S1",)),
        Claim("C2", "The payment was PLN 99 000.", "The source says the payment was PLN 10 000.", ("S1",)),
    ]
    result = verify_batch(claims, [source])
    assert result["status"] == "fail"
    assert result["summary"] == {"total": 2, "pass": 1, "fail": 1, "unverified": 0}


def test_batch_unverified_when_no_failures_but_missing_citation():
    source = Source("S1", "The source contains an adequately long statement about the agreement.")
    claims = [Claim("C1", "The agreement exists.", "The source contains an adequately long statement about the agreement.", ())]
    result = verify_batch(claims, [source])
    assert result["status"] == "unverified"
