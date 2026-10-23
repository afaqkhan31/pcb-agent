# AI PCB Designer

An agentic system that turns a plain-English request ("5V + adjustable supply, 8x10 cm, single layer")
into a routed, hand-etchable **single-layer THT PCB**: spec → circuit → BOM → placement → routing → etch-ready PDF.

EC-360 Software Engineering CEP · Team: Hamdan, Afaq, Shammas, Hamna

## Architecture
```
User prompt
  → Spec Agent (asks clarifying questions)          → Spec JSON
  → Circuit Designer Agent (validated templates)     → Netlist JSON
  → Sourcing Agent (search + component DB / RAG)     → BOM
  → Layout tools (plain Python): trace width → placer → maze router → DRC
  → Review Agent (reads DRC report, triggers fixes)
  → Outputs: BOM CSV, board SVG, mirrored PDF for toner transfer
```
**Rule:** LLMs make decisions; deterministic code does geometry. The LLM never outputs coordinates.

## Setup (each member)
```bash
git clone <repo-url>
cd pcb-agent
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env      # macOS/Linux: cp .env.example .env
# paste your key from https://aistudio.google.com into .env
python -m agents.hello_gemini
python -m agents.spec_agent
pytest
```

## Layout
| Folder | Contents |
|---|---|
| `agents/` | LLM agents + shared Gemini client |
| `core/` | Schemas, trace width, placer, router, DRC (deterministic) |
| `templates/` | Validated circuit templates (owned by Hamdan) |
| `data/` | Curated THT component list + footprints |
| `ui/` | Streamlit app (Sprint 4) |
| `tests/` | Unit tests + prompt test cases |
| `docs/` | SRS, architecture, team charter, sprint reports |

See `docs/team_charter.md` for roles, Git workflow and Definition of Done.

Setup done by SHAMMAS
