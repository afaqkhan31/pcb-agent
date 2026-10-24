"""End-to-end pipeline: request -> Spec -> design -> netlist, BOM, report (-> EasyEDA).

  python -m pipeline                          interactive, uses Gemini for both agents
  python -m pipeline --example dual_rail      offline demo from examples/ (no API key needed)
  python -m pipeline --example dual_rail --easyeda   ...and build it in EasyEDA Pro
  python -m pipeline --list                   list the offline examples

Outputs go to output/<name>/: spec.json, plan.json, netlist.json, bom.csv, design_report.md
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from core.bom import make_bom, missing_lcsc, write_bom_csv
from core.report import design_report, write_report
from core.schemas import DesignPlan, Spec
from templates import DesignError, build_design

EXAMPLES = Path("examples")


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")[:40] or "design"


def run(name: str, request: str, spec: Spec, plan: DesignPlan | None, use_llm: bool,
        easyeda: bool) -> int:
    out = Path("output") / name
    if plan is not None:                                # offline example: plan is given
        design = build_design(spec, plan)
        source, log, explanation = "example", ["plan loaded from example file"], plan.explanation
    else:
        from agents.circuit_designer import design_board
        result = design_board(spec, request, use_llm=use_llm)
        plan, design, source, log = result.plan, result.design, result.source, result.log
        explanation = plan.explanation

    bom = make_bom(design.netlist)
    out.mkdir(parents=True, exist_ok=True)
    (out / "spec.json").write_text(spec.model_dump_json(indent=2), encoding="utf-8")
    (out / "plan.json").write_text(plan.model_dump_json(indent=2), encoding="utf-8")
    (out / "netlist.json").write_text(design.netlist.model_dump_json(indent=2), encoding="utf-8")
    write_bom_csv(bom, out / "bom.csv")
    write_report(design_report(name, request, spec, design, bom, explanation, source, log),
                 out / "design_report.md")

    print(f"\nDesign: {', '.join(design.netlist.blocks)}  ({len(design.netlist.parts)} parts)")
    for w in list(spec.warnings) + design.warnings:
        print("  !", w)
    for c in design.calculations:
        print("  =", c)
    print(f"\nSaved to {out}/  (design_report.md, bom.csv, netlist.json)")

    todo = missing_lcsc(bom)
    if todo:
        print(f"{len(todo)} BOM line(s) still need an LCSC number: "
              + ", ".join(f"{l.mpn} {l.value}" for l in todo))

    if easyeda:
        if todo:
            print("Not sending to EasyEDA: every part needs an LCSC number first.")
            return 1
        from easyeda.builder import run_stages
        if not run_stages(design.netlist, ["parts", "sch", "erc"]):
            return 1
        print(f"\nSchematic is in EasyEDA. Switch to the PCB tab (with a board outline), then run:\n"
              f"  python -m easyeda.builder pcb {out}/netlist.json\n"
              f"  python -m easyeda.builder drc {out}/netlist.json")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="AI PCB Designer pipeline")
    ap.add_argument("--example", help="name of a file in examples/ (offline, no API key)")
    ap.add_argument("--list", action="store_true", help="list offline examples")
    ap.add_argument("--no-llm", action="store_true", help="design with rules instead of Gemini")
    ap.add_argument("--easyeda", action="store_true", help="build the result in EasyEDA Pro")
    args = ap.parse_args()

    if args.list:
        for f in sorted(EXAMPLES.glob("*.json")):
            print(f"{f.stem:12} {json.loads(f.read_text(encoding='utf-8'))['request']}")
        return 0

    try:
        if args.example:
            data = json.loads((EXAMPLES / f"{args.example}.json").read_text(encoding="utf-8"))
            spec = Spec.model_validate(data["spec"])
            plan = DesignPlan.model_validate(data["plan"])
            return run(args.example, data["request"], spec, plan, False, args.easyeda)

        from agents.spec_agent import interview
        spec, conversation = interview()
        if spec.missing_fields:
            print("\nStill missing:", ", ".join(spec.missing_fields), "- can't design yet.")
            return 1
        return run(_slug(spec.summary), conversation, spec, None, not args.no_llm, args.easyeda)
    except DesignError as e:
        print(f"\nCannot design this board: {e}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
