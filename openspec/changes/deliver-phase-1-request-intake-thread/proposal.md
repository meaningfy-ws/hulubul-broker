## Why

Hulubul has a conceptual model and a local LangFlow/PostgreSQL/Neo4j/MCP stack,
but no reproducible application thread proves that a Sender's parcel intention
can become durable business state and resume safely. Runtime flows currently
live outside version control, operational contracts are descriptive only, and
there is no automated evidence for persisted-state routing or clarification.
This change establishes the smallest end-to-end intake thread so later
coordination work starts from tested boundaries rather than more design-only
assumptions.

## Appetite

One reviewable OpenSpec implementation and pull-request cycle. The cut line is
the transition of one persisted request to `complete`, including one-message
and multi-turn clarification paths. Any coordination, matching, transporter,
channel, or production-hardening work is deferred rather than allowed to expand
this change.

## What Changes

**LangFlow source and runtime**
- From: Mutable LangFlow image and database-only prototype flows.
- To: Pinned LangFlow 1.10.2 runtime with three stable-ID, normalized,
  source-controlled flows and an LFX validation/push/pull/drift workflow.
- Reason: A clean environment must reproduce the reviewed orchestration.
- Impact: Additive for local development; replaces unversioned runtime practice.

**Request intake**
- From: No executable Sender intake behavior.
- To: LF-10 captures and immediately validates supplied facts, persists a sparse
  truthful draft, asks one focused question, and completes the same request once
  all required facts are valid.
- Reason: Prove UC-1 across one-message and clarification paths.
- Impact: New behavior; no existing application caller is broken.

**Routing and resumption**
- From: No authoritative session-to-request routing mechanism.
- To: LF-00 loads an application-owned Neo4j conversation binding before every
  route and resumes the same request across interactions and LangFlow restart.
- Reason: Chat memory is context, not lifecycle authority.
- Impact: Adds an operational Neo4j label, relationship, and uniqueness
  constraint without changing the LinkML conceptual model.

**Data-access boundary**
- From: Raw Neo4j MCP exists as an unguarded infrastructure endpoint.
- To: Only LF-70 receives MCP tools; LF-00 and LF-10 submit caller-scoped typed
  operations and consume validated results.
- Reason: Prove the planned data-agent boundary while limiting direct access.
- Impact: Introduces a named, non-production exception for LLM-generated Cypher
  that must be replaced during later hardening.

**Python-supported code and verification**
- From: No application package, operational schemas, tests, or architecture
  enforcement.
- To: Pydantic-owned contracts, generated JSON Schemas, pure intake policy,
  thin LangFlow components, optimistic concurrency, a layered test pyramid,
  Gherkin acceptance features, and deterministic evaluation gates.
- Reason: Keep coded parts reviewable and independently testable without
  duplicating visual orchestration.
- Impact: Expands project dependencies and quality targets; introduces no
  standalone Python API service.

## Capabilities

### New Capabilities

- `phase1-flow-runtime`: Version, validate, deploy, authenticate, and reproduce
  the three Change 1 LangFlow flows with PostgreSQL persistence.
- `operational-contract-validation`: Define and enforce versioned execution
  envelopes, routing/intake results, logical data operations, snapshots, and
  controlled failures.
- `delivery-request-intake`: Capture, incrementally validate, persist, clarify,
  and complete one Sender request without fabricated domain data.
- `domain-state-routing`: Resolve the active request from Neo4j before routing
  and constrain which logical operations each flow may request.
- `conversation-request-resumption`: Continue the same request across turns,
  concurrent-update conflicts, and a retained-state LangFlow restart.

### Modified Capabilities

None. The durable `openspec/specs/` store is empty; all five capabilities are
introduced by this change.

## Key Decisions

- `DEC-002`/`DEC-003`: Full pinned LangFlow plus PostgreSQL is the runtime; Git
  and LFX own flow history and drift control. See
  [`design.md`](design.md#dec-002-use-full-pinned-langflow-with-postgresql).
- `DEC-005`: LLM-driven LF-70 is an explicit non-production Walking Skeleton
  exception, not the target write architecture. See
  [`design.md`](design.md#dec-005-treat-llm-driven-lf-70-as-a-temporary-phase-1-exception).
- `DEC-007`: Python uses a proportional functional core and thin LangFlow
  shell; no FastAPI or empty layers are introduced. See
  [`design.md`](design.md#dec-007-apply-proportional-clean-architecture-to-python).
- `DEC-009`: Sparse drafts are permitted, but every supplied fact is validated
  immediately and the complete aggregate is checked before `complete`. See
  [`design.md`](design.md#dec-009-allow-sparse-persisted-drafts-without-invented-domain-data).
- `DEC-011`: All mutations are atomic and optimistic-concurrency protected; a
  losing writer reloads state instead of replaying a write. See
  [`design.md`](design.md#dec-011-keep-each-data-mutation-atomic-and-use-optimistic-concurrency).
- `DEC-017`: Deterministic checks are hard gates; live-model and judge evidence
  remains soft. See
  [`design.md`](design.md#dec-017-use-a-layered-verification-pyramid).

## Rabbit Holes

- LangFlow/PostgreSQL must not silently become the flow source of truth; UI
  changes must return through normalization and review.
- Sparse drafts must not be forced through complete LinkML validation or filled
  with placeholder people, places, or parcels.
- A write timeout must not trigger a retry of the write-capable agent; its
  outcome is ambiguous until independently inspected.
- Optimistic concurrency must cover field updates as well as status changes;
  status-only compare-and-set still permits lost updates.
- Full-stack tests must not rely on the developer's existing PostgreSQL flow
  catalogue or persistent Neo4j data.
- The Walking Skeleton exception must not grow into production authorization,
  compensation, idempotency, or a general-purpose Cypher gateway.

## No-Gos

- No LF-20 implementation or request behavior after `complete`.
- No matching, ranking, candidate selection, transporter assignment, outbound
  delivery, acceptance, pickup, delivery, closure, feedback, or cancellation.
- No Telegram, WhatsApp, public API, production identity, or authorization.
- No Guardrail Agent, scheduler, recovery worker, event ledger, compensation,
  or message-level idempotency.
- No FastAPI facade, Python repository abstraction, duplicate flow
  orchestration, or forced empty architecture layers.
- No `OperationalConversationBinding` addition to LinkML and no manual edits
  under `model/generated/`.
- No literal credentials in flows, examples, tests, logs, reports, or Git.
- No hard pull-request dependency on a live model or LLM judge.

## Golden Thread

- Phase boundary and flow topology:
  [Phase 1 blueprint architecture overview](../../../architecture/agentic-system-blueprint-phase-1.md#2-architecture-overview)
- Stable architectural commitments and exception scope:
  [incremental strategy](../../../architecture/incremental-system-development-strategy.md#3-stable-architectural-commitments)
- Business behavior:
  [UC-1 Register a parcel request](../../../architecture/use-cases/blue-user-goal.md#uc-1--register-a-parcel-request)
- Control, persistence, and reliability constraints:
  [non-functional requirements catalogue](../../../architecture/non-functional-requirements.md#4-non-functional-requirements-catalogue)
- Required verification layers:
  [Phase 1 test layers](../../../architecture/verification-testing-and-evaluation-strategy.md#5-phase-1-test-layers)
- Planning acceptance and review checklist:
  [Phase 1 handover](../../../DEV/reports/hulubul-phase-1-implementation-planning-handover.md#18-common-pitfalls-to-avoid)

## Impact

- **Code:** New `src/hulubul/core` and `src/hulubul/request_intake`
  packages, custom LangFlow components, operational schema generator, tests,
  and architecture contracts.
- **Flows:** New LF-00, LF-10, and LF-70 tracked JSON plus manifest and LFX
  environment configuration.
- **Data:** Additive Neo4j operational binding schema and sparse request drafts;
  existing LinkML domain artifacts remain unchanged.
- **API:** Internal clients use LangFlow's authenticated run endpoint. Humans
  provide chat content only; trusted infrastructure manages execution metadata.
- **Infrastructure:** Pin images, add readiness/health behavior, mount tracked
  assets, provide safe environment templates, and rotate the current local
  provider credential.
- **Dependencies:** Add the approved direct pins: Pydantic `2.12.5`, LFX
  `1.10.2`, pytest `8.4.1`, pytest-bdd `8.1.0`, pytest-cov `7.0.0`, httpx
  `0.28.1`, Neo4j driver `5.28.2`, Testcontainers `4.10.0`, import-linter
  `2.3`, Ruff `0.12.5`, mypy `1.17.1`, and tox `4.28.4`. Use Gitleaks plus
  the tracked-file structural scanner for secret detection. The complete
  approved tool classes and runtime pins are defined in
  [`design.md`](design.md#dec-002-use-full-pinned-langflow-with-postgresql) and
  [`design.md`](design.md#dec-017-use-a-layered-verification-pyramid).
- **Delivery:** Change 2, `complete-phase-1-parcel-lifecycle`, depends on this
  change being verified, archived, merged, and synchronized into durable specs.
