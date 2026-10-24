"""Circuit template tests. Numbers here were checked by hand; Hamdan signs them off.
No API key needed."""
import pytest

from core.schemas import BlockRequest, BoardConstraints, DesignPlan, InputSource, OutputRail, Spec
from core.values import e24_nearest, e24_up, fmt_ohms, fmt_uf
from templates import DesignError, build_design


# ------------------------------------------------------------------ helpers
def spec(v_in, kind="DC_adapter", project_type="power_supply", outputs=(), missing=()):
    return Spec(project_type=project_type, summary="test",
                input=InputSource(kind=kind, voltage_v=v_in, current_a=None),
                outputs=[OutputRail(name=n, v_min=a, v_max=b, i_max_a=i) for n, a, b, i in outputs],
                board=BoardConstraints(width_mm=80, height_mm=100, layers=1, mounting="THT", max_height_mm=None),
                budget="low", missing_fields=list(missing), clarifying_questions=[], warnings=[])


def block(**kw):
    base = dict(rail_name=None, v_out=None, v_out_min=None, v_out_max=None, i_out_a=None,
                led_count=None, led_color=None, led_current_ma=None, frequency_hz=None)
    base.update(kw)
    return BlockRequest(**base)


def plan(*blocks, protect=False):
    return DesignPlan(blocks=list(blocks), reverse_protection=protect, explanation="test")


def values(design):
    return {p.ref: p.value for p in design.netlist.parts}


def net_of(design, ref, pin_name):
    part = next(p for p in design.netlist.parts if p.ref == ref)
    number = next(n for n, name in part.pins.items() if name == pin_name)
    return next(n.name for n in design.netlist.nets
                if any(x.ref == ref and x.pin == number for x in n.nodes))


# ------------------------------------------------------------------ values
def test_e24():
    assert e24_up(440) == 470
    assert e24_up(120) == 120
    assert e24_nearest(3515) == 3600
    assert fmt_ohms(240) == "240" and fmt_ohms(4700) == "4.7k" and fmt_ohms(1e6) == "1M"
    assert fmt_uf(0.1) == "100nF" and fmt_uf(4700) == "4700uF"


# ------------------------------------------------------------------ regulators
DUAL = plan(block(template_id="fixed_regulator", rail_name="5V", v_out=5, i_out_a=0.5),
            block(template_id="adjustable_regulator", rail_name="VAR", v_out_min=1.25, v_out_max=12, i_out_a=1.0),
            protect=True)


def test_dual_rail_builds_and_is_fully_connected():
    d = build_design(spec(18), DUAL)
    assert d.netlist.blocks == ["power_input:DC", "fixed_regulator:5V", "adjustable_regulator:VAR"]
    assert len(d.netlist.parts) == 18
    # every net has >= 2 pins (build_design already enforces it; this documents it)
    assert all(len(n.nodes) >= 2 for n in d.netlist.nets)


def test_7805_pins_go_to_the_right_nets():
    d = build_design(spec(18), DUAL)
    u = next(p.ref for p in d.netlist.parts if p.catalog_key == "L7805CV")
    assert net_of(d, u, "IN") == "VIN"
    assert net_of(d, u, "GND") == "GND"
    assert net_of(d, u, "OUT") == "5V"


def test_reverse_diode_polarity():
    d = build_design(spec(18), DUAL)
    assert net_of(d, "D1", "A") == "VIN_RAW"      # anode from the connector
    assert net_of(d, "D1", "K") == "VIN"          # cathode feeds the board
    assert d.v_in_min == pytest.approx(17.0)


def test_lm317_values():
    d = build_design(spec(18), DUAL)
    v = values(d)
    assert "240 0.25W" in v.values()                     # R1
    assert "5k" in v.values()                            # pot
    assert "3.6k 0.25W" in v.values()                    # range limit: 5k || 3.6k = 2093 -> 12.15 V
    assert any("1.25 - 12.15 V" in c for c in d.calculations)


def test_lm317_below_1v25_rejected():
    bad = plan(block(template_id="adjustable_regulator", rail_name="VAR", v_out_min=1.0, v_out_max=12, i_out_a=1))
    with pytest.raises(DesignError, match="1.25"):
        build_design(spec(18), bad)


def test_headroom_rejected():
    p = plan(block(template_id="adjustable_regulator", rail_name="3V3", v_out_min=3.3, v_out_max=3.3, i_out_a=0.3))
    with pytest.raises(DesignError, match="headroom|at least"):
        build_design(spec(5, kind="USB"), p)


def test_reverse_diode_counts_in_headroom():
    # 7.5 V in: OK without the diode (2.5 V headroom), fails with it (1.5 V)
    p5 = block(template_id="fixed_regulator", rail_name="5V", v_out=5, i_out_a=0.1)
    build_design(spec(7.5), plan(p5))
    with pytest.raises(DesignError):
        build_design(spec(7.5), plan(p5, protect=True))


def test_only_5_9_12_fixed():
    with pytest.raises(DesignError, match="adjustable"):
        build_design(spec(12), plan(block(template_id="fixed_regulator", rail_name="6V", v_out=6, i_out_a=0.1)))


def test_heat_warning():
    d = build_design(spec(24), plan(block(template_id="fixed_regulator", rail_name="5V", v_out=5, i_out_a=1.0)))
    assert any("19 W" in w and "switching" in w for w in d.warnings)


def test_ac_input_rectifier():
    d = build_design(spec(12, kind="AC_transformer"),
                     plan(block(template_id="fixed_regulator", rail_name="9V", v_out=9, i_out_a=1.0)))
    v = values(d)
    assert v["BR1"] == "W04M"
    assert "4700uF 25V" in v.values()                    # 1 A / (2 x 50 Hz x 2 V) = 5000 uF -> 4700
    assert d.v_in_min == pytest.approx(13.43, abs=0.05)  # 15.57 peak - 2.13 ripple


def test_duplicate_rail_rejected():
    p5 = block(template_id="fixed_regulator", rail_name="5V", v_out=5, i_out_a=0.1)
    with pytest.raises(DesignError, match="Duplicate"):
        build_design(spec(12), plan(p5, p5))


def test_incomplete_spec_rejected():
    with pytest.raises(DesignError, match="incomplete"):
        build_design(spec(12, missing=["outputs[0].i_max_a"]), DUAL)


# ------------------------------------------------------------------ LEDs
def test_led_array_strings():
    d = build_design(spec(12, project_type="led"),
                     plan(block(template_id="led_array", led_count=10, led_color="white", led_current_ma=20)))
    resistors = sorted(p.value for p in d.netlist.parts if p.ref.startswith("R"))
    assert resistors == ["120 0.25W", "120 0.25W", "120 0.25W", "470 1W"]   # 3+3+3+1 LEDs
    assert sum(p.ref.startswith("LED") for p in d.netlist.parts) == 10


def test_led_supply_too_low():
    with pytest.raises(DesignError, match="too low"):
        build_design(spec(3, project_type="led"),
                     plan(block(template_id="led_array", led_count=1, led_color="white", led_current_ma=10)))


def test_scope_limit_25_parts():
    with pytest.raises(DesignError, match="25-part"):
        build_design(spec(5, project_type="led"),
                     plan(block(template_id="led_array", led_count=20, led_color="red", led_current_ma=10)))


# ------------------------------------------------------------------ 555
def test_555_flasher_1hz():
    d = build_design(spec(9, kind="battery", project_type="timer"),
                     plan(block(template_id="ne555_flasher", frequency_hz=1, led_color="red", led_current_ma=15)))
    v = values(d)
    assert "68k 0.25W" in v.values()                     # R2 = (1.44/(1 x 10uF) - 1k)/2 = 71.5k -> 68k
    assert any("f = 1.05 Hz" in c for c in d.calculations)
    u = next(p.ref for p in d.netlist.parts if p.catalog_key == "NE555P")
    assert net_of(d, u, "TRIG") == net_of(d, u, "THR") == "TIMING"
    assert net_of(d, u, "RESET") == net_of(d, u, "VCC") == "VIN"


def test_555_voltage_range():
    with pytest.raises(DesignError, match="NE555 needs"):
        build_design(spec(24, project_type="timer"),
                     plan(block(template_id="ne555_flasher", frequency_hz=1, led_color="red", led_current_ma=15)))


# ------------------------------------------------------------------ widths
def test_trace_widths_follow_net_class():
    d = build_design(spec(18), DUAL)
    assert d.trace_widths["GND"] >= 1.2
    assert d.trace_widths["VAR_ADJ"] == 0.8
