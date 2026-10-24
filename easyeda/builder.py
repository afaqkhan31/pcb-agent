"""Build a Netlist in EasyEDA Pro through the official bridge.

Generalises the Sprint 1 spike: any netlist from the Circuit Designer, not one fixed circuit.
The JavaScript is generated from fixed templates by this code; the LLM never writes it.

  python -m easyeda.builder parts output/dual_rail/netlist.json   # LCSC numbers exist + THT?
  python -m easyeda.builder sch   output/dual_rail/netlist.json   # place + wire (schematic tab open)
  python -m easyeda.builder erc   output/dual_rail/netlist.json
  python -m easyeda.builder pcb   output/dual_rail/netlist.json   # import, net classes, layout, route (PCB tab open)
  python -m easyeda.builder drc   output/dual_rail/netlist.json

Owner: Shammas.  EasyEDA review: Hamdan.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from core.schemas import Netlist, Part
from core.trace_width import trace_width_mm
from easyeda.bridge import Bridge, BridgeError, js_value
from easyeda.spike import JS_DRC, JS_ERC, JS_FIND, JS_IMPORT, JS_LAYOUT, JS_ROUTE, looks_smd

COLUMNS = 5
SPACING = 300                   # schematic units (10 mil each)

# EasyEDA symbols name pins differently; these count as the same pin.
PIN_ALIASES = [
    {"IN", "VI", "VIN", "INPUT"}, {"OUT", "VO", "VOUT", "OUTPUT"}, {"GND", "COM", "COMMON"},
    {"ADJ", "ADJ/GND", "ADJUST"}, {"K", "CATHODE"}, {"A", "ANODE"}, {"W", "WIPER"},
    {"DIS", "DISCH", "DISCHARGE"}, {"THR", "THRES", "THRESHOLD"}, {"TRIG", "TRIGGER"},
    {"CTRL", "CONT", "CV", "CONTROL"}, {"RESET", "RST", "R"}, {"VCC", "V+", "VDD"},
]


# ------------------------------------------------------------------ pure helpers (tested)
def pin_nets(netlist: Netlist) -> dict[str, dict[str, str]]:
    """{ref: {pin number: net name}}"""
    out: dict[str, dict[str, str]] = {}
    for net in netlist.nets:
        for node in net.nodes:
            out.setdefault(node.ref, {})[node.pin] = net.name
    return out


def flag_kinds(netlist: Netlist) -> dict[str, str]:
    """Which schematic symbol to put on each net: Ground flag, Power flag or a net port."""
    kinds = {}
    for n in netlist.nets:
        kinds[n.name] = "Ground" if n.net_class == "ground" else "Power" if n.net_class == "power" else "BI"
    return kinds


def _same_pin(a: str, b: str) -> bool:
    a, b = a.strip().upper(), b.strip().upper()
    if a == b:
        return True
    return any(a in group and b in group for group in PIN_ALIASES)


def compare_pins(part: Part, eda_pins: list[dict]) -> tuple[list[str], list[str]]:
    """Compare our catalog pinout with the EasyEDA symbol. Returns (errors, warnings)."""
    errors, warnings = [], []
    eda = {str(p["number"]): str(p.get("name") or "") for p in eda_pins}
    for number, name in part.pins.items():
        if number not in eda:
            errors.append(f"{part.ref}: EasyEDA symbol has no pin {number} ({name})")
            continue
        eda_name = eda[number]
        both_named = not (name.isdigit() or eda_name.isdigit() or eda_name == "")
        if both_named and not _same_pin(name, eda_name):
            errors.append(f"{part.ref}: pin {number} is '{eda_name}' in EasyEDA but '{name}' in our catalog")
    for number in eda:
        if number not in part.pins:
            warnings.append(f"{part.ref}: EasyEDA pin {number} ({eda[number]}) is not in our netlist (left open)")
    return errors, warnings


def net_classes(netlist: Netlist) -> dict[str, list[str]]:
    power = [n.name for n in netlist.nets if n.net_class in ("power", "ground")]
    signal = [n.name for n in netlist.nets if n.net_class == "signal"]
    return {k: v for k, v in (("POWER", power), ("SIGNAL", signal)) if v}


def net_widths(netlist: Netlist) -> dict[str, float]:
    return {n.name: trace_width_mm(n.net_class, n.current_a) for n in netlist.nets}


# ------------------------------------------------------------------ JavaScript
def js_place(part: Part, x: int, y: int) -> str:
    return JS_FIND + f"""
const dev = await findDevice({js_value(part.lcsc)});
if (!dev) {{ throw new Error('Not in EasyEDA library: ' + {js_value(part.lcsc)}); }}
const comp = await eda.sch_PrimitiveComponent.create(dev, {x}, {y}, undefined, 0, false, true, true);
const id = comp.getState_PrimitiveId();
await eda.sch_PrimitiveComponent.modify(id, {{ designator: {js_value(part.ref)} }});
const pins = await eda.sch_PrimitiveComponent.getAllPinsByPrimitiveId(id);
return {{ id: id, pins: pins.map(p => ({{ number: String(p.pinNumber), name: p.pinName, x: p.x, y: p.y }})) }};
"""


def js_wire(pins: list[dict], cx: int, cy: int, nets: dict[str, str], kinds: dict[str, str]) -> str:
    jobs = []
    for p in pins:
        net = nets.get(p["number"])
        if not net:
            continue
        horizontal = abs(p["x"] - cx) >= abs(p["y"] - cy)
        ex = p["x"] + ((-30 if p["x"] < cx else 30) if horizontal else 0)
        ey = p["y"] + (0 if horizontal else (-30 if p["y"] < cy else 30))
        jobs.append({"x": p["x"], "y": p["y"], "ex": ex, "ey": ey, "net": net, "kind": kinds[net]})
    return f"""
const jobs = {js_value(jobs)};
for (const j of jobs) {{
  await eda.sch_PrimitiveWire.create([j.x, j.y, j.ex, j.ey], j.net);
  if (j.kind === 'BI') {{ await eda.sch_PrimitiveComponent.createNetPort('BI', j.net, j.ex, j.ey); }}
  else {{ await eda.sch_PrimitiveComponent.createNetFlag(j.kind, j.net, j.ex, j.ey); }}
}}
return jobs.length;
"""


def js_net_classes(classes: dict[str, list[str]]) -> str:
    colours = {"POWER": {"r": 220, "g": 40, "b": 40, "alpha": 1}, "SIGNAL": {"r": 40, "g": 90, "b": 220, "alpha": 1}}
    calls = "\n".join(f"out.push(await eda.pcb_Drc.createNetClass({js_value(k)}, {js_value(v)}, {js_value(colours[k])}));"
                      for k, v in classes.items())
    return f"const out = [];\n{calls}\nreturn out;"


# ------------------------------------------------------------------ stages
def stage_parts(b: Bridge, netlist: Netlist) -> bool:
    from easyeda.spike import js_parts
    missing = [p.ref for p in netlist.parts if not p.lcsc]
    if missing:
        print(f"  STOP: no LCSC number for {', '.join(missing)}")
        return False
    ok = True
    for r in b.run(js_parts(sorted({p.lcsc for p in netlist.parts}))):
        if not r["found"]:
            print(f"  FAIL {r['lcsc']}: not in EasyEDA library"); ok = False
        elif looks_smd(r.get("footprint")):
            print(f"  FAIL {r['lcsc']}: {r['name']} looks SMD ({r['footprint']})"); ok = False
        else:
            print(f"  OK   {r['lcsc']}: {r['name']}  [{r['footprint']}]")
    return ok


def stage_sch(b: Bridge, netlist: Netlist) -> bool:
    nets, kinds = pin_nets(netlist), flag_kinds(netlist)
    all_errors = []
    for i, part in enumerate(netlist.parts):
        x, y = (i % COLUMNS) * SPACING, -(i // COLUMNS) * SPACING
        placed = b.run(js_place(part, x, y))
        errors, warnings = compare_pins(part, placed["pins"])
        for w in warnings:
            print("  !", w)
        if errors:
            all_errors += errors
            print(f"  {part.ref:5} placed, NOT wired (pin mismatch)")
            continue
        n = b.run(js_wire(placed["pins"], x, y, nets.get(part.ref, {}), kinds))
        print(f"  {part.ref:5} {part.lcsc:9} placed, {n} pin(s) wired")
    if all_errors:
        print("\n  Pin mismatches (fix data/components.json pins, or add an alias in easyeda/builder.py):")
        for e in all_errors:
            print("   -", e)
        return False
    print("  Schematic done. Save it in EasyEDA (Ctrl+S).")
    return True


def stage_erc(b: Bridge, netlist: Netlist) -> bool:
    errors = b.run(JS_ERC) or []
    fatal = [e for e in errors if e.get("type") in ("fatalError", "error")]
    print(f"  ERC: {len(fatal)} error(s), {len(errors) - len(fatal)} warning(s)")
    for e in errors[:20]:
        print(f"   - [{e.get('type')}] {e.get('rule')} net={e.get('net')}")
    return not fatal



def stage_pcb(b: Bridge, netlist: Netlist) -> bool:
    print("  import from schematic:", b.run(JS_IMPORT))
    print("  net classes:", b.run(js_net_classes(net_classes(netlist))))

    widths = net_widths(netlist)
    print("  trace widths to set in Design Rules (mm):",
          ", ".join(f"{n}={w:.2f}" for n, w in widths.items()))

    print("  auto layout:", b.run(JS_LAYOUT))

    try:
        r = b.run(JS_ROUTE)
    except BridgeError as e:
        print(f"  routing still running or failed ({e}). Wait for EasyEDA, then run the drc stage.")
        return False

    print(f"  routed {r.get('successNetsCount')}/{r.get('totalNetsCount')} nets on BOTTOM; failed: {r.get('failedNets')}")

    if r.get("failedNets"):
        return False

    print("  verifying routed PCB...")

    verify_pcb_tracks(b, netlist)
    verify_connectivity(b)
    check_drc(b)

    print("  PCB verification completed")
    return True



def stage_drc(b: Bridge, netlist: Netlist) -> bool:
    errors = b.run(JS_DRC) or []
    print(f"  DRC: {len(errors)} issue(s)")
    for e in errors[:20]:
        print("   -", json.dumps(e, default=str)[:160])
    return not errors


STAGES = {"parts": stage_parts, "sch": stage_sch, "erc": stage_erc, "pcb": stage_pcb, "drc": stage_drc}


def run_stages(netlist: Netlist, names: list[str], bridge: Bridge | None = None) -> bool:
    b = bridge or Bridge()
    for name in names:
        print(f"[{name}]")
        if not STAGES[name](b, netlist):
            print(f"Stopped at '{name}'.")
            return False
    return True


def main() -> int:
    if len(sys.argv) != 3 or sys.argv[1] not in STAGES:
        print("Usage: python -m easyeda.builder [" + "|".join(STAGES) + "] path/to/netlist.json")
        return 1
    netlist = Netlist.model_validate_json(Path(sys.argv[2]).read_text(encoding="utf-8"))
    try:
        return 0 if run_stages(netlist, [sys.argv[1]]) else 2
    except BridgeError as e:
        print(f"  ERROR: {e}")
        return 3

# --- Integrated non-destructive PCB inspection helpers ---
from check_connectivity import check_connectivity
OUT = Path("output")
BOTTOM_LAYER = 2
MIL_PER_MM = 1 / 0.0254

JS_SAFE_LAYOUT = """
const comps = await eda.pcb_PrimitiveComponent.getAll();
const pads = await eda.pcb_PrimitivePad.getAll();

if (comps.length === 0) {
    throw new Error('No PCB components found');
}

const bounds = [];

for (const comp of comps) {
    const id = comp.getState_PrimitiveId();

    const compPads = pads.filter(p =>
        p.getState_PrimitiveId().startsWith(id)
    );

    if (compPads.length === 0) {
        throw new Error(
            'No pads found for ' + comp.getState_Designator()
        );
    }

    const left = Math.min(...compPads.map(p =>
        p.getState_X() - p.getState_Pad()[1] / 2
    ));

    const right = Math.max(...compPads.map(p =>
        p.getState_X() + p.getState_Pad()[1] / 2
    ));

    const top = Math.min(...compPads.map(p =>
        p.getState_Y() - p.getState_Pad()[2] / 2
    ));

    const bottom = Math.max(...compPads.map(p =>
        p.getState_Y() + p.getState_Pad()[2] / 2
    ));

    bounds.push({
        id: id,
        name: comp.getState_Designator(),
        x: comp.getState_X(),
        y: comp.getState_Y(),
        left, right, top, bottom
    });
}

bounds.sort((a, b) => a.name.localeCompare(b.name));

let nextX = 300;
const gap = 200;
const centerY = -300;
const results = [];

for (const b of bounds) {
    const width = b.right - b.left;
    const centerX = (b.left + b.right) / 2;
    const currentCenterY = (b.top + b.bottom) / 2;

    const targetCenterX = nextX + width / 2;

    const newX = b.x + (targetCenterX - centerX);
    const newY = b.y + (centerY - currentCenterY);

    await eda.pcb_PrimitiveComponent.modify(b.id, {
        x: newX,
        y: newY
    });

    results.push({
        component: b.name,
        x: newX,
        y: newY
    });

    nextX += width + gap;
}

return results;
"""


JS_OUTLINE = """
const comps = await eda.pcb_PrimitiveComponent.getAll();
const pads = await eda.pcb_PrimitivePad.getAll();

if (comps.length === 0) {
    throw new Error('No PCB components found');
}

const positions = [];

for (const comp of comps) {
    const id = comp.getState_PrimitiveId();

    const compPads = pads.filter(p =>
        p.getState_PrimitiveId().startsWith(id)
    );

    if (compPads.length === 0) {
        throw new Error(
            'No pads found for ' + comp.getState_Designator()
        );
    }

    positions.push({
        left: Math.min(...compPads.map(p =>
            p.getState_X() - p.getState_Pad()[1] / 2
        )),
        right: Math.max(...compPads.map(p =>
            p.getState_X() + p.getState_Pad()[1] / 2
        )),
        top: Math.min(...compPads.map(p =>
            p.getState_Y() - p.getState_Pad()[2] / 2
        )),
        bottom: Math.max(...compPads.map(p =>
            p.getState_Y() + p.getState_Pad()[2] / 2
        ))
    });
}

const margin = 300;

const x1 = Math.min(...positions.map(p => p.left)) - margin;
const x2 = Math.max(...positions.map(p => p.right)) + margin;
const y1 = Math.min(...positions.map(p => p.top)) - margin;
const y2 = Math.max(...positions.map(p => p.bottom)) + margin;

const polygon = eda.pcb_MathPolygon.createPolygon([
    x1, y1,
    'L', x2, y1,
    x2, y2,
    x1, y2,
    x1, y1
]);

const outline = await eda.pcb_PrimitivePolyline.create(
    '', 11, polygon, 10, false
);

if (!outline) {
    throw new Error('Board outline creation failed');
}

return {
    success: true,
    x1, y1, x2, y2
};
"""


JS_GET_TRACKS = """
const lines = await eda.pcb_PrimitiveLine.getAll();

return lines.map(line => ({
    id: line.getState_PrimitiveId(),
    net: line.getState_Net(),
    width: line.getState_LineWidth(),
    layer: line.getState_Layer()
}));
"""


def save(name: str, data: object) -> None:
    OUT.mkdir(exist_ok=True)
    path = OUT / name
    path.write_text(
        json.dumps(data, indent=2, default=str),
        encoding="utf-8"
    )
    print("  saved", path)


def load_netlist(path: str) -> Netlist:
    file_path = Path(path)

    if not file_path.is_file():
        raise FileNotFoundError(
            "Netlist file not found: " + str(file_path)
        )

    data = json.loads(file_path.read_text(encoding="utf-8"))

    if hasattr(Netlist, "model_validate"):
        return Netlist.model_validate(data)

    return Netlist.parse_obj(data)


def check_connection(b: Bridge) -> None:
    health = b.health()

    if not health.get("edaConnected"):
        raise BridgeError("EasyEDA Pro is not connected")

    print("  EasyEDA connected successfully")


def check_empty_pcb(b: Bridge) -> None:
    count = b.run("""
const ids = await eda.pcb_PrimitiveComponent.getAllPrimitiveId();
return ids.length;
""")

    if count > 0:
        raise RuntimeError(
            "PCB already contains components. "
            "Open a fresh PCB before running the builder."
        )

    print("  PCB is empty and ready")


def place_components(b: Bridge) -> None:
    print("  placing PCB components...")
    result = b.run(JS_SAFE_LAYOUT)

    for comp in result or []:
        print(" ", comp)


def create_outline(b: Bridge) -> None:
    print("  creating PCB board outline...")
    result = b.run(JS_OUTLINE)
    print("  result:", result)


def calculate_net_widths(netlist: Netlist) -> dict[str, float]:
    widths = {}

    for net in netlist.nets:
        net_class = net.net_class.lower()
        widths[net.name] = trace_width_mm(
            net_class,
            net.current_a
        )

    return widths


def mm_to_mil(width_mm: float) -> float:
    return round(width_mm * MIL_PER_MM, 2)


def apply_trace_widths(netlist: Netlist) -> dict[str, float]:
    widths = calculate_net_widths(netlist)
    widths_mil = {}

    for net, width in widths.items():
        widths_mil[net] = mm_to_mil(width)

    print("Required PCB track widths:")

    for net, width in widths_mil.items():
        print(" ", net, ":", width, "mil")

    return widths_mil


def update_pcb_track_widths(
    b: Bridge,
    netlist: Netlist,
    modify: bool = False
) -> list[dict]:
    widths = apply_trace_widths(netlist)
    tracks = b.run(JS_GET_TRACKS) or []

    if not tracks:
        print("  No PCB tracks found")
        return []

    changes = []

    for track in tracks:
        net = track["net"]

        if net not in widths:
            raise RuntimeError(
                "No calculated width for PCB net: " + str(net)
            )

        if track["layer"] != BOTTOM_LAYER:
            raise RuntimeError(
                "Track found outside bottom layer: " + str(net)
            )

        target_width = widths[net]

        changes.append({
            "id": track["id"],
            "net": net,
            "old_width": track["width"],
            "new_width": target_width
        })

        print(
            " ", net, ":",
            track["width"], "->",
            target_width, "mil"
        )

    save("builder_trace_widths.json", changes)

    if True:  # Preview only: post-route widening previously caused shorts.
        print("  Preview only. No PCB tracks were changed.")
        return changes

    js = """
const changes = %s;
const results = [];

for (const change of changes) {
    const line = await eda.pcb_PrimitiveLine.modify(
        change.id,
        { lineWidth: change.new_width }
    );

    if (!line) {
        throw new Error(
            'Failed to update track: ' + change.id
        );
    }

    results.push({
        id: change.id,
        net: change.net,
        width: line.getState_LineWidth()
    });
}

return results;
""" % js_value(changes)

    result = b.run(js) or []

    save("builder_trace_width_results.json", result)
    print("  Updated", len(result), "PCB tracks")

    return changes


def export_connectivity_data(b: Bridge) -> dict:
    print("  exporting PCB connectivity data...")

    data = b.run("""
const names = await eda.pcb_Net.getAllNetsName();
const result = {};

for (const name of names) {
    result[name] = await eda.pcb_Net.getAllPrimitivesByNet(name);
}

return result;
""") or {}

    save("pcb_connectivity.json", data)

    return data


def verify_connectivity(b: Bridge) -> None:
    print("  checking preliminary PCB connectivity...")

    data = export_connectivity_data(b)
    results = check_connectivity(data)

    save("builder_connectivity_check.json", results)

    for net, result in results.items():
        if not result["preliminary_connected"]:
            raise RuntimeError(
                "Connectivity needs inspection for net: " + net
            )

    print("  Preliminary connectivity check completed")


def verify_pcb_tracks(
    b: Bridge,
    netlist: Netlist | None = None
) -> None:
    print("  verifying PCB tracks...")

    tracks = b.run(JS_GET_TRACKS) or []

    if not tracks:
        raise RuntimeError("No PCB tracks found")

    widths = (
        calculate_net_widths(netlist)
        if netlist is not None
        else {}
    )

    for track in tracks:
        net = track["net"]

        if track["layer"] != BOTTOM_LAYER:
            raise RuntimeError(
                "Track found outside bottom layer: " + str(net)
            )

        if netlist is not None:
            if net not in widths:
                raise RuntimeError(
                    "No calculated width for PCB net: " + str(net)
                )

            minimum_width = mm_to_mil(widths[net])
        else:
            minimum_width = mm_to_mil(1.2)

        if float(track["width"]) + 0.01 < minimum_width:
            raise RuntimeError(
                f"Track {net} is too narrow: {track['width']} mil; "
                f"expected at least {minimum_width} mil"
            )

    print("  Total tracks:", len(tracks))
    print("  All tracks are on bottom layer")
    print("  Track widths meet the required minimums")


def check_drc(b: Bridge) -> list:
    print("  checking PCB design rules...")

    errors = b.run(JS_DRC) or []

    print("  DRC:", len(errors), "issue(s)")
    save("builder_drc.json", errors)

    if errors:
        raise RuntimeError(
            "PCB has DRC violations. Check output/builder_drc.json"
        )

    return errors


def inspect_pcb(bridge: Bridge, netlist: Netlist) -> bool:
    """Inspect existing PCB without editing geometry or track widths."""
    print("Calculated trace widths (preview only):")
    apply_trace_widths(netlist)
    update_pcb_track_widths(bridge, netlist, modify=False)
    verify_pcb_tracks(bridge, netlist)
    verify_connectivity(bridge)
    check_drc(bridge)
    return True


def main_integrated() -> int:
    """Retain original CLI, plus check/widths/inspect commands."""
    args = sys.argv[1:]
    if args and args[0] == "check" and len(args) == 1:
        check_connection(Bridge())
        print("Builder ready")
        return 0
    if args and args[0] in ("widths", "inspect") and len(args) == 2:
        netlist = load_netlist(args[1])
        if args[0] == "widths":
            apply_trace_widths(netlist)
            return 0
        return 0 if inspect_pcb(Bridge(), netlist) else 2
    return main()


if __name__ == "__main__":
    try:
        sys.exit(main_integrated())
    except (BridgeError, RuntimeError, ValueError, FileNotFoundError) as exc:
        print("ERROR:", exc)
        sys.exit(1)
