# Threat model

JurisGround is designed for one narrow failure class: an LLM produces a claim and cites source material that does not actually support that claim.

## In scope

- fabricated or altered quotations;
- numeric facts changed between evidence and generated text;
- citations that exist but do not support the generated claim;
- missing/unknown source IDs;
- claims that materially expand beyond a cited excerpt;
- fail-closed batch validation when one claim fails.

## Out of scope

JurisGround does not determine whether a source is true, current, authoritative, legally controlling, complete, or correctly interpreted. It is not a legal reasoning engine and does not establish factual truth. A PASS means only that the configured deterministic grounding checks passed.

## Security posture

Input should be treated as untrusted data. The v0.1 core performs no network calls and executes no content from sources. Future parsers should preserve this property where possible.
