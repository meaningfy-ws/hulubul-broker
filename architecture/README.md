# Hulubul V1 — Architecture (DRAFT)

Architecture package for the **autonomous, agent-driven parcel-brokerage service**
(Telegram dev / WhatsApp prod, Neo4j graph). Grounded in the v0.4 Functional Flow
Brief and refined across the working sessions. **Draft** — nothing is
implementation-committed; the orchestrator choice (Shape A/B/C) is parked.

**New here? Read [`HANDOVER.md`](HANDOVER.md) first** — it's the resume point.

| Document | Contents | Status |
|----------|----------|--------|
| [HANDOVER.md](HANDOVER.md) | Resume point: state, decisions, parked forks, next steps | ✅ current |
| [project-statement.md](project-statement.md) | Problem, scope, actors, success (from v0.4) | ✅ |
| [architecture-statement.md](architecture-statement.md) | Drivers, C4 L1/L2/L3, mermaid (autonomous direction) | ✅ v2 |
| [use-cases/](use-cases/) | Cockburn use cases — white (UC-0) + blue (UC-1..13) | ✅ |
| [decisions/](decisions/) | ADR-001..018 by C4 level | ✅ v2 |
| [diagrams/workflows.md](diagrams/workflows.md) | Status state machine, happy-path sequence, cascade | ✅ |
| [raci.md](raci.md) | Responsibility matrix across the flow | ✅ |
| [task-2-frameworks-exploration.md](task-2-frameworks-exploration.md) | Framework/tech exploration (non-decisional) | ✅ |
| [specs/](specs/) | LinkML domain schema | ⛔ deferred to modelling session |

## Task status

- **#1 Architecture statement + use cases + ADRs** — ✅ done (draft)
- **#2 Frameworks & technical choices** — ✅ done (exploration, non-decisional)
- **#3 Consolidate crisp doc set** — ✅ done **except** the LinkML schema (modelling-blocked)

## Parked / deferred (see HANDOVER §4–6)

1. **Orchestrator Shape A/B/C** — parked by decision (`task-2…` §7).
2. **Data model, scoped-MCP ops, access-visibility rules, dialogue-act subset** — modelling session.
3. **WhatsApp consent / paid-template / GDPR model** — prod-cutover workstream.
