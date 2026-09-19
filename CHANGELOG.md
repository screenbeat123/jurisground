# Changelog

## Unreleased

- add optional parsing and source binding for common Polish statutory citations;
- validate claim and quote numbers against the actual matched source fragment, with `evidence_numbers` for diagnostics;
- improve fuzzy/OCR evidence selection while keeping comparison work bounded;
- preserve numeric signs, support common grouped formats, and stop guessing ambiguous forms such as `12,500`;
- treat blank or unusable claims as `unverified` and apply lexical-overlap checks to short claims;
- make later `Policy` options keyword-only and keep new `ClaimResult` fields from shifting existing positional calls;
- include adversarial fixtures in source distributions and keep packaging covered by CI.

## 0.2.0

- return the verified source fragment and character offsets for matched quotations;
- report whether a quote matched exactly, after normalization, or through fuzzy matching;
- keep span fields empty when a quote does not meet the verification threshold.

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
