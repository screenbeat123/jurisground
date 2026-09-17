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

This parser is intentionally conservative. It does not currently resolve citations against ELI/ISAP, check whether a provision is in force, interpret the provision, parse ranges, or handle sentence/tiret references. Unsupported ranges and malformed unit order are ignored rather than silently truncated into a different citation.

The next legal-specific layer can use these structured references and offsets to bind a generated citation to the exact provision present in supplied evidence.
