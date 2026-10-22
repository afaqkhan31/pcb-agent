"""Value calculator tests (E24 rounding, capacitor ratings, resistor wattage). No API key needed."""
import pytest

from core.values import (e24_nearest, e24_up, elec_key, elec_voltage_rating, fmt_ohms, fmt_uf,
                         resistor_power_key)


def test_e24_rounding():
    assert e24_up(440) == 470          # LED resistors round up = a bit less current
    assert e24_up(120) == 120          # exact values stay
    assert e24_nearest(3515) == 3600
    assert e24_nearest(71500) == 68000


def test_formatting():
    assert fmt_ohms(240) == "240" and fmt_ohms(4700) == "4.7k" and fmt_ohms(1e6) == "1M"
    assert fmt_uf(0.1) == "100nF" and fmt_uf(4700) == "4700uF"


def test_electrolytic_rating_keeps_20_percent_margin():
    assert elec_voltage_rating(12) == 16        # 12 <= 0.8 x 16
    assert elec_voltage_rating(18) == 25        # 18 > 12.8, 18 <= 20
    assert elec_voltage_rating(30) == 50
    with pytest.raises(ValueError):
        elec_voltage_rating(45)
    assert elec_key(100, 25) == "CAP-ELEC-100UF-25V"


def test_resistor_wattage_has_2x_margin():
    assert resistor_power_key(0.1) == "RES-0.25W"
    assert resistor_power_key(0.188) == "RES-1W"
    with pytest.raises(ValueError):
        resistor_power_key(0.6)
