# Architecture

LLM agents make decisions. Plain Python code and EasyEDA Pro do all geometry.
The LLM never writes EasyEDA code: Python turns the netlist into fixed EasyEDA API calls.

```mermaid
flowchart LR
    U[User prompt] --> S[Spec Agent]
    S -->|Spec JSON| C[Circuit Designer Agent]
    C -->|Netlist JSON| B[Sourcing Agent<br/>web search]
    B -->|verified BOM<br/>LCSC numbers| E[EasyEDA builder<br/>Python + bridge]
    E --> P[EasyEDA Pro<br/>schematic, ERC,<br/>bottom-layer route, DRC]
    P -->|ERC/DRC report| R[Review Agent]
    R -->|fix and re-run| E
    P --> O[Outputs<br/>BOM, mirrored PDF, Gerbers]
    S -.-> SC[Rule checks<br/>spec_checks.py]
    B -.-> DB[(components.json)]
    E -.-> TW[Trace widths<br/>trace_width.py]
```

| Stage | Type | Owner | Sprint |
|---|---|---|---|
| Spec Agent | LLM agent | Afaq | 1-2 |
| Circuit Designer Agent | LLM agent + templates | Afaq, Hamdan | 2 |
| Sourcing Agent | LLM agent + web search + LCSC check | Hamna | 3 |
| EasyEDA builder | Deterministic Python + EasyEDA API | Shammas, Hamdan | 1-3 |
| Review Agent | LLM agent | Afaq | 3 |
| UI and export | Streamlit + EasyEDA export | Hamna | 4 |
