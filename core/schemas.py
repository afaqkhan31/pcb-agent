"""Shared data contracts for every stage of the pipeline.

Every agent reads and writes these models. If you change a field here,
tell the team in the PR description — other stages depend on it.

Schema v1.1 (16 Oct 2026): Part/Netlist/BOMLine updated for EasyEDA + LCSC.

Note: fields have no default values on purpose. Gemini structured output
works most reliably when every field is present (use None for "unknown").
"""
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------- Stage 1: Spec
class ProjectType(str, Enum):
    power_supply = "power_supply"
    led = "led"
    timer = "timer"
    switching = "switching"
    other = "other"


class InputSource(BaseModel):
    kind: Optional[str] = Field(
        description="e.g. 'AC_transformer', 'DC_adapter', 'battery', 'USB'; null if not stated"
    )
    voltage_v: Optional[float] = Field(description="Input voltage in volts; null if not stated")
    current_a: Optional[float] = Field(description="Max input current in amps; null if not stated")


class OutputRail(BaseModel):
    name: str = Field(description="Short rail name, e.g. '5V_FIXED' or 'VAR'")
    v_min: float = Field(description="Minimum output voltage in volts (equal to v_max if fixed)")
    v_max: float = Field(description="Maximum output voltage in volts")
    i_max_a: Optional[float] = Field(description="Max load current in amps; null if not stated")


class BoardConstraints(BaseModel):
    width_mm: Optional[float]
    height_mm: Optional[float]
    layers: int = Field(description="Copper layers. This tool only supports 1.")
    mounting: str = Field(description="Always 'THT' for this tool")
    max_height_mm: Optional[float] = Field(description="Enclosure height limit; null if none")


class Spec(BaseModel):
    project_type: ProjectType
    summary: str = Field(description="One-sentence plain-English summary of what the board does")
    input: InputSource
    outputs: list[OutputRail] = Field(description="Output rails; empty list if not a power project")
    board: BoardConstraints
    budget: Optional[str] = Field(description="'low', 'medium', 'high' or null")
    missing_fields: list[str] = Field(description="Fields needed for design that the user did not give")
    clarifying_questions: list[str] = Field(description="Questions to ask the user, one per missing item")
    warnings: list[str] = Field(description="Impossible or risky requirements, explained briefly")


# ------------------------------------------------------ Stage 2: Circuit design
class PinRef(BaseModel):
    ref: str = Field(description="Component reference, e.g. 'U1'")
    pin: str = Field(description="Pin number or name, e.g. '1' or 'VIN'")


class Net(BaseModel):
    name: str
    net_class: str = Field(description="'power', 'ground' or 'signal' — drives trace width")
    current_a: Optional[float] = Field(description="Worst-case current through this net")
    nodes: list[PinRef]


class Part(BaseModel):
    ref: str
    value: str = Field(description="e.g. '10k', '100uF 25V', 'LM317T'")
    description: str
    catalog_key: str = Field(description="MPN key in data/components.json, e.g. 'LM317T' or 'RES-0.25W'")
    lcsc: Optional[str] = Field(description="LCSC C-number EasyEDA places; null until sourced")
    package: Optional[str] = Field(description="e.g. 'TO-220'; EasyEDA supplies the real footprint")
    pins: dict[str, str] = Field(description="Pin number -> pin name, e.g. {'1': 'IN', '2': 'GND', '3': 'OUT'}")
    pinout_verified: bool = Field(description="True if the pinout came from the curated catalog")


class Netlist(BaseModel):
    """Built by deterministic code (templates), never by the LLM."""
    blocks: list[str] = Field(description="Template blocks used, e.g. ['power_input', 'fixed_regulator:5V']")
    parts: list[Part]
    nets: list[Net]


# -------------------------------------------------------------- Stage 3: BOM
class BOMLine(BaseModel):
    refs: list[str]
    qty: int
    value: str
    package: Optional[str]
    mpn: Optional[str] = Field(description="Manufacturer part number, validated against data/components.json")
    lcsc: Optional[str] = Field(description="LCSC C-number; null means it still has to be sourced")
    datasheet_url: Optional[str]
    unit_price: Optional[float]
    notes: Optional[str]


class BOM(BaseModel):
    lines: list[BOMLine]
    jumpers: int = Field(description="Number of wire jumpers the router needed")


# ------------------------------------------------- Stage 2a: design plan (LLM)
class TemplateId(str, Enum):
    fixed_regulator = "fixed_regulator"
    adjustable_regulator = "adjustable_regulator"
    led_array = "led_array"
    ne555_flasher = "ne555_flasher"


class BlockRequest(BaseModel):
    """One circuit block the Circuit Designer Agent asks for. Unused fields = null."""
    template_id: TemplateId
    rail_name: Optional[str] = Field(description="Output net name for regulators, e.g. '5V' or 'VAR'")
    v_out: Optional[float] = Field(description="fixed_regulator: output voltage (5, 9 or 12)")
    v_out_min: Optional[float] = Field(description="adjustable_regulator: lowest output voltage")
    v_out_max: Optional[float] = Field(description="adjustable_regulator: highest output voltage")
    i_out_a: Optional[float] = Field(description="Regulators: max output current in amps")
    led_count: Optional[int] = Field(description="led_array: number of LEDs")
    led_color: Optional[str] = Field(description="led_array / ne555_flasher: red, green, yellow, orange, blue or white")
    led_current_ma: Optional[float] = Field(description="led_array / ne555_flasher: current per LED in mA")
    frequency_hz: Optional[float] = Field(description="ne555_flasher: blink frequency in Hz")


class DesignPlan(BaseModel):
    blocks: list[BlockRequest] = Field(description="Blocks to build, in order. The power input is added automatically.")
    reverse_protection: bool = Field(description="Add a series diode against reversed DC input (costs ~1 V)")
    explanation: str = Field(description="One or two sentences: why these blocks")
