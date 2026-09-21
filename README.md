# JurisGround

**Check quotes, numbers, and source references in LLM output.**

[![CI](https://github.com/screenbeat123/jurisground/actions/workflows/ci.yml/badge.svg)](https://github.com/screenbeat123/jurisground/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.10--3.12-blue)
![License](https://img.shields.io/badge/license-Apache--2.0-blue)

JurisGround checks whether quoted text can be found in supplied sources, whether numbers agree with the matched evidence, and whether cited source IDs resolve. It also reports simple lexical overlap. It does not decide whether a claim is true or logically follows from a source.

> JurisGround was extracted from a longer-lived private legal-AI project. This repository starts at the extraction point; the parent project's private history and data are not included.

The package is small, deterministic, and makes no network calls.

## What it checks

- **Quote matching** — can the quoted text be found in the cited source?
- **Evidence span** — which source fragment matched, and where is it on the page?
- **Number checks** — do numbers in the claim and quote agree with that fragment?
- **Source IDs** — are the cited sources available?
- **Polish legal citations** — optionally bind a parsed statutory citation to metadata on the matched source.
- **Lexical overlap** — how much of the claim wording appears in the quoted evidence?
- **Batch validation** — a failed claim keeps the whole batch from passing.

## Three failure cases

### 1. Fabricated quote

Source: `The court dismissed the claim because causation was not proven.`

Generated text: `The defendant admitted liability.`

Result: **FAIL — quote_not_found**

### 2. Changed number

Source: `The invoice total was PLN 92 250,00.`

Generated text: `The invoice total was PLN 98 250.`

Result: **FAIL — number_not_in_quote / number_not_in_source**

### 3. Real quote, weak claim overlap

A quote can be real while the generated claim adds wording that is not present in it. JurisGround reports claim-to-quote and claim-to-source lexical overlap separately.

## Install

```bash
git clone https://github.com/screenbeat123/jurisground.git
cd jurisground
pip install -e .
```

For development:

```bash
pip install -e .[dev]
```

## CLI

```bash
jurisground examples/legal_grounding_demo.json --pretty
```

The CLI reads a UTF-8 JSON object; a UTF-8 BOM is accepted. Optional `sources` and `claims` arrays default to empty, and `policy` defaults to an empty object. Source and claim IDs must be nonempty strings. Text fields and entries in `pages` or `source_ids` must be strings; `is_ocr` and policy switches must be booleans. Numeric policy values must be finite numbers, and `min_quote_chars` must be an integer. Unknown policy options are rejected.

The CLI prints JSON and exits with `0` when the whole batch passes, or `2` for `fail` and `unverified`. Invalid JSON, unreadable files, missing IDs, and invalid field types produce an error on stderr, no JSON output, and exit code `2`. Non-ASCII characters use JSON escapes so output works on Windows consoles; JSON readers recover the original Unicode text.

Abbreviated failure output:

```json
{
  "status": "fail",
  "summary": {
    "total": 1,
    "pass": 0,
    "fail": 1,
    "unverified": 0
  },
  "claims": [
    {
      "claim_id": "C1",
      "status": "fail",
      "findings": [
        {
          "code": "quote_not_found"
        },
        {
          "code": "number_not_in_source"
        }
      ]
    }
  ]
}
```

## Python

The main API is `Source`, `Claim`, `Policy`, `verify_claim`, and `verify_batch`. `parse_polish_citations()` and `PolishLegalCitation` provide the optional Polish citation parser.

A quote match above the similarity threshold also returns `matched_text`, `matched_start`, `matched_end`, and `match_method`. Offsets point to the original page text, even when Unicode or whitespace normalization was needed for the match. `matched_start` is inclusive and `matched_end` is exclusive. `match_method` is `exact`, `normalized`, or `fuzzy`. These fields stay empty when no candidate meets the similarity threshold.

## Numeric evidence

With `require_numbers_in_source=True` (the default), numbers in the quote are compared with the selected source fragment. A number elsewhere in the document, on another page, or in another cited source does not count as evidence for that claim.

`quote_number_mismatch` means the quote and matched fragment contain different number sequences. `number_not_in_evidence` means a claim number is missing from the matched fragment. `evidence_numbers` shows the numbers from `matched_text`; `source_numbers` remains a corpus-wide diagnostic.

For fuzzy or OCR matches, JurisGround can choose another above-threshold fragment when the best text match has different numbers. Candidate search is bounded. This still does not tell you what a number refers to or whether its unit is correct.

Signs are preserved: `-100` and `−100` are both negative, while `+100` matches `100`. Thousands and decimal separators are handled conservatively. Clear formats such as `1,234,567` or `12.500,00` are normalized. Ambiguous forms such as `12,500` are kept as written rather than guessed as `12.5` or `12500`.

`require_numbers_in_quote=False` disables claim-to-quote number membership. `require_numbers_in_source=False` disables source and matched-fragment number checks.

## Result status

- `pass`: the configured checks found no violation. This is not confirmation of factual or legal correctness, or semantic entailment.
- `fail`: an implemented validation rule failed. `findings` identifies the rule.
- `unverified`: required input is missing or there is nothing the tokenizer can assess. Empty batches, blank claims, and claims without usable content tokens are not successful validations.

Claims with one or two usable tokens are checked too. Zero lexical overlap always fails, even when `min_claim_support` is zero. Positive overlap must meet the configured threshold. An `unverified` result may return before quote matching; default zero scores on that path are not measurements.

Tokens containing only separators, such as `---` or `___`, are not usable claim content. Digit-only integers use the same numeric normalization during lexical scoring, so `00100` and `100` compare equally.

### Unreleased API change

`Policy.min_content_stems_for_support` has been removed: claim length can no longer disable the overlap check. Remove that keyword from existing calls. `min_claim_support` still controls the required positive overlap. Passing the removed keyword raises `TypeError`.

Only the first three fields (`quote_threshold`, `ocr_quote_threshold`, `min_claim_support`) accept positional arguments. All later settings, starting with `max_expansion_ratio`, must be named. Old calls with more than three positional arguments now raise `TypeError` rather than silently shifting values and changing which numeric checks run. For example, use `Policy(require_numbers_in_quote=False)` to disable only the quote-number check; the source-number check stays enabled.

`ClaimResult` preserves the 0.2.0 positional constructor: the fifteenth argument is `findings`. New fields (`claim_legal_citation`, `evidence_legal_citation`, and `evidence_numbers`) must be passed by name. The 17-argument layout introduced during unreleased development now raises `TypeError`; move its two legal-citation arguments to named fields and keep `findings` in position fifteen or pass it by name.

## Regression cases

The repository includes a small synthetic regression set covering fabricated quotations, changed numeric facts, missing citations, OCR-like text, unsupported claims, and valid grounded claims.

Run:

```bash
pytest
```

**This is a regression suite, not a real-world legal accuracy benchmark.**

## Design

JurisGround is deterministic and offline. Missing evidence fails closed instead of becoming a pass, and the core does not require a hosted model. Tests use synthetic fixtures rather than private legal data.

## Scope and limitations

JurisGround checks mechanical links between a claim and its cited evidence. It does **not** judge whether a source is correct, current, legally controlling, or properly interpreted. A PASS means the configured checks passed, not that the claim is factually or legally correct.

Lexical overlap is deliberately simple. It is not semantic entailment. The default thresholds came from the parent project and are heuristics, not calibrated guarantees.

### Known limitations still under review

Lexical overlap can miss negation and changes in who did what. For example, `did not pay` and `did pay` can receive the same score. A matching quote is not proof that a paraphrase follows from it.

The number parser does not infer a locale beyond the conservative separator rules above, and it does not know what a number refers to. With numeric checks disabled, lexical scoring can also conflate `00.001` with `0.1`; the dingbat digit `➀` is still unsupported. Those two cases are tracked as expected failures. A PASS is only a grounding check; it is not final approval of a document.

## Origin

JurisGround came out of a local-first Polish legal research and drafting project, where wrong quotes and amounts are costly. The public package contains the reusable checks, not the parent application's private data or workflow. See [docs/origin.md](docs/origin.md) for more context.

## Roadmap

- optional JSON Schema for agent outputs;
- larger public regression corpus based on reproduced failures;
- NLI/LLM entailment as an optional second opinion, never a replacement for deterministic checks;
- PR bot that reports grounding regressions.

## License

Apache-2.0.
