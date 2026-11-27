"""End-to-end test: 10 prompts go through the Spec Agent and then the Circuit Designer,
and the outcome is scored X/10. This calls Gemini (uses your API quota), so it is a
script, not a pytest test.

An outcome has one of three statuses:
  built            the design code accepted a plan (blocks listed)
  needs_questions  the Spec Agent still has missing fields, so no design is attempted
  refused          the Circuit Designer could not produce a valid design

Run:  python -m tests.run_e2e_cases
Owner: Afaq.
"""
import json
import sys
import time
from pathlib import Path

CASES_FILE = Path("tests/prompts/e2e_cases.json")
RESULTS_FILE = Path("output/e2e_case_results.json")
PAUSE_S = 4          # stay under the free-tier rate limit
MAX_PARTS = 25


def check_case(case: dict, outcome: dict) -> list[str]:
    """Return a list of problems. Empty list = PASS.

    outcome = {"status": str, "blocks": list[str], "n_parts": int, "error": str | None}
    expected_blocks / forbidden_blocks match the start of a block name,
    e.g. 'relay_driver:12V' or 'fixed_regulator:'.
    """
    problems = []
    if outcome["status"] != case["expected_status"]:
        detail = f" ({outcome['error']})" if outcome.get("error") else ""
        problems.append(f"status was {outcome['status']}{detail}, expected {case['expected_status']}")
        return problems
    if outcome["status"] != "built":
        return problems

    blocks = outcome["blocks"]
    for want in case["expected_blocks"]:
        if not any(b.startswith(want) for b in blocks):
            problems.append(f"missing block '{want}' (got {blocks})")
    for bad in case["forbidden_blocks"]:
        if any(b.startswith(bad) for b in blocks):
            problems.append(f"block '{bad}' must not be used")
    if outcome["n_parts"] > MAX_PARTS:
        problems.append(f"{outcome['n_parts']} parts, limit is {MAX_PARTS}")
    return problems


def run_case(prompt: str) -> dict:
    """Spec Agent, then Circuit Designer. Imported here so pytest can test check_case without an API key."""
    from agents.spec_agent import analyze_prompt
    from agents.circuit_designer import design_board
    from templates import DesignError

    spec = analyze_prompt(prompt)
    if spec.missing_fields:
        return {"status": "needs_questions", "blocks": [], "n_parts": 0,
                "error": None, "questions": spec.clarifying_questions}
    try:
        result = design_board(spec, prompt)
    except DesignError as e:
        return {"status": "refused", "blocks": [], "n_parts": 0, "error": str(e)}
    return {"status": "built", "blocks": result.design.netlist.blocks,
            "n_parts": len(result.design.netlist.parts), "error": None, "source": result.source}

def run_with_retry(prompt: str, tries: int = 4, wait_s: int = 15) -> dict:
    """Retry on 503 / overload. Other errors are raised straight away."""
    for attempt in range(1, tries + 1):
        try:
            return run_case(prompt)
        except Exception as e:
            overloaded = "503" in str(e) or "UNAVAILABLE" in str(e)
            if not overloaded or attempt == tries:
                raise
            print(f"(503, retry {attempt}/{tries - 1} in {wait_s}s) ", end="", flush=True)
            time.sleep(wait_s)

def main() -> None:
    cases = json.loads(CASES_FILE.read_text(encoding="utf-8"))
    wanted = sys.argv[1:]
    if wanted:
        cases = [c for c in cases if c["id"] in wanted]
    results, passed = [], 0

    for case in cases:
        print(f"{case['id']} ... ", end="", flush=True)
        try:
            outcome = run_with_retry(case["prompt"])
            problems = check_case(case, outcome)
        except Exception as e:                # API error, bad JSON, etc.
            problems, outcome = [f"ERROR: {e}"], None

        if problems:
            print("FAIL")
            for p in problems:
                print("     -", p)
        else:
            print("PASS")
            passed += 1
        results.append({"id": case["id"], "passed": not problems,
                        "problems": problems, "outcome": outcome})
        time.sleep(PAUSE_S)

    print(f"\n{passed}/{len(cases)} cases passed")
    RESULTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_FILE.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"Full answers saved to {RESULTS_FILE}")


if __name__ == "__main__":
    main()