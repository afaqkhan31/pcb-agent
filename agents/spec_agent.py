"""Spec Agent v0 — turns a plain-English request into a validated Spec.

Asks clarifying questions (up to 3 rounds) when information is missing.
Owner: Afaq.  Domain review: Hamdan.

Run:  python -m agents.spec_agent
"""
from google.genai import types

from agents.llm import MODEL, client
from core.schemas import Spec

SYSTEM_PROMPT = """You are the requirements engineer for a tool that designs SIMPLE,
SINGLE-LAYER, THROUGH-HOLE (THT) PCBs meant to be hand-etched at home.

Convert the user's request into the Spec JSON schema.

Rules:
- Never invent values. If the user did not give something needed for design, set it to null,
  add it to missing_fields, and add one short clarifying question for it.
- Always required for power projects: input voltage/source, and max current for every output rail.
- layers must be 1 and mounting must be "THT". If the user asks for SMD or multiple layers,
  keep 1 / THT and add a warning explaining the tool's limits.
- Add a warning for physically impossible or risky requests. Example: LM317-type adjustable
  regulators cannot go below about 1.25 V; a linear regulator needs input about 3 V above its
  highest output; large drop x current means a heatsink.
- Convert all dimensions to millimetres (8 cm = 80 mm).
- Keep the summary to one sentence.
"""

MAX_ROUNDS = 3


def parse_spec(conversation: str) -> Spec:
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
    spec = response.parsed
    if spec is None:  # fall back to manual validation if the SDK couldn't parse
        spec = Spec.model_validate_json(response.text)
    return spec


def run_interactive() -> Spec:
    conversation = "User request: " + input("Describe the board you need:\n> ")
    spec = parse_spec(conversation)

    for _ in range(MAX_ROUNDS):
        if not spec.clarifying_questions:
            break
        print("\nI need a bit more information:")
        for q in spec.clarifying_questions:
            answer = input(f"  {q}\n  > ")
            conversation += f"\nQ: {q}\nA: {answer}"
        spec = parse_spec(conversation)

    if spec.warnings:
        print("\nWarnings:")
        for w in spec.warnings:
            print("  -", w)
    return spec


if __name__ == "__main__":
    final = run_interactive()
    print("\nFinal spec:\n" + final.model_dump_json(indent=2))
