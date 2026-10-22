"""Checks the test-runner's grading logic itself. No API key needed."""
import json
from pathlib import Path

from core.schemas import BoardConstraints, InputSource, Spec
from tests.run_spec_cases import check_case, contains_any


def fake_spec(project_type, questions=(), warnings=()):
    return Spec(
        project_type=project_type, summary="x",
        input=InputSource(kind=None, voltage_v=None, current_a=None),
        outputs=[],
        board=BoardConstraints(width_mm=None, height_mm=None, layers=1, mounting="THT", max_height_mm=None),
        budget=None, missing_fields=[],
        clarifying_questions=list(questions), warnings=list(warnings),
    )


def test_alternatives():
    assert contains_any("what is the board dimension?", "size|dimension")
    assert not contains_any("what is the input voltage?", "size|dimension")


def test_pass_when_everything_matches():
    case = {"expected_type": "timer", "ask_keywords": ["size|dimension"], "warn_keywords": []}
    spec = fake_spec("timer", questions=["What board size do you want?"])
    assert check_case(case, spec) == []


def test_fail_when_warning_missing():
    case = {"expected_type": "other", "ask_keywords": [], "warn_keywords": ["layer|smd"]}
    assert check_case(case, fake_spec("other")) != []


def test_case_file_has_10_valid_cases():
    cases = json.loads(Path("tests/prompts/spec_cases.json").read_text(encoding="utf-8"))
    assert len(cases) == 10
    for c in cases:
        assert {"id", "prompt", "expected_type", "ask_keywords", "warn_keywords"} <= c.keys()
