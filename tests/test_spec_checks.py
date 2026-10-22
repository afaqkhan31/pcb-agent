"""Tests for the rule checks. No API key needed: we build Specs by hand."""
from core.schemas import BoardConstraints, InputSource, OutputRail, Spec
from core.spec_checks import add_missing_warnings, check_spec


def make_spec(vin, rails):
    """Small helper: rails is a list of (name, v_min, v_max, i_max_a)."""
    return Spec(
        project_type="power_supply",
        summary="test",
        input=InputSource(kind="DC_adapter", voltage_v=vin, current_a=None),
        outputs=[OutputRail(name=n, v_min=a, v_max=b, i_max_a=i) for n, a, b, i in rails],
        board=BoardConstraints(width_mm=80, height_mm=100, layers=1, mounting="THT", max_height_mm=None),
        budget="low",
        missing_fields=[],
        clarifying_questions=[],
        warnings=[],
    )


def test_good_spec_has_no_warnings():
    spec = make_spec(12, [("5V", 5, 5, 0.1)])          # 7 V x 0.1 A = 0.7 W, fine
    assert check_spec(spec) == []


def test_below_lm317_minimum():
    spec = make_spec(18, [("VAR", 1.0, 12, None)])
    assert any("1.25" in w for w in check_spec(spec))


def test_not_enough_headroom():
    spec = make_spec(5, [("3V3", 3.3, 3.3, 0.1)])       # 5 V in, 3.3 V out: only 1.7 V
    assert any("headroom" in w for w in check_spec(spec))


def test_57_watt_case_suggests_switcher():
    spec = make_spec(24, [("5V", 5, 5, 3.0)])           # (24-5) x 3 = 57 W
    assert any("switching" in w for w in check_spec(spec))


def test_unknown_input_voltage_does_not_crash():
    spec = make_spec(None, [("5V", 5, 5, None)])
    assert check_spec(spec) == []


def test_warnings_are_added_once():
    spec = make_spec(24, [("5V", 5, 5, 3.0)])
    add_missing_warnings(spec)
    add_missing_warnings(spec)
    assert len(spec.warnings) == len(check_spec(spec))
