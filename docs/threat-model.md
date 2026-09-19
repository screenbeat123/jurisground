# Threat model

JurisGround is meant to catch mechanical grounding failures between generated text and supplied sources.

## In scope

- fabricated or altered quotations;
- numbers changed between the claim, quote, and matched source fragment;
- missing or unknown source IDs;
- low lexical overlap or claims that expand well beyond a quoted excerpt;
- optional mismatches between Polish statutory citations and source metadata;
- fail-closed batch validation when one claim fails.

## Out of scope

JurisGround does not determine whether a source is true, current, authoritative, legally controlling, complete, or correctly interpreted. It is not a legal reasoning engine and does not establish factual truth. A PASS means only that the configured checks passed.

## Security posture

Input should be treated as untrusted data. JurisGround performs no network calls and does not execute content from sources.
