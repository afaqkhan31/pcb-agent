"""Deterministic safety checks on a Spec.

The LLM sometimes forgets a warning. These plain-Python rules run AFTER the
Spec Agent and add any warning it missed. This is our hallucination guard
for physics: the numbers are computed, not guessed.
Owner: Afaq.  Rules reviewed by: Hamdan.
"""
from core.schemas import Spec

LM317_MIN_V = 1.25        # adjustable regulators cannot go lower than this
HEADROOM_V = 3.0          # linear regulator needs Vin about 3 V above Vout
HEATSINK_W = 1.0          # above ~1 W a TO-220 needs a heatsink
SWITCHER_W = 10.0         # above ~10 W a linear regulator is a bad idea


def check_spec(spec: Spec) -> list[str]:
    """Return a list of warnings. Empty list means nothing to flag."""
    warnings: list[str] = []
    vin = spec.input.voltage_v

    for rail in spec.outputs:
        adjustable = rail.v_max > rail.v_min

        # Rule 1: adjustable regulator minimum
        if adjustable and rail.v_min < LM317_MIN_V:
            warnings.append(
                f"{rail.name}: {rail.v_min} V requested, but LM317-type regulators "
                f"cannot go below {LM317_MIN_V} V."
            )

        # Rule 2: input headroom (only if we know the input voltage)
        if vin is not None and vin < rail.v_max + HEADROOM_V:
            warnings.append(
                f"{rail.name}: input {vin} V is less than {HEADROOM_V} V above the "
                f"{rail.v_max} V output. A linear regulator needs more headroom."
            )

        # Rule 3: heat in the regulator, worst case = lowest output at full current
        if vin is not None and rail.i_max_a is not None and vin > rail.v_min:
            watts = (vin - rail.v_min) * rail.i_max_a
            if watts > SWITCHER_W:
                warnings.append(
                    f"{rail.name}: about {watts:.0f} W of heat in a linear regulator. "
                    f"Use a switching regulator or a very large heatsink."
                )
            elif watts > HEATSINK_W:
                warnings.append(
                    f"{rail.name}: about {watts:.1f} W of heat. The regulator needs a heatsink."
                )

    return warnings


def add_missing_warnings(spec: Spec) -> Spec:
    """Append rule warnings to the spec, tagged so you can see which came from code."""
    for w in check_spec(spec):
        tagged = "[rule check] " + w
        if tagged not in spec.warnings:
            spec.warnings.append(tagged)
    return spec
