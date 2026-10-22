"""Which catalog entries do the templates need, and which are still missing?

Run:  python -m core.catalog_todo

Every key below must exist in data/components.json with an LCSC number
(or lcsc_by_value for resistors) and with pins named EXACTLY as shown,
because templates connect pins by name.
Owner: Hamna (catalog).  Hamdan reviews pin names.
"""
from __future__ import annotations

from core.components import load_components

# key -> required pin names (number -> name). Numbers follow the usual datasheet pinout;
# if the LCSC part's datasheet numbers them differently, keep the NAMES and change the numbers.
NEEDED = {
    "KF301-5.0-2P":        {"1": "1", "2": "2"},
    "1N4007-TP":           {"1": "K", "2": "A"},
    "1N5408":              {"1": "K", "2": "A"},
    "W04M":                {"1": "+", "2": "AC1", "3": "-", "4": "AC2"},
    "KBP206":              {"1": "+", "2": "AC1", "3": "AC2", "4": "-"},
    "L7805CV":             {"1": "IN", "2": "GND", "3": "OUT"},
    "L7809CV":             {"1": "IN", "2": "GND", "3": "OUT"},
    "L7812CV":             {"1": "IN", "2": "GND", "3": "OUT"},
    "LM317T":              {"1": "ADJ", "2": "OUT", "3": "IN"},
    "NE555P":              {"1": "GND", "2": "TRIG", "3": "OUT", "4": "RESET",
                            "5": "CTRL", "6": "THR", "7": "DIS", "8": "VCC"},
    "POT-5K-RV09":         {"1": "1", "2": "W", "3": "3"},
    "POT-10K-RV09":        {"1": "1", "2": "W", "3": "3"},
    "RES-0.25W":           {"1": "1", "2": "2"},
    "RES-1W":              {"1": "1", "2": "2"},
    "CAP-CER-100NF-50V":   {"1": "1", "2": "2"},
    "CAP-CER-10NF-50V":    {"1": "1", "2": "2"},
    "LED-5MM-RED":         {"1": "K", "2": "A"},
    "LED-5MM-WHITE":       {"1": "K", "2": "A"},
    "LED-3MM-GREEN":       {"1": "K", "2": "A"},
    "CAP-ELEC-10UF-16V":   {"1": "+", "2": "-"},
    "CAP-ELEC-100UF-25V":  {"1": "+", "2": "-"},
    "CAP-ELEC-100UF-50V":  {"1": "+", "2": "-"},
    "CAP-ELEC-470UF-25V":  {"1": "+", "2": "-"},
    "CAP-ELEC-1000UF-25V": {"1": "+", "2": "-"},
    "CAP-ELEC-2200UF-25V": {"1": "+", "2": "-"},
    "CAP-ELEC-4700UF-25V": {"1": "+", "2": "-"},
}
GENERIC = {"RES-0.25W", "RES-1W"}       # need lcsc_by_value instead of one lcsc


def todo() -> list[str]:
    catalog = load_components()
    lines = []
    for key, pins in NEEDED.items():
        part = catalog.get(key.upper())
        if part is None:
            lines.append(f"MISSING  {key:22} pins {pins}")
            continue
        names = sorted(str(v) for v in part["pins"].values())
        if names != sorted(pins.values()):
            lines.append(f"PINS     {key:22} has {part['pins']}, needs names {sorted(pins.values())}")
        if key in GENERIC:
            if not part.get("lcsc_by_value"):
                lines.append(f"LCSC     {key:22} add lcsc_by_value, e.g. {{\"240\": \"C...\", \"1k\": \"C...\"}}")
        elif not part.get("lcsc"):
            lines.append(f"LCSC     {key:22} has no LCSC number")
    return lines


if __name__ == "__main__":
    items = todo()
    print(f"{len(NEEDED) - len({l.split()[1] for l in items})}/{len(NEEDED)} template parts ready.")
    print("\n".join(items) if items else "All template parts are in the catalog.")
