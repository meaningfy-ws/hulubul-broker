# Hulubul V1 — Architecture (DRAFT)

Architecture package for the **autonomous, agent-driven parcel-brokerage service**
(Telegram dev / WhatsApp prod, Neo4j graph). Grounded in the v0.4 Functional Flow
Brief and refined across the working sessions. **Draft** — nothing is
implementation-committed.

**New here? Read [`HANDOVER.md`](HANDOVER.md) first** — it's the resume point.
For contradictions across documents of different vintages, see
[Conflicts & interpretation priorities](#conflicts--interpretation-priorities)
below.

## Document index

| Document | Contents | Date | Status |
|----------|----------|------|--------|
| [HANDOVER.md](HANDOVER.md) | Resume point: state, decisions, parked forks, next steps | Jul 8 | ✅ current (baseline) |
| [project-statement.md](project-statement.md) | Problem, scope, actors, success (from v0.4) | Jul 8 | ✅ |
| [architecture-statement.md](architecture-statement.md) | Drivers, C4 L1/L2/L3, mermaid (autonomous direction) | Jul 8 | ✅ v2 |
| [agentic-system-blueprint.md](agentic-system-blueprint.md) | Target agentic architecture: 10-agent decomposition, state model, LangFlow flows | Jul 20 | ✅ current |
| [agentic-system-blueprint-phase-1.md](agentic-system-blueprint-phase-1.md) | Phase 1 Walking Skeleton: LF-00/10/20/70 flows, domain subset, transition profile | Jul 20 | ✅ current |
| [incremental-system-development-strategy.md](incremental-system-development-strategy.md) | Phase 1–4 build-up plan and stable architectural commitments | Jul 20 | ✅ current |
| [non-functional-requirements.md](non-functional-requirements.md) | V1 NFR catalogue (autonomy, reliability, security, channel, performance) | Jul 20 | ✅ baseline |
| [verification-testing-and-evaluation-strategy.md](verification-testing-and-evaluation-strategy.md) | Testing layers, Testcontainers, evals, LLM-as-judge | Jul 20 | ✅ current |
| [use-cases/](use-cases/) | Cockburn use cases — white (UC-0) + blue (UC-1..13) | Jul 8 | ✅ |
| [decisions/](decisions/) | ADR-001..018 by C4 level | Jul 8 | ✅ v2 (some stale — see conflicts) |
| [diagrams/workflows.md](diagrams/workflows.md) | Status state machine, happy-path sequence, cascade | Jul 8 | ⚠ stale — see conflicts |
| [raci.md](raci.md) | Responsibility matrix across the flow | Jul 8 | ✅ |
| [task-2-frameworks-exploration.md](task-2-frameworks-exploration.md) | Framework/tech exploration (non-decisional) | Jul 8 | ✅ |
| [reports/](reports/) | Research report: Deterministic Control Patterns for LLM Agent Systems | Jul 10 | ✅ non-binding |
| [specs/](specs/) | LinkML domain schema placeholder | Jul 8 | ⛔ deferred (schema now under `../model/linkml/`) |

## Task status

- **#1 Architecture statement + use cases + ADRs** — ✅ done (draft)
- **#2 Frameworks & technical choices** — ✅ done (exploration, non-decisional)
- **#3 Consolidate crisp doc set** — ✅ done **except** the LinkML schema (modelling-blocked)

## Parked / deferred (see HANDOVER §4–6)

1. **Orchestrator Shape A/B/C** — parked by decision (`task-2…` §7). Resolved in
   the Jul 20 blueprints: LangFlow chosen (see
   [Conflicts](#conflicts--interpretation-priorities) item 3).
2. **Data model, scoped-MCP ops, access-visibility rules, dialogue-act subset** — modelling session.
3. **WhatsApp consent / paid-template / GDPR model** — prod-cutover workstream.

## Conflicts & interpretation priorities

The architecture documents were produced over several weeks and evolved across
working sessions. Some points are handled differently in later documents than in
earlier ones. This section records the major conflicts and how to resolve them.

### Precedence rule

**When two documents conflict on the same point, the newer document wins.** The
documents fall into three generations:

| Generation | Date | Documents |
|------------|------|-----------|
| Baseline | Jul 8 | `project-statement.md`, `architecture-statement.md`, `HANDOVER.md`, `raci.md`, `use-cases/`, `decisions/`, `diagrams/workflows.md`, `task-2-frameworks-exploration.md`, `specs/` |
| Model + infra | Jul 17 | `model/linkml/`, `model/modelspecs/`, `Makefile`, `infra/`, `scripts/` |
| Current design | Jul 20 | `agentic-system-blueprint.md`, `agentic-system-blueprint-phase-1.md`, `incremental-system-development-strategy.md`, `non-functional-requirements.md`, `verification-testing-and-evaluation-strategy.md` |

Within the Jul 20 generation, `non-functional-requirements.md` §1 names its own
internal precedence: confirmed scope decisions in the NFR > Project Statement >
System Blueprint > accepted ADRs > research report. Proposed ADRs are used only
where they align with the confirmed V1 direction.

### Auto-resolved conflicts (newer file wins)

**1. V1 autonomy.** The Jul 8 `project-statement.md` and `use-cases/` describe
V1 as "manually or semi-manually" assisted. The Jul 20
`agentic-system-blueprint.md` §1 and `non-functional-requirements.md` §1.1
(NFR-AUT-001) make V1 autonomous — no operator on success paths.
**Resolution:** V1 is autonomous.

**2. WhatsApp in V1.** The Jul 8 `project-statement.md` lists "Full WhatsApp
API" as out-of-scope / post-V1. The Jul 20 `non-functional-requirements.md`
§1.1 and NFR-CHN-002 make WhatsApp production support mandatory for V1 (required
by Field Pilot). **Resolution:** WhatsApp is V1 production scope.

**3. Orchestrator choice.** The Jul 8 documents (`architecture-statement.md`,
`decisions/` ADR-006, `task-2-frameworks-exploration.md` §7, `HANDOVER.md` §4)
explicitly park the "Shape A/B/C" orchestration decision. The Jul 17
`infra/docker-compose.yaml` deploys Langflow, and the Jul 20 blueprints commit
to LangFlow as the orchestrator (LF-00…LF-90 flow inventory).
**Resolution:** LangFlow is the orchestrator; the Shape A/B/C fork is closed.

**8. Dialogue management.** The Jul 8 ADR-018 mandates a DAMSL / ISO 24617-2
dialogue-act layer with a planner. The Jul 8 `task-2-frameworks-exploration.md`
§3 already scoped this down to model-driven slot-filling, and the Jul 20
`non-functional-requirements.md` §5 confirms the DA taxonomy and planner are
deferred. **Resolution:** V1 uses slot-filling only; no DA taxonomy or planner.

**9. V1 use-case scope & agent decomposition.** The Jul 8 documents
(`HANDOVER.md`, `use-cases/`, `architecture-statement.md` §4) cover UC-0…UC-13
with a cosmic-python service-layer decomposition. The Jul 20 documents
(`agentic-system-blueprint.md` §1, `non-functional-requirements.md` §1.2)
restrict V1 to UC-1 and UC-3…UC-9 and decompose the system into 10 named
LangFlow agents. **Resolution:** V1 scope is UC-1 + UC-3–UC-9 with agent
decomposition. The omitted use cases — UC-2 (Transporter preference), UC-10
(Cascade), UC-11 (Cancellation), UC-12 (Transporter profile & routes), UC-13
(Party profile) — are scheduled for inclusion in **Phase 4 (Hardened Service)**
per `incremental-system-development-strategy.md` §7.1.

### Conflicts requiring manual resolution

These conflicts cannot be resolved by the "newer wins" rule alone because the
older documents (mostly ADRs) remain referenced and authoritative in parts, or
because stale material needs active revision rather than simple supersession.

**4. Core architecture shape.** ADR-016 (Jul 8) mandates a cosmic-python FastAPI
core with tools/MCP as the entrypoints layer. The Jul 20
`agentic-system-blueprint.md` is LangFlow-centric: deterministic logic is a
LangFlow component invoked by agents, and a Data Access Agent (not a
service-layer boundary) mediates Neo4j access. The two describe different
architectural shapes. **⚠ Requires manual resolution.**

**5. MCP & per-party access.** ADR-005 and ADR-015 (Jul 8; ADR-015 "Accepted")
commit to a *custom scoped MCP/tool server* over cosmic-python services for
party-facing agents, with the stock `mcp-neo4j-cypher` for admin only. The Jul
20 `agentic-system-blueprint.md` replaces the scoped MCP with a *Data Access
Agent* that uses the stock Neo4j MCP (`read-cypher` / `write-cypher` /
`get-schema`) behind a Guardrail Agent (Phase 2+). The ADRs and the blueprint
describe different mechanisms for the same concern. **⚠ Requires manual
resolution.**

**6. RequestStatus enum.** `diagrams/workflows.md` (Jul 8) draws a state machine
using states — `Matching`, `SentToTransporter`, `NoMatch`, `Closed` — that do
not exist in the Jul 17 LinkML `RequestStatus` enum or the Jul 20 blueprint §6.
The enum (11 values: new, needsClarification, complete, optionsProposed,
waitingResponse, accepted, rejected, pickUpPlanned, pickedUp, delivered,
cancelled) is authoritative, and `closed` is a timestamp attribute on
`DeliveryRequest`, not a status. The workflow diagram is stale and needs active
revision to align with the enum. **⚠ Requires manual resolution (diagram is
stale; needs revision).**

**7. Central domain object.** ADR-001 (Jul 8) frames the **Brokerage event**
(whose subject is a Parcel Request) as the central object. The Jul 17 model
spec + LinkML schema and the Jul 20 blueprint treat **`DeliveryRequest`** as
the authoritative aggregate; there is no `Brokerage` class in the model. The
ADR and the model disagree on what the central object is.
**⚠ Requires manual resolution.**

**10. Admin / entity-resolution / goal-stack.** The Jul 8 ADRs — ADR-007 (admin
plane), ADR-013 (background entity-resolution agent), ADR-014 (goal stack) —
mandate these as V1 capabilities. The Jul 20
`non-functional-requirements.md` §5 defers all three to post-V1 (basic
duplicate prevention only; concurrent-request isolation only; exact Admin role
deferred). The ADRs' statuses do not reflect the deferral.
**⚠ Requires manual resolution.**
