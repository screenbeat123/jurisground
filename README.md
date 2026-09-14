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
- **Numeric provenance** — do numeric facts in the claim occur in the quote and source?
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

A verified quote also returns `matched_text`, `matched_start`, `matched_end`, and `match_method`. Offsets are relative to the original matched page text and use normal Python slice semantics: `matched_start` is inclusive and `matched_end` is exclusive. `match_method` is `exact`, `normalized`, or `fuzzy`. These fields stay empty when the quote does not meet its verification threshold.

## Result status

- `pass`: the configured checks found no violation. This is not confirmation of factual or legal correctness, or semantic entailment.
- `fail`: an implemented validation rule failed. `findings` identifies the rule.
- `unverified`: required input is missing or there is nothing the tokenizer can assess. Empty batches, blank claims, and claims without usable content tokens are not successful validations.

Claims with one or two usable tokens are checked too. Zero lexical overlap always fails, even when `min_claim_support` is zero. Positive overlap must meet the configured threshold. An `unverified` result may return before quote matching; default zero scores on that path are not measurements.

### Unreleased API change

`Policy.min_content_stems_for_support` has been removed: claim length can no longer disable the overlap check. Remove that keyword from existing calls and use named `Policy` arguments. `min_claim_support` still controls the required positive overlap. Passing the removed keyword raises `TypeError` instead of silently ignoring it.

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

Signed and locale-sensitive numbers, checking numbers against the matched fragment rather than the whole cited material, and canonically equivalent Unicode spans still need fixes. Do not use this alpha version as the sole approval gate for consequential documents. The current change fixes empty and short claims; it does not resolve those other findings.

## Why legal AI first?

The parent project is a local-first Polish legal research and drafting system where unsupported claims, wrong amounts, and fabricated quotations have disproportionate cost. JurisGround extracts the domain-neutral verification core. Domain-specific normalization stays outside the public package until there is a reusable adapter with a clear API.

## Roadmap

- optional JSON Schema for agent outputs;
- larger public regression corpus based on reproduced failures;
- NLI/LLM entailment as an optional second opinion, never a replacement for deterministic checks;
- PR bot that reports grounding regressions.

## License

Apache-2.0.
