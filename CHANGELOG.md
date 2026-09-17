# Changelog

## Unreleased

- optionally bind a Polish statutory citation in a claim to legal-unit metadata on the matched source;
- parse common Polish statutory citations into structured article/paragraph/subsection/point/letter fields with original source offsets;
- include the adversarial JSONL fixture in source distributions;
- return `unverified` for blank claims and claims without usable content tokens;
- apply the overlap check to short claims, and reject zero overlap even with a zero threshold;
- remove `Policy.min_content_stems_for_support` (alpha API change); use named arguments without that keyword;
- replace the old bypass test with regression cases and positive controls, including batch and CLI results;
- document status meanings and the remaining numeric, Unicode, and semantic limitations;
- make Policy settings after the first three fields keyword-only so old positional calls cannot silently change numeric checks;
- exclude separator-only tokens from lexical comparisons while retaining hyphenated words;
- reuse numeric normalization for digit-only integer tokens in overlap scoring, including leading zeros.

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
