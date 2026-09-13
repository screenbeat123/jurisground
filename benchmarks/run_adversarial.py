from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from jurisground import Claim, Policy, Source, verify_claim

root = Path(__file__).parents[1]
rows = [json.loads(line) for line in (root / "evals" / "adversarial_cases.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
results = []
for row in rows:
    source = Source(**row["source"])
    claim_data = row["claim"]
    claim = Claim(claim_data["id"], claim_data["text"], claim_data.get("quote", ""), tuple(claim_data.get("source_ids") or []))
    result = verify_claim(claim, [source], Policy(**(row.get("policy") or {})))
    ok = result.status == row["expected_status"] and set(row.get("expected_codes") or []).issubset({f.code for f in result.findings})
    results.append((row, result, ok))

passed = sum(ok for _, _, ok in results)
categories = Counter(row["category"] for row, _, _ in results)
category_passed = Counter(row["category"] for row, _, ok in results if ok)
lines = [
    "# Adversarial regression report",
    "",
    f"Cases: **{len(results)}**  ",
    f"Expected outcomes matched: **{passed}/{len(results)}**",
    "",
    "This is a synthetic regression suite, not an empirical accuracy benchmark on real legal matters.",
    "",
    "| Category | Passed | Total |",
    "|---|---:|---:|",
]
for category in sorted(categories):
    lines.append(f"| {category} | {category_passed[category]} | {categories[category]} |")
lines += ["", "## Failures", ""]
failures = [(row, result) for row, result, ok in results if not ok]
if not failures:
    lines.append("None.")
else:
    for row, result in failures:
        lines.append(f"- `{row['name']}` expected `{row['expected_status']}`, got `{result.status}`")
(root / "reports" / "eval_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"{passed}/{len(results)} expected outcomes matched")
raise SystemExit(0 if passed == len(results) else 1)
