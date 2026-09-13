import json
from pathlib import Path

from jurisground import Claim, Policy, Source, verify_claim


def test_adversarial_eval_suite():
    path = Path(__file__).parents[1] / "evals" / "adversarial_cases.jsonl"
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert rows
    for row in rows:
        source = Source(**row["source"])
        claim_data = row["claim"]
        claim = Claim(
            id=claim_data["id"], text=claim_data["text"], quote=claim_data.get("quote", ""),
            source_ids=tuple(claim_data.get("source_ids") or []),
        )
        policy = Policy(**(row.get("policy") or {}))
        result = verify_claim(claim, [source], policy)
        assert result.status == row["expected_status"], row["name"]
        expected_codes = set(row.get("expected_codes") or [])
        actual_codes = {finding.code for finding in result.findings}
        assert expected_codes.issubset(actual_codes), (row["name"], expected_codes, actual_codes)
