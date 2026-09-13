# Changelog

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
