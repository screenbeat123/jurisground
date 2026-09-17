# Polish legal citations

`parse_polish_citations()` extracts common Polish statutory references into structured fields while preserving the exact source span.

Supported citation units in this first version:

- `art.` — article;
- `§` — paragraph, mainly for codes;
- `ust.` — subsection;
- `pkt` — point;
- `lit.` — letter.

The parser accepts article and lower-unit numbers with amendment suffixes such as `17a` or `106gba`. It also recognizes a small explicit set of common code abbreviations: `k.c.`, `k.p.c.`, `k.k.`, `k.p.k.`, `k.r.o.`, `k.p.`, `k.s.h.`, `k.k.s.`, and `p.p.s.a.`.

Each result contains the original `raw` text, `start` and `end` offsets, and normalized component values. Offsets use normal Python slice semantics, so `text[result.start:result.end] == result.raw`.

The component order follows the Polish legislative drafting convention for references such as `art. ... ust. ... pkt ... lit. ...`. The implementation also accepts `§` after `art.` for code-style references.

## Binding a citation to evidence

The grounding gate can optionally bind one parsed citation in a claim to legal-unit metadata attached to the source that supplied the verified quote. Set `Source.legal_citation` to one supported citation and enable `Policy(require_legal_citation_match=True)`.

The comparison is directional: every component explicitly stated by the claim must match the evidence metadata. Evidence may be more specific, so a claim citing `art. 471 k.c.` can be supported by a source tagged `art. 471 § 1 k.c.`. The reverse is rejected because article-level metadata cannot prove a paragraph-specific citation.

The first binding version intentionally requires exactly one supported citation in the claim and exactly one in the matched source metadata. Metadata may have surrounding whitespace, but after trimming the entire value must be the citation; surrounding prose or punctuation is rejected. Missing, ambiguous, invalid or mismatched metadata produces a focused finding instead of silently skipping the legal check. `ClaimResult` includes normalized `claim_legal_citation` and `evidence_legal_citation` fields for auditing.

Legal binding is opt-in and does not change the generic grounding behavior when disabled. For precise results, represent legal chunks as separate sources and attach the citation of the unit represented by each chunk.

This parser and binding check are intentionally conservative. They do not resolve citations against ELI/ISAP, check whether a provision is in force, interpret the provision, parse ranges, or handle sentence/tiret references. Unsupported ranges and malformed unit order are ignored rather than silently truncated into a different citation.
