import copy
import json
import os
import subprocess
import sys

import pytest


TEXT = "The court dismissed the claim."
VALID = {
    "sources": [{"id": "S", "text": TEXT}],
    "claims": [{"id": "C", "text": TEXT, "quote": TEXT, "source_ids": ["S"]}],
}


def _run_cli(tmp_path, payload=None, *, raw=None, pretty=False, output_encoding=None):
    path = tmp_path / "input.json"
    if raw is None:
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    path.write_bytes(raw)
    env = os.environ.copy()
    if output_encoding:
        env["PYTHONIOENCODING"] = output_encoding
    args = [sys.executable, "-m", "jurisground.cli", str(path)]
    if pretty:
        args.append("--pretty")
    return subprocess.run(args, capture_output=True, env=env, timeout=10)


def _assert_input_error(process, location=None):
    assert process.returncode == 2, process.stderr
    assert process.stdout == b""
    assert process.stderr.startswith(b"jurisground: invalid input: "), process.stderr
    assert b"Traceback" not in process.stderr
    if location:
        assert location.encode("ascii") in process.stderr


@pytest.mark.parametrize("pretty", [False, True])
def test_valid_json_preserves_success_and_pretty_output(tmp_path, pretty):
    process = _run_cli(tmp_path, VALID, pretty=pretty)
    assert process.returncode == 0, process.stderr
    assert process.stderr == b""
    assert json.loads(process.stdout)["status"] == "pass"
    assert (b'\n  "status"' in process.stdout) == pretty


@pytest.mark.parametrize("payload", [{}, {"sources": [], "claims": []}, {"claims": [{"id": "C"}]}])
def test_missing_optional_content_remains_unverified_json(tmp_path, payload):
    process = _run_cli(tmp_path, payload)
    assert process.returncode == 2
    assert process.stderr == b""
    assert json.loads(process.stdout)["status"] == "unverified"


def test_valid_failed_claim_keeps_json_result_and_exit_two(tmp_path):
    payload = copy.deepcopy(VALID)
    payload["claims"][0]["text"] = "The defendant admitted liability."
    process = _run_cli(tmp_path, payload)
    assert process.returncode == 2
    assert process.stderr == b""
    assert json.loads(process.stdout)["status"] == "fail"


@pytest.mark.parametrize("raw", [b"{", b"", b'{"claims":', b"\xff\xfe\x80"])
def test_invalid_json_or_encoding_has_controlled_error(tmp_path, raw):
    _assert_input_error(_run_cli(tmp_path, raw=raw))


@pytest.mark.parametrize("payload", [[], None, "text", 1, True])
def test_root_must_be_an_object(tmp_path, payload):
    _assert_input_error(_run_cli(tmp_path, payload), "input must be an object")


@pytest.mark.parametrize("field", ["sources", "claims"])
@pytest.mark.parametrize("value", [None, {}, "S", False, 1])
def test_source_and_claim_collections_must_be_arrays(tmp_path, field, value):
    _assert_input_error(_run_cli(tmp_path, {field: value}), field)


@pytest.mark.parametrize("field", ["sources", "claims"])
@pytest.mark.parametrize("value", [None, [], "S", 1])
def test_source_and_claim_entries_must_be_objects(tmp_path, field, value):
    _assert_input_error(_run_cli(tmp_path, {field: [value]}), f"{field}[0]")


@pytest.mark.parametrize("field", ["sources", "claims"])
@pytest.mark.parametrize("record", [{}, {"id": None}, {"id": 1}, {"id": True}, {"id": ""}, {"id": " \t"}])
def test_source_and_claim_ids_must_be_present_nonempty_strings(tmp_path, field, record):
    _assert_input_error(_run_cli(tmp_path, {field: [record]}), f"{field}[0].id")


@pytest.mark.parametrize("collection,field,value", [
    ("sources", "text", None),
    ("sources", "text", 123),
    ("sources", "pages", "page text"),
    ("sources", "pages", None),
    ("sources", "pages", [12]),
    ("sources", "is_ocr", "false"),
    ("sources", "is_ocr", 1),
    ("sources", "legal_citation", {}),
    ("claims", "text", []),
    ("claims", "quote", None),
    ("claims", "source_ids", "S"),
    ("claims", "source_ids", None),
    ("claims", "source_ids", [1]),
    ("claims", "source_ids", [""]),
])
def test_record_fields_are_validated_before_verification(tmp_path, collection, field, value):
    payload = copy.deepcopy(VALID)
    payload[collection][0][field] = value
    _assert_input_error(_run_cli(tmp_path, payload), f"{collection}[0].{field}")


@pytest.mark.parametrize("policy", [None, [], "defaults", 0, False])
def test_policy_must_be_an_object_even_for_empty_batches(tmp_path, policy):
    _assert_input_error(_run_cli(tmp_path, {"policy": policy}), "policy")


@pytest.mark.parametrize("name", ["require_numbers_in_quote", "require_numbers_in_source", "require_legal_citation_match"])
@pytest.mark.parametrize("value", ["false", 0, None])
def test_policy_switches_require_json_booleans(tmp_path, name, value):
    _assert_input_error(_run_cli(tmp_path, {"policy": {name: value}}), f"policy.{name}")


@pytest.mark.parametrize("name", ["quote_threshold", "ocr_quote_threshold", "min_claim_support", "max_expansion_ratio", "min_expansion_support"])
@pytest.mark.parametrize("value", [True, "0.5", None])
def test_numeric_policy_fields_reject_non_numbers(tmp_path, name, value):
    _assert_input_error(_run_cli(tmp_path, {"policy": {name: value}}), f"policy.{name}")


@pytest.mark.parametrize("value", [True, 10.5, "10", None])
def test_quote_length_requires_an_integer(tmp_path, value):
    _assert_input_error(_run_cli(tmp_path, {"policy": {"min_quote_chars": value}}), "min_quote_chars")


@pytest.mark.parametrize("number", ["NaN", "Infinity", "-Infinity", "1e999", "-1e999", "9" * 400])
def test_nonfinite_numeric_policy_values_are_rejected(tmp_path, number):
    raw = ('{"policy":{"quote_threshold":' + number + '}}').encode("ascii")
    _assert_input_error(_run_cli(tmp_path, raw=raw))


def test_unknown_policy_option_is_a_controlled_error(tmp_path):
    _assert_input_error(_run_cli(tmp_path, {"policy": {"unknown": True}}), "unknown policy option")


def test_valid_optional_fields_policy_and_extra_metadata_still_work(tmp_path):
    payload = copy.deepcopy(VALID)
    payload["sources"][0].update(pages=[TEXT], text="unused", is_ocr=True, legal_citation=None, extra="metadata")
    payload["claims"][0]["extra"] = "metadata"
    payload.update(extra="metadata", policy={"quote_threshold": 1, "min_quote_chars": 10, "require_numbers_in_quote": False})
    process = _run_cli(tmp_path, payload)
    assert process.returncode == 0, process.stderr
    assert json.loads(process.stdout)["claims"][0]["matched_text"] == TEXT


def test_utf8_bom_input_is_accepted(tmp_path):
    raw = b"\xef\xbb\xbf" + json.dumps(VALID).encode("utf-8")
    process = _run_cli(tmp_path, raw=raw)
    assert process.returncode == 0, process.stderr
    assert json.loads(process.stdout)["status"] == "pass"


@pytest.mark.parametrize("pretty", [False, True])
def test_unicode_output_survives_cp1250_without_losing_text(tmp_path, pretty):
    payload = copy.deepcopy(VALID)
    text = "The court dismissed the claim \u2780 \u6771\u4eac \U0001f600."
    payload["sources"][0]["text"] = text
    payload["claims"][0].update(text=text, quote=text)
    process = _run_cli(tmp_path, payload, pretty=pretty, output_encoding="cp1250:strict")
    assert process.returncode == 0, process.stderr
    assert process.stderr == b""
    assert process.stdout.isascii()
    result = json.loads(process.stdout)
    assert result["claims"][0]["matched_text"] == text


def test_missing_unicode_filename_has_controlled_cp1250_error(tmp_path):
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "cp1250:strict"
    process = subprocess.run(
        [sys.executable, "-m", "jurisground.cli", str(tmp_path / "\u2780-missing.json")],
        capture_output=True, env=env, timeout=10,
    )
    _assert_input_error(process)
    assert process.stderr.isascii()


def test_excessive_json_nesting_has_controlled_error(tmp_path):
    raw = b'{"metadata":' + b"[" * 2000 + b"0" + b"]" * 2000 + b"}"
    _assert_input_error(_run_cli(tmp_path, raw=raw))
