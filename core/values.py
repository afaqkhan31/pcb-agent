"""Component value helpers: E-series rounding and value formatting.

Deterministic on purpose: the LLM never picks resistor or capacitor values.
Owner: Hamdan (PCB rules).
"""
from __future__ import annotations

import math

E24 = [1.0, 1.1, 1.2, 1.3, 1.5, 1.6, 1.8, 2.0, 2.2, 2.4, 2.7, 3.0,
       3.3, 3.6, 3.9, 4.3, 4.7, 5.1, 5.6, 6.2, 6.8, 7.5, 8.2, 9.1]

# Standard electrolytic values (uF) and voltage ratings (V) we allow
ELEC_UF = [1, 2.2, 4.7, 10, 22, 47, 100, 220, 470, 1000, 2200, 4700]
ELEC_V = [16, 25, 35, 50]
CAP_DERATING = 0.8          # run electrolytics at <= 80% of rated voltage


def _e24_candidates(value: float) -> list[float]:
    decade = 10 ** math.floor(math.log10(value))
    return [m * decade for m in E24] + [10 * decade]


def e24_nearest(value: float) -> float:
    return min(_e24_candidates(value), key=lambda c: abs(c - value))


def e24_up(value: float) -> float:
    """Smallest E24 value >= value (e.g. LED resistors: round up = less current)."""
    return min(c for c in _e24_candidates(value) if c >= value * 0.9999)


def fmt_ohms(r: float) -> str:
    """240 -> '240', 4700 -> '4.7k', 75000 -> '75k', 1e6 -> '1M'."""
    for div, unit in ((1e6, "M"), (1e3, "k"), (1, "")):
        if r >= div:
            v = r / div
            s = f"{v:.2f}".rstrip("0").rstrip(".")
            return s + unit
    return f"{r:g}"


def fmt_uf(c_uf: float) -> str:
    """100 -> '100uF', 0.1 -> '100nF', 0.01 -> '10nF'."""
    if c_uf >= 1:
        return f"{c_uf:g}uF"
    return f"{c_uf * 1000:g}nF"


def elec_voltage_rating(working_v: float) -> int:
    """Smallest standard rating with the working voltage at <= 80% of it."""
    for v in ELEC_V:
        if working_v <= v * CAP_DERATING:
            return v
    raise ValueError(f"No electrolytic rating for {working_v} V (max {ELEC_V[-1]} V)")


def elec_key(c_uf: float, rating_v: int) -> str:
    """Catalog key used in data/components.json, e.g. 'CAP-ELEC-100UF-25V'."""
    return f"CAP-ELEC-{c_uf:g}UF-{rating_v}V"


def resistor_power_key(watts: float) -> str:
    """Pick the resistor family with >= 2x margin on dissipation."""
    if watts * 2 <= 0.25:
        return "RES-0.25W"
    if watts * 2 <= 1.0:
        return "RES-1W"
    raise ValueError(f"{watts:.2f} W is too much for one THT resistor")
