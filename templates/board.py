"""Board builder that every circuit template writes into.

A template adds parts and connects pins BY NAME (e.g. U1 "IN"). The builder
turns names into pin numbers using the curated catalog (data/components.json).
If a part isn't in the catalog yet, the template's default pinout is used
and the part is flagged as "pinout unverified".

Owner: Hamdan (templates).  Code review: Afaq.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from core.components import find_part
from core.schemas import Net, Netlist, Part, PinRef
from core.trace_width import trace_width_mm


class DesignError(ValueError):
    """A template can't build what was asked (bad value, out of range...)."""


# Pinouts used when a part is not in the catalog yet. Hamdan: check these.
DEFAULT_PINS = {
    "two_pin":      {"1": "1", "2": "2"},                         # R, ceramic C, terminal
    "electrolytic": {"1": "+", "2": "-"},
    "diode":        {"1": "K", "2": "A"},
    "led":          {"1": "K", "2": "A"},
    "pot":          {"1": "1", "2": "W", "3": "3"},
    "78xx":         {"1": "IN", "2": "GND", "3": "OUT"},
    "lm317":        {"1": "ADJ", "2": "OUT", "3": "IN"},
    "ne555":        {"1": "GND", "2": "TRIG", "3": "OUT", "4": "RESET",
                     "5": "CTRL", "6": "THR", "7": "DIS", "8": "VCC"},
    "bridge":       {"1": "+", "2": "AC1", "3": "-", "4": "AC2"},
}


@dataclass
class NetInfo:
    net_class: str                 # 'power', 'ground' or 'signal'
    current_a: float | None
    nodes: list[PinRef] = field(default_factory=list)


class Board:
    def __init__(self) -> None:
        self.parts: list[Part] = []
        self.nets: dict[str, NetInfo] = {}
        self.blocks: list[str] = []
        self.warnings: list[str] = []
        self.calculations: list[str] = []     # human-readable "why this value"
        self._counters: dict[str, int] = {}

    # ------------------------------------------------------------ parts
    def add_part(self, prefix: str, catalog_key: str, value: str, description: str,
                 default_pins: str) -> str:
        """Add a part and return its reference, e.g. 'R3'."""
        self._counters[prefix] = self._counters.get(prefix, 0) + 1
        ref = f"{prefix}{self._counters[prefix]}"
        cat = find_part(catalog_key)
        if cat:
            pins = {str(k): str(v) for k, v in cat["pins"].items()}
            # Generic families (resistors) can list a C-number per value: "lcsc_by_value": {"240": "C..."}
            lcsc = cat.get("lcsc") or cat.get("lcsc_by_value", {}).get(value.split()[0])
            part = Part(ref=ref, value=value, description=description, catalog_key=catalog_key,
                        lcsc=lcsc, package=cat.get("package"),
                        pins=pins, pinout_verified=True)
        else:
            part = Part(ref=ref, value=value, description=description, catalog_key=catalog_key,
                        lcsc=None, package=None, pins=dict(DEFAULT_PINS[default_pins]),
                        pinout_verified=False)
        self.parts.append(part)
        return ref

    def _part(self, ref: str) -> Part:
        return next(p for p in self.parts if p.ref == ref)

    # ------------------------------------------------------------ nets
    def net(self, name: str, net_class: str, current_a: float | None = None) -> str:
        """Declare a net (or raise its current if it already exists)."""
        info = self.nets.get(name)
        if info is None:
            self.nets[name] = NetInfo(net_class, current_a)
        elif current_a is not None:
            info.current_a = max(info.current_a or 0.0, current_a)
        return name

    def connect(self, net: str, ref: str, pin_name: str) -> None:
        """Connect pin `pin_name` of part `ref` to `net`."""
        if net not in self.nets:
            raise DesignError(f"Net {net} used before it was declared")
        part = self._part(ref)
        numbers = [n for n, name in part.pins.items() if name.upper() == pin_name.upper()]
        if len(numbers) != 1:
            raise DesignError(f"{ref} ({part.catalog_key}) has no single pin named '{pin_name}'. "
                              f"Catalog pins: {part.pins}")
        self.nets[net].nodes.append(PinRef(ref=ref, pin=numbers[0]))

    def connect_2(self, ref: str, net_a: str, net_b: str) -> None:
        """Two-pin part with pins named '1' and '2' (resistor, ceramic cap, terminal)."""
        self.connect(net_a, ref, "1")
        self.connect(net_b, ref, "2")

    # ------------------------------------------------------------ output
    def check(self) -> list[str]:
        """Mini-ERC on our own netlist. Returns problems (empty = OK)."""
        problems = []
        seen: dict[tuple[str, str], str] = {}
        for name, info in self.nets.items():
            if len(info.nodes) < 2:
                problems.append(f"Net {name} has only {len(info.nodes)} connection(s)")
            for node in info.nodes:
                key = (node.ref, node.pin)
                if key in seen:
                    problems.append(f"{node.ref} pin {node.pin} is on both {seen[key]} and {name}")
                seen[key] = name
        for part in self.parts:
            for number, pin_name in part.pins.items():
                if (part.ref, number) not in seen:
                    problems.append(f"{part.ref} pin {number} ({pin_name}) is not connected")
        if len(self.parts) > 25:
            problems.append(f"{len(self.parts)} parts: more than the 25-part scope limit")
        return problems

    def to_netlist(self) -> Netlist:
        problems = self.check()
        if problems:
            raise DesignError("Netlist check failed: " + "; ".join(problems))
        nets = [Net(name=n, net_class=i.net_class, current_a=i.current_a, nodes=i.nodes)
                for n, i in self.nets.items()]
        return Netlist(blocks=self.blocks, parts=self.parts, nets=nets)

    def trace_widths(self) -> dict[str, float]:
        """Width per net from our IPC-2221 calculator + hand-etch floors."""
        return {n: trace_width_mm(i.net_class, i.current_a) for n, i in self.nets.items()}
