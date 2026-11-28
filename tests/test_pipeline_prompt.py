"""pipeline --prompt: no API key and no EasyEDA needed (both are faked)."""
import json
import sys
from pathlib import Path

import pipeline
from core.schemas import Spec
from easyeda.bridge import BridgeError

ROOT = Path(__file__).resolve().parents[1]


def example_spec(name):
    data = json.loads((ROOT / "examples" / f"{name}.json").read_text(encoding="utf-8"))
    return Spec.model_validate(data["spec"])


def read_log(name):
    return json.loads((ROOT / "output" / name / "agent_log.json").read_text(encoding="utf-8"))


def test_prompt_runs_offline(monkeypatch):
    monkeypatch.chdir(ROOT)
    monkeypatch.setattr("agents.spec_agent.analyze_prompt", lambda text: example_spec("ac_9v"))
    monkeypatch.setattr(sys, "argv", ["pipeline", "--prompt", "9V 1A from 12V AC", "--no-llm"])
    assert pipeline.main() == 0
    log = read_log(pipeline._slug(example_spec("ac_9v").summary))
    status = {s["stage"]: s["status"] for s in log["stages"]}
    for stage in ("spec", "design", "bom", "report"):
        assert status[stage] == "ok"
    assert log["result"] == "ok"
    assert log["circuit_designer_log"]


def test_missing_detail_asks_question(monkeypatch, capsys):
    monkeypatch.chdir(ROOT)
    spec = example_spec("ac_9v").model_copy(update={"missing_fields": ["board size"],
                                                    "clarifying_questions": ["How big is the board?"]})
    monkeypatch.setattr("agents.spec_agent.analyze_prompt", lambda text: spec)
    monkeypatch.setattr(sys, "argv", ["pipeline", "--prompt", "a supply"])
    assert pipeline.main() == 1
    out = capsys.readouterr().out
    assert "How big is the board?" in out
    assert "Traceback" not in out


def test_bridge_error_is_a_clear_message(monkeypatch, capsys):
    monkeypatch.chdir(ROOT)
    monkeypatch.setattr("agents.spec_agent.analyze_prompt", lambda text: example_spec("ac_9v"))
    monkeypatch.setattr(pipeline, "missing_lcsc", lambda bom: [])      # pretend every part has an LCSC number

    def fake_run_stages(netlist, names, bridge=None):
        raise BridgeError("connection refused")

    monkeypatch.setattr("easyeda.builder.run_stages", fake_run_stages)
    monkeypatch.setattr(sys, "argv", ["pipeline", "--prompt", "9V 1A from 12V AC", "--no-llm", "--easyeda"])
    assert pipeline.main() == 3
    out = capsys.readouterr().out
    assert "EasyEDA bridge problem" in out
    assert "Traceback" not in out
    log = read_log(pipeline._slug(example_spec("ac_9v").summary))
    assert log["result"] == "failed"
    assert any(s["stage"] == "easyeda_parts" and s["status"] == "failed" for s in log["stages"])


class FakeGeminiError(Exception):
    code = 503


def test_gemini_busy_gives_one_clear_line():
    assert "Gemini is busy" in pipeline._explain_error(FakeGeminiError("high demand"))