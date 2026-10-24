"""Circuit Designer Agent loop. A fake 'Gemini' is used, so no API key."""
import pytest

from agents.circuit_designer import MAX_ATTEMPTS, design_board, rules_plan
from core.schemas import DesignPlan
from templates import DesignError
from tests.test_templates import block, plan, spec

GOOD = plan(block(template_id="fixed_regulator", rail_name="5V", v_out=5, i_out_a=0.5))
BAD = plan(block(template_id="fixed_regulator", rail_name="6V", v_out=6, i_out_a=0.5))   # no 7806


class FakeGemini:
    """Returns the queued plans in order and records every prompt it was sent."""
    def __init__(self, *plans):
        self.plans, self.prompts = list(plans), []

    def __call__(self, contents, system):
        self.prompts.append(contents)
        item = self.plans.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def test_good_plan_accepted_first_time():
    fake = FakeGemini(GOOD)
    r = design_board(spec(12), "5V supply", ask=fake)
    assert r.source == "llm" and len(fake.prompts) == 1
    assert "fixed_regulator:5V" in r.design.netlist.blocks


def test_rejected_plan_error_is_fed_back():
    fake = FakeGemini(BAD, GOOD)
    r = design_board(spec(12), "5V supply", ask=fake)
    assert r.source == "llm" and len(fake.prompts) == 2
    assert "rejected it with this error" in fake.prompts[1]
    assert "No fixed regulator for 6" in fake.prompts[1]      # the exact code error reached the LLM


def test_gives_up_after_max_attempts():
    fake = FakeGemini(*([BAD] * MAX_ATTEMPTS))
    with pytest.raises(DesignError, match="No valid design"):
        design_board(spec(12), "6V supply", ask=fake)


def test_api_failure_falls_back_to_rules():
    fake = FakeGemini(RuntimeError("429 RESOURCE_EXHAUSTED"))
    s = spec(18, outputs=[("5V", 5, 5, 0.5), ("VAR", 1.25, 12, 1.0)])
    r = design_board(s, "dual rail", ask=fake)
    assert r.source == "rules"
    assert r.design.netlist.blocks == ["power_input:DC", "fixed_regulator:5V", "adjustable_regulator:VAR"]


def test_rules_plan_skips_diode_when_headroom_is_tight():
    p = rules_plan(spec(8, outputs=[("5V", 5, 5, 0.1)]))     # 8 - 1 - 5 = 2 V < 2.5 V
    assert p.reverse_protection is False


def test_incomplete_spec_never_reaches_the_llm():
    fake = FakeGemini(GOOD)
    with pytest.raises(DesignError, match="missing"):
        design_board(spec(12, missing=["input.voltage_v"]), "x", ask=fake)
    assert fake.prompts == []
