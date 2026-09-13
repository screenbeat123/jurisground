# JurisGround

**Verify that LLM-generated claims are actually supported by their cited sources.**

JurisGround checks a simple but important question: **does the generated claim actually come from the sources it cites?**

A real citation is not enough. A model can cite an existing document while changing a number, inventing a quotation, or making a stronger claim than the evidence supports. JurisGround adds a deterministic verification layer between generation and publication.

> Status: early OSS extraction from a larger working legal-AI system. v0.1 is intentionally small and has no hosted-model dependency.

## What it checks

- **Quote integrity** — can the cited quotation be found in the cited source?
- **Numeric provenance** — do numeric facts in the claim occur in the quote and source?
- **Claim-to-evidence support** — does the wording of the claim have measurable support in the cited evidence?
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
pip install -e .
```

## CLI

```bash
jurisground examples/legal_grounding_demo.json --pretty
```

The CLI exits with `0` only when the whole batch passes. `fail` and `unverified` return a non-zero exit code, which makes the gate usable in CI or agent workflows.

## Python

The public API exposes `Source`, `Claim`, `Policy`, `verify_claim`, and `verify_batch`.

## Adversarial regression suite

The repository includes a synthetic regression suite covering fabricated quotations, changed numeric facts, missing citations, fuzzy/OCR-like text, unsupported claims, and valid grounded claims.

Run:

```bash
pytest
python benchmarks/run_adversarial.py
```

See `reports/eval_report.md` for the current generated report.

**This is a regression suite, not a real-world legal accuracy benchmark.**

## Design principles

1. **Deterministic before probabilistic.** Validation should be inspectable and reproducible.
2. **Evidence over confidence.** A model's confidence score is not source support.
3. **Fail closed.** Missing evidence should not silently become a PASS.
4. **No model lock-in.** The validator does not require a hosted LLM.
5. **No private corpus required.** Tests use synthetic fixtures.

## Scope and limitations

JurisGround verifies evidence linkage. It does **not** establish that a source is true, current, authoritative, legally controlling, complete, or correctly interpreted. A PASS means the configured grounding checks passed — not that the claim is factually or legally correct.

The lexical support score in v0.1 is intentionally simple and auditable. It is a guardrail, not semantic entailment. Future versions may add optional model-based entailment while keeping deterministic checks independently visible.

## Why legal AI first?

The project was extracted from a local-first Polish legal research/drafting system where unsupported claims, wrong amounts, and fabricated quotations have disproportionate cost. The core is domain-neutral; `jurisground.adapters.pl_legal` keeps Polish legal normalization separate from the generic verifier.

## Roadmap

- richer source-span provenance;
- optional JSON Schema for agent outputs;
- configurable domain adapters;
- NLI/LLM entailment as an optional second opinion, never a replacement for deterministic checks;
- larger open adversarial corpus;
- PR bot that reports grounding regressions.

## License

Apache-2.0.
