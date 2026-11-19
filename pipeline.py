"""End-to-end pipeline: request -> Spec -> design -> netlist, BOM, report (-> EasyEDA).

  python -m pipeline --prompt "5V 1A supply from 12V DC, 5x5 cm"   one line in, no questions asked
  python -m pipeline --prompt "..." --easyeda                       ...and build it in EasyEDA Pro
  python -m pipeline                          interactive, uses Gemini for both agents
  python -m pipeline --example dual_rail      offline demo from examples/ (no API key needed)
  python -m pipeline --example dual_rail --easyeda   ...and build it in EasyEDA Pro
  python -m pipeline --list                   list the offline examples

Outputs go to output/<name>/: spec.json, plan.json, netlist.json, bom.csv, design_report.md,
agent_log.json (every stage: start time, seconds, result, errors).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from core.bom import make_bom, missing_lcsc, write_bom_csv
from core.report import design_report, write_report
from core.schemas import DesignPlan, Spec
from easyeda.bridge import BridgeError
from templates import DesignError, build_design

EXAMPLES = Path("examples")


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")[:40] or "design"


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


# ------------------------------------------------------------------ agent log
class AgentLog:
    """Records every pipeline stage: start time, seconds taken, result and detail.

    Saved to output/<name>/agent_log.json at the end of every run, also when a stage fails.
    """

    def __init__(self, request: str, name: str) -> None:
        self.request = request
        self.name = name
        self.started = _now()
        self.stages: list[dict] = []
        self.designer_log: list[str] = []      # the Circuit Designer's own attempt log
        self.exit_code: int | None = None
        self.error: str | None = None

    @contextmanager
    def stage(self, name: str):
        entry = {"stage": name, "started": _now(), "seconds": None, "status": "running", "detail": ""}
        self.stages.append(entry)
        t0 = time.monotonic()
        try:
            yield entry
        except Exception as e:
            entry["status"] = "failed"
            entry["detail"] = f"{type(e).__name__}: {e}"
            raise
        else:
            if entry["status"] == "running":
                entry["status"] = "ok"
        finally:
            entry["seconds"] = round(time.monotonic() - t0, 2)

    def save(self) -> Path | None:
        path = Path("output") / self.name / "agent_log.json"
        data = {
            "request": self.request,
            "started": self.started,
            "result": "ok" if self.exit_code == 0 else "failed",
            "exit_code": self.exit_code,
            "error": self.error,
            "stages": self.stages,
            "circuit_designer_log": self.designer_log,
        }
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except OSError:
            return None
        return path


# ------------------------------------------------------------------ EasyEDA
def _easyeda_stage(log: AgentLog, netlist, name: str) -> bool:
    from easyeda.builder import run_stages
    with log.stage(f"easyeda_{name}") as st:
        ok = run_stages(netlist, [name])
        if not ok:
            st["status"] = "failed"
            st["detail"] = "stage reported problems (see the terminal output)"
        return ok


# ------------------------------------------------------------------ run
def run(name: str, request: str, spec: Spec, plan: DesignPlan | None, use_llm: bool,
        easyeda: bool, log: AgentLog) -> int:
    log.name = name
    out = Path("output") / name

    with log.stage("design") as st:
        if plan is not None:                            # offline example: plan is given
            design = build_design(spec, plan)
            source, dlog = "example", ["plan loaded from example file"]
        else:
            from agents.circuit_designer import design_board
            result = design_board(spec, request, use_llm=use_llm)
            plan, design, source, dlog = result.plan, result.design, result.source, result.log
        st["detail"] = f"{source}: " + ", ".join(design.netlist.blocks)
    log.designer_log = list(dlog)
    explanation = plan.explanation

    with log.stage("bom") as st:
        bom = make_bom(design.netlist)
        st["detail"] = f"{len(bom.lines)} BOM line(s), {len(design.netlist.parts)} part(s)"

    with log.stage("report") as st:
        out.mkdir(parents=True, exist_ok=True)
        (out / "spec.json").write_text(spec.model_dump_json(indent=2), encoding="utf-8")
        (out / "plan.json").write_text(plan.model_dump_json(indent=2), encoding="utf-8")
        (out / "netlist.json").write_text(design.netlist.model_dump_json(indent=2), encoding="utf-8")
        write_bom_csv(bom, out / "bom.csv")
        write_report(design_report(name, request, spec, design, bom, explanation, source, dlog),
                     out / "design_report.md")
        st["detail"] = f"saved to {out}"

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
            with log.stage("easyeda_precheck") as st:
                st["status"] = "failed"
                st["detail"] = "missing LCSC numbers: " + ", ".join(f"{l.mpn} {l.value}" for l in todo)
            print("Not sending to EasyEDA: every part needs an LCSC number first.")
            return 1
        for stage in ("parts", "sch", "erc"):
            if not _easyeda_stage(log, design.netlist, stage):
                return 1
        input("\nSwitch EasyEDA to an EMPTY PCB tab, then press Enter...")
        for stage in ("pcb", "drc"):
            if not _easyeda_stage(log, design.netlist, stage):
                return 1
        print("\nBoard built in EasyEDA: parts, sch, erc, pcb and drc all finished.")
    return 0


# ------------------------------------------------------------------ errors
def _explain_error(e: Exception) -> str:
    """One clear line for any unexpected error (no traceback for the user)."""
    code = getattr(e, "code", None)
    if code in (429, 500, 503):
        return "Gemini is busy: wait a minute and retry."
    if code in (400, 401, 403):
        return "Gemini rejected the request: check GEMINI_API_KEY in your .env file."
    return f"Unexpected error ({type(e).__name__}): {e}"


def _fail(log: AgentLog, code: int, message: str) -> int:
    print(f"\n{message}")
    log.error = message
    return code


# ------------------------------------------------------------------ main
def _needs_detail(spec: Spec, log: AgentLog) -> int:
    log.error = "needs more detail: " + ", ".join(spec.missing_fields)
    return 1


def _dispatch(args: argparse.Namespace, log: AgentLog) -> int:
    if args.example:
        with log.stage("spec") as st:
            data = json.loads((EXAMPLES / f"{args.example}.json").read_text(encoding="utf-8"))
            spec = Spec.model_validate(data["spec"])
            plan = DesignPlan.model_validate(data["plan"])
            st["detail"] = f"loaded from examples/{args.example}.json"
        return run(args.example, data["request"], spec, plan, False, args.easyeda, log)

    if args.prompt:
        from agents.spec_agent import analyze_prompt
        with log.stage("spec") as st:
            spec = analyze_prompt(args.prompt)
            st["detail"] = spec.summary
            if spec.missing_fields:
                st["status"] = "needs_input"
                st["detail"] = "missing: " + ", ".join(spec.missing_fields)
        if spec.missing_fields:
            print("\nThe Spec Agent needs more detail before it can design:")
            for q in spec.clarifying_questions:
                print("  ?", q)
            print("Add the answers to your prompt and run again.")
            return _needs_detail(spec, log)
        return run(_slug(spec.summary), args.prompt, spec, None, not args.no_llm, args.easyeda, log)

    from agents.spec_agent import interview
    with log.stage("spec") as st:
        spec, conversation = interview()
        st["detail"] = spec.summary
    if spec.missing_fields:
        print("\nStill missing:", ", ".join(spec.missing_fields), "- can't design yet.")
        return _needs_detail(spec, log)
    return run(_slug(spec.summary), conversation, spec, None, not args.no_llm, args.easyeda, log)


def main() -> int:
    ap = argparse.ArgumentParser(description="AI PCB Designer pipeline")
    ap.add_argument("--prompt", help="the whole request in one line (no questions asked)")
    ap.add_argument("--example", help="name of a file in examples/ (offline, no API key)")
    ap.add_argument("--list", action="store_true", help="list offline examples")
    ap.add_argument("--no-llm", action="store_true", help="design with rules instead of Gemini")
    ap.add_argument("--easyeda", action="store_true", help="build the result in EasyEDA Pro")
    args = ap.parse_args()

    if args.list:
        for f in sorted(EXAMPLES.glob("*.json")):
            print(f"{f.stem:12} {json.loads(f.read_text(encoding='utf-8'))['request']}")
        return 0

    request = args.prompt or args.example or "interactive"
    log = AgentLog(request, _slug(request))
    try:
        code = _dispatch(args, log)
    except DesignError as e:
        code = _fail(log, 2, f"Cannot design this board: {e}")
    except BridgeError as e:
        code = _fail(log, 3, f"EasyEDA bridge problem: {e}. Start the EasyEDA bridge and try again.")
    except RuntimeError as e:
        code = _fail(log, 5, f"EasyEDA check failed: {e}")
    except Exception as e:
        code = _fail(log, 4, _explain_error(e))

    log.exit_code = code
    path = log.save()
    if path:
        print(f"Log saved to {path}")
    return code


if __name__ == "__main__":
    sys.exit(main())