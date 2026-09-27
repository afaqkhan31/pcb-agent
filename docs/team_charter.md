# Team Charter — AI PCB Designer (EC-360 CEP)

## Team
| Member | Technical ownership (whole project) |
|---|---|
| **Hamdan** | PCB domain lead: circuit templates, design rules, DRC, test prompts, final board validation and etching |
| **Afaq** | Agent engineering: Gemini integration, Spec Agent, Circuit Designer Agent, orchestration of the multi-agent pipeline |
| **Shammas** | Layout engine: trace-width calculator, placer, grid maze router, jumper handling |
| **Hamna** | Components and output: component database, Sourcing Agent (search + RAG), BOM, Streamlit UI, PDF/SVG export |

Ownership is about accountability, not exclusivity. Everyone codes, everyone reviews.
Any PR touching templates, design rules, trace widths, footprints or DRC needs Hamdan's review.

## Scrum role rotation
| Sprint | Product Owner | Scrum Master | Developers |
|---|---|---|---|
| 1 — Foundation | Hamdan | Afaq | Shammas, Hamna |
| 2 — Single agent | Hamna | Hamdan | Afaq, Shammas |
| 3 — Advanced | Afaq | Shammas | Hamdan, Hamna |
| 4 — Integration | Shammas | Hamna | Hamdan, Afaq |

In a four-person team, the PO and SM also write code. The role adds duties; it doesn't remove development work.

## Definition of Done
A story is Done when:
1. The code is merged into `dev` through a PR reviewed by at least one other member
2. The Jira ticket key is in the branch name and commit messages, and the ticket is closed
3. Tests pass (`pytest`) and new logic has at least one test
4. It was shown in the sprint review

## Git workflow
- `main`: protected, always demo-ready. Merged from `dev` at the end of each sprint only.
- `dev`: integration branch. PRs go here.
- Feature branches: `feature/PCBA-12-short-name`
- Commit messages: `PCBA-12: add Spec schema`
- Commit from your **own** GitHub account; individual contributions are graded.
- Never commit `.env` or API keys.

## Meetings
- **Sprint planning:** first day of each sprint, about 45 min
- **Stand-up:** 3 times a week, 10 min (in person or in the group chat: done / doing / blocked)
- **Sprint review + retrospective:** last day of each sprint, about 45 min; screenshot the burndown chart
- **PCB 101 sessions:** Hamdan, 30 min in each of Sprints 1 and 2
