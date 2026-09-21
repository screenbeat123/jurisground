# Changelog

## 0.3.0 — 2026-09-22

- Compare claim and quote numbers with the matched source fragment, and expose `evidence_numbers` in results.
- Match whole numeric tokens so `100` cannot use part of `-100` or `1000` as evidence. Preserve signs and common grouped formats without guessing ambiguous separators such as `12,500`.
- Find the correct OCR fragment when a closer text match contains the wrong number.
- Match equivalent Unicode text while keeping offsets into the original source.
- Parse common Polish statutory citations and optionally bind them to source metadata. Reject unsupported ranges and malformed unit continuations without shortening them into another citation.
- Treat blank or unusable claims as `unverified`, and check lexical overlap for short claims too.
- Remove `Policy.min_content_stems_for_support` and require named arguments after the first three settings. Preserve the 0.2.0 `ClaimResult` constructor, with `findings` in position fifteen; new result fields require names.
- Report invalid CLI input without a traceback, accept UTF-8 BOM files, and preserve Unicode JSON output on Windows consoles.
- Include the synthetic demo and adversarial regression fixtures in source distributions.

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
