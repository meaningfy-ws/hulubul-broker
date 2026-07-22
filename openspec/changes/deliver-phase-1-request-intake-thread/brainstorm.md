# Phase 1 Request Intake Thread Brainstorm

Date: 2026-07-21

This file captures the design exploration and decisions that preceded the
`deliver-phase-1-request-intake-thread` change. It is intentionally a decision
record rather than a structured technical design. The later `proposal.md` and
`design.md` artifacts will shape and organize this material without copying it
verbatim.

## Starting Point

The requested outcome was an implementation-ready plan for Hulubul Phase 1,
the Walking Skeleton. The planning process had to:

- use the repository's OpenSpec and Superpowers bridge workflow;
- resolve how LangFlow should be developed, versioned, deployed, and tested;
- decide whether Phase 1 should be one change or several changes;
- preserve the existing architecture's Phase 1 scope and no-gos;
- pass clarity gates before implementation;
- produce technical artifacts suitable for implementation agents;
- stop before implementation unless the developer explicitly authorized it.

The repository was in an early scaffolding state. The LinkML model and local
Neo4j, MCP, LangFlow, and PostgreSQL infrastructure existed, but application
code, tests, CI, and tracked Hulubul LangFlow flows did not.

## Sources Reviewed

The exploration read and reconciled the following repository sources:

1. [Task 03 inputs](../../../DEV/tasks/task03.md#task-inputs)
2. [Architecture interpretation priorities](../../../architecture/README.md#conflicts--interpretation-priorities)
3. [Phase 1 flow inventory](../../../architecture/agentic-system-blueprint-phase-1.md#3-phase-1-flow-inventory)
4. [Target agent scope](../../../architecture/agentic-system-blueprint.md#1-scope-interpretation)
5. [Non-functional requirements catalogue](../../../architecture/non-functional-requirements.md#4-non-functional-requirements-catalogue)
6. [Planning handover authority](../../../DEV/reports/hulubul-phase-1-implementation-planning-handover.md#1-purpose-and-authority)
7. [Phase 1 test layers](../../../architecture/verification-testing-and-evaluation-strategy.md#5-phase-1-test-layers)
8. [Project scope](../../../architecture/project-statement.md#what-we-are-building)
9. [Stable architectural commitments](../../../architecture/incremental-system-development-strategy.md#3-stable-architectural-commitments)
10. [Use-case catalogue](../../../architecture/use-cases/README.md#catalogue)
11. [UC-1 Register a parcel request](../../../architecture/use-cases/blue-user-goal.md#uc-1--register-a-parcel-request)
12. The explicitly relevant [architecture decisions](../../../architecture/decisions/README.md#architecture-decision-records-draft-v2):
    ADR-001, ADR-005, ADR-006, ADR-011, ADR-015, ADR-016, and ADR-017
13. `infra/docker-compose.yaml`, `infra/README.md`, MCP configuration, Neo4j
    schema and seed Cypher, the Makefile, package configuration, generated
    models, and the empty application source tree
14. The local OpenSpec configuration, superpowers-bridge schema, templates,
    commands, and artifact dependency graph
15. The ignored LangFlow prototype at
    `DEV/langflow-workflows/Simple Custom Agent.json`

The explicitly excluded obsolete framework exploration and deterministic-LLM
research report were not used.

The exploration also consulted official LangFlow 1.10.x documentation:

- Flow DevOps Toolkit: <https://docs.langflow.org/flow-devops-sdk>
- Docker deployment: <https://docs.langflow.org/deployment-docker>
- Containerized applications: <https://docs.langflow.org/develop-application>
- Import and export: <https://docs.langflow.org/concepts-flows-import>
- Custom components: <https://docs.langflow.org/components-custom-components>
- Flow trigger endpoints: <https://docs.langflow.org/api-flows-run>
- API authentication: <https://docs.langflow.org/api-keys-and-authentication>
- PostgreSQL configuration:
  <https://docs.langflow.org/configuration-custom-database>
- LFX runtime behavior:
  <https://github.com/langflow-ai/langflow/blob/main/src/lfx/README.md>

## Initial Findings

The Phase 1 business boundary was already sufficiently defined:

- four physical flows: LF-00 Main Router, LF-10 Request Intake, LF-20 Parcel
  Coordination, and LF-70 Data Access;
- mandatory Neo4j routing-context lookup before specialist routing;
- one active request per LangFlow session;
- minimum request capture, at most one focused clarification at a time, and
  resumption of the same request;
- one configured seeded transporter rather than matching;
- simulated outbound communication and transporter actor messages;
- lifecycle progression through delivery and a non-null closed timestamp;
- PostgreSQL for LangFlow messages, traces, and application state;
- Neo4j as the authoritative business-state store;
- structured contracts and deterministic rendering;
- no production channel, authentication, matching, rejection cascade,
  cancellation, feedback, scheduler, Guardrail Agent, or production recovery.

The main open issues were implementation boundaries and reproducibility rather
than product scope.

The running local stack contained LangFlow/lfx 1.10.2, PostgreSQL 16.14,
Neo4j 5.26.28, and `mcp-neo4j-cypher` 0.6.0. The declared LangFlow image used
the mutable `latest` tag. LangFlow flows lived in PostgreSQL and the only local
flow export was ignored by Git. No tracked flow directory, custom-component
directory, operational schema, API automation credential, test suite, or CI
pipeline existed.

Official LangFlow guidance confirmed that:

- `lfx pull`, `status`, `push`, `validate`, and `export` support a Git-backed
  flow lifecycle;
- normalized exported JSON can be the reviewed source of truth;
- custom components can be mounted into Docker with
  `LANGFLOW_COMPONENTS_PATH`;
- tracked flows can be loaded into a full LangFlow image;
- full LangFlow can persist flows and messages in PostgreSQL;
- standalone `lfx run` and `lfx serve` use a no-op database and do not preserve
  LangFlow messages or application data as the full runtime does;
- the authenticated `/api/v1/run/{flow_id}` endpoint is sufficient to invoke
  flows programmatically.

## Decision Chain

### Q1: Where should Phase 1 enforce lifecycle rules and construct Cypher?

Options considered:

1. Deterministic LF-70: agents propose typed operations while source-controlled
   Python policy validates transitions and constructs allowlisted Cypher.
2. LLM-driven LF-70: follow the Phase 1 blueprint literally, with the LF-70
   agent selecting MCP tools and generating Cypher behind typed validation.
3. Python/FastAPI core: place deterministic services and Neo4j writes behind a
   separate service called by LangFlow.

Developer decision: **LLM-driven LF-70**.

Reasoning and consequences:

- It proves the architecture described by the Phase 1 blueprint.
- LF-70 remains the sole holder of raw MCP tools.
- Domain flows submit typed logical operations rather than raw Cypher.
- Deterministic validation must still surround requests and results.
- Independent Neo4j assertions must verify every important write.
- The choice creates a deliberate tension with NFR-CTL-002 and the target
  deterministic service boundary.

### Q2: Is LLM-driven LF-70 temporary or the target architecture?

Options considered:

1. Explicit non-production Phase 1 exception.
2. Permanent change to the target architecture.
3. Defer the decision and block write implementation.

Developer decision: **temporary Phase 1 exception**.

The exception must be named in the proposal and design. It is limited to the
non-production Walking Skeleton. Phase 2 must replace generic LLM-generated
writes rather than treating this shortcut as the production architecture.
During Phase 1, operation allowlisting, expected-status checks, schema
validation, affected-record checks, and direct graph assertions constrain and
evaluate the exception.

### Q3: How should LangFlow flows be developed?

Options considered:

1. Agent-first hybrid: agents create tracked components and initial flow JSON;
   the developer reviews and tunes flows in the UI; every UI change is pulled,
   normalized, reviewed, and committed.
2. Human UI-first hybrid: the developer creates initial visual flows while
   agents build contracts and tests.
3. Agent-only flow files: agents edit JSON without a required UI review.

Developer decision: **agent-first hybrid**.

Git is authoritative. LangFlow/PostgreSQL holds the deployed runtime copy.
Stable flow IDs and `lfx status` detect drift. The visual editor remains a
debugging and review surface, not an unversioned source of truth.

### Q4: Which LLM-backed tests should block ordinary pull requests?

Options considered:

1. Deterministic hard gates with live-model soft gates.
2. Live-model hard gates on every pull request.
3. No automated live-model evaluation.

Developer decision: **deterministic hard, live soft**.

Contracts, policies, flow validation, fake/recorded-model checks, MCP/Neo4j
assertions, and deterministic integration behavior are hard gates. Live-model
datasets and LLM-as-judge evidence run separately or as non-blocking checks
until their stability and value are demonstrated.

### Q5: How should Phase 1 be split into OpenSpec changes?

Options considered:

| Approach | Benefit | Cost |
| --- | --- | --- |
| One Phase 1 change | One complete acceptance boundary | Too large for one reliable plan, apply, and review cycle |
| Two vertical changes | Each change produces demonstrable behavior with manageable dependencies | Change 2 must wait for Change 1 to establish the baseline |
| Three staged changes | Smallest units | Creates an infrastructure-only first change and more spec synchronization overhead |

Developer decision: **two sequential vertical changes**.

Change 1 is `deliver-phase-1-request-intake-thread` and proves intake,
clarification, persisted-state routing, and resumption with the necessary
runtime foundation. Change 2 is `complete-phase-1-parcel-lifecycle` and adds
coordination from the completed request through closure.

OpenSpec has no first-class cross-change program dependency. The Phase 1
blueprint and roadmap remain the program authority. Change 2 is materialized
only after Change 1 is implemented, verified, archived, merged, and synced into
the durable specification baseline.

### Q6: Should this planning supertask also implement Change 1?

Options considered:

1. Plan Phase 1 at roadmap level, fully materialize and gate Change 1, then
   stop before implementation.
2. Fully materialize both change plans before implementing either one.
3. Continue immediately into implementation after planning.

Developer decision: **fully plan and gate Change 1, then stop**.

Detailed planning of Change 2 before Change 1 exists would create stale file-
level assumptions. The roadmap records Change 2's boundary and dependencies so
that the remaining Phase 1 work stays visible.

### Q7: Which LangFlow runtime and API boundary should Phase 1 use?

The approved realization is:

- full LangFlow 1.10.2 with PostgreSQL;
- matching LFX tooling for flow validation and synchronization;
- normalized, tracked flow JSON with stable IDs;
- tracked and mounted custom Python components;
- authenticated direct use of `/api/v1/run/{flow_id}`;
- no thin FastAPI facade in Phase 1;
- no standalone LFX runtime for acceptance testing.

Standalone LFX was rejected because its no-op database cannot prove the
required PostgreSQL-backed message persistence and restart/resume behavior.
FastAPI was deferred because it adds no required Phase 1 boundary. It becomes
relevant when channel webhook normalization, trusted actor derivation, public
API versioning, API-key shielding, or a deterministic service boundary is
introduced.

### Q8: What exactly should Change 1 deliver?

The approved thread is:

```text
Chat or API input
  -> LF-00 mandatory persisted-state lookup
  -> LF-10 Request Intake
  -> LF-70 Data Access through MCP
  -> request graph and session binding in Neo4j
  -> typed IntakeResult
  -> deterministic chat rendering
```

Change 1 includes:

- pinned and reproducible LangFlow infrastructure;
- flow-as-code development and drift detection;
- executable operational contracts;
- application-owned `OperationalConversationBinding` in Neo4j, kept outside
  the conceptual LinkML domain model;
- exact Phase 1 graph mapping;
- LF-70 routing, read, create, update, and intake status operations;
- LF-10 one-message and clarification paths;
- LF-00 mandatory context loading and routing;
- independent graph assertions;
- restart and same-request resumption verification.

The thread is accepted when a complete request succeeds in one message and an
incomplete request is completed by a later clarification without creating a
second request.

### Q9: Are all LangFlow tests system-level black-box tests?

The developer asked for clarification before approving the test design.

Clarification: **no**. The agreed test pyramid is:

| Level | Subject | Style |
| --- | --- | --- |
| Static flow checks | Export structure, compatibility, variables, secrets, drift | `lfx validate` and deterministic file checks |
| Python unit tests | Contracts, policies, rendering, custom-component logic | Isolated white-box pytest tests |
| Component adapter tests | LangFlow type conversion and error mapping | Narrow tests around custom component classes |
| Single-flow integration | LF-70 or LF-10 at its invocation boundary | Deployed-flow black-box tests |
| Multi-flow integration | LF-00 routing into a specialist and LF-70 | Black-box behavior plus trace assertions |
| System tests | User-visible intake and restart/resume | Full-stack LF-00 API tests with direct graph assertions |
| Agent evaluation | Extraction, routing, and operation behavior | Recorded/fake hard gate and live-model soft gate |

`lfx run` may provide a fast file-level smoke test but cannot replace deployed
integration tests because it does not reproduce PostgreSQL persistence.

Developer decision: **approve this test pyramid**.

### Q10: Must every test originate from Gherkin?

Clarification: **no**. Gherkin is the acceptance spine, not the source of every
low-level test.

The design-phase features express business-observable behavior:

- complete request intake;
- clarification and completion of the same request;
- conversation/request continuity across interactions and restart;
- in Change 2, lifecycle coordination through closure.

Gherkin must not mention JSON parsing, Pydantic internals, Cypher, MCP tool
visibility, API paths, or LFX normalization. Those concerns receive focused
pytest tests. Step definitions are implementation work and invoke the deployed
flow boundary while independently checking persisted outcomes.

Developer decision: **approve Gherkin as the acceptance spine**.

### Q11: Should Clean Architecture apply to the Python-supported portion?

Options considered:

1. Proportional functional core and LangFlow shell.
2. Force all four layers to exist immediately, even if some are empty.
3. Keep all logic embedded in standalone custom component files.

Developer decision: **apply Clean Architecture proportionally**.

The intended shape is:

- pure `models` for operational contracts, typed errors, enums, completeness,
  and transition policy;
- `services` only where deterministic coordination genuinely exists outside
  the visual flows;
- `adapters` only for Python-owned I/O, without wrapping stock MCP merely to
  satisfy a folder convention;
- thin LangFlow custom-component `entrypoints` that translate LangFlow values
  to and from the clean core;
- import-linter boundaries and layer-specific tests;
- no duplicate Python implementation of LF-00, LF-10, or LF-70 orchestration;
- no empty layers, repository abstraction, or FastAPI service added for
  architectural appearance.

### Q12: What retry policy should Phase 1 use?

The initial proposal was one structured-output repair attempt and no automatic
write retries. The developer requested safe retries.

Options considered:

1. Retry transient MCP reads and model calls once; never retry writes after
   dispatch.
2. Retry reads only.
3. Add idempotency semantics so selected writes can retry.

Developer decision: **retry reads and model calls once**.

The model retry also covers one malformed structured-output repair attempt.
Retries use a bounded delay. A dispatched write is never automatically retried
because Phase 1 has no idempotency key or compensation mechanism and cannot
distinguish a failed write from an ambiguous response after mutation.

### Q13: What artifacts and gates should planning produce?

The approved planning set is:

- a Phase 1 roadmap report under `DEV/reports/`;
- the superpowers-bridge artifacts for Change 1;
- design-phase Gherkin features for intake and resumption;
- a lightweight proposal readiness check;
- a preliminary clarity pass before projecting Gherkin;
- a full 13-item clarity gate over design, specs, tasks, plan, and features;
- an AI-coder understandability score of at least 9/10;
- OpenSpec structural validation;
- a stop for developer review before apply.

The bridge artifact sequence is:

```text
brainstorm
  -> proposal and design
  -> capability specs
  -> tasks
  -> plan
  -> apply
  -> verify
  -> retrospective
  -> archive
```

Developer decision: **approve this artifact and gate sequence**.

### Q14: Which model is the live evaluation baseline?

Options considered:

1. Retain the currently exercised NEAR/DeepSeek model.
2. Standardize on an OpenAI model.
3. Specify capabilities only and defer the concrete model.

Developer decision: **use the current NEAR/DeepSeek baseline**,
`global/nearai/deepseek-v4-flash`, while keeping provider and model selection
configurable. Soft evaluation evidence must record the concrete model,
settings, date, and flow version used.

## Post-Design Review Clarifications

After `design.md` was written, the developer reviewed several phrases and
requested clarification. The review produced the following refinements.

### Q15: Does the human user provide message, correlation, or session IDs?

No. The human supplies message content only. The LangFlow envelope component
generates message and correlation UUIDs internally. Trusted invocation
infrastructure supplies session continuity: the API/test harness selects a
session and Playground uses its chat session. A future channel adapter maps
chat identity to the session. These identifiers are never parsed from user
prose or requested conversationally.

### Q16: What is a sparse-draft-safe request projection?

It is a read model of persisted request state that explicitly permits fields
or related nodes to be absent while the request is `new` or
`needsClarification`. It does not mean a projection with missing data removed
or hidden. It exposes absence explicitly so completeness policy can identify
the exact missing fields.

### Q17: Are the five operations generic agent tools?

They are the shared application-level command vocabulary behind LF-70, not
end-user actions and not raw database tools. Caller permissions are distinct:
LF-00 may only request routing context; LF-10 may create/read/update a request
and request status transitions; LF-70 alone maps those commands to raw MCP
schema/read/write tools. Domain flows invoke one typed LF-70 Run Flow boundary.

### Q18: Is there a Python system entrypoint?

The system entrypoint remains LangFlow's LF-00 run endpoint supplied by the
LangFlow image. Python `entrypoints` are custom component plugin classes loaded
inside LangFlow. They adapt LangFlow values to the clean core; they do not start
a separate HTTP server. Tests and future channel adapters call LangFlow
directly until a public facade has a concrete responsibility.

### Q19: Is validation deferred until the request is complete?

No. Every supplied fact is validated on the interaction that captures it.
Single-field and available cross-field rules run immediately; invalid facts are
rejected or clarified before being accepted as persisted data. Only the final
aggregate completeness check waits until all mandatory facts are available.
Change 1 cannot verify whether a free-text location exists in the real world;
a later geocoding/address capability must validate a location at capture time,
not after all unrelated fields have arrived.

### Q20: Do separate writes create race conditions?

Status-only compare-and-set was insufficient for concurrent field updates, so
the design was strengthened. Request-plus-binding creation is atomic and
`sessionId` is unique. Every subsequent mutation compares the previously read
`updated` timestamp, while transitions also compare status. One concurrent
writer wins; the other receives a typed conflict and reloads state. Writes are
not automatically replayed. Message-level idempotency remains outside Change 1.

### Q21: What do the credential, FastAPI, and migration statements mean?

- The ignored credential is not known to be committed. Rotation is precautionary
  because Git ignore does not protect local values from processes, logs,
  backups, screenshots, or prior accidental sharing.
- Without FastAPI, internal clients use LangFlow's native run request/response
  envelope. Human chat users do not see it. A later facade can hide the
  framework contract when channels or external consumers exist.
- The OpenSpec `Migration Plan` describes moving the current repository/runtime
  into Change 1 and rolling it back safely. It is not the future Phase 1 to
  Phase 2 transition.

### Q22: What text-length boundary applies to captured intake facts?

LinkML does not declare text-length limits. The developer approved one temporary
operational boundary for Change 1: after surrounding whitespace is stripped,
Receiver name, pickup location, drop-off location, parcel declared content, and
an optional preferred period each contain 1-4,000 characters. The 4,000-character
maximum matches the existing inbound-message cap and leaves headroom below
Telegram's 4,096-character text-message limit. Later channel-specific contracts
may introduce tighter limits through a separate change.

### Q23: Which missing fact is clarified first?

The developer approved this fixed priority: Receiver identity, pickup location,
drop-off location, then parcel declared content. Intake still reports the full
missing set but asks only for the first missing field in that order. An invalid
fact supplied in the current interaction takes priority so it is corrected
immediately.

### Q24: Which error represents duplicate graph continuity?

The developer approved `GRAPH_CONTEXT_INCONSISTENT` for duplicate bindings,
duplicate active-request relationships, duplicate active targets, and other
invalid graph cardinality. `BINDING_REQUEST_MISMATCH` remains specific to a
binding whose active request cannot be resolved.

### Q25: How long is sanitized CI evidence retained?

The developer approved 30 days for sanitized Change 1 test and evaluation
artifacts. Native traces, message text, prompts, credentials, unrestricted
Cypher, and raw model or MCP content are never uploaded.

### Q26: How is the clarification judge calibrated?

The developer approved five live judge runs. The soft baseline requires a
median total of at least 8/10 and a non-zero score for every criterion in every
run. The workflow remains manual and non-blocking.

### Q27: Which current runtime image digests are pinned?

The developer approved the observed PostgreSQL and Neo4j images required by
DEC-002: `postgres:16-trixie@sha256:33f923b05f64ca54ac4401c01126a6b92afe839a0aa0a52bc5aeb5cc958e5f20`
and `neo4j:5.26-community@sha256:362542416de6c09a971484d1893878016cc3b5cdec166e54b1c824a220ecd6b9`.

### Q28: How are LangFlow native traces handled without complete redaction?

LangFlow 1.10.2 native traces may persist prompt, message, model, and tool
payloads without complete built-in redaction. The developer approved native
tracing only for synthetic simulated-Sender data in disposable acceptance and
local Change 1 environments. Automated assertions project allowlisted metadata
in memory, raw traces are never uploaded, and real party or client data remains
outside this Walking Skeleton.

### Q29: Which clarity corrections supersede provisional implementation wording?

The post-planning clarity review found that several implementation details had
been left implicit or had drifted between artifacts. The developer approved the
following corrections without changing the shaped scope or earlier product
decisions:

- LF-00 and LF-10 receive strict `RouterInput` and `IntakeInput` wrappers whose
  trusted envelope and routing context are assembled on deterministic boundary
  edges, not supplied by a model.
- Direct LangFlow API invocation obtains the simulated actor from named request
  variables; Playground obtains it from ignored environment configuration. No
  FastAPI or channel adapter is introduced.
- Session IDs accept only a bare UUID or canonical `p1-<UUID>`, normalize to
  lowercase canonical form, and must agree between the LangFlow message and
  graph context. Omitted sessions do not fall back to a flow ID.
- Contract validation precedes capability authorization. A known, valid
  operation outside a caller's capability is the only case that returns
  `OPERATION_NOT_ALLOWED`.
- Neo4j transaction time owns creation timestamps; updates compare timestamp
  and status; preferred period is additive-only; zero-row writes are classified
  by a non-mutating authoritative read.
- Raw persisted status is adapted before `RoutingContext`; closed state has
  precedence, all recognized statuses have an exhaustive route, and unknown raw
  text is never exposed.
- Gherkin projects actor-observable use-case, capability, and NFR acceptance.
  Internal engineering checks remain pytest-only and still require evidence
  mapping.

This section is a historical correction record. The capability specs are
normative for behavior and `design.md` is authoritative for technical
realization.

## Accepted Failure Behavior

The following behavior was accepted during design review:

| Condition | Phase 1 behavior |
| --- | --- |
| No conversation binding | Route to intake; this is normal, not an error |
| Binding/request mismatch | Return a typed routing failure and do not guess or mutate |
| Duplicate binding or active-request cardinality | Return `GRAPH_CONTEXT_INCONSISTENT` and do not guess or mutate |
| Unknown status | Return a typed unsupported-context failure and do not mutate |
| `rejected` or `cancelled` status | Return a typed unsupported-Phase-1 failure and do not mutate |
| Malformed agent result | Make one model repair attempt, then return a typed failure |
| Transient model failure | Retry once with a bounded delay, then fail in a controlled form |
| Transient MCP read failure | Retry once with a bounded delay, then fail in a controlled form |
| MCP write timeout after dispatch | Do not retry automatically; report an ambiguous write failure |
| Invalid expected status | Reject the transition and leave the graph unchanged |
| Unexpected affected-record count | Stop progression, report failure, and require independent graph verification |
| Closed request | Return an informational result and perform no mutation |

Production compensation, broad retry policies, recovery scheduling, and an
audit/event ledger remain outside Change 1.

## Candidate Capability Boundaries

The proposal was expected to shape the following candidate capabilities. The
proposal remains authoritative for their final names and boundaries:

1. `phase1-flow-runtime`
2. `operational-contract-validation`
3. `delivery-request-intake`
4. `domain-state-routing`
5. `conversation-request-resumption`

Change 2 is expected to introduce `parcel-lifecycle-coordination` and
`simulated-transporter-communication`, then modify relevant routing,
resumption, and contract capabilities against the archived Change 1 baseline.

## Planning Details Still To Derive

These items are not unresolved product or architecture forks. They are
concrete design work that `design.md` must derive from the approved decisions
and repository sources before `tasks.md` and `plan.md` can pass the clarity
gate:

- exact Neo4j labels, relationships, properties, constraints, and atomic write
  boundaries based on LinkML outputs and existing seed conventions;
- exact operational contract fields, schema versions, nullability, error
  codes, and additional-property policy;
- exact source and test paths for the proportional Python architecture;
- exact LangFlow component inventory, stable flow IDs, input/output component
  IDs, and environment variable names;
- exact API test actor envelope and session/correlation ID conventions;
- exact one-retry delay and transient-error classification;
- exact hard-gate test commands and clean-environment startup sequence;
- exact flow normalization and secret-scanning rules;
- exact 20-case evaluation dataset and pass criteria.

No implementation may silently choose these details. They must be made
explicit in the design, specification, and implementation plan.

## Convergence Check

The verbal brainstorming reached the repository's five promotion criteria:

1. Scope is locked to the first vertical Phase 1 intake thread and its required
   foundation.
2. Major design forks are resolved, including LF-70, runtime, FastAPI, flow
   ownership, Clean Architecture, retries, test gates, and change slicing.
3. Cross-system dependencies are mapped: full LangFlow, PostgreSQL, MCP, and
   Neo4j are available; model behavior is mockable for hard gates and the
   existing NEAR/DeepSeek model is the soft baseline.
4. Acceptance criteria are stateable and trace to UC-1, the Phase 1 blueprint,
   NFRs, and the verification strategy.
5. The final rounds approved process, runtime, boundaries, testing,
   architecture, failure behavior, artifacts, and model baseline without
   introducing new alternatives.

The approved next step was to shape the Change 1 proposal and design, derive
capability specifications and Gherkin, produce tasks and a TDD-level plan, run
the clarity gates, and stop before implementation for developer review.
