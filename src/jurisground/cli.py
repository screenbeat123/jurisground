from __future__ import annotations

import argparse
import json
from pathlib import Path

from .gate import verify_batch
from .models import Claim, Policy, Source


def _load(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _source(item: dict) -> Source:
    return Source(
        id=str(item["id"]),
        text=str(item.get("text") or ""),
        pages=tuple(str(x) for x in (item.get("pages") or [])),
        is_ocr=bool(item.get("is_ocr")),
        legal_citation=str(item["legal_citation"]) if item.get("legal_citation") is not None else None,
    )


def _claim(item: dict) -> Claim:
    return Claim(
        id=str(item["id"]),
        text=str(item.get("text") or ""),
        quote=str(item.get("quote") or ""),
        source_ids=tuple(str(x) for x in (item.get("source_ids") or [])),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify whether LLM claims are grounded in cited sources.")
    parser.add_argument("input", help="JSON file containing sources and claims")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    args = parser.parse_args()

    payload = _load(args.input)
    sources = [_source(item) for item in payload.get("sources") or []]
    claims = [_claim(item) for item in payload.get("claims") or []]
    policy = Policy(**(payload.get("policy") or {}))
    result = verify_batch(claims, sources, policy)
    print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None))
    return 0 if result["status"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
