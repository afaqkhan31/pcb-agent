"""Validated circuit templates. Each block adds parts + nets to a Board.

Every value here is computed by code. Each calculation is written to
board.calculations so a human (Hamdan) can check it in the design report.

Blocks:
  power_input          terminal + reverse-polarity diode + bulk cap  (DC)
                       terminal + bridge rectifier + filter cap      (AC)
  fixed_regulator      78xx (5, 9 or 12 V)
  adjustable_regulator LM317 with pot (+ optional limit resistor)
  led_array            LED strings with series resistors
  ne555_flasher        555 astable driving one LED

Owner: Hamdan.  Rules come from datasheets; tune the constants below.
"""
from __future__ import annotations

import math

from core.components import load_components
from core.values import (ELEC_UF, e24_nearest, e24_up, elec_key, elec_voltage_rating,
                         fmt_ohms, fmt_uf, resistor_power_key)
from templates.board import Board, DesignError

# ----------------------------------------------------------------- constants
DIODE_DROP_V = 1.0            # 1N4007 / 1N5408 forward drop at load
BRIDGE_DROP_V = 1.4           # two diodes conduct in a bridge
MAINS_HZ = 50                 # Pakistan mains
RIPPLE_TARGET_V = 2.0         # filter cap sized for this ripple
FIXED_78XX = {5.0: "L7805CV", 9.0: "L7809CV", 12.0: "L7812CV"}
REG_MAX_A = 1.5
REG_HEADROOM_MIN_V = 2.5      # below this a 78xx/LM317 drops out
REG_HEADROOM_GOOD_V = 3.0
HEATSINK_W = 1.0
SWITCHER_W = 10.0
LM317_VREF = 1.25
LM317_R1 = 240.0              # datasheet value; keeps >= 5 mA minimum load
LM317_VMAX = 37.0
POTS = {5000.0: "POT-5K-RV09", 10000.0: "POT-10K-RV09"}
LED_VF = {"red": 2.0, "green": 2.1, "yellow": 2.1, "orange": 2.0, "blue": 3.2, "white": 3.2}
LED_KEYS = {"red": "LED-5MM-RED", "white": "LED-5MM-WHITE", "green": "LED-3MM-GREEN"}
LED_HEADROOM_V = 1.0          # keep at least this across each LED resistor
NE555_VCC = (4.5, 16.0)
NE555_HIGH_DROP_V = 1.7       # output high is about Vcc - 1.7 V at 20 mA
NE555_R1 = 1000.0
TIMING_CAPS_UF = [10.0, 100.0, 1.0]   # preference order


# ----------------------------------------------------------------- helpers
def _elec(board: Board, c_uf: float, working_v: float, desc: str) -> str:
    """Add an electrolytic. Prefer a catalog part with enough voltage rating."""
    need_v = elec_voltage_rating(working_v)
    catalog = load_components()
    options = sorted(int(k.rsplit("-", 1)[1][:-1]) for k in catalog
                     if k.startswith(f"CAP-ELEC-{c_uf:g}UF-"))
    rating = next((v for v in options if v >= need_v), need_v)
    key = elec_key(c_uf, rating)
    return board.add_part("C", key, f"{fmt_uf(c_uf)} {rating}V", desc, "electrolytic")


def _ceramic(board: Board, nf: int, desc: str) -> str:
    return board.add_part("C", f"CAP-CER-{nf}NF-50V", fmt_uf(nf / 1000), desc, "two_pin")


def _resistor(board: Board, ohms: float, watts: float, desc: str) -> str:
    try:
        key = resistor_power_key(watts)
    except ValueError as e:
        raise DesignError(str(e)) from e
    label = "1W" if key == "RES-1W" else "0.25W"
    return board.add_part("R", key, f"{fmt_ohms(ohms)} {label}", desc, "two_pin")


def _terminal(board: Board, desc: str) -> str:
    return board.add_part("J", "KF301-5.0-2P", "Screw terminal 2P", desc, "two_pin")


# ----------------------------------------------------------------- power input
def power_input(board: Board, kind: str | None, v_in: float, total_current_a: float,
                reverse_protection: bool) -> float:
    """Input connector and conditioning. Returns the lowest DC voltage on net VIN."""
    gnd = board.net("GND", "ground", total_current_a)
    vin = board.net("VIN", "power", total_current_a)
    j = _terminal(board, "Power input")

    if kind == "AC_transformer":
        board.blocks.append("power_input:AC")
        ac1, ac2 = board.net("AC1", "power", total_current_a), board.net("AC2", "power", total_current_a)
        board.connect_2(j, ac1, ac2)
        if total_current_a <= 1.0:
            key = "W04M"
        elif total_current_a <= 2.0:
            key = "KBP206"
        else:
            raise DesignError(f"{total_current_a} A is above the 2 A bridge rectifiers we support")
        br = board.add_part("BR", key, key, "Bridge rectifier", "bridge")
        for net, pin in ((ac1, "AC1"), (ac2, "AC2"), (vin, "+"), (gnd, "-")):
            board.connect(net, br, pin)

        v_peak = v_in * math.sqrt(2) - BRIDGE_DROP_V
        need_uf = total_current_a / (2 * MAINS_HZ * RIPPLE_TARGET_V) * 1e6
        c_uf = next((c for c in ELEC_UF if c >= need_uf), ELEC_UF[-1])
        ripple = total_current_a / (2 * MAINS_HZ * c_uf * 1e-6)
        if c_uf < need_uf:
            board.warnings.append(f"Filter needs {need_uf:.0f} uF; using {c_uf} uF gives {ripple:.1f} V ripple.")
        c = _elec(board, c_uf, v_peak, "Rectifier filter")
        board.connect(vin, c, "+")
        board.connect(gnd, c, "-")
        board.calculations.append(
            f"Rectifier: {v_in} V AC x 1.414 - {BRIDGE_DROP_V} V = {v_peak:.1f} V peak. "
            f"C >= I/(2 f Vr) = {total_current_a}/(2 x {MAINS_HZ} x {RIPPLE_TARGET_V}) = {need_uf:.0f} uF -> {c_uf} uF, "
            f"ripple {ripple:.2f} V.")
        v_min = v_peak - ripple
    else:
        board.blocks.append("power_input:DC")
        if reverse_protection:
            raw = board.net("VIN_RAW", "power", total_current_a)
            board.connect_2(j, raw, gnd)
            if total_current_a <= 1.0:
                key = "1N4007-TP"
            elif total_current_a <= 3.0:
                key = "1N5408"
            else:
                raise DesignError(f"{total_current_a} A is too much for a series protection diode")
            d = board.add_part("D", key, key, "Reverse-polarity protection", "diode")
            board.connect(raw, d, "A")
            board.connect(vin, d, "K")
            v_min = v_in - DIODE_DROP_V
            board.calculations.append(
                f"Reverse protection: {key} in series, VIN = {v_in} - {DIODE_DROP_V} = {v_min:.1f} V.")
        else:
            board.connect_2(j, vin, gnd)
            v_min = v_in
        c = _elec(board, 100, v_in, "Input bulk capacitor")
        board.connect(vin, c, "+")
        board.connect(gnd, c, "-")
    return v_min


# ----------------------------------------------------------------- regulators
def _check_regulator(name: str, v_in: float, v_out_max: float, v_out_min: float, i_out: float,
                     board: Board) -> None:
    headroom = v_in - v_out_max
    if headroom < REG_HEADROOM_MIN_V:
        raise DesignError(f"{name}: input {v_in:.1f} V is only {headroom:.1f} V above {v_out_max} V; "
                          f"a linear regulator needs at least {REG_HEADROOM_MIN_V} V.")
    if headroom < REG_HEADROOM_GOOD_V:
        board.warnings.append(f"{name}: only {headroom:.1f} V headroom; may drop out at full load or high ripple.")
    if i_out > REG_MAX_A:
        raise DesignError(f"{name}: {i_out} A is above the {REG_MAX_A} A regulator limit.")
    watts = (v_in - v_out_min) * i_out
    board.calculations.append(f"{name}: worst-case heat = ({v_in:.1f} - {v_out_min}) x {i_out} = {watts:.1f} W.")
    if watts > SWITCHER_W:
        board.warnings.append(f"{name}: about {watts:.0f} W of heat; needs a large heatsink, "
                              f"or lower the input voltage / use a switching regulator.")
    elif watts > HEATSINK_W:
        board.warnings.append(f"{name}: about {watts:.1f} W of heat; the TO-220 needs a heatsink.")


def _output_stage(board: Board, rail: str, v_out_max: float) -> None:
    """Output caps, protection diode (OUT->IN) and output terminal, shared by both regulators."""
    vout, gnd = rail, "GND"
    c1 = _ceramic(board, 100, f"{rail} output decoupling")
    board.connect_2(c1, vout, gnd)
    c2 = _elec(board, 100, v_out_max, f"{rail} output bulk")
    board.connect(vout, c2, "+")
    board.connect(gnd, c2, "-")
    d = board.add_part("D", "1N4007-TP", "1N4007-TP", f"{rail} regulator protection (OUT->IN)", "diode")
    board.connect(vout, d, "A")
    board.connect("VIN", d, "K")
    j = _terminal(board, f"{rail} output")
    board.connect_2(j, vout, gnd)


def fixed_regulator(board: Board, rail: str, v_out: float, i_out: float, v_in: float) -> None:
    key = FIXED_78XX.get(float(v_out))
    if key is None:
        raise DesignError(f"No fixed regulator for {v_out} V (we have {sorted(FIXED_78XX)}); "
                          f"use adjustable_regulator instead.")
    _check_regulator(rail, v_in, v_out, v_out, i_out, board)
    board.blocks.append(f"fixed_regulator:{rail}")
    board.net(rail, "power", i_out)
    u = board.add_part("U", key, key, f"{v_out:g} V fixed regulator", "78xx")
    board.connect("VIN", u, "IN")
    board.connect("GND", u, "GND")
    board.connect(rail, u, "OUT")
    cin = _ceramic(board, 100, f"{rail} regulator input decoupling")
    board.connect_2(cin, "VIN", "GND")
    _output_stage(board, rail, v_out)


def adjustable_regulator(board: Board, rail: str, v_min: float, v_max: float, i_out: float,
                         v_in: float) -> None:
    if v_min < LM317_VREF - 1e-9:
        raise DesignError(f"{rail}: LM317 cannot go below {LM317_VREF} V (asked {v_min} V).")
    if v_max > LM317_VMAX:
        raise DesignError(f"{rail}: LM317 maximum is {LM317_VMAX} V (asked {v_max} V).")
    _check_regulator(rail, v_in, v_max, v_min, i_out, board)
    board.blocks.append(f"adjustable_regulator:{rail}")
    board.net(rail, "power", i_out)
    adj = board.net(f"{rail}_ADJ", "signal", 0.01)

    u = board.add_part("U", "LM317T", "LM317T", f"Adjustable regulator {v_min:g}-{v_max:g} V", "lm317")
    board.connect("VIN", u, "IN")
    board.connect(rail, u, "OUT")
    board.connect(adj, u, "ADJ")
    cin = _ceramic(board, 100, f"{rail} regulator input decoupling")
    board.connect_2(cin, "VIN", "GND")

    r1 = _resistor(board, LM317_R1, (LM317_VREF ** 2) / LM317_R1, f"{rail} LM317 R1 (OUT-ADJ)")
    board.connect_2(r1, rail, adj)

    r2_max = LM317_R1 * (v_max / LM317_VREF - 1)
    pot_ohms = next((p for p in sorted(POTS) if p >= r2_max), None)
    if pot_ohms is None:
        raise DesignError(f"{rail}: needs {r2_max:.0f} ohm, larger than our biggest pot.")
    rv = board.add_part("RV", POTS[pot_ohms], fmt_ohms(pot_ohms), f"{rail} voltage adjust", "pot")
    board.connect(adj, rv, "1")
    board.connect("GND", rv, "W")
    board.connect("GND", rv, "3")
    calc = (f"{rail}: Vout = 1.25 x (1 + R2/R1), R1 = {LM317_R1:g} ohm. "
            f"R2 for {v_max} V = {r2_max:.0f} ohm -> {fmt_ohms(pot_ohms)} pot")

    pot_v_max = LM317_VREF * (1 + pot_ohms / LM317_R1)
    real_v_max = min(pot_v_max, v_in - REG_HEADROOM_MIN_V)
    if real_v_max > v_max * 1.05:
        # Pot + supply could exceed the request: a parallel resistor caps the range.
        r3 = e24_up(pot_ohms * r2_max / (pot_ohms - r2_max))   # round up: max >= request
        r_par = pot_ohms * r3 / (pot_ohms + r3)
        real_v_max = LM317_VREF * (1 + r_par / LM317_R1)
        rlim = _resistor(board, r3, 0.01, f"{rail} range limit (parallel to pot)")
        board.connect_2(rlim, adj, "GND")
        calc += (f"; pot alone reaches {pot_v_max:.1f} V, so R3 = {fmt_ohms(r3)} in parallel "
                 f"limits it to {real_v_max:.2f} V")
    board.calculations.append(calc + f". Range: {LM317_VREF} - {real_v_max:.2f} V.")
    _output_stage(board, rail, v_max)


# ----------------------------------------------------------------- LEDs
def led_array(board: Board, v_supply: float, count: int, color: str, current_ma: float) -> None:
    color = (color or "red").lower()
    if color not in LED_VF:
        raise DesignError(f"Unknown LED colour '{color}'. Use one of {sorted(LED_VF)}.")
    if not 1 <= count <= 20:
        raise DesignError(f"{count} LEDs: supported range is 1-20.")
    if not 1 <= current_ma <= 30:
        raise DesignError(f"{current_ma} mA: 5 mm LEDs need 1-30 mA.")
    vf, i = LED_VF[color], current_ma / 1000
    per_string = int((v_supply - LED_HEADROOM_V) // vf)
    if per_string < 1:
        raise DesignError(f"{v_supply:.1f} V is too low for a {color} LED (Vf {vf} V).")
    board.blocks.append(f"led_array:{count}x{color}")
    strings = math.ceil(count / per_string)
    board.net("VIN", "power", strings * i)
    key = LED_KEYS.get(color, f"LED-5MM-{color.upper()}")
    board.calculations.append(
        f"LEDs: {color} Vf ~{vf} V, ({v_supply:.1f} - {LED_HEADROOM_V}) / {vf} = {per_string} per string, "
        f"{count} LEDs -> {strings} string(s), total {strings * current_ma:g} mA.")

    left = count
    for s in range(1, strings + 1):
        n = min(per_string, left)
        left -= n
        r_ideal = (v_supply - n * vf) / i
        r = e24_up(r_ideal)
        watts = i * i * r
        rr = _resistor(board, r, watts, f"String {s} current limit")
        node = board.net(f"LED_S{s}_0", "signal", i)
        board.connect_2(rr, "VIN", node)
        for k in range(1, n + 1):
            led = board.add_part("LED", key, f"{color} LED", f"String {s} LED {k}", "led")
            board.connect(node, led, "A")
            node = "GND" if k == n else board.net(f"LED_S{s}_{k}", "signal", i)
            board.connect(node, led, "K")
        real_ma = (v_supply - n * vf) / r * 1000
        board.calculations.append(
            f"String {s}: {n} LED(s), R = ({v_supply:.1f} - {n} x {vf}) / {i} = {r_ideal:.0f} -> "
            f"{fmt_ohms(r)} (E24 up), {real_ma:.1f} mA, {watts * 1000:.0f} mW.")


# ----------------------------------------------------------------- 555 flasher
def ne555_flasher(board: Board, v_supply: float, frequency_hz: float, color: str,
                  current_ma: float) -> None:
    if not NE555_VCC[0] <= v_supply <= NE555_VCC[1]:
        raise DesignError(f"NE555 needs {NE555_VCC[0]}-{NE555_VCC[1]} V (supply is {v_supply:.1f} V).")
    if not 0.1 <= frequency_hz <= 1000:
        raise DesignError(f"{frequency_hz} Hz: supported range is 0.1-1000 Hz.")
    color = (color or "red").lower()
    if color not in LED_VF:
        raise DesignError(f"Unknown LED colour '{color}'.")
    board.blocks.append(f"ne555_flasher:{frequency_hz:g}Hz")

    # Timing: f = 1.44 / ((R1 + 2 R2) C). Pick C so R2 lands in 10k-1M.
    for c_uf in TIMING_CAPS_UF:
        r2_ideal = (1.44 / (frequency_hz * c_uf * 1e-6) - NE555_R1) / 2
        if 10e3 <= r2_ideal <= 1e6:
            break
    else:
        raise DesignError(f"No timing capacitor gives a sensible R2 for {frequency_hz} Hz.")
    r2 = e24_nearest(r2_ideal)
    f_real = 1.44 / ((NE555_R1 + 2 * r2) * c_uf * 1e-6)
    duty = (NE555_R1 + r2) / (NE555_R1 + 2 * r2) * 100

    vcc, gnd = "VIN", "GND"
    t, dis, ctrl = board.net("TIMING", "signal", 0.01), board.net("DIS", "signal", 0.01), \
        board.net("CTRL", "signal", 0.001)
    out = board.net("555_OUT", "signal", current_ma / 1000)
    led_a = board.net("LED_A", "signal", current_ma / 1000)

    u = board.add_part("U", "NE555P", "NE555P", "555 timer, astable", "ne555")
    for net, pin in ((gnd, "GND"), (t, "TRIG"), (out, "OUT"), (vcc, "RESET"),
                     (ctrl, "CTRL"), (t, "THR"), (dis, "DIS"), (vcc, "VCC")):
        board.connect(net, u, pin)
    r1 = _resistor(board, NE555_R1, (v_supply ** 2) / NE555_R1 * 0.5, "555 R1 (VCC-DIS)")
    board.connect_2(r1, vcc, dis)
    r2r = _resistor(board, r2, 0.001, "555 R2 (DIS-THR)")
    board.connect_2(r2r, dis, t)
    ct = _elec(board, c_uf, v_supply, "555 timing capacitor")
    board.connect(t, ct, "+")
    board.connect(gnd, ct, "-")
    cc = _ceramic(board, 10, "555 CTRL decoupling")
    board.connect_2(cc, ctrl, gnd)
    cd = _ceramic(board, 100, "555 supply decoupling")
    board.connect_2(cd, vcc, gnd)

    vf, i = LED_VF[color], current_ma / 1000
    r_led = e24_up((v_supply - NE555_HIGH_DROP_V - vf) / i)
    rl = _resistor(board, r_led, i * i * r_led, "LED current limit")
    board.connect_2(rl, out, led_a)
    led = board.add_part("LED", LED_KEYS.get(color, f"LED-5MM-{color.upper()}"), f"{color} LED",
                         "Flashing LED", "led")
    board.connect(led_a, led, "A")
    board.connect(gnd, led, "K")
    board.calculations.append(
        f"555: f = 1.44 / ((R1 + 2 R2) C), R1 = 1k, C = {fmt_uf(c_uf)}: R2 = {r2_ideal / 1000:.1f}k -> "
        f"{fmt_ohms(r2)}, f = {f_real:.2f} Hz, duty {duty:.0f}%. "
        f"LED R = ({v_supply:.1f} - {NE555_HIGH_DROP_V} - {vf}) / {i} -> {fmt_ohms(r_led)}.")
