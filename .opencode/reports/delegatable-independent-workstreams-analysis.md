---
title: "Delegatable Independent Workstreams from Phases 2–4"
version: "v0.1"
date: "2026-07-22"
project: "Hulubul V1"
status: "Recommendation report for delegation planning"
---

# Delegatable Independent Workstreams from Phases 2–4

## 1. Purpose

Identify workstreams from Phases 2–4 that can be shaped, designed, and built
independently of the Phase 1 main implementation line, so they can be delegated
to a contributing team member.

## 2. Selection criteria

Each candidate was evaluated against the criteria from `DEV/tasks/task04.md`:

| Criterion | Meaning |
|---|---|
| **Shapeable now** | Not blocked by unknowns or assumptions that Phase 1 is verifying. Design can start immediately. |
| **Weakly connected to Phase 1** | Does not depend on the Phase 1 agent flow topology, intake logic, or routing implementation. May depend on early Phase 1 dev scaffolding (Python package, tests, lint, Makefile — Tasks 1.1–1.4). |
| **Clear I/O** | Input and output are definable right now from existing architecture documents. |
| **Delegation value** | Represents a coherent unit of work that one contributor can own end-to-end, including design. |

## 3. Methodology

Reviewed the following architecture documents:

- `incremental-system-development-strategy.md` (phase definitions and commitments)
- `agentic-system-blueprint.md` (target agent inventory, use-case ownership, flow design)
- `agentic-system-blueprint-phase-1.md` (Phase 1 scope and boundary)
- `non-functional-requirements.md` (NFR catalogue with phase requirements)
- `verification-testing-and-evaluation-strategy.md` (testing evolution by phase)
- `project-statement.md` (product scope and actors)
- Phase 1 Change 1 artifacts (`proposal.md`, `plan.md`, `design.md`, `tasks.md`)
- `hulubul-phase-1-implementation-planning-handover.md`

For each phase, every capability and NFR was assessed against the four criteria
above. Blocked candidates were separated from viable ones.

## 4. Context: what Phase 1 owns and verifies

Understanding the Phase 1 boundary is essential for identifying what is
genuinely independent.

**Phase 1 (Walking Skeleton) — Change 1 + planned Change 2:**
- LF-00 Main Router, LF-10 Request Intake, LF-70 Data Access (Change 1)
- LF-20 Parcel Coordination: seeded transporter, simulated forwarding,
  acceptance, pickup, delivery, closure (Change 2, depends on Change 1)
- Operational contracts (Pydantic models, JSON Schemas)
- Neo4j operational binding schema
- Python package structure, test infrastructure, quality tooling
- LangFlow flow versioning and deployment toolchain

**Phase 1 is verifying:**
- LangFlow orchestration works for Hulubul's agent pattern
- Data Access Agent + MCP boundary is viable
- Routing-context-first routing is sound
- Structured outputs + deterministic rendering work
- Resumability across LangFlow restarts
- The operational contract approach is testable

Workstreams that depend on these validations being complete are **not** shapeable
now. Workstreams that are architecturally independent of these concerns are
shapeable now.

## 5. Candidate inventory

### 5.1 Viable candidates

#### C1 — Channel Abstraction & Telegram/WhatsApp Adapters

| Attribute | Assessment |
|---|---|
| **Phase** | 3 (Field Pilot) |
| **NFRs** | NFR-CHN-001 through NFR-CHN-006, NFR-TST-006 |
| **Shapeable now** | Yes — NFRs define the provider-neutral contract, message correlation, delivery semantics, and provider isolation requirements |
| **Weakly connected** | Yes — channel adapters are entrypoint-layer concerns that replace LangFlow Playground Chat Input/Output; they do not depend on agent flow topology or intake logic |
| **Clear I/O** | Input: inbound provider messages (text, metadata, channel identity, reply references). Output: outbound messages, delivery status callbacks, structured inbound events for the application |
| **Dependency on Phase 1** | Only on the operational message envelope contract (defined in Change 1) and the Python package/test scaffolding (Tasks 1.1–1.4) |
| **Delegation value** | High — a whole system capability with clear boundaries, testable contracts, and direct production value |

**What the contributor would own:**
- Design the provider-neutral `MessagingChannel` interface (inbound message
  reception, outbound message dispatch, delivery callback handling, reply
  correlation).
- Implement the Telegram adapter (development channel) against the Telegram
  Bot API.
- Define the WhatsApp adapter interface and implement it against the WhatsApp
  Business API (or at minimum the adapter skeleton + contract tests, depending
  on provider access).
- Build the provider-neutral channel contract test suite (NFR-CHN-006,
  NFR-TST-006): both adapters must pass the same interaction contract plus
  provider-specific failure tests.
- Design the identity-mapping interface (`resolve_channel_actor` —
  Channel.systemID → Agent and role context, NFR-SEC-001).

**Open parameters (do not block design, can be config-driven):**
- WhatsApp delivery semantics (provider acceptance vs. delivered callback vs.
  read receipt — Section 6, item 3 of NFRs).
- Provider-specific rate limits, retry policies, session-window rules
  (NFR-CHN-004: handled in the adapter, not in domain logic).

**Why it is the strongest candidate:** The user already identified it, the NFRs
are exceptionally detailed, and it is both a functional feature and an NFR
workstream. The contributor can design, implement, and test it as a
self-contained change.

---

#### C2 — Operational Audit & Event Log Infrastructure

| Attribute | Assessment |
|---|---|
| **Phase** | 2 (WB) for NFR-DAT-008; 3 (FP) for NFR-DAT-009 |
| **NFRs** | NFR-DAT-008 (complete audit trail), NFR-DAT-009 (immutability and privacy), NFR-OPS-001 (correlation) |
| **Shapeable now** | Yes — the audit record contents are fully specified in NFR-DAT-008 |
| **Weakly connected** | Yes — audit infrastructure is a cross-cutting service with a clear recording interface; it does not depend on agent flow topology |
| **Clear I/O** | Input: structured audit events (correlation ID, request ID, actor, role, calling agent/flow, operation/event, policy decision, previous/resulting state, result, config/model/workflow version). Output: append-only, queryable, immutable audit trail |
| **Dependency on Phase 1** | Only on the Python package/test scaffolding and the correlation-id pattern (defined in Change 1) |
| **Delegation value** | High — infrastructure that every subsequent phase needs; clear non-functional scope |

**What the contributor would own:**
- Design the audit event schema (typed Pydantic models for the NFR-DAT-008
  field list).
- Implement an append-only audit store (Neo4j label with creation-only
  semantics, or a separate store — design decision for the contributor).
- Build the audit recording interface (called by data-access operations,
  policy decisions, and transition events).
- Design a read-only query interface for operators (NFR-OPS-006).
- Implement privacy controls: identifiers, hashes, reason codes, or redacted
  summaries instead of full content (NFR-DAT-009).
- Write unit and integration tests proving immutability and completeness.

**Open parameters (do not block design):**
- Retention periods (Section 6, item 8 — config-driven).
- Exact storage choice (Neo4j label vs. separate store).

---

#### C3 — Externalized Configuration Framework

| Attribute | Assessment |
|---|---|
| **Phase** | 2 (WB) — NFR-MNT-004 |
| **NFRs** | NFR-MNT-004 (externalized operational configuration), NFR-OPS-005 (safe deployment and rollback) |
| **Shapeable now** | Yes — the parameter list is known from the NFR catalogue and the open-parameters section |
| **Weakly connected** | Yes — configuration is a cross-cutting infrastructure concern |
| **Clear I/O** | Input: structured configuration values (provider selection, reminder timing, timeout, nudge count, candidate cap, matching weights, model settings, safety limits). Output: validated, auditable, rollback-capable configuration consumed by all services |
| **Dependency on Phase 1** | Only on the Python package/test scaffolding |
| **Delegation value** | Moderate — smaller scope than C1 or C2, but foundational for Phase 2+ |

**What the contributor would own:**
- Design the configuration schema covering all known operational parameters
  (from NFRs Section 6 open parameters and NFR-MNT-004).
- Implement a validated configuration loader with schema enforcement.
- Add auditability (configuration changes are logged with version and author).
- Add rollback capability (previous configuration versions are retained).
- Write unit tests for validation, audit, and rollback.

**Open parameters (do not block design):**
- Exact values for each parameter (config-driven by design).

---

#### C4 — Scheduler & Wait-Store Infrastructure

| Attribute | Assessment |
|---|---|
| **Phase** | 2 (WB) for basic; 3 (FP) for full recovery — NFR-REL-004, NFR-PERF-004 |
| **NFRs** | NFR-REL-004 (automated waits and recovery), NFR-PERF-004 (scheduler timeliness) |
| **Shapeable now** | Partially — the scheduler service is generic, but the wait-condition schema and recovery policy depend on Phase 2 agent decisions |
| **Weakly connected** | Yes — the scheduler is a separate service that triggers recovery actions; it does not depend on Phase 1 agent flows |
| **Clear I/O** | Input: persisted wait conditions with deadlines. Output: triggered reminders, timeouts, cascade actions at due time |
| **Dependency on Phase 1** | Only on the Python package/test scaffolding and Neo4j infrastructure |
| **Delegation value** | Moderate — the infrastructure is buildable, but full utility requires Phase 2 recovery policy decisions |

**What the contributor would own:**
- Design the wait-condition data model (deadline, reminder count, recovery
  policy reference, owning agent, request context).
- Implement the scheduler service (polling or event-driven, processes due
  conditions, triggers the owning agent).
- Implement the deterministic recovery policy selector (remind, cascade, or
  escalate based on configured rules — NFR-REL-004).
- Write unit and integration tests for scheduling accuracy and restart
  recovery (NFR-PERF-004: 95% within 5 minutes).

**Blocking note:** The recovery policy parameters (reminder delay, final
timeout, cascade timing — Section 6, item 2) are open. The contributor can
design the infrastructure with config-driven policies, but the actual policy
values need a product decision. This makes it shapeable but not fully
implementable without that decision.

---

#### C5 — LLM Guardrail Agent Design & Prototype

| Attribute | Assessment |
|---|---|
| **Phase** | 2 (WB) — NFR-CTL-003, NFR-CTL-004, NFR-SEC-008 |
| **NFRs** | NFR-CTL-003 (action-gate sequence), NFR-CTL-004 (deterministic hard checks around LLM guardrail), NFR-SEC-008 (prompt-injection resilience) |
| **Shapeable now** | Design yes; implementation partially — the agent specification is detailed in the blueprint (Section 8.10), but integration requires LF-70 internals |
| **Weakly connected** | Moderately — the guardrail is a new stage inside LF-70's internal flow, but it can be designed as a standalone agent with its own contract |
| **Clear I/O** | Input: DataOperationRequest + Cypher plan. Output: ALLOW / DENY / REQUIRE_REVIEW decision with reason codes and constraints |
| **Dependency on Phase 1** | Depends on LF-70's internal structure and the DataOperationRequest/Result contract (defined in Change 1) |
| **Delegation value** | Moderate — design and prototype are valuable, but full integration is a Phase 2 task |

**What the contributor would own:**
- Design the guardrail agent's decision model, tools, and evaluation criteria
  (all specified in blueprint Section 8.10).
- Design the deterministic hard checks that wrap the LLM guardrail
  (NFR-CTL-004: operation allowlist, schema validation, query timeout,
  result-size limit, parameterization, delete prohibition, expected-status
  comparison, idempotency, max affected records).
- Prototype the guardrail as a standalone LangFlow flow or Python service
  with mock data-access plans.
- Design the audit recording for guardrail decisions.
- Write unit tests for each deterministic check and a guardrail evaluation
  dataset.

**Blocking note:** The guardrail integrates between the data-access planner
and MCP execution inside LF-70. Until LF-70's Phase 1 form is built and
archived, the integration point is conceptual. The contributor can own the
design and prototype, but not the integration.

---

### 5.2 Blocked candidates (not shapeable now)

| Candidate | Phase | Blocker |
|---|---|---|
| **Deterministic Matching Engine** | 2 (WB) | Matching rules (eligibility, weighting, route compatibility) are undecided (blueprint Section 11 + NFR Section 6, item 6). Transporter profile/route data model is from UC-12, deferred to Phase 4. |
| **Transporter Profile & Route Management (UC-12)** | 4 (HS) | Depends on matching engine design and Phase 4 scope decisions. |
| **Feedback System (UC-9 feedback)** | 4 (HS) | Feedback questions, rating scale, eligible participants, and matching impact are undecided (blueprint Section 11). |
| **Full Observability Platform** | 3 (FP) | Platform choice (Arize, Langfuse, Traceloop) is open. Phase 1 uses native LangFlow traces; reassess in Phase 3. The correlation-ID framework could be designed, but the platform decision blocks implementation. |
| **Phase 2 Agent Splits (Matching, Brokerage, Fulfilment, Closure, Clarification)** | 2 (WB) | Deeply dependent on Phase 1 agent flow topology, LF-20 structure (Change 2), and the data-access contract being validated. Cannot be designed independently. |
| **Session Isolation & Multi-Request Support** | 3 (FP) | Depends on the session/binding model from Phase 1 being validated and the Phase 2 multi-request binding rules being designed. |
| **Outbound Reliability / Outbox** | 3 (FP) | Depends on the channel adapter (C1) and the Brokerage Agent dispatch logic being defined. |
| **Cancellation (UC-11)** | 4 (HS) | Cancellation policy after acceptance is an open parameter (Section 6, item 5). |
| **Entity Resolution** | 4 (HS) | Deferred beyond basic duplicate prevention; probabilistic merge is explicitly out of V1 scope. |

## 6. Ranked recommendations

| Rank | Candidate | Type | Readiness | Delegation fit | Recommended scope |
|---|---|---|---|---|---|
| **1** | **C1 — Channel Abstraction & Telegram/WhatsApp Adapters** | Functional + NFR | High | Excellent | Full change: design interface, implement Telegram adapter, WhatsApp adapter (or skeleton), contract test suite, identity-mapping interface |
| **2** | **C2 — Operational Audit & Event Log** | NFR infrastructure | High | Excellent | Full change: design audit event schema, implement append-only store, recording interface, query interface, privacy controls, tests |
| **3** | **C3 — Externalized Configuration Framework** | NFR infrastructure | High | Good | Full change: design config schema, implement validated loader, auditability, rollback, tests |
| **4** | **C4 — Scheduler & Wait-Store Infrastructure** | NFR infrastructure | Moderate | Moderate | Infrastructure with config-driven policies; recovery policy values need a product decision before full utility |
| **5** | **C5 — LLM Guardrail Agent Design & Prototype** | Functional + NFR | Moderate | Moderate | Design + prototype only; integration is a Phase 2 task after LF-70 is archived |

## 7. Dependency notes

All viable candidates depend on the early Phase 1 dev scaffolding being in
place (Python package, pyproject.toml, pytest, Makefile, import-linter —
Change 1, Tasks 1.1–1.4). If the contributor starts before those tasks are
merged, they will need to create their own minimal scaffolding or wait for
the first Phase 1 commits.

C1 additionally depends on the `MainFlowInput` / `ActorContext` envelope
contract from Change 1, but this is already designed in the plan and does not
require Phase 1 runtime validation — only the typed contract definitions.

No viable candidate depends on LF-00, LF-10, LF-70, or LF-20 being built or
validated.

## 8. Artifacts the contributor should read

- `architecture/non-functional-requirements.md` — especially Sections 4.6
  (channel portability), 4.4 (auditability), 4.8 (configurability), 4.1
  (reliability), and 6 (open parameters).
- `architecture/agentic-system-blueprint.md` — especially Sections 8.1
  (Router, `resolve_channel_actor`), 8.5 (Brokerage, channel delivery rule),
  8.9 (Data Access contract), and 8.10 (Guardrail).
- `architecture/agentic-system-blueprint-phase-1.md` — especially Section 11
  (operational schemas, for the message envelope contract).
- `architecture/incremental-system-development-strategy.md` — phase
  boundaries and stable commitments.
- `architecture/verification-testing-and-evaluation-strategy.md` — Section 12
  (testing additions in later phases).
- `openspec/changes/deliver-phase-1-request-intake-thread/plan.md` — for the
  operational contract definitions the adapter must conform to.
- `architecture/use-cases/blue-user-goal.md` — for UC-4 (forward request),
  UC-5 (respond), and UC-7/UC-8 (pickup/delivery coordination) that define
  what the channel must carry.
