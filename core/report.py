"""Human-readable design report (Markdown) for review and the demo."""
from __future__ import annotations

from pathlib import Path

from core.schemas import BOM, Spec
from templates import Design

SOURCES = {"llm": "Circuit Designer Agent (Gemini)", "rules": "rule-based fallback",
           "example": "example file (offline)"}


def design_report(title: str, request: str, spec: Spec, design: Design, bom: BOM,
                  plan_explanation: str, source: str, log: list[str]) -> str:
    out = [f"# Design report: {title}", "", f"**Request:** {request}", "",
           f"**Summary:** {spec.summary}", "",
           f"**Blocks:** {', '.join(design.netlist.blocks)}  ",
           f"**Planned by:** {SOURCES.get(source, source)}"
           f": {plan_explanation}", ""]

    warnings = list(spec.warnings) + list(design.warnings)
    if warnings:
        out += ["## Warnings", ""] + [f"- {w}" for w in warnings] + [""]

    out += ["## Calculations", ""] + [f"- {c}" for c in design.calculations] + [""]

    out += ["## Nets and trace widths", "", "| Net | Class | Current (A) | Width (mm) | Pins |",
            "|---|---|---|---|---|"]
    for n in design.netlist.nets:
        cur = "" if n.current_a is None else f"{n.current_a:g}"
        pins = ", ".join(f"{x.ref}.{x.pin}" for x in n.nodes)
        out.append(f"| {n.name} | {n.net_class} | {cur} | {design.trace_widths[n.name]:.2f} | {pins} |")

    out += ["", "## Bill of materials", "", "| Refs | Qty | Value | Catalog key | LCSC | Notes |",
            "|---|---|---|---|---|---|"]
    for l in bom.lines:
        out.append(f"| {' '.join(l.refs)} | {l.qty} | {l.value} | {l.mpn} | {l.lcsc or '—'} | {l.notes or ''} |")

    if log:
        out += ["", "## Agent log", ""] + [f"- {x}" for x in log]
    return "\n".join(out) + "\n"


def write_report(text: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
