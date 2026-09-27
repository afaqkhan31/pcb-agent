"""Trace width calculator (IPC-2221, external layer).

Deterministic on purpose: this is a tool the agents call, not something
the LLM decides. Owner: Shammas (rules reviewed by Hamdan).

IPC-2221 external layer:  I = k * dT^0.44 * A^0.725
    I  = current (A), dT = allowed temperature rise (C),
    A  = cross-section (mil^2), k = 0.048 for external layers.
"""
from __future__ import annotations

MM_PER_MIL = 0.0254
MILS_PER_OZ = 1.378  # copper thickness of 1 oz/ft^2

# Hand-etching (toner transfer) limits — Hamdan to tune these.
MIN_SIGNAL_WIDTH_MM = 0.8
MIN_POWER_WIDTH_MM = 1.2
MIN_CLEARANCE_MM = 0.6


def ipc2221_width_mm(current_a: float, temp_rise_c: float = 10.0, copper_oz: float = 1.0) -> float:
    """Raw IPC-2221 width for an external trace, in mm."""
    if current_a <= 0:
        return 0.0
    k = 0.048
    area_mil2 = (current_a / (k * temp_rise_c ** 0.44)) ** (1 / 0.725)
    width_mil = area_mil2 / (copper_oz * MILS_PER_OZ)
    return width_mil * MM_PER_MIL


def trace_width_mm(net_class: str, current_a: float | None,
                   temp_rise_c: float = 10.0, copper_oz: float = 1.0) -> float:
    """Width to actually use: IPC value, never below the hand-etch floor for that net class.

    Power and ground nets get at least 1.2 mm; signal nets at least 0.8 mm.
    """
    floor = MIN_POWER_WIDTH_MM if net_class in ("power", "ground") else MIN_SIGNAL_WIDTH_MM
    ipc = ipc2221_width_mm(current_a or 0.0, temp_rise_c, copper_oz)
    return round(max(floor, ipc), 2)


if __name__ == "__main__":
    for cls, amps in [("signal", 0.01), ("power", 0.5), ("power", 1.5), ("ground", 3.0)]:
        print(f"{cls:7s} {amps:5.2f} A -> {trace_width_mm(cls, amps):.2f} mm")
