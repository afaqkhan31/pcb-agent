# Software Requirements Specification: AI PCB Designer
Version 1.0 · Sprint 1 · EC-360 · Team: Hamdan, Afaq, Shammas, Hamna

## 1. Introduction
### 1.1 Purpose
The AI PCB Designer turns a plain-English request, such as "a 5 V fixed and 1-12 V variable power supply", into a printable single-layer through-hole PCB design. It asks questions when information is missing, builds the circuit from validated templates, produces a parts list and a design report, and builds the board in EasyEDA Pro. This document is for the project team, our instructors and anyone who needs to know what the system must do.
### 1.2 Scope
The system takes a plain-English request and produces a hand-etchable, single-layer, through-hole PCB design with a spec, a netlist, a parts list with LCSC numbers and a design report.
The system does NOT handle SMD parts, multi-layer boards or free-form circuits that are not in our templates.

## 2. Overall description
### 2.1 Users
Students and hobbyists who can etch a board at home but cannot design one. They do not need circuit-design knowledge, because the tool chooses the circuit and calculates the values.
### 2.2 Constraints
- Single layer, through-hole only, about 25 components max, rectangular board
- Circuits come only from validated templates
- Google Gemini free tier; Python 3.11+
- Hand-etch rules: signal trace >= 0.8 mm, power/ground >= 1.2 mm, clearance >= 0.6 mm
- EasyEDA Pro desktop (v3.2.150 or newer) and its API bridge must be running on the machine

## 3. Functional requirements
| ID | Requirement | Sprint |
|---|---|---|
| FR-1 | Accept a plain-English board request | 1 |
| FR-2 | Ask clarifying questions for missing information (max 3 rounds) | 1 |
| FR-3 | Warn about impossible or out-of-scope requests | 1 |
| FR-4 | Output a validated Spec JSON | 1 |
| FR-5 | Choose a circuit template and produce a netlist | 2 |
| FR-6 | Produce a BOM with LCSC numbers that are verified in the EasyEDA library (THT only) | 2-3 |
| FR-7 | Build the schematic in EasyEDA Pro, then place and route on the bottom layer only (jumpers if needed) | 3 |
| FR-8 | Run EasyEDA ERC and DRC and explain any problems | 3 |
| FR-9 | Export BOM, mirrored PDF for toner transfer and Gerbers from EasyEDA | 4 |
| FR-10 | Web interface (Streamlit) | 4 |

## 4. Non-functional requirements
- All geometry is done by EasyEDA and deterministic code, never by the LLM.
- The LLM never writes component values or EasyEDA code. It only picks from fixed templates and actions.
- Each stage should respond in under 30 seconds.
- API keys are never committed to the repository.
- Every new function has a pytest test.
- The tool runs on Windows and Linux.

## 5. Architecture
See docs/architecture.md.