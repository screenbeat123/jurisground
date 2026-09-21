from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import fields
from pathlib import Path

from .gate import verify_batch
from .models import Claim, Policy, Source


def _finite_float(value: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("JSON numbers must be finite")
    return number


def _invalid_constant(value: str):
    raise ValueError(f"JSON does not support {value}")


def _object(value, location: str) -> dict:
    if not isinstance(value, dict):
        raise ValueError(f"{location} must be an object")
    return value


def _array(value, location: str) -> list:
    if not isinstance(value, list):
        raise ValueError(f"{location} must be an array")
    return value


def _string(value, location: str, *, identifier: bool = False) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{location} must be a string")
    if identifier and not value.strip():
        raise ValueError(f"{location} must not be empty")
    return value


def _strings(value, location: str, *, identifiers: bool = False) -> tuple[str, ...]:
    return tuple(
        _string(item, f"{location}[{index}]", identifier=identifiers)
        for index, item in enumerate(_array(value, location))
    )


def _boolean(value, location: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{location} must be a boolean")
    return value


def _load(path: str) -> dict:
    text = Path(path).read_text(encoding="utf-8-sig")
    return _object(json.loads(text, parse_float=_finite_float, parse_constant=_invalid_constant), "input")


def _source(item, location: str) -> Source:
    item = _object(item, location)
    legal_citation = item.get("legal_citation")
    if legal_citation is not None:
        legal_citation = _string(legal_citation, f"{location}.legal_citation")
    return Source(
        id=_string(item.get("id"), f"{location}.id", identifier=True),
        text=_string(item.get("text", ""), f"{location}.text"),
        pages=_strings(item.get("pages", []), f"{location}.pages"),
        is_ocr=_boolean(item.get("is_ocr", False), f"{location}.is_ocr"),
        legal_citation=legal_citation,
    )


def _claim(item, location: str) -> Claim:
    item = _object(item, location)
    return Claim(
        id=_string(item.get("id"), f"{location}.id", identifier=True),
        text=_string(item.get("text", ""), f"{location}.text"),
        quote=_string(item.get("quote", ""), f"{location}.quote"),
        source_ids=_strings(item.get("source_ids", []), f"{location}.source_ids", identifiers=True),
    )


def _policy(value) -> Policy:
    options = _object(value, "policy")
    defaults = {field.name: field.default for field in fields(Policy)}
    for name, value in options.items():
        if name not in defaults:
            raise ValueError(f"unknown policy option {ascii(name)}")
        location = f"policy.{name}"
        default = defaults[name]
        if isinstance(default, bool):
            _boolean(value, location)
        elif isinstance(default, int):
            if type(value) is not int:
                raise ValueError(f"{location} must be an integer")
        else:
            if type(value) not in (int, float):
                raise ValueError(f"{location} must be a finite number")
            try:
                finite = math.isfinite(value)
            except OverflowError:
                finite = False
            if not finite:
                raise ValueError(f"{location} must be a finite number")
    return Policy(**options)


def main() -> int:
    parser = argparse.ArgumentParser(description="Check quotes, numbers, and source references in LLM output.")
    parser.add_argument("input", help="JSON file containing sources and claims")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    args = parser.parse_args()

    try:
        payload = _load(args.input)
        sources = [
            _source(item, f"sources[{index}]")
            for index, item in enumerate(_array(payload.get("sources", []), "sources"))
        ]
        claims = [
            _claim(item, f"claims[{index}]")
            for index, item in enumerate(_array(payload.get("claims", []), "claims"))
        ]
        policy = _policy(payload.get("policy", {}))
    except (OSError, UnicodeError, ValueError, RecursionError) as error:
        message = f"jurisground: invalid input: {error}"
        print(message.encode("ascii", errors="backslashreplace").decode("ascii"), file=sys.stderr)
        return 2
    result = verify_batch(claims, sources, policy)
    print(json.dumps(result, ensure_ascii=True, indent=2 if args.pretty else None))
    return 0 if result["status"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
