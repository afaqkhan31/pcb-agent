"""Turn a Spec + DesignPlan into a checked Netlist. 100% deterministic.

    design = build_design(spec, plan)
    design.netlist, design.warnings, design.calculations, design.trace_widths
"""
from __future__ import annotations

from dataclasses import dataclass

from core.schemas import DesignPlan, Netlist, Spec, TemplateId
from templates import blocks
from templates.board import Board, DesignError

__all__ = ["Design", "DesignError", "build_design", "TEMPLATE_GUIDE"]

DEFAULT_LED_MA = 15.0

# Shown to the Circuit Designer Agent so it knows what it can ask for.
TEMPLATE_GUIDE = """Available circuit templates (the power input block is always added for you):
- fixed_regulator: 78xx linear regulator. Needs rail_name, v_out (ONLY 5, 9 or 12), i_out_a (<= 1.5).
- adjustable_regulator: LM317 with a pot. Needs rail_name, v_out_min (>= 1.25), v_out_max (<= 37), i_out_a (<= 1.5).
- led_array: LEDs in series strings with resistors, powered from the input. Needs led_count (1-20),
  led_color (red, green, yellow, orange, blue, white), led_current_ma (1-30, use 15 if not given).
- ne555_flasher: 555 astable blinking one LED, powered from the input (4.5-16 V). Needs frequency_hz
  (0.1-1000), led_color, led_current_ma.
Use one regulator block per output rail. Linear regulators need input >= output + 2.5 V.
Not supported (say so in explanation, return no blocks): switching regulators, relays,
microcontrollers, SMD parts, multi-layer boards."""


@dataclass
class Design:
    netlist: Netlist
    warnings: list[str]
    calculations: list[str]
    trace_widths: dict[str, float]
    v_in_min: float


def _need(value, what: str, block: str):
    if value is None:
        raise DesignError(f"{block}: missing {what}")
    return value


def build_design(spec: Spec, plan: DesignPlan) -> Design:
    """Raises DesignError with a clear message if anything is impossible."""
    if spec.missing_fields:
        raise DesignError(f"Spec is incomplete (missing {spec.missing_fields}); ask the user first.")
    if not plan.blocks:
        raise DesignError("Plan has no blocks: nothing to build. " + plan.explanation)
    v_in = _need(spec.input.voltage_v, "input voltage", "power_input")

    # Total current through the input = sum of regulator outputs + LED/555 loads
    total = 0.0
    for b in plan.blocks:
        if b.template_id in (TemplateId.fixed_regulator, TemplateId.adjustable_regulator):
            total += _need(b.i_out_a, "i_out_a", b.template_id.value)
        elif b.template_id == TemplateId.led_array:
            total += (b.led_count or 0) * (b.led_current_ma or DEFAULT_LED_MA) / 1000
        else:
            total += 0.03
    total = round(total, 3)

    board = Board()
    v_dc = blocks.power_input(board, spec.input.kind, v_in, total, plan.reverse_protection)

    rails_seen = set()
    for b in plan.blocks:
        t = b.template_id
        if t in (TemplateId.fixed_regulator, TemplateId.adjustable_regulator):
            rail = (b.rail_name or f"RAIL{len(rails_seen) + 1}").upper().replace(" ", "_")
            if rail in rails_seen or rail in ("VIN", "GND"):
                raise DesignError(f"Duplicate or reserved rail name '{rail}'")
            rails_seen.add(rail)
            if t == TemplateId.fixed_regulator:
                blocks.fixed_regulator(board, rail, _need(b.v_out, "v_out", t.value), b.i_out_a, v_dc)
            else:
                blocks.adjustable_regulator(board, rail, _need(b.v_out_min, "v_out_min", t.value),
                                            _need(b.v_out_max, "v_out_max", t.value), b.i_out_a, v_dc)
        elif t == TemplateId.led_array:
            blocks.led_array(board, v_dc, _need(b.led_count, "led_count", t.value),
                             b.led_color or "red", b.led_current_ma or DEFAULT_LED_MA)
        elif t == TemplateId.ne555_flasher:
            blocks.ne555_flasher(board, v_dc, _need(b.frequency_hz, "frequency_hz", t.value),
                                 b.led_color or "red", b.led_current_ma or DEFAULT_LED_MA)

    netlist = board.to_netlist()          # runs the connectivity check
    unverified = sorted({p.catalog_key for p in netlist.parts if not p.pinout_verified})
    if unverified:
        board.warnings.append("Not in catalog yet (pinout + LCSC unverified): " + ", ".join(unverified))
    return Design(netlist=netlist, warnings=board.warnings, calculations=board.calculations,
                  trace_widths=board.trace_widths(), v_in_min=v_dc)
