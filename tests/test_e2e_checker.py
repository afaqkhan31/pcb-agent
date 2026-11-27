"""Checks the end-to-end runner's grading logic itself. No API key needed."""
import json
from pathlib import Path

from tests.run_e2e_cases import check_case


def built(blocks, n_parts=10):
    return {"status": "built", "blocks": blocks, "n_parts": n_parts, "error": None}


CASE = {"expected_status": "built", "expected_blocks": ["relay_driver:12V"], "forbidden_blocks": []}


def test_pass_when_block_matches():
    assert check_case(CASE, built(["power_input:DC", "relay_driver:12V"])) == []


def test_fail_when_block_missing():
    assert check_case(CASE, built(["power_input:DC", "relay_driver:5V"])) != []


def test_fail_when_forbidden_block_used():
    case = {**CASE, "expected_blocks": [], "forbidden_blocks": ["unregulated_output"]}
    assert check_case(case, built(["power_input:DC", "unregulated_output"])) != []


def test_fail_when_too_many_parts():
    assert check_case(CASE, built(["relay_driver:12V"], n_parts=26)) != []


def test_fail_when_status_differs():
    case = {"expected_status": "refused", "expected_blocks": [], "forbidden_blocks": []}
    assert check_case(case, built(["fixed_regulator:5V"])) != []


def test_pass_when_refused_as_expected():
    case = {"expected_status": "refused", "expected_blocks": [], "forbidden_blocks": []}
    outcome = {"status": "refused", "blocks": [], "n_parts": 0, "error": "no valid design"}
    assert check_case(case, outcome) == []


def test_case_file_has_10_valid_cases():
    cases = json.loads(Path("tests/prompts/e2e_cases.json").read_text(encoding="utf-8"))
    assert len(cases) == 10
    assert len({c["id"] for c in cases}) == 10
    for c in cases:
        assert {"id", "prompt", "expected_status", "expected_blocks", "forbidden_blocks"} <= c.keys()
        assert c["expected_status"] in {"built", "needs_questions", "refused"}