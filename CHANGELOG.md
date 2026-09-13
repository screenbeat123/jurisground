# Changelog

## 0.1.2

- remove two misleading Policy switches that did not have sound public semantics;
- treat an empty batch as `unverified` instead of `pass`;
- remove unused finding severity plumbing and the unused Polish legal adapter;
- trim synthetic regression cases to distinct behaviors and remove the duplicate benchmark/report path;
- replace artificial test wording with natural examples;
- clarify that the public repository was extracted from a longer-lived parent project.

## 0.1.1

- base lexical-support gating on normalized content stems instead of raw whitespace-separated words;
- expose the minimum content-stem count and expansion-support threshold through `Policy`;
- add regression coverage for stopword-heavy claims and configurable support thresholds.

## 0.1.0

- extracted a standalone deterministic grounding core from a larger legal-AI system;
- quote existence/fuzzy matching;
- numeric provenance checks;
- claim-to-quote and claim-to-source support scores;
- source-ID validation;
- fail-closed batch gate;
- CLI, synthetic adversarial regression suite, and GitHub Actions CI;
- optional Polish legal normalization adapter.
