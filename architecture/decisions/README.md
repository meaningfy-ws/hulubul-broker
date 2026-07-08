# Architecture Decision Records (DRAFT v2)

Revised after review feedback: V1 is **autonomous agent brokerage**, not
operator-driven. Organised by C4 level. ⚠ CONFIRM = still open.
Model detail (classes, properties, payloads) is deferred to a dedicated
**modelling session**; container/component set to the **architecture review**.

| ADR | Level | Decision | Status |
|-----|-------|----------|--------|
| ADR-001 | L1 | Central object is the brokered connection (Sender→Transporter→Receiver) around a Parcel Request | Proposed |
| ADR-002 | L1 | Sender initiates brokerage; all actors self-manage profiles (secondary flows) | Proposed |
| ADR-003 | L1 | Channel-abstracted messaging: Telegram in dev/test, WhatsApp in prod | Proposed |
| ADR-004 | L2 | Autonomous agent brokerage — no operator on success paths | Proposed |
| ADR-005 | L2 | Neo4j graph store as system of record, reached by agents via Neo4j MCP | Proposed |
| ADR-006 | L2 | Agent orchestration is the core execution model | Proposed |
| ADR-007 | L2 | Admin/observability plane: admin agent + chat (optional UI) | Proposed |
| ADR-008 | L2 | Channel gateway with per-provider adapters | Proposed |
| ADR-009 | L3 | Contact Point is a first-class object, part-of a Transporter Profile | Proposed |
| ADR-010 | L3 | Automated recovery & resumption via scheduled triggers (3 nudges) | Proposed |
| ADR-011 | L3 | Receiver identity/profile required for a complete dispatch | Proposed |
| ADR-012 | L3 | Matching is a dedicated recommender (favourite→that, else top-3); bidding later | Proposed |
| ADR-013 | L2 | Background entity-resolution agent for dedup/merge | Proposed |
| ADR-014 | L3 | Conversational session control + goal stack, decoupled from chat thread | Proposed |
| ADR-015 | L2 | Agent↔data access: app-level scoping, writes via services; stay on Community | Accepted (revisit) |
| ADR-016 | L2 | Low-code/UI-first orchestration; coded parts Meaningfy-compliant; pragmatic testing | Proposed |
| ADR-017 | L2 | Transaction-like validated writes; no hard deletes | Proposed |
| ADR-018 | L3 | Dialogue management grounded in dialogue-act theory + planning | Proposed |

Full text below.

---

## ADR-001 — Central object: the brokered connection (L1)

**Context.** The product is not a parcel tracker; it is **connection brokerage**
between a package Sender, a Transporter, and (secondarily) a Receiver. A
brokered connection presupposes known identities and profiles for all parties
(incl. location), plus route information and route frequency.

**Decision.** Model the domain around the **Brokerage** event — a matched
connection Sender→Transporter→Receiver — whose subject is a **Parcel Request**.
Profiles, routes and route frequency are **preconditions**, not by-products.

**Consequences.** +Matching and trust sit at the centre, not logistics tracking.
+Profiles/routes are first-class, populated before brokerage runs. −Requires
profile+route data to exist before a request can be fully brokered (bootstrapping
via the secondary profile flows, ADR-002). Class/property detail → modelling session.

**Confirmation.** Domain model roots on Brokerage + Parcel Request; profiles and
routes are referenced entities.

---

## ADR-002 — Sender initiates brokerage; all actors self-manage profiles (L1)

**Context.** The main event (deliver a package A→B) is Sender-initiated. But
Transporters create/update/improve their profile and routes, and Senders and
Receivers register and improve their own profiles — these are first-class
secondary flows, not admin chores.

**Decision.** **Sender** triggers the brokerage event. **Transporter, Sender and
Receiver** each own use cases to register and maintain their profile (and, for
Transporters, routes/frequency).

**Consequences.** +Data preconditions (ADR-001) are filled by the actors
themselves. +No operator data-entry. −More conversational surfaces (profile
capture per actor type). Receiver-initiated *brokerage* remains post-V1.

**Confirmation.** Use-case catalogue gains profile-lifecycle use cases per actor;
brokerage use cases stay Sender-triggered.

---

## ADR-003 — Channel-abstracted messaging; Telegram dev, WhatsApp prod (L1)

**Context.** Production target is WhatsApp; development and testing run on
**Telegram** (faster/cheaper to iterate). Users must keep a familiar chat UX
while structured state lives in the system.

**Decision.** All party interaction is **channel-abstracted**. The runtime
channel is Telegram in dev/test and WhatsApp in prod, selected by configuration;
the authoritative state (Brokerage, Parcel Request, profiles, status) never lives
only in chat.

**Consequences.** +Iterate on Telegram, deploy on WhatsApp with no domain change.
+Channel-agnostic agents. −Must respect two providers' quirks behind one
interface. −Parity testing needed before the WhatsApp cutover.

**Confirmation.** Channel gateway with Telegram + WhatsApp adapters (ADR-008);
no provider details in agent/domain logic.

---

## ADR-004 — Autonomous agent brokerage; no operator on success paths (L2)

**Context.** The goal is a service that brokers connections without human
operators. A person intervenes only when something breaks (a bug or an
unrecoverable exception), not to run the normal flow.

**Decision.** Every successful brokerage scenario is driven **end-to-end by
agents**. Human involvement is limited to the admin/observability plane (ADR-007)
for exceptions and controlled corrections.

**Consequences.** +Scales without operator headcount. +Forces the flow to be
fully specified (no "operator will figure it out"). −Requires robust recovery,
timeouts and guardrails (ADR-010). −Exception handling and observability must be
first-class, not afterthoughts.

**Confirmation.** No use case requires an operator on the happy path; the
Admin actor appears only in exception/observability use cases.

---

## ADR-005 — Neo4j graph store via MCP as system of record (L2)

**Context.** Parties, profiles, locations, routes, frequencies, preferences and
past brokerages form a densely connected graph; matching traverses it. Agents
need a governed way to read/write it.

**Decision.** **Neo4j** is the operational system of record. Agents reach it
through the **Neo4j MCP** server as a tool, not through bespoke data code.

**Consequences.** +Matching/relationship queries are first-class. +Uniform,
inspectable tool surface for agents. +Schema is introspectable (agents/admin can
read it to "know how to talk to it"). −Graph-model fluency required. −MCP
read/write scoping and guardrails must be defined (admin write vs party-facing).

**Refinement (task-2).** "Via the Neo4j MCP" is split by principal: **party-facing
agents use a thin *custom scoped* MCP/tool server** (named per-party operations over
the domain services — see ADR-015), **not** the stock server; the **admin agent** uses
the stock `mcp-neo4j-cypher` on a separate, audited credential. The generic Cypher MCP
is never exposed on the party path.

**Confirmation.** Graph store container = Neo4j Community; party access via the scoped
tool server, admin access via the audited stock MCP; schema exposed for introspection.

---

## ADR-006 — Agent orchestration is the core execution model (L2)

**Context.** The brokerage flow is a set of conversational, tool-using steps
(intake, profile capture, matching, negotiation, status, recovery) that suit an
orchestrated set of agents wired to tools and the Neo4j MCP.

**Decision.** Adopt **agent orchestration** as the primary execution model. Each
agent has a defined role, prompt, and tool wiring; orchestration routes a
brokerage through them. The concrete framework is chosen in task #2.

**Consequences.** +Natural fit for conversational, tool-driven brokerage.
+Roles/prompts are inspectable and tunable (ADR-007). −Needs orchestration,
state hand-off and failure semantics designed carefully. −Prompt/tool wiring
becomes versioned configuration, not incidental.

**Confirmation.** Agents + orchestrator appear as containers/components in the
review; each agent's prompt and tool wiring are first-class, inspectable artefacts.

---

## ADR-007 — Admin/observability plane: admin agent + chat (optional UI) (L2)

**Context.** The team must fine-tune the agent architecture (each agent's prompts
and tool/Neo4j-MCP wiring), see what orders were sent by whom, make controlled
updates, read the DB schema, and help resolve a brokerage issue — without an
operator in the normal loop.

**Decision.** Provide an **admin plane**: an **admin agent** with read/write
access to Neo4j (broader scope than party-facing agents) plus a **chat
interface** (and optionally a UI) for inspection, tuning and controlled
intervention.

**Consequences.** +Observability and safe intervention without touching the happy
path. +Prompts/wiring, orders and schema are inspectable in one place. −Elevated
write access needs strong guardrails and an audit trail. −Extra surface to build
and secure.

**Confirmation.** Admin agent + chat/UI container in the review; write actions
audited; access scoped separately from party-facing agents.

---

## ADR-008 — Channel gateway with per-provider adapters (L2)

**Context.** ADR-003 requires Telegram (dev) and WhatsApp (prod) behind one
abstraction.

**Decision.** A **Channel Gateway** exposes one messaging interface to the
agents; **per-provider adapters** (Telegram, WhatsApp) implement it. Provider
selection is configuration.

**Consequences.** +Agents are channel-agnostic. +New providers = new adapter.
−Gateway must normalise provider differences (attachments, delivery/read
receipts, session windows). −Provider-specific limits (e.g. WhatsApp templating)
handled in the adapter.

**Confirmation.** Gateway interface consumed by agents; Telegram and WhatsApp
adapters behind it; no provider identifiers in domain/agent logic.

---

## ADR-009 — Contact Point is a first-class object, part-of a Profile (L3)

**Context.** A Sender can name a transporter that has no full profile yet; a
Transporter Profile is made up of one or more contacts. Ontological commitment:
**a Contact Point is a component (part-of) of a Transporter Profile.**

**Decision.** **Contact Point** is a first-class entity that is a **component of
a Transporter Profile** (composition; a Profile aggregates ≥1 Contact Point). A
**provisional** Contact Point may be captured before its full Profile exists and
is later attached/merged by the entity-resolution agent (ADR-013). Behaviour:
Contact Points are validity-checked by a **round-robin ping + ack**; a Transporter
is notified **anonymously** when someone adds them as a preference.

**Consequences.** +Supports "contact before profile". +Clean composition for
matching and merging. −Provisional CPs need resolution rules (ADR-013). Detailed
class/property design → modelling session.

**Confirmation.** Domain model: Contact Point `part-of` Transporter Profile;
provisional-CP state; validity + anonymous-preference behaviours in the use cases.

---

## ADR-010 — Automated recovery & resumption via scheduled triggers (L3)

**Context.** With no operator, paused interactions (unread messages, awaited
responses, stalled brokerages) must be driven to a positive or negative
resolution automatically. There is **no operator cascade**.

**Decision.** Use **scheduled triggers (cron-like)** plus recovery logic to
resume paused interactions. Contextual, config-driven timings:
- conversational nudge on unread: **~1–2h**;
- status change / other action (advance or close): **~24h**.
Escalation cap: **3 nudges**, then the interaction is closed negatively.

**Consequences.** +Self-healing flow without humans. +Timeouts and the 3-nudge
cap are explicit and tunable. −Needs idempotent, resumable state and clear
terminal conditions.

**Confirmation.** A scheduler/recovery component reads paused brokerages from
Neo4j and re-invokes the responsible agent; timings + 3-nudge cap are configuration.

---

## ADR-011 — Receiver identity/profile required for a complete dispatch (L3)

**Context.** Correction to the earlier "deferred receiver" assumption. A complete
package dispatch must know the Receiver (identity + profile, incl. destination),
even if no live Telegram/WhatsApp connection with the Receiver is established.

**Decision.** **Receiver identity and profile are required** for a Parcel Request
to be considered complete/dispatchable. Establishing a **live channel connection**
to the Receiver is **optional** (delivery coordination may proceed via Sender/
Transporter).

**Consequences.** +Destination and recipient are always known before dispatch.
+Delivery is never blocked solely by a missing Receiver chat. −Sender must supply
Receiver data up front (captured in intake / Receiver profile flow).

**Confirmation.** Completeness check requires Receiver identity+destination; the
Receiver channel link is an optional attribute.

---

## ADR-012 — Matching is a dedicated component (L3)

**Context.** Selection is recommend-to-Sender, not agent-imposed, and its logic is
non-trivial (favourite, past experience, route, urgency). It must be isolated and
independently testable, not smeared across the conversation agent.

**Decision.** A **dedicated Matching component** owns selection logic: if the
Sender has a **favourite** transporter → recommend that one; otherwise **propose
the top 3**, ranked by **past experience (highest weight)**, expressed preference,
relevant route / served location, and needed delivery date / urgency. The Sender
chooses or ranks.

**Future extension.** The recommender is the V1 shape (sender-pull, curated). It is
designed to later grow into a **bidding / marketplace** model where transporters
bid for a request. V1 keeps recommend-to-sender; broadcast-and-claim / bidding is
post-V1 and must not be assumed by the V1 flow.

**Consequences.** +Selection logic is one testable unit (fixtures per ranking
rule). +Ranking weights are tunable. +Clean seam for a later bidding mode.
−Needs profile+route+history data present (ADR-001 preconditions). −Weighting
scheme to be validated with real data.

**Confirmation.** Matching component with its own unit tests; conversation agent
calls it and presents the result; bidding kept out of V1 scope.

---

## ADR-013 — Background entity-resolution agent (L2)

**Context.** Provisional Contact Points and duplicate entities accumulate (same
transporter reached two ways, near-duplicate profiles). Merge rules are not purely
mechanical — they sometimes need a human judgement.

**Decision.** A **background entity-resolution agent** periodically reconciles
duplicate entities (Contact Points and other types). When unsure, it asks the
relevant party (Sender/Transporter) in a **human-friendly way** whether two things
are the same, and merges on confirmation. Runs off scheduled triggers (ADR-010).

**Consequences.** +Data quality self-heals without operators. +Human-in-the-loop
only for ambiguous merges, on the party's own data. −Needs candidate-pair
detection, safe/reversible merges, and an audit trail. −Another background agent
to orchestrate and rate-limit (don't over-ask users).

**Confirmation.** Entity-resolution agent as a background component; merge actions
audited and reversible.

---

## ADR-014 — Conversational session control + goal stack (L3)

**Context.** Multiple discrete goals (send a package, receive one, choose a
transporter, get a confirmation…) can happen inside **one long chat**. The system
must always know "what are we doing now" and not conflate concerns.

**Decision.** Maintain **strict session control**: one **session per discrete
goal**, decoupled from the chat thread. A per-party **goal stack** resolves the
active goal, supports nesting/interruption (start a sub-goal, return to the
parent), and ties each message to the right session/brokerage.

**Consequences.** +Clean separation of concerns within a single conversation.
+Each session maps to a brokerage/sub-goal and its own state + timeouts (ADR-010).
−Needs goal detection, push/pop rules and disambiguation prompts. −Session state
is first-class in the model and the store.

**Confirmation.** Session + goal-stack model in Neo4j; the orchestrator routes each
inbound message to the active session; unit + scenario tests for interleaved goals.

---

## ADR-015 — Agent↔data access: app-level scoping, writes via services (L2) — Accepted, revisit

**Context.** How do agents touch Neo4j? Direct Cypher via MCP is powerful for
reads, but two forces push back: (1) DDD/validation/transactions require writes to
pass domain rules (ADR-017); (2) **Neo4j Community lacks fine-grained
access control** — no per-user/role security, no multiple databases (Enterprise
only). So the DB itself cannot confine a party to "their data".

**Options.** (A) Agents run raw Cypher for everything via MCP. (B) All access
through domain services exposed as tools (tools→services→neo4j adapter). (C) Split:
**scoped reads** may use Cypher (through a boundary that injects the party filter);
**writes** go through domain services enforcing validation + transaction + access.

**Decision (accepted; revisit at stages).** **(C), enforced in the application/
domain model, not the DB.** We **stay on Neo4j Community**. Access is an
**application-specific, modelled constraint**, defined precisely at the data-model
stage. Governing rule for a party (e.g. a Contact Point):

> may know only **what was discussed in its own pact/interaction**, and may see
> the **public info of entities it has previously interacted with** — and nothing
> more.

Party-facing agents never get raw, unscoped DB credentials; the access layer
injects this ownership/interaction boundary on reads and routes all writes through
validated domain use cases. The **admin agent** (ADR-007) gets elevated, audited
access. Both read and write guardrails are **deterministically defined rules,
documented once the data model is settled** (modelling session). To be revisited as
the model and scale evolve.

**Consequences.** +Boundaries enforced in-app where Community Neo4j can't; no
Enterprise dependency. +Reads stay expressive within the party's scope; writes
stay safe. −The visibility rule must be modelled explicitly (which relationships
count as "interacted with", what is "public") and tested. −A middleware/service
layer sits between agents and the DB (less "magic direct Cypher").

**Confirmation.** Tools/MCP = entrypoint layer → services (writes) / scoped-read
adapter → Neo4j; access-boundary tests; admin path separated and audited.

---

## ADR-016 — Low-code/UI-first orchestration; coded parts Meaningfy-compliant (L2)

**Context.** Preference is **as much UI configuration and as little code as
possible** (n8n / Airflow / Flowise / Langflow …). Whatever *is* coded must comply
with Meaningfy standards. Everything should ideally be testable — including the
low-code workflows — but MVP pragmatism (YAGNI) may relax that.

**Decision.** Orchestration and flows are built **UI-first in a low-code tool**
(chosen in task #2). Custom code is kept **minimal** and, where written, follows
**Meaningfy standards** — SDD/BDD/TDD/DDD on **cosmic-python** (models, adapters,
services, entrypoints), with **tools/MCP as the entrypoints** layer. Testability is
**pragmatic**: test the deterministic coded core rigorously (matching, guardrails,
writes); test low-code workflows where feasible (black-box / integration tests
hitting workflow endpoints — Python tests over workflows are not contradictory);
**relax coverage for MVP-only, low-risk flows**.

**Consequences.** +Fast delivery, non-devs can tune flows. +Deterministic IP stays
clean, layered, well-tested. −Two worlds to keep coherent (low-code flows + Python
core) — the boundary must be explicit. −Low-code workflows are harder to unit-test;
accept integration-level coverage there. −"Which logic is code vs flow" must be
decided per feature (default: deterministic/guarded/stateful → code; NL/routing/
glue → flow).

**Confirmation.** Task #2 selects the tool(s); import-linter + pytest + pytest-bdd
on the coded core; workflow smoke/integration tests; a documented code-vs-flow rule.

---

## ADR-017 — Transaction-like validated writes; no hard deletes (L3)

**Context.** User↔DB interactions must behave transactionally with data validation
and shape checks; deletion is generally undesirable in a brokerage/audit domain.

**Decision.** All user-driven mutations run as **transaction-like** operations
through domain services (ADR-015) with **validation + data-shape checks at the
boundary** before commit. **No hard deletes** — use soft-delete / archival /
status transitions, except explicit special cases.

**Consequences.** +Consistency and auditability; history is retained (matches
"keep request history"). +Validation lives once, at the write boundary. −Soft-delete
adds lifecycle state to the model. −Neo4j write transactions must wrap multi-node
mutations.

**Confirmation.** Service-layer write use cases wrap Neo4j transactions; schema/
shape validation before commit; soft-delete/status fields in the model.

---

## ADR-018 — Dialogue management grounded in dialogue-act theory + planning (L3)

**Context.** The system must understand not just message *content* but
**communicative intent** — speech acts / dialogue acts, communicative goals, and
their sequencing — across many interleaved goals in one long chat (ADR-014). This
is a well-studied area; we should reuse theory rather than invent an ad-hoc intent
scheme.

**Decision.** Model conversation with an explicit **dialogue-act layer** informed
by established frameworks — **DAMSL** (Dialogue Act Markup in Several Layers) and
**ISO 24617-2 / DiAML** (the standard dialogue-act taxonomy with communicative
functions across dimensions: task, feedback, turn/time management, etc.). Inbound
messages are classified into dialogue acts; a **Dialogue Manager / planner** tracks
communicative goals and drives the next act, sitting above the session/goal-stack
(ADR-014) and feeding the deterministic components (matching, writes).

**Consequences.** +Principled, reusable intent model instead of bespoke labels.
+Communicative goals + planning are first-class and inspectable. +Maps cleanly onto
the goal stack and recovery (ADR-010/014). −Requires a dialogue-act classifier and
a planning component (build vs LLM-assisted — decide in task #2). −Full ISO 24617-2
is large; adopt a **pragmatic subset** relevant to brokerage dialogues, not the
whole standard.

**Open.** Which act inventory subset; how much planning is explicit vs
LLM-emergent; and confirm the third framework referenced in discussion
("EVA/eva" — clarify which framework is meant) before citing it.

**Confirmation.** A Dialogue Manager component with a documented (subset) dialogue-
act taxonomy; goals/plans modelled and testable in scenarios.
