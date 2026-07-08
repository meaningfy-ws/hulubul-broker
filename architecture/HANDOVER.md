# Hulubul V1 — Architecture Handover

**Purpose:** resume point for the architecture work. Captures what's decided, what's
drafted, what's parked, and the next steps. Everything is **DRAFT** — nothing is
implementation-committed.

## 1. What Hulubul is (one paragraph)

An **autonomous, agent-driven parcel-brokerage service**: it turns a Sender's
intention into a structured **Parcel Request**, recommends transporters, and carries
the communication through pick-up and delivery — over a **chat channel (Telegram in
dev, WhatsApp in prod)**, on a **Neo4j graph** system of record. No human operator on
success paths; humans intervene only for exceptions via an admin plane. Conversation
is **model-driven slot-filling** (mandatory-field validation), not a heavyweight
dialogue engine.

## 2. Artefact map (everything on disk under `architecture/`)

| File | What it is | Status |
|------|-----------|--------|
| `project-statement.md` | Problem, scope, actors, success (from v0.4) | ✅ reviewed |
| `architecture-statement.md` | Drivers + C4 L1/L2/L3 + mermaid | ✅ **v2 — reworked to the autonomous-agent direction; orchestrator drawn as a parked box** |
| `use-cases/` | Cockburn use cases: `white-summary.md` (UC-0), `blue-user-goal.md` (UC-1..13) | ✅ **incl. profile-lifecycle UC-12/13 + the 4 folded details** |
| `decisions/README.md` | **ADR-001..018**, by C4 level | ✅ current (v2; ADR-005 refined re: scoped MCP) |
| `diagrams/workflows.md` | Status state-machine, happy-path sequence, cascade | ✅ draft (still valid) |
| `raci.md` | Responsibility matrix across the flow | ✅ **added** |
| `task-2-frameworks-exploration.md` | Framework/tech exploration (6-agent research) | ✅ complete, **non-decisional** |
| `specs/` | LinkML domain schema | ⛔ **placeholder only — deferred to modelling session** |
| `README.md` | Package index | ✅ current |
| `HANDOVER.md` | This file | — |

## 3. Decisions locked (see `decisions/README.md` for full ADRs)

- **Central object:** brokered connection (Sender→Transporter→Receiver) around a Parcel Request; profiles + routes + frequency are preconditions (ADR-001).
- **Initiation:** Sender starts brokerage; all three actors self-manage profiles (ADR-002).
- **Channel:** Telegram dev → WhatsApp prod, behind one `ChannelPort` (ADR-003/008).
- **Autonomy:** agents drive all success paths; humans only on exceptions (ADR-004).
- **Data:** Neo4j Community as system of record; **party agents get a thin *custom scoped* MCP/tool server** over cosmic-python services (stock Cypher MCP is admin-only, audited); access control is app-level, deterministic rules documented after modelling (ADR-005/015).
- **Method:** low-code/UI-first orchestration, minimal Meaningfy-compliant Python core (cosmic-python), pragmatic testing; deterministic matching + guarded writes stay outside the LLM (ADR-006/012/016/017).
- **Matching:** dedicated recommender — favourite → that, else top-3; bidding is a designed-for future extension (ADR-012).
- **Recovery:** cron/scheduled triggers, 3-nudge cap, no operator cascade (ADR-010).
- **Receiver:** identity/profile required for a complete dispatch; live receiver chat optional (ADR-011).
- **Support agents:** background entity-resolution agent (ADR-013); session-per-goal + goal stack (ADR-014); admin/observability plane (ADR-007).
- **Dialogue:** scoped down to **model-driven slot-filling + mandatory-field validation** — no BDI/planner/logical formalisms (ADR-018).

**Common tech spine (from task-2, low-controversy):** aiogram (Telegram) / 360dialog
(WhatsApp) · Neo4j Community · scoped MCP over FastAPI cosmic-python core · LiteLLM
(Haiku/Sonnet) · cron/APScheduler + Neo4j state · pytest/pytest-bdd + DeepEval +
self-hosted Langfuse.

## 4. Parked / open decisions (do NOT assume)

1. **Orchestration Shape A/B/C** — single low-code (Dify) vs split (n8n + chat-flow + FastAPI) vs Python-agent (Pydantic AI + DBOS + Langfuse). **Explicitly parked** — decide later, ideally after prototyping thin slices. See `task-2-frameworks-exploration.md` §7.
2. **WhatsApp consent / paid-template / GDPR model** — a real workstream before prod cutover; invisible on Telegram dev; not yet an ADR.
3. **`ChannelPort` capability set**, **scoped-MCP operation catalogue + visibility rule**, **dialogue-act naming subset** — all → **modelling session**.

## 5. Task #3 status — consolidation DONE except one modelling-blocked item

Task #3 was driven to completion up to the A/B/C decision. Completed:
- ✅ **Reworked `architecture-statement.md` §2–4** to the settled autonomous-agent L2/L3 (Channel Gateway · Orchestrator [Shape parked] · Brokerage Core [FastAPI/cosmic-python] · Scoped MCP + Admin MCP · Neo4j · Scheduler/Recovery · LLM Gateway · Admin/Observability · Entity-resolution agent), with new container + component mermaid.
- ✅ **Added profile-lifecycle use cases** UC-12 (Transporter + routes) and UC-13 (Sender/Receiver party profile).
- ✅ **Folded the 4 interaction details**: anonymous "added as a preference" notice (UC-2); Contact-Point validity via round-robin **ping + ack** (UC-2); Transporter may request additional package info before deciding (UC-5); firm precondition "complete Sender profile before an order" (UC-1).
- ✅ **Produced the RACI matrix** (`raci.md`).
- ✅ **Refined ADR-005** — party path uses a custom scoped MCP; admin uses the stock server, audited.
- ✅ **Updated the index** (`README.md`) and this handover.

**Only remaining item (modelling-blocked):**
- ⛔ **LinkML domain schema** (`specs/`) — write in/after the modelling session, not before. Placeholder in `specs/README.md` lists exactly what it must contain.

## 6. Recommended next steps (in order)

1. **Modelling session** — data model (Brokerage, Parcel Request, Contact Point ⊂ Transporter Profile, Session/Goal, Zone/Route), the app-level access/visibility rules, scoped-MCP operation catalogue, dialogue-act naming subset. Unblocks most of §5 and the LinkML schema.
2. **Architecture review** — finalise the L2/L3 container/component rework (§5 item 1).
3. **Finish task #3 consolidation** — fold everything into the crisp, cross-referenced set + RACI, ready for work-shaping.
4. **Then** revisit the Shape A/B/C orchestration fork with a thin prototype.

## 7. Task tracker state

- #1 Architecture statement + use cases + ADRs — **done** (draft)
- #2 Frameworks & technical choices — **done** (exploration, non-decisional)
- #3 Consolidate crisp doc set — **done except the LinkML schema** (modelling-blocked; §5)
- (implied) Modelling session — **not started**, recommended next (unblocks LinkML + A/B/C prep)
