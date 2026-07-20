---
title: "Hulubul V1 — Non-Functional Requirements"
version: "1.0"
status: "V1 baseline"
date: "2026-07-20"
---

# Hulubul V1 — Non-Functional Requirements

## 1. Basis documents and interpretation

This specification is based on:

1. **Hulubul V1 — Project Statement**
2. **Architecture Decision Records — Draft v2**
3. **Deterministic Control Patterns for LLM Agent Systems — research report**
4. **Hulubul Agentic System Blueprint v0.3**
5. **Subsequent scope decisions confirmed during NFR review**

The documents do not have equal authority:

1. Explicitly confirmed scope decisions in this document take precedence.
2. The Project Statement defines the product goal and V1 validation intent.
3. The System Blueprint defines the current target decomposition, component boundaries, state model, and incremental implementation phases.
4. Accepted ADRs are architectural constraints. Proposed ADRs are used where they align with the confirmed V1 direction and the System Blueprint.
5. The research report is non-binding. It informs control, safety, reliability, and testability requirements, but its technology recommendations are not automatically requirements.

### 1.1 Confirmed scope resolutions

The following interpretations replace contradictory or ambiguous statements in the basis documents:

- **V1 is autonomous.** A successful parcel intermediation path must not depend on a human operator.
- **WhatsApp is supported in V1 production use.** Telegram may be used in development and testing through the same channel abstraction.
- **The exact Admin role and intervention boundary are deferred.** The system must nevertheless preserve and expose unrecoverable exceptions for controlled handling.
- **Receiver identity and profile are required before dispatch**, in accordance with ADR-011. A live WhatsApp connection to the Receiver is optional.
- Advanced target-architecture capabilities are **not automatically V1 scope** merely because they appear in an ADR, research option, or target blueprint. They are listed as deferred unless required to make the confirmed V1 flow safe and operational.

### 1.2 V1 flow covered by this specification

The NFR baseline applies to the autonomous implementation of:

- UC-1 — Register a parcel request
- UC-3 — Match and choose a transporter
- UC-4 — Forward request to a transporter
- UC-5 — Respond to a transport request
- UC-6 — Provide clarification or missing information
- UC-7 — Plan pick-up and hand over the parcel
- UC-8 — Coordinate and confirm delivery
- UC-9 — Close request and collect feedback

The NFRs also cover the internal candidate cascade required after rejection or timeout.

---

## 2. Priority and implementation-phase definitions

### 2.1 Priority

| Priority | Meaning |
|---|---|
| **Mandatory** | Must be satisfied before the V1 Field Pilot or any production-like use with real participants, unless an explicit temporary exception is recorded. |
| **Desirable** | Should be implemented in V1 when proportionate. It may be deferred only with a documented risk assessment and owner. |
| **Deferred** | Not required for V1. The V1 architecture should avoid unnecessarily preventing later implementation. |

### 2.2 Blueprint phase abbreviations

| Abbreviation | Blueprint phase |
|---|---|
| **WS** | Walking Skeleton |
| **WB** | Working Brokerage |
| **FP** | Field Pilot |
| **HS** | Hardened Service |

A non-production Walking Skeleton may temporarily omit controls that are mandatory for V1, such as the final WhatsApp gateway or full guardrails. Such exceptions must be isolated to development, clearly documented, and removed by the phase shown in the **Required by** column.

---

## 3. Principal V1 quality goals

The V1 system must:

1. complete the supported brokerage flow autonomously;
2. preserve authoritative business state independently of chat history;
3. resume safely after waits, retries, duplicate messages, and process restarts;
4. isolate each participant and request from unrelated data and actions;
5. treat LLM output as a proposal rather than an authority;
6. make all consequential actions deterministic, validated, scoped, and auditable;
7. provide a production-capable WhatsApp interaction path without coupling the domain to WhatsApp-specific behaviour;
8. remain simple enough to support V1 learning rather than prematurely implementing the full target architecture.

---

# 4. Non-functional requirements catalogue

## 4.1 Autonomy, durability, and reliability

| ID | Priority | Requirement | Acceptance criteria | Required by |
|---|---|---|---|---|
| **NFR-AUT-001** | Mandatory | **Autonomous success paths.** Every supported happy path and expected negative path, including rejection, timeout, clarification, candidate fallback, delivery confirmation, and closure, must proceed without routine human operation. | End-to-end scenario tests complete UC-1 and UC-3–UC-9 without an Admin action. Human intervention is used only for an explicitly classified unrecoverable exception. | WB |
| **NFR-REL-001** | Mandatory | **Authoritative durable process state.** Parcel Request state, active candidate, clarification context, wait conditions, and closure data must survive agent, workflow, and application restarts. | Restart tests at each waiting stage resume the same request without data loss or recreation. Chat history alone is insufficient to restore the process. | WS |
| **NFR-REL-002** | Mandatory | **Deterministic resumption.** After an interruption, the system must derive the next permissible action from authoritative state and pending operational context. | Replaying the same persisted state produces the same permitted next transition, independently of conversational wording. | WB |
| **NFR-REL-003** | Mandatory | **Idempotent side effects.** Every externally triggered or retryable mutation must carry an idempotency key and must be safe to replay. | Duplicate inbound messages, provider callbacks, scheduled triggers, and agent retries do not create duplicate requests, dispatches, responses, reminders, or state transitions. | WB |
| **NFR-REL-004** | Mandatory | **Automated waits and recovery.** Waiting states must have persisted deadlines and a deterministic policy for reminder, timeout, cascade, closure, or exception creation. | Due wait conditions are processed after restart; reminder counts and final actions are not reset; candidate cascade uses the persisted candidate queue. | WB |
| **NFR-REL-005** | Mandatory | **Safe message-delivery semantics.** A request must enter `waitingResponse` only after the configured trusted delivery condition is met. | Dispatch initiation, provider acceptance, delivery confirmation, and failure are recorded separately. A failed send cannot be treated as a delivered request. | FP |
| **NFR-REL-006** | Mandatory | **Failure containment.** Failure of one request, agent flow, model call, or outbound message must not corrupt or block unrelated requests. | Fault-injection tests show that another participant's active requests continue to operate and retain correct state. | FP |
| **NFR-REL-007** | Desirable | **Graceful temporary degradation.** When a non-critical AI or external dependency is temporarily unavailable, the system should preserve the request and provide a safe acknowledgement rather than losing the interaction. | Recoverable failures create a persisted retry or exception condition and a user-appropriate acknowledgement. | FP |

## 4.2 Process integrity and deterministic control

| ID | Priority | Requirement | Acceptance criteria | Required by |
|---|---|---|---|---|
| **NFR-CTL-001** | Mandatory | **Authoritative lifecycle enforcement.** Request statuses may change only through defined domain events and permitted source-state transitions. | Automated tests reject every unsupported transition, including direct jumps such as `complete → delivered`. | WS |
| **NFR-CTL-002** | Mandatory | **LLM as proposer, not executor.** Natural-language agents may propose logical operations, but may not directly perform database writes, invent statuses, or bypass transition rules. | All side effects are executed by deterministic services or guarded operation flows after validation. | WS |
| **NFR-CTL-003** | Mandatory | **Action-gate sequence.** Consequential actions must pass, in order: trusted actor resolution, operation allowlisting, schema validation, authorization, expected-state validation, idempotency check, execution, and audit recording. | Integration tests demonstrate denial at each gate and prove that later gates or execution are not reached after denial. | WB |
| **NFR-CTL-004** | Mandatory | **Deterministic hard checks around any LLM guardrail.** An LLM Guardrail Agent may assist with semantic policy, but must not be the sole security or correctness boundary. | Operation names, request scope, expected status, maximum affected records, parameterization, delete prohibition, and idempotency are enforced without relying on model judgment. | WB |
| **NFR-CTL-005** | Mandatory | **No hard deletes in normal operation.** Requests and business history must use closure, cancellation, archival, invalidation, or soft-delete semantics. | Production operation tools expose no unrestricted `DELETE` or `DETACH DELETE`; any exceptional destructive maintenance procedure is separately authorized and audited. | WB |
| **NFR-CTL-006** | Mandatory | **Receiver completeness rule.** A request cannot be dispatched until Receiver identity/profile and destination are present and validated according to the V1 minimum-data rule. | Dispatch is rejected when Receiver requirements are incomplete. A live Receiver channel is not required unless the flow specifically needs it. | WB |

## 4.3 Security, authorization, and privacy

| ID | Priority | Requirement | Acceptance criteria | Required by |
|---|---|---|---|---|
| **NFR-SEC-001** | Mandatory | **Trusted channel identity mapping.** The actor identity used for authorization must be derived from trusted gateway metadata, not from claims in message text or agent output. | Attempts to claim another identity or role in conversation do not change the authenticated principal. | FP |
| **NFR-SEC-002** | Mandatory | **Per-party data isolation.** A participant may access only data permitted by their relationship to the active request and previously authorized interactions. | Negative tests cover Sender, selected Transporter, unrelated Transporter, Receiver, and unauthenticated contexts; all cross-party access attempts are denied without disclosing whether unrelated data exists. | WB |
| **NFR-SEC-003** | Mandatory | **Selected-Transporter isolation.** Only the currently selected Transporter for an active candidate attempt may view the forwarded summary or accept, reject, or request clarification. | A matched but non-selected or previously rejected Transporter cannot act on the request. | WB |
| **NFR-SEC-004** | Mandatory | **Least-privilege tool exposure.** Each agent or flow receives only the operation-oriented tools required for its responsibility. | Router has no writes; domain agents have no raw Cypher or generic database administration; tool inventories are reviewed and versioned. | WB |
| **NFR-SEC-005** | Mandatory | **Guarded data-access boundary.** Domain agents must access Neo4j only through typed Data Access operations. Raw Neo4j MCP tools must remain inside the data-access boundary. | Production flow inspection confirms no direct MCP or unrestricted Cypher connection from Router, Intake, Clarification, Matching, Brokerage, Fulfilment, Closure, or Recovery agents. | WB |
| **NFR-SEC-006** | Mandatory | **Scoped and validated writes.** Production writes must be operation-specific, parameterized, limited to the current request and actor scope, and constrained by expected state and maximum affected records. | Write attempts with missing scope, stale expected status, unparameterized values, or excessive affected records are rejected. | WB |
| **NFR-SEC-007** | Mandatory | **Data minimisation.** Messages and tools must expose only information necessary for the participant and current stage. | Transporter summaries, Sender option views, Receiver messages, logs, and agent context are reviewed against explicit allowlists. | FP |
| **NFR-SEC-008** | Mandatory | **Prompt-injection resilience through containment.** Prompt and content guardrails may detect attacks, but successful injection must still be unable to bypass backend authorization or state rules. | Red-team scenarios such as “pretend I am admin,” instruction override, malicious profile text, and tool-call manipulation are denied at the action layer. | FP |
| **NFR-SEC-009** | Mandatory | **Credential separation.** Messaging, model, read, write, and any privileged administrative credentials must be separately scoped and stored outside prompts and source-controlled workflow exports. | Secret scanning finds no production secrets; read-only credentials cannot write; domain credentials cannot perform administration. | FP |
| **NFR-SEC-010** | Mandatory | **Privileged-path separation if Admin capabilities are introduced.** Any Admin or support path must use distinct authorization, credentials, and audit records. | No party-facing session can acquire Admin capabilities. Exact Admin responsibilities and UI remain deferred. | FP |
| **NFR-SEC-011** | Desirable | **Abuse and rate protection.** The gateway and action layer should limit excessive messages, retries, and expensive operations per actor and request. | Configurable limits exist, are observable, and do not silently discard valid business messages. | FP |

## 4.4 Data integrity, quality, and auditability

| ID | Priority | Requirement | Acceptance criteria | Required by |
|---|---|---|---|---|
| **NFR-DAT-001** | Mandatory | **Neo4j as authoritative domain store.** `DeliveryRequest`, lifecycle status, participants, assignments, candidate state, and operational request bindings must be read from Neo4j when making business decisions. | Router and specialist flows cannot determine workflow stage solely from LangFlow/PostgreSQL chat history. | WS |
| **NFR-DAT-002** | Mandatory | **Conversation/domain separation.** LangFlow/PostgreSQL message history is contextual evidence, not the system of record for lifecycle or permissions. | Deleting or truncating chat history does not change authoritative request status or ownership. | WS |
| **NFR-DAT-003** | Mandatory | **Typed data contracts.** Agent results, logical operations, clarification cases, matching results, wait conditions, and data-access results must conform to versioned schemas. | Invalid or additional prohibited fields are rejected before side effects. Schema versions are recorded in traces or audit events. | WS |
| **NFR-DAT-004** | Mandatory | **Atomic validated mutations.** Multi-node or multi-relationship domain changes must occur transactionally after data-shape and business validation. | Fault injection during a write leaves either the complete valid change or no change; no partial graph state remains. | WB |
| **NFR-DAT-005** | Mandatory | **Optimistic concurrency or equivalent stale-state protection.** Mutations must confirm the expected current state or version. | Concurrent or late responses cannot overwrite a newer accepted, rejected, cancelled, delivered, or closed outcome. | WB |
| **NFR-DAT-006** | Mandatory | **Persistent candidate queue.** Matching must produce a persisted, ordered candidate queue reusable by Brokerage without rerunning or silently reordering matching after each rejection. | Restart and rejection tests continue from the correct next candidate and preserve prior attempt results. | WB |
| **NFR-DAT-007** | Mandatory | **Typed clarification context.** Intake clarification and Transporter clarification must be distinguishable and must preserve their correct resume owner and resume status. | Resolving a Transporter question returns to `waitingResponse`; it does not restart intake or matching. | WB |
| **NFR-DAT-008** | Mandatory | **Complete audit trail.** Every material read, write, policy decision, transition, dispatch, callback, reminder, exception, and privileged correction must be attributable and timestamped. | Audit records contain correlation ID, request ID, actor, role, calling agent/flow, operation/event, policy decision, previous and resulting state, result, and configuration/model/workflow version where relevant. | WB |
| **NFR-DAT-009** | Mandatory | **Audit immutability and privacy.** Audit records must be append-oriented and protected from ordinary business writes, while avoiding unnecessary message content and sensitive data. | Domain operation tools cannot alter prior audit events; logs use identifiers, hashes, reason codes, or redacted summaries where full content is unnecessary. | FP |
| **NFR-DAT-010** | Desirable | **Basic duplicate prevention.** V1 should detect obvious duplicate profiles or Contact Points before creating another canonical entity. | Exact-identifier duplicates are prevented or linked for review. Autonomous probabilistic merging is not required. | FP |

## 4.5 Conversation, routing, and session isolation

| ID | Priority | Requirement | Acceptance criteria | Required by |
|---|---|---|---|---|
| **NFR-CON-001** | Mandatory | **Explicit session-to-request binding.** Each active conversation session must be deterministically associated with its active request or require disambiguation. | A message cannot be applied to an arbitrary “most recent” request when multiple candidates exist. | WS |
| **NFR-CON-002** | Mandatory | **Authoritative pre-routing context.** Before Router classification, the system must resolve actor identity, reply reference where available, session/request binding, request status, closure state, assignment, and pending clarification context. | Router receives the documented routing-context schema on every inbound business message. | WS |
| **NFR-CON-003** | Mandatory | **Concurrent-request isolation.** A participant may have multiple open requests without data, reminders, replies, or state transitions crossing between them. | Scenario tests interleave two requests in one chat and verify correct routing or explicit disambiguation. | FP |
| **NFR-CON-004** | Mandatory | **Ambiguity handling.** When the active request, intended action, actor role, or referenced message cannot be resolved safely, the system must ask a focused clarification rather than guess. | Ambiguous short replies such as “yes,” “tomorrow,” or “accept” do not cause a side effect until context is resolved. | WB |
| **NFR-CON-005** | Mandatory | **Bounded conversational context.** Agents must receive only the history and domain facts needed for the current task and actor. | Context construction tests prove that unrelated requests and other participants' private messages are excluded. | FP |
| **NFR-CON-006** | Desirable | **Conversation continuity after deployment or model change.** Existing active requests should continue without requiring the user to restate already persisted facts. | A compatible workflow/model rollout can resume active sessions from domain and operational state. | FP |

## 4.6 Channel portability and WhatsApp support

| ID | Priority | Requirement | Acceptance criteria | Required by |
|---|---|---|---|---|
| **NFR-CHN-001** | Mandatory | **Channel abstraction.** Domain, agent, and lifecycle logic must use a provider-neutral messaging interface. | No Telegram or WhatsApp provider identifiers or payload structures appear in domain rules or state-transition logic. | WS |
| **NFR-CHN-002** | Mandatory | **WhatsApp production capability.** V1 must support inbound and outbound WhatsApp interactions required by UC-1 and UC-3–UC-9. | End-to-end tests through the production-intended WhatsApp adapter cover identity mapping, ordinary messages, reply correlation where supported, outbound dispatch, delivery failure, and callbacks used by the flow. | FP |
| **NFR-CHN-003** | Mandatory | **Telegram development parity.** Telegram may be used in development and testing, but must satisfy the same provider-neutral contract. | Contract tests run against Telegram and WhatsApp adapters; documented provider differences do not change domain outcomes. | FP |
| **NFR-CHN-004** | Mandatory | **Provider-specific policy isolation.** Templates, session windows, message size, attachment handling, receipts, retries, and rate limits must be handled in the adapter or gateway. | Provider constraints can change without modifying request lifecycle or agent prompts. | FP |
| **NFR-CHN-005** | Mandatory | **Message correlation.** Inbound replies and delivery callbacks must be correlated to the correct outbound message, request, candidate attempt, and participant whenever provider metadata permits. | Duplicate, delayed, and out-of-order callback tests do not update the wrong attempt or request. | FP |
| **NFR-CHN-006** | Desirable | **Provider substitution.** Adding another chat provider should require a new adapter and contract tests, not a redesign of the domain or agents. | A documented adapter interface and provider conformance suite exist. | FP |

## 4.7 Performance, availability, backup, and recovery targets

The following numeric values are **proposed V1 targets**. They should be validated against expected pilot size, provider limits, model latency, and infrastructure budget before the Field Pilot.

| ID | Priority | Requirement | Acceptance criteria | Required by |
|---|---|---|---|---|
| **NFR-PERF-001** | Mandatory | **Inbound acknowledgement latency.** The user must receive an acknowledgement or final response within **5 seconds at p95** when the channel permits it. | Measured at the gateway under expected pilot load. Long model/tool work may continue after acknowledgement. | FP |
| **NFR-PERF-002** | Mandatory | **Interactive response latency.** Operations not waiting on another participant or provider callback should produce the substantive response within **20 seconds at p95** and **60 seconds maximum**, otherwise a recoverable delayed-work state is created. | Load tests exclude intentional waiting periods but include model, policy, data-access, and rendering time. | FP |
| **NFR-PERF-003** | Mandatory | **Internal deterministic operation latency.** Ordinary scoped domain reads and writes should complete within **2 seconds at p95** under expected pilot load. | Measured separately from LLM and external provider latency. | FP |
| **NFR-PERF-004** | Mandatory | **Scheduler timeliness.** At least **95%** of due reminders, timeouts, and recovery actions must start within **5 minutes** of their configured due time. | Scheduler metrics and due-condition replay tests provide evidence. | FP |
| **NFR-AVA-001** | Mandatory | **V1 service availability.** The production V1 service should provide **99.5% monthly availability**, excluding announced maintenance. | Availability is measured at the inbound gateway and critical action API. | FP |
| **NFR-DR-001** | Mandatory | **Backup and restoration.** Authoritative domain and audit data must have automated backups with a proposed **RPO of 15 minutes** and **RTO of 4 hours**. | A documented restore exercise reconstructs active requests, wait conditions, and audit records within the targets. | FP |
| **NFR-CAP-001** | Mandatory | **Pilot capacity and backpressure.** The system must be tested at no less than **2× the expected pilot peak** and must queue or reject overload safely without corrupting state. | Load tests cover inbound messages, concurrent model calls, matching, callbacks, and scheduled recovery. | FP |
| **NFR-CAP-002** | Deferred | Multi-region high availability, active-active deployment, and large-marketplace-scale capacity are not V1 requirements. | — | HS / post-V1 |

## 4.8 Maintainability, configurability, and portability

| ID | Priority | Requirement | Acceptance criteria | Required by |
|---|---|---|---|---|
| **NFR-MNT-001** | Mandatory | **Blueprint-aligned responsibility boundaries.** Routing, intake, clarification, matching, brokerage, fulfilment, closure, recovery, messaging, data access, and guardrails must remain logically separable. | Earlier phases may consolidate flows, but interfaces and responsibilities remain explicit and no component becomes an unrestricted universal agent. | WS |
| **NFR-MNT-002** | Mandatory | **Deterministic logic outside prompts.** Authorization, lifecycle transitions, completeness, matching eligibility, idempotency, timeout policy, and write validation must not exist only as natural-language instructions. | Each rule has executable code, policy, schema, or deterministic workflow branching and automated tests. | WB |
| **NFR-MNT-003** | Mandatory | **Version-controlled low-code artefacts.** LangFlow flows, prompts, schemas, tool definitions, parsers, and configuration must be exportable, versioned, reviewed, and reproducibly deployed. | A clean environment can deploy the recorded version without manual UI reconstruction. | WS |
| **NFR-MNT-004** | Mandatory | **Externalised operational configuration.** Provider selection, reminder timing, timeout, nudge count, candidate cap, matching weights, model settings, and safety limits must be configuration rather than scattered code or prompts. | Configuration changes are validated, auditable, and rollback-capable. | WB |
| **NFR-MNT-005** | Mandatory | **Explicit code-versus-flow rule.** Stateful, security-sensitive, validation-heavy, or deterministic domain logic belongs in code/services; natural-language interpretation, bounded routing, and conversational rendering may remain in LangFlow agents. | Architecture review can identify one authoritative implementation location for every critical rule. | WB |
| **NFR-MNT-006** | Mandatory | **Replaceable provider boundaries.** Business state and rules must not depend on a particular LLM model, WhatsApp library, Telegram library, or raw MCP payload. | Provider adapters and typed application contracts isolate external APIs. | FP |
| **NFR-MNT-007** | Desirable | **Model fallback.** The system should support a configured fallback model for non-security-critical interpretation and response generation. | Fallback activation preserves typed contracts and does not bypass action gates. | FP |
| **NFR-MNT-008** | Desirable | **Operationally simple V1.** New distributed infrastructure components should be introduced only when a demonstrated V1 requirement cannot be met by the existing application, Neo4j, PostgreSQL/LangFlow, scheduler, and gateway stack. | Each additional platform dependency has a documented problem statement and operational owner. | All |

## 4.9 Testability and evaluation

| ID | Priority | Requirement | Acceptance criteria | Required by |
|---|---|---|---|---|
| **NFR-TST-001** | Mandatory | **Critical invariant tests.** Automated tests must cover authorization, state transitions, completeness, idempotency, scoped writes, candidate order, clarification resumption, and closure preconditions. | Every documented invariant has at least one positive and one negative test. | WB |
| **NFR-TST-002** | Mandatory | **End-to-end use-case scenarios.** Automated or repeatable scenario tests must cover UC-1 and UC-3–UC-9, including rejection, no response, clarification, fallback, and unconfirmed delivery. | Each scenario asserts user-visible messages, persisted state, audit events, and absence of unauthorized disclosure. | FP |
| **NFR-TST-003** | Mandatory | **Restart and replay tests.** Tests must restart the process during each long wait and replay duplicate messages and callbacks. | State and external side effects remain correct after replay. | WB |
| **NFR-TST-004** | Mandatory | **Agent regression evaluation.** Changes to prompts, models, routing, or tool descriptions must be evaluated against a versioned corpus of representative conversations. | Release evidence reports routing accuracy, structured-output validity, unsupported-action rate, and scenario success rate. | FP |
| **NFR-TST-005** | Mandatory | **Security and injection tests.** The test suite must include identity spoofing, cross-request access, role escalation, malicious instructions, tool-argument manipulation, oversized results, and prohibited Cypher patterns. | No test reaches an unauthorized side effect or sensitive response. | FP |
| **NFR-TST-006** | Mandatory | **Channel contract tests.** Telegram and WhatsApp adapters must pass the same provider-neutral interaction contract plus provider-specific failure tests. | Contract suite is part of release verification. | FP |
| **NFR-TST-007** | Desirable | **Workflow black-box tests.** Low-code flows should be tested through their exposed endpoints in addition to component-level tests of deterministic services. | Smoke tests run against deployed workflow versions in CI or a release environment. | WB |

## 4.10 Observability and operations

| ID | Priority | Requirement | Acceptance criteria | Required by |
|---|---|---|---|---|
| **NFR-OPS-001** | Mandatory | **End-to-end correlation.** Inbound messages, agent runs, logical operations, data-access calls, provider sends/callbacks, wait conditions, and audit events must share trace or correlation identifiers. | An operator can reconstruct a request's execution path without searching by message text. | WB |
| **NFR-OPS-002** | Mandatory | **Operational metrics.** The system must report active requests by status, stalled waits, reminder and timeout counts, candidate exhaustion, message-delivery failures, policy denials, model/tool latency, error rate, and retry count. | Metrics are available for dashboards and alerting; labels avoid unbounded PII or message content. | FP |
| **NFR-OPS-003** | Mandatory | **Actionable alerting.** Alerts must cover gateway outage, scheduler delay, repeated workflow failure, high delivery-failure rate, audit-write failure, backup failure, and abnormal authorization denials. | Alert tests verify routing to an owned operational channel and include request or trace references. | FP |
| **NFR-OPS-004** | Mandatory | **Unrecoverable-exception preservation.** When autonomous recovery cannot proceed, the system must preserve state, block unsafe continuation, and create a structured exception record. | The record contains reason, affected request, attempted recoveries, last safe state, and permitted resolution options. Exact Admin workflow remains deferred. | WB |
| **NFR-OPS-005** | Mandatory | **Safe deployment and rollback.** Workflow, prompt, policy, schema, and service releases must be identifiable and rollback-capable without corrupting active requests. | Deployment and rollback exercises preserve or migrate active state; incompatible schema changes are blocked. | FP |
| **NFR-OPS-006** | Desirable | **Inspection interface.** Operators should have a read-oriented view of request state, waits, recent decisions, and failures without direct database access. | The exact implementation may be logs, dashboards, a support view, or an Admin interface. | FP |

## 4.11 AI-specific quality and matching behaviour

| ID | Priority | Requirement | Acceptance criteria | Required by |
|---|---|---|---|---|
| **NFR-AI-001** | Mandatory | **Structured agent outputs.** Every action-capable agent flow must produce an enforced result schema that is deterministically rendered or executed. | Free-form text cannot independently trigger a write or transition; malformed output is rejected or safely retried. | WS |
| **NFR-AI-002** | Mandatory | **No fabricated domain facts.** Agents must not invent request status, participant identity, candidate availability, delivery confirmation, or database results. | User-visible factual statements are derived from tool results or explicitly framed as a request for information. | WB |
| **NFR-AI-003** | Mandatory | **Safe uncertainty handling.** Low confidence or conflicting context must result in clarification, denial, retry, or exception creation rather than an unsafe guess. | Evaluation scenarios measure unsupported actions and ambiguity handling. | WB |
| **NFR-AI-004** | Mandatory | **Deterministic matching core.** Eligibility, ranking inputs, candidate cap, and candidate ordering must be computed outside the LLM prompt. | Matching fixtures produce repeatable results for the same versioned inputs and configuration. | WB |
| **NFR-AI-005** | Mandatory | **Explainable recommendations.** Presented transporter options and persisted match results must carry stable reason codes and ranking/configuration version. | The Sender-facing explanation is generated from allowed candidate data and reason codes, not invented post hoc. | WB |
| **NFR-AI-006** | Desirable | **Model and prompt quality monitoring.** The team should monitor structured-output failure, tool retry, clarification rate, routing correction, user abandonment, and successful closure. | Metrics are attributable to model, prompt, flow, and schema versions. | FP |

---

# 5. Explicitly deferred or out-of-scope target capabilities

The following items may remain valuable target-architecture directions, but they are **not V1 NFR commitments** unless separately promoted through a decision record:

| Deferred capability | V1 treatment |
|---|---|
| **Full general-purpose goal stack and one session per arbitrary user goal** | V1 must isolate concurrent parcel requests, but does not require a generic nested-goal framework. |
| **Dialogue-act taxonomy based on DAMSL or ISO 24617-2 and explicit conversation planning** | V1 may use simpler typed intents and operation schemas. |
| **Background autonomous entity-resolution agent with probabilistic merge decisions** | V1 requires basic duplicate prevention and safe manual/controlled resolution, not a full agent. |
| **Dedicated external policy engine or authorization graph such as OPA, Cedar, OpenFGA, or SpiceDB** | The deterministic authorization outcome is mandatory; the implementation technology is not. |
| **Temporal or another distributed durable-workflow platform** | Durable waits and recovery are mandatory; a new workflow platform is not required if the current stack meets them. |
| **Dedicated Admin Agent and full Admin UI** | Exact Admin role, correction permissions, and interface remain deferred. Privileged access must be separated if introduced. |
| **Automated reversible entity merging** | Deferred beyond basic duplicate protection. |
| **Advanced marketplace bidding, automatic ranking optimisation, or ML-based matching** | V1 uses deterministic favourite/top-three recommendation and candidate ordering. |
| **Full transporter dashboard, native mobile application, online payments, live tracking, disputes, or complex ratings** | Product scope remains post-V1. |
| **Receiver-initiated brokerage** | Post-V1. |
| **Broad attachment processing, malware scanning, OCR, or multimodal reasoning** | Deferred until attachment types, storage, safety, and retention are explicitly scoped. |
| **Multi-region active-active architecture and marketplace-scale availability** | Hardened-service or later concern. |
| **Formal configurable autonomous-versus-admin-assisted runtime modes** | Not required unless the product later decides to support both modes. |

---

# 6. Open parameters that must be fixed before the Field Pilot

These are not unresolved architecture conflicts, but mandatory operational parameters whose exact values or policies must be approved before real-pilot use:

1. **Minimum-data rule** for Sender, Receiver, parcel, route, dates, and special handling.
2. **Transporter response policy:** reminder delay, number of reminders, final timeout, late-response handling, and cascade timing.
3. **WhatsApp delivery semantics:** provider acceptance, delivered callback, read receipt, or another signal required before `waitingResponse`.
4. **Confirmation authority:** which actors may confirm pickup and delivery, and how contradictory confirmations are resolved.
5. **Cancellation policy after acceptance.**
6. **Matching configuration:** eligibility, route/date compatibility, preference weighting, past-experience definition, and handling of invalid Channels.
7. **Pilot load assumptions** used to validate the performance and capacity targets.
8. **Retention periods** for conversation content, operational records, audit records, and closed requests.
9. **Exception ownership:** who receives and resolves structured unrecoverable exceptions until the Admin model is finalized.
10. **Whether attachments are included in the Field Pilot.**

---

# 7. Blueprint alignment summary

| Blueprint area | NFR alignment |
|---|---|
| **Router and mandatory routing context** | NFR-DAT-001/002, NFR-CON-001/002/003 |
| **Request Intake and Clarification** | NFR-CTL-006, NFR-DAT-003/007, NFR-CON-004 |
| **Matching and Choice** | NFR-DAT-006, NFR-AI-004/005 |
| **Brokerage and candidate cascade** | NFR-REL-003/004/005, NFR-SEC-003, NFR-CHN-005 |
| **Fulfilment and Closure** | NFR-CTL-001/005, NFR-DAT-004/005/008 |
| **Recovery Agent and scheduler** | NFR-REL-004, NFR-PERF-004, NFR-OPS-004 |
| **Data Access boundary and MCP** | NFR-SEC-004/005/006, NFR-CTL-003/004 |
| **Guardrail stages** | NFR-CTL-003/004, NFR-SEC-008, NFR-TST-005 |
| **Neo4j and LangFlow/PostgreSQL responsibilities** | NFR-DAT-001/002, NFR-REL-001 |
| **Telegram/WhatsApp gateway** | NFR-CHN-001–006 |
| **Incremental phases** | Temporary WS exceptions are allowed only in non-production; all Mandatory FP requirements apply before real-pilot use. |

---

# 8. V1 release gate

The system is ready for a V1 Field Pilot only when:

1. all **Mandatory** requirements marked **WS**, **WB**, or **FP** are satisfied or have an explicitly approved, time-bounded exception;
2. the end-to-end scenarios for UC-1 and UC-3–UC-9 pass through the WhatsApp adapter;
3. restart, duplicate-message, timeout, rejection-cascade, cross-party access, prompt-injection, and invalid-transition tests pass;
4. backup restoration and deployment rollback have been exercised;
5. the open parameters in Section 6 have named decisions and owners;
6. autonomous failures produce structured, inspectable exceptions without corrupting or silently abandoning requests.
