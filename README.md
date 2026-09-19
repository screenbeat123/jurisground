# JurisGround

**Check quoted text and numeric tokens against sources; report lexical overlap.**

[![CI](https://github.com/screenbeat123/jurisground/actions/workflows/ci.yml/badge.svg)](https://github.com/screenbeat123/jurisground/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.10--3.12-blue)
![License](https://img.shields.io/badge/license-Apache--2.0-blue)

JurisGround locates quotations in supplied sources and runs numeric-token and lexical-overlap checks. It reports the matching fragment and rule violations. It does not decide whether a claim is true or follows logically from a source.

> JurisGround is the public extraction of grounding checks from a longer-lived private legal-AI project. The Git history in this repository starts at the extraction point; it does not represent the age or full history of the parent system.

The public package is intentionally small and has no hosted-model dependency.

## What it checks

- **Quote integrity** — can the cited quotation be found in the cited source?
- **Evidence location** — which source fragment matched, and where is it on the page?
- **Numeric checks** — do parsed numbers in the quote and claim agree with the matched source fragment?
- **Lexical overlap** — how much of the claim wording appears in the quoted evidence? This score does not establish agreement in meaning.
- **Source provenance** — are cited source IDs present and resolvable?
- **Fail-closed batch validation** — one failed claim can block the batch from being treated as grounded.

## Three failure cases

### 1. Fabricated quote

Source: `The court dismissed the claim because causation was not proven.`

Generated text: `The defendant admitted liability.`

Result: **FAIL — quote_not_found**

### 2. Changed number

Source: `The invoice total was PLN 92 250,00.`

Generated text: `The invoice total was PLN 98 250.`

Result: **FAIL — number_not_in_quote / number_not_in_source**

### 3. Real citation, unsupported claim

A quote can exist in the source but still fail to support the generated claim. JurisGround scores claim-to-quote and claim-to-source support separately so a valid citation is not automatically treated as evidence.

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

The CLI exits with `0` only when the whole batch passes. `fail` and `unverified` return a non-zero exit code, which makes the gate usable in CI or agent workflows.

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

The public API exposes `Source`, `Claim`, `Policy`, `verify_claim`, and `verify_batch`.

A quote match above the similarity threshold also returns `matched_text`, `matched_start`, `matched_end`, and `match_method`. Offsets are relative to the original matched page text and use normal Python slice semantics: `matched_start` is inclusive and `matched_end` is exclusive. `match_method` is `exact`, `normalized`, or `fuzzy`. These fields stay empty when no candidate meets the similarity threshold. A located fragment can still fail numeric or lexical checks; its presence is not approval of the quote or claim.

## Numeric evidence

With `require_numbers_in_source=True` (the default), numeric checks use the located source fragment as well as the cited corpus. `quote_number_mismatch` means the quote and that fragment have different parsed number sequences, including order and repetition. `number_not_in_evidence` means a claim number is missing from that fragment. A matching number elsewhere in the document, on another page, or in another cited source does not satisfy this check.

`evidence_numbers` contains the numbers parsed from `matched_text`. It is `null` when no above-threshold candidate is available, and `[]` when the candidate contains no numbers. `source_numbers` keeps its existing meaning: all numbers from the cited material, for diagnostics. It is not the basis for approving a number absent from the matched fragment.

`require_numbers_in_quote` controls claim-to-quote membership. `require_numbers_in_source` controls the source and matched-fragment checks, including quote-number integrity. Setting the latter to `False` explicitly disables those checks; the reported evidence numbers do not mean they were enforced.

For fuzzy matching, JurisGround checks other above-threshold fragments, including separate candidates on the same page, before failing solely because the highest-similarity candidate has a different numeric sequence. Adjacent window boundaries are refined under a fixed comparison budget so a nearby date or amount is less likely to be pulled into an otherwise valid match without making long fuzzy checks grow quadratically. If no numerically compatible candidate exists, the best verified fragment is still returned with the numeric findings. Numeric membership does not establish who a number refers to, its unit, or its legal significance. Signed integers preserve a leading minus; the Unicode minus sign `−` is normalized to `-`. An explicit plus is treated as positive, so `+100` and `100` compare equally. Negative zero is normalized to zero.

Separator handling is deliberately conservative rather than locale-inferred. Space/NBSP grouping and unambiguous repeated or mixed grouping forms are normalized numerically. A single comma or dot followed by exactly three digits is kept separator-sensitive because forms such as `12,500` and `12.500` are ambiguous across locales. As a result, `12,500`, `12.500`, `12500`, and `12.5` are not silently treated as the same value.


## Result status

- `pass`: the configured checks found no violation. This is not confirmation of factual or legal correctness, or semantic entailment.
- `fail`: an implemented validation rule failed. `findings` identifies the rule.
- `unverified`: required input is missing or there is nothing the tokenizer can assess. Empty batches, blank claims, and claims without usable content tokens are not successful validations.

Claims with one or two usable tokens are checked too. Zero lexical overlap always fails, even when `min_claim_support` is zero. Positive overlap must meet the configured threshold. An `unverified` result may return before quote matching; default zero scores on that path are not measurements.

Tokens containing only separators, such as `---` or `___`, are not usable claim content. Digit-only integer tokens use the existing numeric normalizer in overlap scoring: `00100` and `100` compare equally in either direction, including inside longer text. This is not a new rule for signed numbers or locale-sensitive separators.

### Unreleased API change

`Policy.min_content_stems_for_support` has been removed: claim length can no longer disable the overlap check. Remove that keyword from existing calls. `min_claim_support` still controls the required positive overlap. Passing the removed keyword raises `TypeError`.

Only the first three fields (`quote_threshold`, `ocr_quote_threshold`, `min_claim_support`) accept positional arguments. All later settings, starting with `max_expansion_ratio`, must be named. Old calls with more than three positional arguments now raise `TypeError` rather than silently shifting values and changing which numeric checks run. For example, use `Policy(require_numbers_in_quote=False)` to disable only the quote-number check; the source-number check stays enabled.

## Regression cases

The repository includes a small synthetic regression set covering fabricated quotations, changed numeric facts, missing citations, OCR-like text, unsupported claims, and valid grounded claims.

Run:

```bash
pytest
```

**This is a regression suite, not a real-world legal accuracy benchmark.**

## Design principles

1. **Deterministic before probabilistic.** Validation should be inspectable and reproducible.
2. **Evidence over confidence.** A model's confidence score is not source support.
3. **Fail closed.** Missing evidence should not silently become a PASS.
4. **No model lock-in.** The validator does not require a hosted LLM.
5. **No private corpus required.** Tests use synthetic fixtures.

## Scope and limitations

JurisGround verifies evidence linkage. It does **not** establish that a source is true, current, authoritative, legally controlling, complete, or correctly interpreted. A PASS means the configured grounding checks passed — not that the claim is factually or legally correct.

The lexical support score is intentionally simple and auditable. It is a guardrail, not semantic entailment. The default thresholds are heuristic baselines carried over from the parent system; they are configurable and are not presented as universally calibrated values.

### Known limitations still under review

Lexical overlap can miss negation and changes in who did what. For example, `did not pay` and `did pay` can receive the same score. A matching quote is not proof that a paraphrase follows from it.

Locale-specific interpretation beyond the conservative separator rules above and canonically equivalent Unicode spans still need fixes. With both numeric checks disabled, the lexical scorer can also conflate `00.001` with `0.1`; the dingbat digit `➀` is currently treated as unassessable content. These two reported cases are tracked as strict expected-failure tests, not counted as passing tests. Do not use this alpha version as the sole approval gate for consequential documents. Empty/short-claim validation and numeric binding to the matched fragment have been addressed. The other findings above remain unresolved.

## Why legal AI first?

The parent project is a local-first Polish legal research and drafting system where unsupported claims, wrong amounts, and fabricated quotations have disproportionate cost. JurisGround extracts the domain-neutral verification core. Domain-specific normalization stays outside the public package until there is a reusable adapter with a clear API.

## Roadmap

- optional JSON Schema for agent outputs;
- larger public regression corpus based on reproduced failures;
- NLI/LLM entailment as an optional second opinion, never a replacement for deterministic checks;
- PR bot that reports grounding regressions.

## License

Apache-2.0.
