"""Curated THT component list + validator.

Every part an agent suggests must exist in data/components.json and be used
inside its ratings. The `lcsc` C-number is the exact part EasyEDA will place;
EasyEDA supplies the symbol and footprint from it.
Owner: Hamna.  Ratings reviewed by: Hamdan.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "components.json"
REQUIRED_KEYS = {"mpn", "lcsc", "category", "description", "package",
                 "pins", "v_max", "i_max_a", "power_w", "notes"}
LCSC_PATTERN = re.compile(r"^C\d+$")


@lru_cache(maxsize=1)
def load_components() -> dict[str, dict]:
    """Return {MPN in upper case: part dict}."""
    parts = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    return {p["mpn"].upper(): p for p in parts}


def find_part(mpn: str) -> dict | None:
    """Look up a part by MPN, ignoring upper/lower case. None if not in our list."""
    return load_components().get(mpn.strip().upper())


def find_by_lcsc(lcsc: str) -> dict | None:
    """Look up a part by its LCSC C-number, e.g. 'C111887'."""
    lcsc = lcsc.strip().upper()
    return next((p for p in load_components().values() if (p["lcsc"] or "").upper() == lcsc), None)


def validate_part(mpn: str, voltage_v: float | None = None,
                  current_a: float | None = None) -> list[str]:
    """Return problems with using this part. Empty list = OK to use."""
    part = find_part(mpn)
    if part is None:
        return [f"{mpn} is not in our component list (possible hallucination)."]

    problems = []
    if voltage_v is not None and part["v_max"] is not None and voltage_v > part["v_max"]:
        problems.append(f"{mpn}: {voltage_v} V is above its {part['v_max']} V rating.")
    if current_a is not None and part["i_max_a"] is not None and current_a > part["i_max_a"]:
        problems.append(f"{mpn}: {current_a} A is above its {part['i_max_a']} A rating.")
    return problems
