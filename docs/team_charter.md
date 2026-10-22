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

## Definition of Ready
A story can enter a sprint when:
1. Written as a user story: "As a <who>, I want <what>, so that <why>".
2. Has at least 3 testable acceptance criteria.
3. Estimated in story points by the team (1, 2, 3, 5, 8; anything bigger is split).
4. Linked to an epic and assigned to one owner.
5. Dependencies are known (which story or PR must be merged first).
6. Small enough to finish inside one sprint.

## Definition of Done
A story is Done when:
1. All acceptance criteria are met.
2. Code is merged into dev through a pull request approved by another member (nobody merges their own PR).
3. Every commit message starts with the Jira key as a Smart Commit, e.g. "SCRUM-12 #comment add LM317 template".
4. pytest passes and every new piece of logic has at least one test.
5. No API keys or .env files are committed.
6. Docs updated if behaviour changed (README or docs/).
7. The Jira issue is moved to Done and the work is shown in the sprint review.

## Git workflow
- `main`: protected, always demo-ready. Merged from `dev` at the end of each sprint only.
- `dev`: integration branch. PRs go here.
- Feature branches: `feature/SCRUM-12-short-name`
- Commit messages are Jira Smart Commits: `SCRUM-12 #comment add Spec schema`
- Your `git config user.email` must be the same email as your Jira account, or Smart Commits are ignored.
- Commit from your **own** GitHub account; individual contributions are graded.
- Never commit `.env` or API keys.

## Meetings
- **Sprint planning:** first day of each sprint, about 45 min
- **Stand-up:** 3 times a week, 10 min (in person or in the group chat: done / doing / blocked)
- **Sprint review + retrospective:** last day of each sprint, about 45 min; screenshot the burndown chart
- **PCB 101 sessions:** Hamdan, 30 min in each of Sprints 1 and 2
