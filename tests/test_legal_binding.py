import json
import subprocess
import sys

import pytest

from jurisground import Claim, Policy, Source, verify_batch, verify_claim


QUOTE = "Art. 471 k.c. określa odpowiedzialność za niewykonanie zobowiązania."
POLICY = Policy(require_legal_citation_match=True)


def check(claim_text, legal_citation, *, source_text=QUOTE, source_ids=("S1",), sources=None):
    if sources is None:
        sources = [Source("S1", source_text, legal_citation=legal_citation)]
    return verify_claim(Claim("C1", claim_text, QUOTE, source_ids), sources, POLICY)


def codes(result):
    return {finding.code for finding in result.findings}


def test_exact_legal_citation_matches():
    result = check(QUOTE, "art. 471 k.c.")
    assert result.status == "pass"
    assert result.claim_legal_citation == {
        "article": "471", "paragraph": None, "subsection": None,
        "point": None, "letter": None, "act": "k.c.",
    }
    assert result.evidence_legal_citation == result.claim_legal_citation


def test_evidence_may_be_more_specific_than_claim():
    result = check(QUOTE, "art. 471 § 1 k.c.")
    assert result.status == "pass"
    assert result.evidence_legal_citation["paragraph"] == "1"


@pytest.mark.parametrize(
    ("claim_text", "evidence", "field"),
    [
        (QUOTE, "art. 472 k.c.", "article"),
        (QUOTE, "art. 471 k.p.c.", "act"),
        ("Art. 471 § 2 k.c. określa odpowiedzialność za niewykonanie zobowiązania.", "art. 471 § 1 k.c.", "paragraph"),
        ("Art. 471 ust. 2 k.c. określa odpowiedzialność za niewykonanie zobowiązania.", "art. 471 ust. 1 k.c.", "subsection"),
        ("Art. 471 pkt 2 k.c. określa odpowiedzialność za niewykonanie zobowiązania.", "art. 471 pkt 1 k.c.", "point"),
        ("Art. 471 pkt 1 lit. b k.c. określa odpowiedzialność za niewykonanie zobowiązania.", "art. 471 pkt 1 lit. a k.c.", "letter"),
    ],
)
def test_mismatch_reports_specific_field(claim_text, evidence, field):
    result = verify_claim(
        Claim("C1", claim_text, claim_text, ("S1",)),
        [Source("S1", claim_text, legal_citation=evidence)],
        POLICY,
    )
    assert result.status == "fail"
    finding = next(f for f in result.findings if f.code == "legal_citation_mismatch")
    assert field in finding.details["fields"]


def test_claim_more_specific_than_evidence_fails():
    text = "Art. 471 § 1 k.c. określa odpowiedzialność za niewykonanie zobowiązania."
    result = verify_claim(Claim("C1", text, text, ("S1",)), [Source("S1", text, legal_citation="art. 471 k.c.")], POLICY)
    assert result.status == "fail"
    assert "legal_citation_mismatch" in codes(result)


def test_missing_evidence_metadata_fails_closed():
    result = check(QUOTE, None)
    assert result.status == "fail"
    assert "legal_evidence_citation_missing" in codes(result)


@pytest.mark.parametrize("value", ["not a citation", "art. 471 k.c.; art. 472 k.c.", "art. 5-7 k.c."])
def test_invalid_evidence_metadata_fails_closed(value):
    result = check(QUOTE, value)
    assert result.status == "fail"
    assert "legal_evidence_citation_invalid" in codes(result)


def test_missing_claim_citation_fails_when_required():
    text = "Dłużnik odpowiada za niewykonanie zobowiązania."
    result = verify_claim(Claim("C1", text, text, ("S1",)), [Source("S1", text, legal_citation="art. 471 k.c.")], POLICY)
    assert result.status == "fail"
    assert "legal_citation_missing" in codes(result)


def test_multiple_claim_citations_are_ambiguous():
    text = "Art. 471 k.c. oraz art. 472 k.c. określają odpowiedzialność dłużnika."
    result = verify_claim(Claim("C1", text, text, ("S1",)), [Source("S1", text, legal_citation="art. 471 k.c.")], POLICY)
    assert result.status == "fail"
    assert "legal_citation_ambiguous" in codes(result)


def test_default_policy_does_not_enable_legal_binding():
    result = verify_claim(Claim("C1", QUOTE, QUOTE, ("S1",)), [Source("S1", QUOTE, legal_citation="art. 999 k.p.c.")])
    assert result.status == "pass"
    assert result.claim_legal_citation is None
    assert result.evidence_legal_citation is None


def test_binding_uses_source_that_supplied_quote():
    other = "Art. 471 k.c. Inny tekst, który nie zawiera cytatu z roszczenia."
    sources = [
        Source("S1", other, legal_citation="art. 471 k.c."),
        Source("S2", QUOTE, legal_citation="art. 472 k.c."),
    ]
    result = check(QUOTE, None, source_ids=("S1", "S2"), sources=sources)
    assert result.matched_source_id == "S2"
    assert result.status == "fail"
    assert "legal_citation_mismatch" in codes(result)


def test_claim_without_act_can_bind_to_specific_act():
    text = "Art. 471 określa odpowiedzialność za niewykonanie zobowiązania."
    result = verify_claim(Claim("C1", text, text, ("S1",)), [Source("S1", text, legal_citation="art. 471 k.c.")], POLICY)
    assert result.status == "pass"


def test_batch_serializes_legal_audit_fields():
    result = verify_batch([Claim("C1", QUOTE, QUOTE, ("S1",))], [Source("S1", QUOTE, legal_citation="art. 471 § 1 k.c.")], POLICY)
    assert result["status"] == "pass"
    item = result["claims"][0]
    assert item["claim_legal_citation"]["article"] == "471"
    assert item["evidence_legal_citation"]["paragraph"] == "1"


def test_cli_reads_source_legal_citation_and_policy(tmp_path):
    path = tmp_path / "input.json"
    path.write_text(json.dumps({
        "sources": [{"id": "S1", "text": QUOTE, "legal_citation": "art. 472 k.c."}],
        "claims": [{"id": "C1", "text": QUOTE, "quote": QUOTE, "source_ids": ["S1"]}],
        "policy": {"require_legal_citation_match": True},
    }, ensure_ascii=False), encoding="utf-8")
    process = subprocess.run([sys.executable, "-m", "jurisground.cli", str(path)], capture_output=True, text=True, timeout=10)
    assert process.returncode == 2, process.stderr
    payload = json.loads(process.stdout)
    assert payload["claims"][0]["claim_legal_citation"]["article"] == "471"
    assert "legal_citation_mismatch" in {f["code"] for f in payload["claims"][0]["findings"]}
