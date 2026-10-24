"""Circuit Designer Agent: Spec -> DesignPlan -> checked Netlist.

The agent loop:
  1. Gemini reads the spec + the user's words and proposes a DesignPlan
     (which templates, with which parameters).
  2. Deterministic code builds the board (templates/). Every value is computed,
     and the netlist is checked (every pin connected, no shorts, <= 25 parts).
  3. If the code rejects the plan, the exact error goes back to Gemini, which
     fixes the plan. Up to MAX_ATTEMPTS times.
If Gemini is unavailable, power supplies fall back to a rule-based plan.

The LLM never outputs component values, pins or coordinates.
Owner: Afaq (agent) + Hamdan (templates).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from core.schemas import BlockRequest, DesignPlan, Spec, TemplateId
from templates import TEMPLATE_GUIDE, Design, DesignError, build_design
from templates.blocks import DIODE_DROP_V, FIXED_78XX, REG_HEADROOM_MIN_V

MAX_ATTEMPTS = 3

SYSTEM_PROMPT = f"""You are the circuit designer for a tool that makes simple single-layer
through-hole PCBs for hand etching. Choose circuit blocks from the templates below and fill in
their parameters from the spec and the user's own words. You never choose resistor or capacitor
values: the code computes those.

{TEMPLATE_GUIDE}

Rules:
- Only use numbers the user or the spec gave. If a needed number is missing, use the documented
  default (LED current 15 mA, LED colour red) and say so in the explanation.
- Set reverse_protection to true for DC adapters and batteries, unless the input is less than
  1 V + 2.5 V above the highest regulated output (the diode costs about 1 V). False for AC input.
- Leave fields that don't apply to a block as null.
"""

AskFn = Callable[[str, str], DesignPlan]


@dataclass
class DesignResult:
    plan: DesignPlan
    design: Design
    source: str                     # 'llm' or 'rules'
    log: list[str] = field(default_factory=list)


def _gemini_ask(contents: str, system: str) -> DesignPlan:
    from agents.structured import ask_structured
    return ask_structured(contents, system, DesignPlan, temperature=0.1)


def _empty_block(template_id: TemplateId, **kw) -> BlockRequest:
    base = dict(rail_name=None, v_out=None, v_out_min=None, v_out_max=None, i_out_a=None,
                led_count=None, led_color=None, led_current_ma=None, frequency_hz=None)
    base.update(kw)
    return BlockRequest(template_id=template_id, **base)


def rules_plan(spec: Spec) -> DesignPlan:
    """Deterministic fallback for power supplies: one regulator per output rail."""
    if spec.project_type.value != "power_supply" or not spec.outputs:
        raise DesignError("Rule-based fallback only handles power supplies.")
    blocks = []
    for rail in spec.outputs:
        if rail.v_min == rail.v_max and float(rail.v_max) in FIXED_78XX:
            blocks.append(_empty_block(TemplateId.fixed_regulator, rail_name=rail.name,
                                       v_out=rail.v_max, i_out_a=rail.i_max_a))
        else:
            blocks.append(_empty_block(TemplateId.adjustable_regulator, rail_name=rail.name,
                                       v_out_min=rail.v_min, v_out_max=rail.v_max, i_out_a=rail.i_max_a))
    v_in = spec.input.voltage_v or 0
    highest = max(r.v_max for r in spec.outputs)
    protect = spec.input.kind != "AC_transformer" and v_in - DIODE_DROP_V - highest >= REG_HEADROOM_MIN_V
    return DesignPlan(blocks=blocks, reverse_protection=protect,
                      explanation="Rule-based: one regulator per rail (78xx if 5/9/12 V fixed, else LM317).")


def _prompt(spec: Spec, request_text: str) -> str:
    return (f"User's words:\n{request_text}\n\n"
            f"Validated spec (JSON):\n{spec.model_dump_json(indent=2)}\n\n"
            f"Return the DesignPlan.")


def design_board(spec: Spec, request_text: str, ask: AskFn | None = None,
                 use_llm: bool = True) -> DesignResult:
    """Run the agent loop. Raises DesignError if no valid design is found."""
    if spec.missing_fields:
        raise DesignError(f"Spec still has missing fields {spec.missing_fields}; ask the user first.")
    log: list[str] = []

    if use_llm:
        ask = ask or _gemini_ask
        contents = _prompt(spec, request_text)
        last_error: DesignError | None = None
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                plan = ask(contents, SYSTEM_PROMPT)
            except Exception as e:                      # API down, no key, bad JSON...
                log.append(f"attempt {attempt}: Gemini call failed ({type(e).__name__}: {e})")
                last_error = None
                break
            try:
                design = build_design(spec, plan)
                log.append(f"attempt {attempt}: plan accepted ({', '.join(design.netlist.blocks)})")
                return DesignResult(plan, design, "llm", log)
            except DesignError as e:
                last_error = e
                log.append(f"attempt {attempt}: rejected by code: {e}")
                contents += (f"\n\nYour previous plan was:\n{plan.model_dump_json()}\n"
                             f"The design code rejected it with this error:\n{e}\n"
                             f"Return a corrected DesignPlan. If it cannot be fixed, return no blocks "
                             f"and explain why.")
                if not plan.blocks:
                    raise DesignError(f"Agent could not find a valid design: {plan.explanation}") from e

        if last_error is not None:                      # Gemini answered, but never validly
            raise DesignError(f"No valid design after {MAX_ATTEMPTS} attempts. Last error: {last_error}")

    plan = rules_plan(spec)                             # raises for non-power projects
    design = build_design(spec, plan)
    log.append("used rule-based plan")
    return DesignResult(plan, design, "rules", log)
