"""EasyEDA bridge spike: can Python build a real board in EasyEDA Pro?

Test circuit: 7805 regulator with input/output capacitors and two screw terminals.
Run the steps in order (EasyEDA Pro open, bridge running, extension loaded):

  python -m easyeda.spike check    # 1. bridge + EasyEDA connected?
  python -m easyeda.spike parts    # 2. are our LCSC numbers real, and THT?
  python -m easyeda.spike sch      # 3. place parts + net labels   (schematic page open)
  python -m easyeda.spike erc      # 4. schematic check (ERC)
  python -m easyeda.spike pcb      # 5. import, auto-place, route bottom layer  (PCB tab open)
  python -m easyeda.spike drc      # 6. PCB design rule check
  python -m easyeda.spike rules    # 7. save EasyEDA's rule format so we can set trace widths later

Owner: Shammas.  EasyEDA guidance + review: Hamdan.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from easyeda.bridge import Bridge, BridgeError, js_value

OUT = Path("output")

# ---------------------------------------------------------------- test circuit
# LCSC numbers found by web search on 6 Oct 2026. Step 2 checks them in EasyEDA.
PARTS = [
    {"ref": "J1", "lcsc": "C474881", "what": "2-pin screw terminal, input"},
    {"ref": "C1", "lcsc": "C44601",  "what": "100uF 25V electrolytic, input"},
    {"ref": "U1", "lcsc": "C111887", "what": "L7805CV 5V regulator, TO-220"},
    {"ref": "C2", "lcsc": "C44601",  "what": "100uF 25V electrolytic, output"},
    {"ref": "J2", "lcsc": "C474881", "what": "2-pin screw terminal, output"},
]

# ref -> {pin number: net}.  Step 3 prints the real pin names: Hamdan checks
# them (e.g. 7805: 1=IN, 2=GND, 3=OUT; capacitor: 1=+, 2=-).
NETS = {
    "J1": {"1": "VIN", "2": "GND"},
    "C1": {"1": "VIN", "2": "GND"},
    "U1": {"1": "VIN", "2": "GND", "3": "+5V"},
    "C2": {"1": "+5V", "2": "GND"},
    "J2": {"1": "+5V", "2": "GND"},
}

SMD_HINTS = ("SMD", "SOT", "SOD", "SOP", "SOIC", "QFN", "QFP", "TSSOP", "MSOP",
             "0402", "0603", "0805", "1206", "1210", "2512", "SMA", "SMB", "SMC", "DPAK")


def looks_smd(footprint_name: str | None) -> bool:
    """Rough guard: True if the footprint name looks surface-mount."""
    name = (footprint_name or "").upper()
    return any(h in name for h in SMD_HINTS)


def save(name: str, data: object) -> None:
    OUT.mkdir(exist_ok=True)
    (OUT / name).write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
    print(f"  saved output/{name}")


# ---------------------------------------------------------------- JavaScript
# Shared helper: find a device by LCSC number (fills in libraryUuid if missing).
JS_FIND = """
const findDevice = async (lcsc) => {
  const r = await eda.lib_Device.getByLcscIds(lcsc);
  const dev = Array.isArray(r) ? r[0] : r;
  if (dev && !dev.libraryUuid) { dev.libraryUuid = await eda.lib_LibrariesList.getSystemLibraryUuid(); }
  return dev;
};
"""


def js_parts(lcsc_ids: list[str]) -> str:
    return JS_FIND + f"""
const out = [];
for (const id of {js_value(lcsc_ids)}) {{
  const d = await findDevice(id);
  out.push(d ? {{ lcsc: id, found: true, name: d.name, footprint: d.footprintName || (d.footprint && d.footprint.name), description: d.description }}
             : {{ lcsc: id, found: false }});
}}
return out;
"""


def js_schematic(parts: list[dict], nets: dict) -> str:
    return JS_FIND + f"""
const parts = {js_value(parts)};
const nets = {js_value(nets)};
const placed = [];
let x = 0;
for (const p of parts) {{
  const dev = await findDevice(p.lcsc);
  if (!dev) {{ throw new Error('Not in EasyEDA library: ' + p.lcsc); }}
  const comp = await eda.sch_PrimitiveComponent.create(dev, x, 0, undefined, 0, false, true, true);
  const id = comp.getState_PrimitiveId();
  await eda.sch_PrimitiveComponent.modify(id, {{ designator: p.ref }});
  const pins = await eda.sch_PrimitiveComponent.getAllPinsByPrimitiveId(id);
  const pinInfo = [];
  for (const pin of pins) {{
    const net = (nets[p.ref] || {{}})[String(pin.pinNumber)] || null;
    pinInfo.push({{ number: pin.pinNumber, name: pin.pinName, net: net }});
    if (!net) {{ continue; }}
    const horizontal = Math.abs(pin.x - x) >= Math.abs(pin.y);
    const ex = horizontal ? pin.x + (pin.x < x ? -30 : 30) : pin.x;
    const ey = horizontal ? pin.y : pin.y + (pin.y < 0 ? -30 : 30);
    await eda.sch_PrimitiveWire.create([pin.x, pin.y, ex, ey], net);
    if (net === 'GND') {{ await eda.sch_PrimitiveComponent.createNetFlag('Ground', 'GND', ex, ey); }}
    else {{ await eda.sch_PrimitiveComponent.createNetPort('BI', net, ex, ey); }}
  }}
  placed.push({{ ref: p.ref, lcsc: p.lcsc, pins: pinInfo }});
  x += 400;
}}
return placed;
"""


JS_ERC = "return await eda.sch_Drc.check(false, false, true);"
JS_IMPORT = "return await eda.pcb_Document.importChanges();"
JS_LAYOUT = "return await eda.pcb_Document.autoLayout();"
JS_ROUTE = """
return await eda.pcb_Document.autoRouting({ layers: [EPCB_LayerId.BOTTOM] });
"""
JS_DRC = "return await eda.pcb_Drc.check(false, false, true);"
JS_RULES = """
return {
  configName: await eda.pcb_Drc.getCurrentRuleConfigurationName(),
  config: await eda.pcb_Drc.getCurrentRuleConfiguration(),
  netRules: await eda.pcb_Drc.getNetRules()
};
"""
JS_INFO = "return await eda.dmt_Project.getCurrentProjectInfo();"


# ---------------------------------------------------------------- steps
def step_check(b: Bridge) -> None:
    h = b.health()
    print(f"  bridge at {b.base}, EasyEDA connected: {h.get('edaConnected')}")
    info = b.run(JS_INFO)
    print(f"  open project: {(info or {}).get('friendlyName') or (info or {}).get('name') or 'none'}")


def step_parts(b: Bridge) -> None:
    ids = sorted({p["lcsc"] for p in PARTS})
    results = b.run(js_parts(ids))
    ok = True
    for r in results:
        if not r["found"]:
            print(f"  FAIL {r['lcsc']}: not in EasyEDA library (wrong number?)")
            ok = False
        elif looks_smd(r.get("footprint")):
            print(f"  FAIL {r['lcsc']}: {r['name']} looks SMD ({r['footprint']})")
            ok = False
        else:
            print(f"  OK   {r['lcsc']}: {r['name']}  footprint={r['footprint']}")
    save("spike_parts.json", results)
    print("  All parts verified." if ok else "  Fix the failed numbers before step 3.")


def step_sch(b: Bridge) -> None:
    placed = b.run(js_schematic(PARTS, NETS))
    for comp in placed:
        pins = ", ".join(f"{p['number']}:{p['name']}->{p['net'] or '-'}" for p in comp["pins"])
        print(f"  {comp['ref']:3} {comp['lcsc']:9} {pins}")
    save("spike_schematic.json", placed)
    print("  Hamdan: check every pin name matches the net next to it. Save the schematic in EasyEDA.")


def step_erc(b: Bridge) -> None:
    errors = b.run(JS_ERC) or []
    print(f"  ERC: {len(errors)} issue(s)")
    for e in errors[:15]:
        print(f"   - [{e.get('type')}] {e.get('rule')} net={e.get('net')}")
    save("spike_erc.json", errors)


def step_pcb(b: Bridge) -> None:
    print("  importing schematic changes...")
    print("   ", b.run(JS_IMPORT))
    print("  auto layout...")
    print("   ", b.run(JS_LAYOUT))
    print("  auto routing on BOTTOM layer only (can take a while)...")
    try:
        result = b.run(JS_ROUTE)
    except BridgeError as e:
        print(f"   bridge gave up waiting ({e}). Routing may still finish in EasyEDA. "
              f"Wait, look at the board, then run:  python -m easyeda.spike drc")
        return
    print(f"   routed {result.get('successNetsCount')}/{result.get('totalNetsCount')} nets; "
          f"failed: {result.get('failedNets')}")
    save("spike_route.json", result)


def step_drc(b: Bridge) -> None:
    errors = b.run(JS_DRC) or []
    print(f"  DRC: {len(errors)} issue(s)")
    for e in errors[:15]:
        print("   -", json.dumps(e, default=str)[:160])
    save("spike_drc.json", errors)


def step_rules(b: Bridge) -> None:
    save("easyeda_rules.json", b.run(JS_RULES))
    print("  Open output/easyeda_rules.json and find where track width is stored. Note it for Sprint 2.")


STEPS = {"check": step_check, "parts": step_parts, "sch": step_sch, "erc": step_erc,
         "pcb": step_pcb, "drc": step_drc, "rules": step_rules}


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] not in STEPS:
        print("Usage: python -m easyeda.spike [" + "|".join(STEPS) + "]")
        sys.exit(1)
    try:
        STEPS[sys.argv[1]](Bridge())
    except BridgeError as e:
        print(f"  ERROR: {e}")
        sys.exit(2)


if __name__ == "__main__":
    main()
