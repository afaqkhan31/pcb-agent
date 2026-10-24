"""Bill of materials from a Netlist, plus CSV export. Deterministic.
Owner: Hamna.
"""
from __future__ import annotations

import csv
import re
from pathlib import Path

from core.schemas import BOM, BOMLine, Netlist


def _ref_key(ref: str) -> tuple[str, int]:
    m = re.match(r"([A-Z]+)(\d+)", ref)
    return (m.group(1), int(m.group(2))) if m else (ref, 0)


def make_bom(netlist: Netlist, jumpers: int = 0) -> BOM:
    groups: dict[tuple[str, str], list] = {}
    for part in netlist.parts:
        groups.setdefault((part.catalog_key, part.value), []).append(part)

    lines = []
    for (key, value), parts in groups.items():
        first = parts[0]
        if not first.pinout_verified:
            note = "Not in catalog yet: add it to data/components.json"
        elif first.lcsc is None:
            note = "Choose LCSC part by value (Sourcing Agent / lcsc_by_value)"
        else:
            note = None
        lines.append(BOMLine(refs=sorted((p.ref for p in parts), key=_ref_key), qty=len(parts),
                             value=value, package=first.package, mpn=key, lcsc=first.lcsc,
                             datasheet_url=None, unit_price=None, notes=note))
    lines.sort(key=lambda l: _ref_key(l.refs[0]))
    return BOM(lines=lines, jumpers=jumpers)


def missing_lcsc(bom: BOM) -> list[BOMLine]:
    """Lines EasyEDA can't place yet (no C-number)."""
    return [l for l in bom.lines if not l.lcsc]


def write_bom_csv(bom: BOM, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Refs", "Qty", "Value", "Catalog key", "LCSC", "Package", "Notes"])
        for l in bom.lines:
            w.writerow([" ".join(l.refs), l.qty, l.value, l.mpn, l.lcsc or "", l.package or "", l.notes or ""])
        if bom.jumpers:
            w.writerow(["", bom.jumpers, "Wire jumper", "", "", "", "Added by router"])
