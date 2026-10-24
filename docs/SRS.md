# Software Requirements Specification: AI PCB Designer
Version 1.0 · Sprint 1 · EC-360 · Team: Hamdan, Afaq, Shammas, Hamna

## 1. Introduction
### 1.1 Purpose
(2-3 sentences: what the system does and who this document is for.)
### 1.2 Scope
(What it does: plain-English request -> hand-etchable single-layer THT PCB.
 What it does NOT do: SMD, multi-layer, free-form circuits.)

## 2. Overall description
### 2.1 Users
(Students and hobbyists who can etch a board but can't design one.)
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
(Write 5-6 lines, e.g.: geometry is done by EasyEDA and deterministic code, never by the LLM;
 the LLM never writes EasyEDA code, only picks from fixed actions;
 each stage responds in under 30 s; API keys are never committed;
 every new function has a pytest test; runs on Windows and Linux.)

## 5. Architecture
See docs/architecture.md.
