# Product Backlog: AI PCB Designer

Sprint 1 (12–23 Oct 2026): 13 stories, 48 points. Later sprints: 9 stories, 42 points. Total 90 points.

Jira keys are in the Jira project (SCRUM). This file mirrors Jira so the backlog is also versioned in Git.

## Definition of Ready

1. Written as a user story: "As a <who>, I want <what>, so that <why>".
2. Has at least 3 testable acceptance criteria.
3. Estimated in story points by the team (1, 2, 3, 5, 8; anything bigger is split).
4. Linked to an epic and assigned to one owner.
5. Dependencies are known (which story or PR must be merged first).
6. Small enough to finish inside one sprint.

## Definition of Done

1. All acceptance criteria are met.
2. Code is merged into dev through a pull request approved by another member (nobody merges their own PR).
3. Every commit message starts with the Jira key as a Smart Commit, e.g. "SCRUM-12 #comment add LM317 template".
4. pytest passes and every new piece of logic has at least one test.
5. No API keys or .env files are committed.
6. Docs updated if behaviour changed (README or docs/).
7. The Jira issue is moved to Done and the work is shown in the sprint review.

## Sprint 1 backlog

| # | Story | Epic | Owner | Pts |
|---|---|---|---|---|
| 1 | GitHub repository workflow and protection | Project Infrastructure | Afaq | 2 |
| 2 | Connect GitHub for Jira (Smart Commits) | Project Infrastructure | Afaq | 1 |
| 3 | Team onboarding and Gemini API connection on every laptop | Project Infrastructure | Afaq | 1 |
| 4 | Spec Agent v1: clarifying questions and rule checks | Spec Parsing | Afaq | 5 |
| 5 | Circuit Designer Agent with validation-feedback loop | Circuit Design | Afaq | 5 |
| 6 | Shared schemas v1.1 and value calculator | Spec Parsing | Hamdan | 2 |
| 7 | Circuit templates: 78xx, LM317, LED array, 555 flasher | Circuit Design | Hamdan | 8 |
| 8 | 10 prompt test cases and automatic runner | Spec Parsing | Hamdan | 3 |
| 9 | Trace-width tests and EasyEDA bridge spike | Layout Engine | Shammas | 5 |
| 10 | EasyEDA builder: netlist to schematic, PCB, ERC/DRC | Layout Engine | Shammas | 5 |
| 11 | Component catalog with LCSC numbers and validator | Component Sourcing | Hamna | 5 |
| 12 | BOM, design report and pipeline command | UI & Export | Hamna | 3 |
| 13 | SRS document and architecture diagram | Project Infrastructure | Hamna | 3 |

**Total: 48 points**

### 1. GitHub repository workflow and protection

**Epic:** Project Infrastructure · **Owner:** Afaq · **Points:** 2  

*As a team member, I want a protected GitHub repository with a dev branch, so that unreviewed code never reaches the demo branch.*

**Acceptance criteria**

- [ ] dev exists and is the default branch.
- [ ] main and dev require a pull request with 1 approval; force pushes and deletion are blocked.
- [ ] All four members are collaborators and a direct push to dev is rejected.

### 2. Connect GitHub for Jira (Smart Commits)

**Epic:** Project Infrastructure · **Owner:** Afaq · **Points:** 1  

*As the Scrum Master, I want commits and pull requests linked to Jira issues, so that every piece of work is traceable.*

**Acceptance criteria**

- [ ] The GitHub for Jira app is installed for the pcb-agent repository.
- [ ] A commit containing a SCRUM key appears in that issue's Development panel.
- [ ] A Smart Commit with #comment adds a comment to the issue.

### 3. Team onboarding and Gemini API connection on every laptop

**Epic:** Project Infrastructure · **Owner:** Afaq · **Points:** 1  

*As a team member, I want a working local setup with the Gemini API, so that I can run and test the code myself.*

**Acceptance criteria**

- [ ] Every member runs python -m agents.hello_gemini and gets a Gemini answer (terminal screenshot kept).
- [ ] pytest passes on every member's laptop.
- [ ] Every member has at least one merged pull request from their own GitHub account.

### 4. Spec Agent v1: clarifying questions and rule checks

**Epic:** Spec Parsing · **Owner:** Afaq · **Points:** 5  

*As a hobbyist, I want to describe my board in plain English and be asked about anything missing, so that the design starts from a complete, correct specification.*

**Acceptance criteria**

- [ ] The agent returns a Spec JSON that validates against the Pydantic schema.
- [ ] It asks one question per missing field (input voltage, current, board size), for at most 3 rounds.
- [ ] It warns about SMD/multi-layer requests, outputs below 1.25 V on an LM317, low regulator headroom and high heat; Python rule checks add any warning Gemini missed.
- [ ] It retries automatically when Gemini returns 429/503.

### 5. Circuit Designer Agent with validation-feedback loop

**Epic:** Circuit Design · **Owner:** Afaq · **Points:** 5  

*As a hobbyist, I want the tool to choose a suitable circuit for my specification, so that I don't need circuit-design knowledge.*

**Acceptance criteria**

- [ ] Gemini returns a DesignPlan that only uses the available templates and never contains component values.
- [ ] If the code rejects the plan, the exact error is sent back to Gemini, which corrects it (maximum 3 attempts).
- [ ] If Gemini is unreachable, power supplies fall back to a rule-based plan.
- [ ] Tests with a fake Gemini cover the accept, correct, give-up and fallback paths.

### 6. Shared schemas v1.1 and value calculator

**Epic:** Spec Parsing · **Owner:** Hamdan · **Points:** 2  

*As a developer, I want shared data contracts and component-value helpers, so that each pipeline stage can be built in parallel.*

**Acceptance criteria**

- [ ] Spec, DesignPlan, Netlist (with LCSC numbers and pin maps) and BOM are Pydantic models.
- [ ] Resistors round to E24 (upwards for LED resistors); electrolytic ratings keep at least 20% margin; resistor wattage has 2x margin.
- [ ] Unit tests for the value helpers pass.

### 7. Circuit templates: 78xx, LM317, LED array, 555 flasher

**Epic:** Circuit Design · **Owner:** Hamdan · **Points:** 8  

*As a hobbyist, I want correct component values calculated for my circuit, so that the board works the first time I build it.*

**Acceptance criteria**

- [ ] Templates exist for DC/AC input, 78xx (5/9/12 V), LM317 adjustable, LED strings and a 555 flasher.
- [ ] Every value is computed by code and explained in the design report.
- [ ] The netlist check passes: every pin connected, no pin on two nets, at most 25 parts.
- [ ] Impossible requests (e.g. 3.3 V from 5 V with an LM317) are rejected with a clear reason.
- [ ] Hand-checked values are covered by tests.

### 8. 10 prompt test cases and automatic runner

**Epic:** Spec Parsing · **Owner:** Hamdan · **Points:** 3  

*As the Product Owner, I want the Spec Agent tested automatically against 10 realistic prompts, so that we can measure accuracy and catch hallucinations.*

**Acceptance criteria**

- [ ] 10 cases cover normal, incomplete, vague, out-of-scope (SMD/4-layer) and dangerous (57 W) requests.
- [ ] The runner prints PASS/FAIL per case and an X/10 score.
- [ ] Full answers are saved to output/spec_case_results.json.

### 9. Trace-width tests and EasyEDA bridge spike

**Epic:** Layout Engine · **Owner:** Shammas · **Points:** 5  

*As the team, we want to prove that Python can drive EasyEDA Pro, so that we only depend on it if it really works.*

**Acceptance criteria**

- [ ] Trace-width tests pass (signal >= 0.8 mm, power/ground >= 1.2 mm, IPC-2221 above the floor).
- [ ] Python connects to EasyEDA Pro through the official bridge.
- [ ] The spike places a 7805 circuit by LCSC number, runs ERC, routes the bottom layer and runs DRC.
- [ ] A GO/NO-GO result is recorded in docs/easyeda_spike_results.md.

### 10. EasyEDA builder: netlist to schematic, PCB, ERC/DRC

**Epic:** Layout Engine · **Owner:** Shammas · **Points:** 5  

*As a hobbyist, I want my designed circuit built as a real PCB in EasyEDA, so that I get a board I can etch.*

**Acceptance criteria**

- [ ] Any netlist from the Circuit Designer is placed in EasyEDA by LCSC number.
- [ ] Pin names are compared with the catalog before wiring; a mismatch stops the build.
- [ ] Power and signal net classes are created and routing is limited to the bottom layer.
- [ ] ERC and DRC results are printed.

### 11. Component catalog with LCSC numbers and validator

**Epic:** Component Sourcing · **Owner:** Hamna · **Points:** 5  

*As a hobbyist, I want only real, verified through-hole parts in my design, so that the AI cannot invent components.*

**Acceptance criteria**

- [ ] data/components.json stores LCSC number, ratings and pin map for each part.
- [ ] validate_part rejects unknown parts and parts used above their ratings.
- [ ] python -m core.catalog_todo shows all parts needed for the dual-rail demo as complete.

### 12. BOM, design report and pipeline command

**Epic:** UI & Export · **Owner:** Hamna · **Points:** 3  

*As a hobbyist, I want one command that gives me a BOM and a design report, so that I can review and order parts.*

**Acceptance criteria**

- [ ] python -m pipeline runs the full chain; --example runs offline without an API key.
- [ ] The BOM CSV groups identical parts and flags any part still missing an LCSC number.
- [ ] The design report lists warnings, calculations, nets with trace widths, the BOM and the agent log.

### 13. SRS document and architecture diagram

**Epic:** Project Infrastructure · **Owner:** Hamna · **Points:** 3  

*As a stakeholder, I want an SRS and an architecture diagram, so that the scope and design of the system are clear.*

**Acceptance criteria**

- [ ] docs/SRS.md lists functional requirements (with target sprint) and non-functional requirements.
- [ ] docs/architecture.md contains a diagram that renders on GitHub.
- [ ] Both are reviewed and merged.

## Product backlog (later sprints)

| # | Story | Epic | Owner | Pts | Sprint |
|---|---|---|---|---|---|
| 14 | Sourcing Agent: find and verify LCSC parts | Component Sourcing | Hamna | 8 | 3 |
| 15 | Set trace widths automatically in EasyEDA | Layout Engine | Shammas | 3 | 2 |
| 16 | Review Agent: explain ERC/DRC and trigger fixes | Review & DRC | Afaq | 5 | 3 |
| 17 | Wire-jumper fallback for unroutable nets | Layout Engine | Shammas | 5 | 3 |
| 18 | More templates: transistor relay driver, rectifier-only supply | Circuit Design | Hamdan | 5 | 2 |
| 19 | Streamlit user interface | UI & Export | Hamna | 5 | 4 |
| 20 | Export mirrored PDF and Gerbers | UI & Export | Shammas | 3 | 4 |
| 21 | Edge-case and hallucination test suite | Review & DRC | Hamdan | 3 | 4 |
| 22 | Etch and test a real agent-designed board | Review & DRC | Hamdan | 5 | 4 |

### 14. Sourcing Agent: find and verify LCSC parts

**Epic:** Component Sourcing · **Owner:** Hamna · **Points:** 8 · **Planned sprint:** 3  

*As a hobbyist, I want missing parts found automatically, so that every part in my BOM can be ordered and placed.*

**Acceptance criteria**

- [ ] Gemini web search proposes LCSC numbers for parts not in the catalog.
- [ ] Each proposal is verified in EasyEDA (exists, through-hole, pin names match) before use.
- [ ] Rejected proposals are logged with the reason.

### 15. Set trace widths automatically in EasyEDA

**Epic:** Layout Engine · **Owner:** Shammas · **Points:** 3 · **Planned sprint:** 2  

*As a hobbyist, I want trace widths set from current and net class, so that power traces survive hand etching and current.*

**Acceptance criteria**

- [ ] Calculated widths are written into EasyEDA design rules per net class.
- [ ] Routed power traces are at least 1.2 mm and signal traces at least 0.8 mm.
- [ ] DRC passes with these rules.

### 16. Review Agent: explain ERC/DRC and trigger fixes

**Epic:** Review & DRC · **Owner:** Afaq · **Points:** 5 · **Planned sprint:** 3  

*As a hobbyist, I want design-rule problems explained in plain English and fixed where possible, so that I get a clean board.*

**Acceptance criteria**

- [ ] The agent reads ERC/DRC results and explains each issue.
- [ ] It picks fixes only from a fixed list of allowed actions and re-runs the check.
- [ ] It stops after 3 rounds and reports what is left.

### 17. Wire-jumper fallback for unroutable nets

**Epic:** Layout Engine · **Owner:** Shammas · **Points:** 5 · **Planned sprint:** 3  

*As a hobbyist, I want a jumper instead of a failed design when a single layer can't route a net, so that the board is still buildable.*

**Acceptance criteria**

- [ ] Nets that fail autorouting are listed.
- [ ] Jumpers are added and counted in the BOM.
- [ ] The number of jumpers is minimised and reported.

### 18. More templates: transistor relay driver, rectifier-only supply

**Epic:** Circuit Design · **Owner:** Hamdan · **Points:** 5 · **Planned sprint:** 2  

*As a hobbyist, I want more common circuits supported, so that the tool covers more of my projects.*

**Acceptance criteria**

- [ ] Relay driver with flyback diode and base resistor calculated from coil current.
- [ ] Rectifier + filter without regulator.
- [ ] Hand-checked values covered by tests.

### 19. Streamlit user interface

**Epic:** UI & Export · **Owner:** Hamna · **Points:** 5 · **Planned sprint:** 4  

*As a hobbyist, I want a simple web interface, so that I don't need the terminal.*

**Acceptance criteria**

- [ ] Chat-style questions and answers with the Spec Agent.
- [ ] Shows the design report and lets me download the BOM.
- [ ] Clear error messages when a design is impossible.

### 20. Export mirrored PDF and Gerbers

**Epic:** UI & Export · **Owner:** Shammas · **Points:** 3 · **Planned sprint:** 4  

*As a hobbyist, I want a mirrored, 1:1 PDF of the copper layer, so that I can toner-transfer and etch the board at home.*

**Acceptance criteria**

- [ ] Bottom copper exported mirrored at 1:1 scale.
- [ ] Gerber files exported for optional ordering.
- [ ] A printed test page measures correctly.

### 21. Edge-case and hallucination test suite

**Epic:** Review & DRC · **Owner:** Hamdan · **Points:** 3 · **Planned sprint:** 4  

*As the Product Owner, I want the whole pipeline tested on difficult inputs, so that we can show it fails safely.*

**Acceptance criteria**

- [ ] At least 20 prompts including contradictory and unsafe requests.
- [ ] No invented parts or values appear in any output.
- [ ] Results summarised in the final report.

### 22. Etch and test a real agent-designed board

**Epic:** Review & DRC · **Owner:** Hamdan · **Points:** 5 · **Planned sprint:** 4  

*As the team, we want to etch and power up a board designed by the tool, so that we prove the whole system works in reality.*

**Acceptance criteria**

- [ ] Board etched from the exported PDF.
- [ ] Measured output voltages within 5% of the design.
- [ ] Photos and measurements in the final report.
