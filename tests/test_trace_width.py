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
