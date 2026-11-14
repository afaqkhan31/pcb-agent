"""Tests for relay_driver and unregulated_output. Numbers are Hamdan's hand calculations.
No API key needed."""
import pytest

from core.schemas import BlockRequest, BoardConstraints, DesignPlan, InputSource, OutputRail, Spec
from core.values import e24_down
from templates import DesignError, build_design


# ------------------------------------------------------------------ helpers
def spec(v_in, kind="DC_adapter", project_type="switching", outputs=(), missing=()):
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


def keys(design):
    return {p.catalog_key for p in design.netlist.parts}


def net_of(design, ref, pin_name):
    part = next(p for p in design.netlist.parts if p.ref == ref)
    number = next(n for n, name in part.pins.items() if name == pin_name)
    return next(n.name for n in design.netlist.nets
                if any(x.ref == ref and x.pin == number for x in n.nodes))


def relay(control_v=None, load_a=2.0):
    return plan(block(template_id="relay_driver", control_voltage_v=control_v, load_current_a=load_a))


# ------------------------------------------------------------------ e24_down
def test_e24_down():
    # approx: E24 maths gives 819.9999 for 820
    assert e24_down(1433) == pytest.approx(1300)
    assert e24_down(602) == pytest.approx(560)
    assert e24_down(867) == pytest.approx(820)


# ------------------------------------------------------------------ relay driver
def test_relay_12v_relay_5v_control():
    d = build_design(spec(12), relay(control_v=5))
    assert "RELAY-SRD-12VDC-SL-C" in keys(d)
    assert "1.3k 0.25W" in values(d).values()            # Rb = 4.3 / 3 mA = 1433 -> 1.3k
    assert "10k 0.25W" in values(d).values()             # base pull-down
    assert any("Ic = 12/400 = 30.0 mA" in c for c in d.calculations)


def test_relay_5v_relay_5v_control():
    d = build_design(spec(5, kind="USB"), relay(control_v=5))
    assert "RELAY-SRD-05VDC-SL-C" in keys(d)
    assert "560 0.25W" in values(d).values()             # Rb = 4.3 / 7.14 mA = 602 -> 560
    assert any("Ic = 5/70 = 71.4 mA" in c for c in d.calculations)


def test_relay_12v_relay_3v3_control():
    d = build_design(spec(12), relay(control_v=3.3))
    assert "820 0.25W" in values(d).values()             # Rb = 2.6 / 3 mA = 867 -> 820


def test_relay_default_control_voltage_is_5v():
    d = build_design(spec(12), relay(control_v=None))
    assert "1.3k 0.25W" in values(d).values()


def test_relay_no_coil_for_9v():
    with pytest.raises(DesignError, match="No relay coil"):
        build_design(spec(9), relay(control_v=5))


def test_relay_load_current_too_high():
    with pytest.raises(DesignError, match="contacts"):
        build_design(spec(12), relay(control_v=5, load_a=15))


def test_relay_control_voltage_out_of_range():
    with pytest.raises(DesignError, match="Control voltage"):
        build_design(spec(12), relay(control_v=1.0))


def test_relay_netlist_and_flyback_diode():
    d = build_design(spec(12), relay(control_v=5))       # build_design already checks every pin is connected
    diode = next(p.ref for p in d.netlist.parts if p.description == "Relay flyback diode")
    assert net_of(d, diode, "K") == "VIN"
    assert net_of(d, diode, "A") == "COIL_LO"
    q = next(p.ref for p in d.netlist.parts if p.catalog_key == "PN2222A")
    assert net_of(d, q, "B") == "BASE"
    assert net_of(d, q, "E") == "GND"
    assert net_of(d, q, "C") == "COIL_LO"
    assert d.netlist.blocks == ["power_input:DC", "relay_driver:12V"]


def test_relay_mains_warning():
    d = build_design(spec(12), relay(control_v=5))
    assert any("low-voltage loads only" in w for w in d.warnings)


# ------------------------------------------------------------------ unregulated output
def test_unregulated_12v_ac_half_amp():
    d = build_design(spec(12, kind="AC_transformer"),
                     plan(block(template_id="unregulated_output", i_out_a=0.5)))
    v = values(d)
    assert v["BR1"] == "W04M"
    assert "4700uF 25V" in v.values()                    # 0.5 / (2 x 50 x 2) = 2500 uF -> 4700
    assert sum(p.ref.startswith("J") for p in d.netlist.parts) == 2   # input + output terminal
    assert any("14.5" in c for c in d.calculations)      # 15.57 peak - 1.06 ripple
    assert d.netlist.blocks == ["power_input:AC", "unregulated_output"]


def test_unregulated_rejects_dc_input():
    with pytest.raises(DesignError, match="AC input"):
        build_design(spec(12), plan(block(template_id="unregulated_output", i_out_a=0.5)))