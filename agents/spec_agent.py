"""Spec Agent v1 — turns a plain-English request into a validated Spec.

Asks clarifying questions (up to 3 rounds) when information is missing,
then runs deterministic rule checks (core/spec_checks.py) and saves the
result to output/spec.json.
Owner: Afaq.  Domain review: Hamdan.

Run:  python -m agents.spec_agent
"""
import time
from pathlib import Path

from google.genai import errors, types

from agents.llm import MODEL, client
from core.schemas import Spec
from core.spec_checks import add_missing_warnings

SYSTEM_PROMPT = """You are the requirements engineer for a tool that designs SIMPLE,
SINGLE-LAYER, THROUGH-HOLE (THT) PCBs meant to be hand-etched at home.

Convert the user's request into the Spec JSON schema.

Rules:
- Never invent values. If the user did not give something needed for design, set it to null,
  add it to missing_fields, and add one short clarifying question for it.
- Always required for power projects: input voltage/source, and max current for every output rail.
- Always required for every project: board size. Ask for it if missing.
- layers must be 1 and mounting must be "THT". If the user asks for SMD or multiple layers,
  keep 1 / THT and add a warning explaining the tool's limits.
- Add a warning for physically impossible or risky requests. Example: LM317-type adjustable
  regulators cannot go below about 1.25 V; a linear regulator needs input about 3 V above its
  highest output; large drop x current means a heatsink.
- Convert all dimensions to millimetres (8 cm = 80 mm).
- Keep the summary to one sentence.
"""

MAX_ROUNDS = 3
RETRY_CODES = (429, 500, 503)   # rate limit / server busy on the free tier
OUTPUT_FILE = Path("output/spec.json")


def parse_spec(conversation: str, tries: int = 3) -> Spec:
    """One Gemini call -> Spec. Retries if the free tier is busy."""
    for attempt in range(1, tries + 1):
        try:
            response = client.models.generate_content(
                model=MODEL,
                contents=conversation,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    response_mime_type="application/json",
                    response_schema=Spec,
                    temperature=0.1,
                ),
            )
            break
        except errors.APIError as e:
            if e.code in RETRY_CODES and attempt < tries:
                wait = 5 * attempt
                print(f"  (Gemini busy: {e.code}. Retrying in {wait} s...)")
                time.sleep(wait)
            else:
                raise

    spec = response.parsed
    if spec is None:  # fall back to manual validation if the SDK couldn't parse
        spec = Spec.model_validate_json(response.text)
    return spec


def analyze_prompt(prompt: str) -> Spec:
    """Non-interactive: one prompt in, checked Spec out. Used by the test runner."""
    spec = parse_spec("User request: " + prompt)
    return add_missing_warnings(spec)


def run_interactive() -> Spec:
    return interview()[0]


def interview(request: str | None = None) -> tuple[Spec, str]:
    """Ask clarifying questions until the spec is complete. Returns (spec, full conversation).

    The conversation is passed on to the Circuit Designer Agent, because details like
    LED count or blink rate live in the user's words, not in the Spec fields.
    """
    if request is None:
        request = input("Describe the board you need:\n> ")
    conversation = "User request: " + request
    spec = parse_spec(conversation)

    for _ in range(MAX_ROUNDS):
        if not spec.clarifying_questions:
            break
        print("\nI need a bit more information:")
        for q in spec.clarifying_questions:
            answer = input(f"  {q}\n  > ")
            conversation += f"\nQ: {q}\nA: {answer}"
        spec = parse_spec(conversation)

    spec = add_missing_warnings(spec)

    if spec.warnings:
        print("\nWarnings:")
        for w in spec.warnings:
            print("  -", w)
    return spec, conversation


def save_spec(spec: Spec, path: Path = OUTPUT_FILE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(spec.model_dump_json(indent=2), encoding="utf-8")
    print(f"\nSaved to {path}")


if __name__ == "__main__":
    final = run_interactive()
    print("\nFinal spec:\n" + final.model_dump_json(indent=2))
    save_spec(final)
