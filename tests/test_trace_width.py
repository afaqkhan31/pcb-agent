from core.trace_width import (
    MIN_POWER_WIDTH_MM,
    MIN_SIGNAL_WIDTH_MM,
    ipc2221_width_mm,
    trace_width_mm,
)


def test_ipc_1A_is_about_0_3mm():
    # Known reference value: 1 A, 10 C rise, 1 oz external ≈ 0.30 mm
    assert 0.28 <= ipc2221_width_mm(1.0) <= 0.32


def test_signal_never_below_floor():
    assert trace_width_mm("signal", 0.001) == MIN_SIGNAL_WIDTH_MM


def test_power_never_below_floor():
    assert trace_width_mm("power", 0.1) == MIN_POWER_WIDTH_MM


def test_high_current_exceeds_floor():
    assert trace_width_mm("power", 5.0) > MIN_POWER_WIDTH_MM


def test_power_wider_than_signal_same_current():
    assert trace_width_mm("power", 0.2) > trace_width_mm("signal", 0.2)


def test_more_current_means_wider():
    # Width must grow with current (checked at values above the floor)
    assert trace_width_mm("power", 5.0) > trace_width_mm("power", 3.0)


def test_3A_power_trace_about_1_37mm():
    # IPC-2221, 10 C rise, 1 oz: 3 A needs about 1.37 mm, above the 1.2 mm floor
    assert 1.30 <= trace_width_mm("power", 3.0) <= 1.45


def test_ground_uses_power_floor():
    assert trace_width_mm("ground", 0.01) == MIN_POWER_WIDTH_MM


def test_unknown_current_uses_floor():
    assert trace_width_mm("signal", None) == MIN_SIGNAL_WIDTH_MM
