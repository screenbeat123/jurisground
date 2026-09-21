# Synthetic grounding demo

This fixture is **SYNTHETIC**: every source and claim was written for development and testing. It is not a real legal matter or a record of production or external use.

From the repository or an unpacked source distribution, install the package and run:

```bash
python -m pip install .
python -m jurisground.cli examples/legal_grounding_demo.json --pretty
```

The input contains one source, three claims, and `require_legal_citation_match=true`. Each claim quotes the same source sentence. The second changes the amount in the claim; the third changes the act abbreviation from `k.c.` to `k.p.c.`.

| Claim | Expected status | What the result shows |
| --- | --- | --- |
| `supported` | `pass` | The quote, amount, and citation match. |
| `changed_amount` | `fail` | `9200` is absent from the quote and matched evidence. |
| `changed_citation` | `fail` | `legal_citation_mismatch` identifies the changed act. |

The batch returns `fail`, with one passing claim and two failing claims. Exit code **2 is expected** because the example deliberately includes errors. In the JSON output, inspect `matched_text`, `evidence_numbers`, the legal-citation fields, and `findings` to see which evidence each check used.

These outcomes demonstrate the implemented checks on invented inputs. They do not measure legal accuracy or establish that a claim follows logically from its source.
