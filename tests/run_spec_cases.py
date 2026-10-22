"""Runs every prompt in tests/prompts/spec_cases.json through the Spec Agent
and checks the answer. This calls Gemini (uses your API quota), so it is a
script, not a pytest test.

Run:  python -m tests.run_spec_cases
Owner: Hamdan.
"""
import json
import time
from pathlib import Path

CASES_FILE = Path("tests/prompts/spec_cases.json")
RESULTS_FILE = Path("output/spec_case_results.json")
PAUSE_S = 4   # stay under the free-tier rate limit


def contains_any(text: str, keyword: str) -> bool:
    """keyword may hold alternatives split by '|', e.g. 'size|dimension'."""
    return any(alt.strip().lower() in text for alt in keyword.split("|"))


def check_case(case: dict, spec) -> list[str]:
    """Return a list of problems. Empty list = PASS."""
    problems = []
    ask_text = " ".join(spec.clarifying_questions + spec.missing_fields).lower()
    warn_text = " ".join(spec.warnings).lower()

    if spec.project_type.value != case["expected_type"]:
        problems.append(f"type was {spec.project_type.value}, expected {case['expected_type']}")
    for kw in case["ask_keywords"]:
        if not contains_any(ask_text, kw):
            problems.append(f"did not ask about '{kw}'")
    for kw in case["warn_keywords"]:
        if not contains_any(warn_text, kw):
            problems.append(f"did not warn about '{kw}'")
    return problems


def load_agent():
    """Imported here (not at the top) so pytest can test check_case without an API key."""
    try:
        from agents.spec_agent import analyze_prompt      # Spec Agent v1 (Afaq)
        return analyze_prompt
    except ImportError:                                   # before v1 is merged
        from agents.spec_agent import parse_spec
        return lambda prompt: parse_spec("User request: " + prompt)


def main() -> None:
    analyze_prompt = load_agent()
    cases = json.loads(CASES_FILE.read_text(encoding="utf-8"))
    results, passed = [], 0

    for case in cases:
        print(f"{case['id']} ... ", end="", flush=True)
        try:
            spec = analyze_prompt(case["prompt"])
            problems = check_case(case, spec)
            output = spec.model_dump(mode="json")
        except Exception as e:                # API error, bad JSON, etc.
            problems, output = [f"ERROR: {e}"], None

        if problems:
            print("FAIL")
            for p in problems:
                print("     -", p)
        else:
            print("PASS")
            passed += 1
        results.append({"id": case["id"], "passed": not problems,
                        "problems": problems, "spec": output})
        time.sleep(PAUSE_S)

    print(f"\n{passed}/{len(cases)} cases passed")
    RESULTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_FILE.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"Full answers saved to {RESULTS_FILE}")


if __name__ == "__main__":
    main()
