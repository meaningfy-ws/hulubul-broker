## Context

Hulubul Phase 1 is an architectural Walking Skeleton. This change delivers the
first vertical thread: a Sender can state a parcel intention, receive one
focused clarification when information is missing, and complete the same
persisted `DeliveryRequest` across interactions and a LangFlow restart.

The repository already contains the LinkML domain model and a local stack with
LangFlow, PostgreSQL, Neo4j, and Neo4j MCP. It does not contain application
code, tracked Hulubul flows, executable operational contracts, automated tests,
or CI. The current LangFlow image is declared as `latest`, and runtime flows
exist only in PostgreSQL. The ignored prototype under `DEV/` is not a Hulubul
flow and is not a source artifact.

The governing architecture requires:

- Neo4j to remain authoritative for request state;
- PostgreSQL to retain LangFlow messages, flow records, and traces;
- LF-00 to load persisted routing context before selecting a specialist;
- LF-70 to be the only flow with raw Neo4j MCP tools;
- typed operation and result contracts;
- deterministic rendering from validated structured results;
- independently asserted writes and restart/resumption evidence.

The external architecture sources for this design are:

1. the [Phase 1 architecture overview](../../../architecture/agentic-system-blueprint-phase-1.md#2-architecture-overview);
2. the [incremental Phase 1 strategy](../../../architecture/incremental-system-development-strategy.md#4-phase-1---walking-skeleton);
3. the [Phase 1 verification layers](../../../architecture/verification-testing-and-evaluation-strategy.md#5-phase-1-test-layers);
4. the [UC-1 business flow](../../../architecture/use-cases/blue-user-goal.md#uc-1--register-a-parcel-request);
5. the [NFR catalogue](../../../architecture/non-functional-requirements.md#4-non-functional-requirements-catalogue); and
6. the [planning handover](../../../DEV/reports/hulubul-phase-1-implementation-planning-handover.md#4-phase-1-objective).

### Artifact roles and authority

| Artifact | Role | Authority in this change |
| --- | --- | --- |
| `brainstorm.md` | Historical exploration and correction record | Non-normative; it preserves decisions and rejected alternatives but does not override later artifacts |
| `proposal.md` | Strategic scope, appetite, capabilities, and no-gos | Authoritative for shaped scope and capability boundaries |
| `specs/*/spec.md` | Requirements and named capability scenarios | Normative authority for observable behavior and contract obligations |
| `design.md` | Technical decisions and realizability | Authoritative for how the normative behavior is realized within proposal scope |
| `tasks.md` | Stable coarse implementation tracker | Authoritative only for coarse task IDs and coverage intent |
| `plan.md` | Executable decomposition | Authoritative for implementation steps only after it is reconciled with the current proposal, specs, design, tasks, and features |
| `tests/features/*.feature` | Business-language examples | Executable projection of actor-observable UC, capability, and NFR acceptance; it does not define internal implementation behavior |

Deliberate role-specific projection is valid: artifacts need not duplicate every
detail when they express the same decision at different levels. If artifacts
conflict, resolve behavior from specs, technical realization from design, scope
from proposal, coarse identity from tasks, and executable sequencing from the
latest reconciled plan. A plan or feature cannot override a normative spec or a
design constraint.

The implementation stakeholder is the developer operating the local LangFlow
environment. The only Phase 1 actor in this change is a simulated Sender.
Production channel users, authentication, operators, and Transporters are not
introduced.

## Goals / Non-Goals

**Goals:**

- Deliver LF-00 Main Router, LF-10 Request Intake, and LF-70 Data Access as
  tracked, reproducible LangFlow 1.10.2 flows.
- Accept one authenticated API interaction envelope and a local Playground
  equivalent without allowing user prose to set actor identity.
- Persist one sparse or complete request and one active-request binding per
  session in Neo4j.
- Route from authoritative Neo4j state rather than chat history.
- Complete a request in one message or through successive focused
  clarification turns without creating another request.
- Validate every cross-flow input and output against versioned Pydantic-owned
  operational contracts.
- Keep LF-70 as the sole raw MCP boundary and explicitly constrain its
  temporary LLM-generated-Cypher exception.
- Apply proportional Clean Architecture to Python code: pure policy and
  contracts inside, thin LangFlow components outside.
- Make Git the flow source of truth and PostgreSQL the deployed runtime copy.
- Provide hard deterministic tests from unit through full-stack resumption,
  plus a soft live-model evaluation baseline.
- Leave a contract-compatible seam for LF-20 and stronger deterministic write
  execution in the next change/phase.

**Non-Goals:**

- LF-20 Parcel Coordination or any behavior after a request reaches `complete`.
- Matching, ranking, Sender choice, transporter assignment, forwarding,
  acceptance, pickup, delivery, or closure.
- Telegram, WhatsApp, attachments, feedback, cancellation, rejection, or
  Transporter-originated clarification.
- Production authentication, authorization, party-facing MCP, multi-request
  sessions, scheduler, recovery worker, Guardrail Agent, audit/event ledger, or
  compensation.
- FastAPI or another public application facade above LangFlow.
- Standalone LFX as the acceptance runtime.
- Changing the LinkML conceptual model to represent operational conversation
  bindings or incomplete drafts.
- Hand-editing generated LinkML outputs.
- Duplicating LF-00, LF-10, or LF-70 orchestration in Python services.
- Making live-model or LLM-as-judge results hard pull-request gates.

## Decisions

### DEC-001: Deliver one vertical intake change before lifecycle coordination

- **Choice:** Change 1 ends when the same request reaches `complete`; Change 2
  adds LF-20 and the remaining lifecycle only after Change 1 is verified,
  archived, and merged.
- **Reason:** The thread produces observable business behavior while keeping
  one OpenSpec plan and review within a manageable context. It also gives
  Change 2 a proven contract and persisted-state baseline.
- **Alternatives considered:** One Phase 1 change was rejected as too large for
  reliable agentic implementation. Three changes were rejected because the
  first would be infrastructure-only and would multiply cross-change spec
  synchronization.

### DEC-002: Use full, pinned LangFlow with PostgreSQL

- **Choice:** Run LangFlow and LFX 1.10.2. Pin the inspected LangFlow image as
  `langflowai/langflow:1.10.2@sha256:ae6f9afd03bc032dc2989ece49791fcf83871230aff9d6e485c8e1ebada1e70f`.
  Retain PostgreSQL as the LangFlow database. Pin PostgreSQL as
  `postgres:16-trixie@sha256:33f923b05f64ca54ac4401c01126a6b92afe839a0aa0a52bc5aeb5cc958e5f20`
  and Neo4j as
  `neo4j:5.26-community@sha256:362542416de6c09a971484d1893878016cc3b5cdec166e54b1c824a220ecd6b9`.
- **Reason:** Full LangFlow supplies the visual editor, API, native traces, and
  PostgreSQL persistence needed to prove resumption. Image and tool versions
  must match the flow export format.
- **Alternatives considered:** Standalone `lfx run` and `lfx serve` were
  rejected because their no-op database does not persist LangFlow messages or
  application state. A source installation was rejected because the official
  image already supplies the required 1.10.2 components.

The tracked runtime assets are:

```text
langflow/
├── README.md
├── flow-manifest.yaml
├── .lfx/environments.yaml
└── flows/
    ├── 10-lf-70-data-access.json
    ├── 20-lf-10-request-intake.json
    └── 30-lf-00-main-router.json
```

The numeric prefixes encode deployment order. No placeholder LF-20 flow is
created.

### DEC-003: Make Git authoritative through LFX

- **Choice:** Stable-ID flow JSON is normalized and committed. `lfx pull`,
  `status`, `export`, `validate`, `upgrade`, and `push` mediate changes between
  Git and the local LangFlow instance.
- **Reason:** PostgreSQL remains necessary runtime state but cannot provide
  reviewable history, reproducible clean deployment, or CI drift detection.
- **Alternatives considered:** Volume-only flow storage was rejected as
  unreproducible. Hand-written JSON without UI review was rejected as brittle
  against LangFlow component schemas.

The development loop is agent-first hybrid:

1. An agent authors or modifies tracked flows/components.
2. `lfx validate --level 4 --strict --skip-credentials` validates them.
3. `lfx push --env local` deploys them by stable flow ID.
4. The developer inspects or tunes the flow in the UI.
5. `lfx status` detects drift.
6. `lfx pull` and `lfx export` normalize reviewed UI changes back into Git.
7. A second normalization pass must be byte-identical.

Normalization strips volatile timestamps, owner/folder identifiers, selected
or dragging canvas state, absolute positions, and secret values. It sorts JSON
object keys but does not independently reorder node or edge arrays. Flow-aware
tests and Gitleaks reject credentials, private keys, credential-bearing URLs,
unexpected environment variables, and non-empty LangFlow secret fields.

### DEC-004: Invoke LangFlow directly and defer FastAPI

- **Choice:** Automation calls authenticated
  `POST /api/v1/run/{lf00-flow-id}`. LF-70 and LF-10 are also directly invocable
  for integration testing. No additional HTTP service is introduced.
- **Reason:** LangFlow already provides the API boundary required by this
  internal Walking Skeleton. An extra service would add deployment, contracts,
  and tests without satisfying another acceptance criterion.
- **Alternatives considered:** A thin FastAPI facade was deferred until channel
  webhook normalization, trusted identity derivation, provider shielding, or a
  deterministic service boundary requires it.

LangFlow API keys are supplied through `LANGFLOW_API_KEY_SOURCE=env`; actual
keys are ignored and never stored in flow JSON or `.lfx/environments.yaml`.
Local UI auto-login may remain enabled, but it does not disable API-key
authentication.

### DEC-005: Treat LLM-driven LF-70 as a temporary Phase 1 exception

- **Choice:** LF-70 receives a typed `DataOperationRequest`, uses its LLM agent
  to select Neo4j MCP tools and generate Cypher, validates the resulting
  `DataOperationResult`, and remains the only flow that can call raw MCP.
- **Reason:** This proves the specific Walking Skeleton proposed by the Phase 1
  blueprint.
- **Alternatives considered:** Deterministic Cypher construction inside Python
  was preferred for the target architecture but rejected for this experiment.
  A Python data service was rejected because it would bypass the intended MCP
  proof.

This decision is an explicit non-production exception to NFR-CTL-002 and the
target ADR-015/016/017 service-write boundary. It is constrained by:

- a closed enum of five Change 1 operations;
- typed, operation-specific payloads rather than raw JSON or caller Cypher;
- identifiers generated before LF-70 rather than invented by its LLM;
- an expected current status on every transition;
- schema validation before and after the LLM;
- exactly one request aggregate affected by confirmed writes;
- direct Neo4j assertions in tests;
- no automatic replay after a write has been dispatched;
- trace assertions that no other flow exposes MCP tools.

Phase 2 must replace generic generated writes; this design must not be cited as
approval for production LLM-authored Cypher.

### DEC-006: Use Pydantic as the operational contract source

- **Choice:** Strict Pydantic v2 models under
  `src/hulubul/core/models/operational/` own all cross-flow contracts. A
  deterministic generator commits JSON Schema draft 2020-12 outputs under
  `schemas/operational/v1/`.
- **Reason:** Python models provide reusable runtime validation and focused unit
  tests. Generated JSON Schema lets LangFlow, fixtures, and non-Python tooling
  consume the same contract without a second hand-maintained definition.
- **Alternatives considered:** JSON Schema as the hand-authored source was
  rejected because custom Python components would need a parallel object model.
  LinkML was rejected because these are execution contracts, not domain
  concepts.

All operational models use:

```text
extra="forbid"
strict=True
str_strip_whitespace=True
frozen=True
```

Top-level contracts carry `schema_version="1.0.0"` and `correlation_id`.
Absence is represented by `None`, never by an empty string. Successful IDs are
non-empty. Generated files include stable `$id` values and a manifest recording
the generator and Pydantic versions.

Contract groups are:

| Contract | Required architectural content |
| --- | --- |
| `MainFlowInput` | internally generated message/correlation UUIDs, trusted LangFlow session ID, simulated actor context, 1-4000 character message |
| `RouterInput` | strict wrapper over `MainFlowInput envelope` and `RoutingContext routing_context`, with equal wrapper/nested schema versions and correlations and equal nested session IDs |
| `IntakeInput` | strict wrapper over `MainFlowInput envelope` and `RoutingContext routing_context`, with the same equality invariants plus intake-only routing-state invariants |
| `RoutingContext` | binding presence, request ID/status, closed timestamp, routing stage, typed error |
| `RouterResult` | routed/informational/failure outcome, intake/none target, reason, safe message |
| `IntakeFacts` | sender/receiver identity, 1-4,000 character pickup/drop-off text, parcel content, optional preferred period |
| `IntakeResult` | clarification/complete/failure result, same request ID, status, facts, missing fields, one clarification field |
| `DataOperationRequest` | discriminated operation union, operation UUID, correlation/session/actor, typed payload |
| `DataOperationResult` | confirmed/rejected/ambiguous outcome, dispatch flag, status before/after, affected count, typed result/error |
| `DeliveryRequestSnapshot` | persisted request view that explicitly permits missing draft data and carries `updated` for optimistic concurrency |
| `OperationalError` | enum code/category, safe message, retryability, field violations |

`RouterInput` and `IntakeInput` are top-level versioned contracts. For each
wrapper, `schema_version` and `correlation_id` MUST equal those in both nested
objects, and `envelope.session_id` MUST equal `routing_context.session_id`.
`IntakeInput` additionally requires `routing_context.routing_stage=intake`, no
routing error, and exactly one of these states:

- no binding, no request ID, and no request status; or
- one valid binding to one request whose typed status is `new` or
  `needsClarification`.

No other stage, error, partial binding, or bound status validates as
`IntakeInput`. `RoutingContext.request_status` remains
`RequestStatus | None`; raw graph text never enters either wrapper.

`ContractKind` has exactly these 11 members and the generated version-1
inventory has exactly the corresponding 11 schemas:

```text
main-flow-input
router-input
intake-input
routing-context
router-result
intake-facts
intake-result
data-operation-request
data-operation-result
delivery-request-snapshot
operational-error
```

Allowed operations are exactly:

```text
getRequestRoutingContext
createDeliveryRequest
readDeliveryRequest
updateDeliveryRequest
setRequestStatus
```

These are application-level data commands, not user actions and not raw MCP
tools. Domain flows share the vocabulary but receive different capabilities:

| Caller | Permitted operation |
| --- | --- |
| LF-00 | `getRequestRoutingContext` only |
| LF-10 | `createDeliveryRequest`, `readDeliveryRequest`, `updateDeliveryRequest`, `setRequestStatus` |
| LF-70 | Executes all five typed commands and alone maps them to `get-schema`, `read-cypher`, or `write-cypher` MCP tools |

LF-00 and LF-10 invoke LF-70 through one typed Run Flow boundary. They do not
receive five raw database tools and cannot submit arbitrary Cypher.

The five payload shapes are: routing context `{}`; create `{identifiers,
facts}` with no caller timestamp; read `{request_id}`; update `{request_id,
expected_updated_at, expected_status, updates, identifiers}`; and status
`{request_id, expected_updated_at, expected_status, target_status}`. A null
preferred-period update means no change; a non-null value is valid only while
the persisted preferred period is absent.

Validation precedes authorization. Unknown operation discriminators,
operation/payload mismatches, fields named `cypher` or `query`, and any other
undeclared field fail strict contract validation as `INVALID_CONTRACT` before a
caller capability is considered. `OPERATION_NOT_ALLOWED` is reserved for a
known operation with a fully contract-valid payload that is outside the
declared capability of the identified caller. Tests keep malformed-contract
and valid-but-forbidden capability cases separate.

`missing_fields` reports every missing required field, while
`clarification_field` contains zero or one field. Rendering asks for only that
field. The deterministic missing-field priority is Receiver identity, pickup
location, drop-off location, then parcel declared content. A supplied invalid
field takes priority during its interaction so correction is immediate.

### DEC-007: Apply proportional Clean Architecture to Python

- **Choice:** Put pure shared contracts in `hulubul/core/models`, intake policy
  in `hulubul/request_intake/models`, deterministic coordination helpers in
  `hulubul/request_intake/services`, and thin LangFlow custom components in
  `hulubul/request_intake/entrypoints`. Create no adapter package until Python
  owns an external integration.
- **Reason:** Contracts and decisions remain testable without importing
  LangFlow, while the visual flow remains the orchestration source of truth.
- **Alternatives considered:** Embedding all policy in custom components was
  rejected as framework coupling. Empty four-layer scaffolding and a Python MCP
  wrapper were rejected as ceremony and duplicated infrastructure.

Planned production paths are:

```text
src/hulubul/core/models/operational/
├── base.py
├── enums.py
├── errors.py
├── envelope.py
├── routing.py
├── intake.py
├── data_operations.py
└── snapshots.py

src/hulubul/request_intake/
├── models/
│   ├── completeness.py
│   └── transitions.py
├── services/
│   ├── data_operation_policy.py
│   ├── graph_identifiers.py
│   ├── rendering.py
│   └── retry_policy.py
└── entrypoints/langflow/components/hulubul/
    ├── execution_envelope.py
    ├── contract_boundary.py
    ├── data_operation_boundary.py
    ├── retry_decision.py
    └── deterministic_renderer.py
```

The custom component base is mounted read-only at `/app/custom_components`,
with `/app/custom_components/hulubul/` serving as LangFlow's category package.
`PYTHONPATH=/app/src` exposes the clean core. Import-linter enforces that models
do not import services or entrypoints and that services do not import
entrypoints.

The system-level entrypoint remains LangFlow's LF-00 run endpoint, supplied by
the LangFlow image. The Python `entrypoints` above are plugin classes loaded
inside that runtime; they are not a second server or a standalone command. A
client calls LangFlow directly, LangFlow instantiates the custom components,
and those components delegate validation and policy to the pure Python core.

### DEC-008: Persist operational binding as a relationship-backed extension

- **Choice:** Add an application-owned operational schema:

```text
(:OperationalConversationBinding {
  sessionId,
  createdAt,
  updatedAt
})-[:BINDS_ACTIVE_REQUEST]->(:DeliveryRequest)
```

`sessionId` is unique. The relationship is the sole active-request reference;
there is no duplicate `activeRequestId` property.
- **Reason:** A relationship provides direct referential traversal and avoids
  synchronizing a property with a graph edge. The label remains outside LinkML
  because it is an execution concern.
- **Alternatives considered:** A string-only `activeRequestId` was rejected as
  weaker graph integrity. Adding the binding to LinkML was rejected because it
  would pollute the conceptual domain with one runtime's session mechanism.

The constraint lives in `infra/cypher/operational-schema.cypher`. Neo4j
Community cannot enforce one outgoing relationship, so LF-70 policy and tests
must reject zero or multiple bound requests.

Duplicate evidence uses three distinct fixtures without weakening that
constraint:

- the schema integration test attempts a second binding with the same
  `sessionId` and proves the uniqueness constraint rejects it;
- a boundary unit test supplies a synthetic raw lookup record with
  `binding_count=2` and proves fail-closed adaptation without constructing an
  impossible constrained graph; and
- constrained Neo4j integration fixtures retain one binding but create
  duplicate `BINDS_ACTIVE_REQUEST` relationships and/or distinct active targets,
  which Neo4j Community permits, and prove `GRAPH_CONTEXT_INCONSISTENT`.

### DEC-009: Allow sparse persisted drafts without invented domain data

- **Choice:** A request in `new` or `needsClarification` may omit receiver,
  parcel, pickup, or drop-off nodes. The complete LinkML aggregate is validated
  only before transition to `complete`.
- **Reason:** Phase 1 explicitly requires immediate draft persistence and
  clarification of missing data, while LinkML describes the valid complete
  aggregate. Sparse drafts preserve truth; placeholder people, places, or
  parcels would be fabricated data.
- **Alternatives considered:** Delaying creation until complete was rejected
  because it prevents same-request binding and durable clarification.
  Placeholder nodes were rejected because they violate model meaning.

The Sender actor is enough identity to create a draft on the first valid
interaction. `readDeliveryRequest` and its snapshot contract tolerate absent
optional subgraphs while status is `new` or `needsClarification`.

For a first-time trusted simulated actor without an existing Sender `Agent`,
Change 1 creates the minimum enduring Agent and request-specific Sender
participation needed for truthful intake. Trusted simulated actor metadata
satisfies UC-1's Sender-identity prerequisite for this Walking Skeleton and
implements only UC-1 step 2's identify-or-create behavior. It does not claim a
complete UC-13 party profile and creates no broader profile workflow,
contact-point management, profile editing, verification, or channel enrollment.

"Complete aggregate validation" does not mean postponing validation of supplied
facts. Validation runs incrementally on every interaction:

1. The message envelope is validated before model execution.
2. Every newly extracted fact is validated immediately for type, non-blank
   content, length, enum membership, and any domain rule that can be evaluated
   from that fact alone.
3. Cross-field rules run as soon as all fields required by that rule are
   available.
4. Invalid supplied data is rejected or clarified in the same interaction and
   is not persisted as accepted fact.
5. Only the final completeness check waits until all required fields exist; it
   validates the full LinkML-compatible subset before `complete`.

For Change 1, pickup and drop-off are intentionally free-text `Place` values,
so validation can reject empty/oversized/structurally invalid text but cannot
prove that a real-world address exists. A later geocoding/address capability
must validate each location when it is captured, not defer that check until the
request is otherwise complete.

After surrounding whitespace is stripped, each human-supplied Receiver name,
pickup location, drop-off location, parcel declared-content description, and
optional preferred period must contain 1-4,000 characters. This temporary
uniform maximum reuses the `MainFlowInput` boundary and leaves headroom below
Telegram's 4,096-character text-message limit. It is an operational Change 1
constraint, not a LinkML model constraint; later channel-specific contracts may
introduce tighter limits through a separate change.

The conceptual request graph uses these exact labels and directions:

```text
(:DeliveryRequest)-[:HAS_SENDER]->(:Sender)-[:PLAYED_BY]->(:Agent)
(:DeliveryRequest)-[:HAS_RECEIVER]->(:Receiver)-[:PLAYED_BY]->(:Agent)
(:DeliveryRequest)-[:HAS_DELIVERY_ITEM]->(:Parcel)
(:DeliveryRequest)-[:HAS_PICK_UP_LOCATION]->(:Place)
(:DeliveryRequest)-[:HAS_DROP_OFF_LOCATION]->(:Place)
```

`DeliveryRequest.hasStatus` is a string property, not a node or relationship.
Change 1 writes only `new`, `needsClarification`, and `complete`. `closed`
remains null.

### DEC-010: Generate identifiers outside the data-access LLM

- **Choice:** `graph_identifiers.py` creates all graph IDs before a create or
  update operation reaches LF-70.
- **Reason:** The operation contract, not generated Cypher, owns identity. This
  makes results assertable and prevents the LLM from silently selecting IDs.
- **Alternatives considered:** Letting Cypher use random IDs was rejected as
  opaque and difficult to verify. Merging on names was rejected because names
  are not unique identities.

Identity rules are:

- New requests use `req-<uuid4>`.
- Sender/Receiver role, Parcel, and Place IDs use the existing `s-`, `r-`,
  `p-`, and `pl-` prefixes with UUID values.
- The trusted simulated Sender identifier is the request actor's URN. The
  enduring Sender `Agent.id` is a UUIDv5 derived from that identifier, so the
  same actor can be reused safely across requests.
- A supplied Receiver stable identifier receives the same UUIDv5 treatment.
  If only a Receiver name is supplied, the operation creates a request-scoped
  receiver identifier `urn:hulubul:phase1:receiver:<request-uuid>`; it does not
  merge people by name.
- Because `Agent.name` is required, a missing display name falls back to the
  stable identifier. The identifier is never inferred from prose when trusted
  actor metadata exists.
- `Place.name` stores the supplied free-text location. `Place.hasIdentifier`
  is a generated `urn:uuid:<uuid>` and `Place.hasType` is the declared constant
  `unclassifiedPlace`; the request relationships encode pickup versus drop-off
  purpose.

All symbolic prefixes, types, statuses, operation names, and error codes are
enums/constants rather than free strings scattered through flows or tests.

### DEC-011: Keep each data mutation atomic and use optimistic concurrency

- **Choice:** Each LF-70 operation executes one Neo4j write transaction. Request
  and binding creation are one transaction. Field updates are one transaction.
  Every update is compare-and-set using both the request's previously read
  `expected_updated_at` and `expected_status`; status changes additionally
  require `target_status`. A confirmed mutation must affect exactly one request.
- **Reason:** This follows the documented logical operation boundary and keeps
  mutation postconditions independently testable. It also avoids inventing a
  new compound operation during Change 1.
- **Alternatives considered:** Combining update and transition into one new
  operation would provide stronger use-case atomicity but would change the
  approved operation inventory. Treating the whole conversational turn as one
  transaction is not supported across LangFlow runs.

The transition table is exactly:

```text
none                 -> new
new                  -> needsClarification
new                  -> complete
needsClarification   -> complete
```

Creation always persists `new` first. LF-10 then requests the appropriate
status transition. If the transition fails after successful creation/update,
the graph remains in a truthful recoverable `new` or `needsClarification`
state; the next authoritative read recomputes completeness. No operation may
claim a status that was not confirmed by its own affected-record result.

Create payloads contain no caller-supplied `created_at` or `updated_at`.
Neo4j obtains one transaction timestamp and assigns it to both request
`created` and request `updated` (and the corresponding binding timestamps), then
returns both request timestamps. Update and status operations return the new
authoritative `updated` value.

Fact updates are additive-only in Change 1. In particular, a null
`preferred_period` means no change; a non-null value may fill an absent
`preferredPeriod`; and no update may clear or replace an existing preferred
period. The same no-replacement rule applies to accepted singular intake
subgraphs.

If an update or status write returns zero rows, LF-70 performs one non-mutating
authoritative read to classify the result as missing/inconsistent request,
`INVALID_EXPECTED_STATUS`, `CONCURRENT_MODIFICATION`, or
`INVALID_STATUS_TRANSITION` as applicable. This classification read never
replays or modifies the attempted write.

Concurrency behavior is explicit:

- The unique `OperationalConversationBinding.sessionId` constraint and atomic
  request-plus-binding transaction ensure that two simultaneous first messages
  cannot commit two active requests for one session; the losing transaction is
  rolled back without an orphan request.
- `readDeliveryRequest` returns `updated`. Every subsequent update/status
  payload carries that value as `expected_updated_at`.
- A successful mutation sets a new UTC `updated` timestamp and returns it. A
  following status operation uses the returned value, not the stale initial
  snapshot.
- Two concurrent clarification writes from the same snapshot cannot both
  match. The loser receives `CONCURRENT_MODIFICATION`, does not overwrite the
  winner, and must reload authoritative state before the user retries.
- Phase 1 does not auto-retry the losing write because replaying extracted
  facts against changed state is a new decision, not a transport retry.

This prevents lost updates and duplicate active requests. It does not provide
idempotent replay of the same inbound message; message-level idempotency remains
outside Change 1.

### DEC-012: Use three stable-ID Change 1 flows

- **Choice:** Derive flow IDs as UUIDv5 values from
  `https://meaningfy.ws/hulubul/langflow/flow/<flow-key>/v1` with
  `UUID_NAMESPACE_URL`.
- **Reason:** Stable IDs allow deterministic push/update, API tests, and drift
  detection across clean databases.
- **Alternatives considered:** UI-generated IDs were rejected because imports
  could create duplicates or invalidate callers.

| Flow | UUID | Responsibility |
| --- | --- | --- |
| LF-00 Main Router | `38b7ee64-26c8-5d4d-97e4-6e62a0fcb557` | Input envelope, mandatory LF-70 context read, route to LF-10 or no-op result, validate/render output |
| LF-10 Request Intake | `6843ae79-147f-55d4-a25b-01d6143a12cc` | Extract facts, create/read/update same request, select one clarification, reach complete |
| LF-70 Data Access | `94f6774d-ebc7-5bf1-8486-886f91886a5f` | Validate logical operation, invoke Neo4j MCP, validate structured result |

Stable boundary component IDs use
`<LangFlowType>-hlb-<lf-number>-<semantic-role>-v1`. The manifest records flow
IDs, public input/result component IDs, Chat Output IDs, and cross-flow Run
Flow references. Cosmetic canvas changes never replace IDs.

LF-00 and LF-10 use this fixed trust-preserving topology:

1. LF-00 Chat Input emits one LangFlow `Message` to the execution-envelope
   component.
2. The envelope and LF-70 lookup result enter a deterministic `RouterInput`
   boundary on direct edges. Only the resulting validated canonical wrapper is
   exposed to the Router model.
3. The LF-10 Run Flow binding receives validated `envelope` and
   `routing_context` through advanced fixed inputs excluded from the model tool
   schema. The Router may choose the intake capability but cannot author,
   substitute, or override either trusted nested object.
4. LF-10 first assembles and validates `IntakeInput` deterministically, then
   gives only that canonical wrapper to its Intake model.

No model output, user tweak, public input, or conversational value can replace
the advanced envelope/context edges. Static topology tests and boundary unit
tests prove the advanced inputs are wired from the validated predecessors and
absent from model-callable schemas.

LF-70 does not instantiate `RoutingContext` directly from a Neo4j row. It first
validates an internal strict raw lookup record with nullable
`requestStatusRaw`. A deterministic adapter then applies this closed precedence:

1. Invalid binding, relationship, target, or request cardinality becomes a
   failure context with the exact continuity error.
2. A valid absent binding becomes intake with no request ID/status.
3. For a valid bound request, a non-null closed timestamp wins over every raw
   status and becomes a closed informational context.
4. Raw `new` and `needsClarification` become typed intake contexts; `complete`
   becomes a typed complete informational context.
5. Each of `optionsProposed`, `waitingResponse`, `accepted`, `rejected`,
   `pickUpPlanned`, `pickedUp`, `delivered`, and `cancelled` becomes a typed
   unsupported context with `UNSUPPORTED_PHASE1_STATUS` and no mutation.
6. A null raw status on a non-closed bound request becomes a failure context
   with `GRAPH_CONTEXT_INCONSISTENT`.
7. Any other non-null raw value becomes `request_status=None`, stage `failure`,
   and `UNSUPPORTED_REQUEST_STATUS`.

The raw value is never copied into `OperationalError`, a user message, a log,
or a trace. Parameterized tests exhaust all 11 recognized statuses, unknown
raw values, null status, closed precedence over every recognized/unknown value,
and all valid/invalid cardinality shapes.

LF-00 routing behavior in this change is:

| Persisted context | Result |
| --- | --- |
| No binding | Invoke LF-10 |
| `new` | Invoke LF-10 for the same request |
| `needsClarification` | Invoke LF-10 for the same request |
| `complete` | Return intake-complete informational result; do not mutate |
| Non-null `closed` | Return closed informational result; do not mutate |
| Any of the eight recognized post-intake statuses | Return unsupported-Phase-1 failure; do not mutate |
| Missing bound request, duplicate binding/target, unknown raw status | Return typed routing failure; do not guess or mutate |

### DEC-013: Separate trusted execution metadata from user prose

- **Choice:** Human users provide only message content. The
  `ExecutionEnvelopeComponent` accepts one LangFlow `Message`, generates
  `message_id` and `correlation_id`, and deterministically derives the Phase 1
  session and simulated actor from LangFlow-controlled metadata.
- **Reason:** User text must not be able to grant an actor role or select a
  different session/request. Correlation and message IDs must be unique per
  interaction while the session remains stable.
- **Alternatives considered:** Parsing actor identity from prose and hardcoding
  one session in the flow were rejected as unsafe and untestable.

API invocation supplies actor metadata through LangFlow request variables with
these exact header names:

```text
X-LANGFLOW-GLOBAL-VAR-HULUBUL_PHASE1_ACTOR_ID
X-LANGFLOW-GLOBAL-VAR-HULUBUL_PHASE1_ACTOR_DISPLAY_NAME
```

The actor ID header is required and the display-name header is optional. The
request-variable values are advanced trusted inputs to the envelope component;
they are not parsed from `input_value`, model output, or user prose. Local
Playground invocation instead reads required ignored environment variable
`HULUBUL_PHASE1_PLAYGROUND_ACTOR_ID` and optional ignored variable
`HULUBUL_PHASE1_PLAYGROUND_ACTOR_DISPLAY_NAME`. No FastAPI or channel adapter
is required to realize either path.

The envelope component accepts `Message` only, never a free `str`. It reads the
session from both `Message.session_id` and the active LangFlow graph context,
normalizes each accepted form, and requires equality. An accepted session is
either a bare UUID or canonical `p1-<UUID>`; both normalize to lowercase
`p1-<uuid>`. Empty values, arbitrary identifiers, malformed UUIDs, mismatched
message/graph sessions, and LangFlow's flow-ID fallback when the caller omits a
session are rejected as `INVALID_INPUT`.

The internal envelope uses:

```text
session_id: p1-<lowercase UUID>
actor_id: urn:uuid:<UUID>
actor_role: sender
identity_assurance: simulated
source: api | playground
message_id: internally generated UUID per interaction
correlation_id: internally generated UUID per interaction
```

`actor_role=sender`, `identity_assurance=simulated`, and the source value for
each invocation path are component constants, not caller-controlled fields.
API and CI harnesses choose a session ID so that they can resume it, but the
conversational user never sees or types that value. This is simulated Phase 1
trust for synthetic Walking Skeleton data, not production authentication,
authorization, or proof of identity. Production identity assurance and channel
mapping remain explicitly out of scope.

### DEC-014: Render only validated structured output

- **Choice:** LF-10 and LF-00 expose one validated structured result path.
`DeterministicRendererComponent` converts its safe `user_message` to Chat
Output. It never calls a model.
- **Reason:** A separate free-text agent output could trigger duplicate model
calls or diverge from the structured result used by automation.
- **Alternatives considered:** Connecting both text and structured agent outputs
was rejected because LangFlow may evaluate the model twice and produce
inconsistent answers.

### DEC-015: Retry reads and model calls once, never dispatched writes

- **Choice:** Retry eligible operations once after a fixed 500 ms delay, for
  exactly two total attempts.
- **Reason:** A bounded retry tolerates common transient read/model failures
  without turning Phase 1 into a recovery system. A timed-out write is
  ambiguous because there is no idempotency key or compensation.
- **Alternatives considered:** No retries was considered too brittle. Retrying
  writes was rejected as unsafe. Adding write idempotency was deferred to the
  later deterministic operation architecture.

Retryable model conditions are timeouts, connection/protocol failures, HTTP
408/425/429/500/502/503/504, and one malformed structured result. Retryable MCP
read conditions are timeouts, connection failures, HTTP
408/425/429/502/503/504, and Neo4j transient/service-unavailable failures.

Authentication, validation, unsupported operations/statuses, Cypher client or
syntax errors, constraints, and affected-record mismatches never retry. A
malformed result after a write is passed once to a tool-less repair step; the
write-capable LF-70 action is not rerun. A write timeout returns
`MCP_WRITE_AMBIGUOUS`, `write_dispatched=true`, no affected count, and
`retryable=false`.

### DEC-016: Use explicit error contracts and no-mutation behavior

- **Choice:** Every controlled failure returns `OperationalError`; no failure
  may claim a successful mutation or fabricated request status.
- **Reason:** Typed errors let callers render safe responses, tests assert
  exact behavior, and later guardrails can be inserted without changing
  callers.
- **Alternatives considered:** Exceptions or free-text agent explanations were
  rejected because they are unstable cross-flow contracts.

The declared error vocabulary includes `MODEL_AUTHENTICATION_FAILURE` for
provider credential rejection and `MCP_OPERATION_FAILURE` for a non-transient,
non-authentication MCP operation failure that is neither a controlled contract
rejection nor an ambiguous dispatched write. Both are non-retryable and use
canonical safe dependency messages without raw provider/MCP text.

External dependency errors:

| Error | Detection | Response | Retry/fallback | Evidence |
| --- | --- | --- | --- | --- |
| Model transient failure | provider timeout/network/status classification | preserve correlation and retry classifier result | one retry after 500 ms; then `MODEL_TRANSIENT_FAILURE` | component log and trace |
| Model authentication failure | provider unauthorized/forbidden classification | stop before accepting model output | never retry; `MODEL_AUTHENTICATION_FAILURE` | safe dependency log and hard-gate scenario |
| Malformed model result | Pydantic/JSON Schema rejection | tool-less repair with validation | one repair; then `MALFORMED_AGENT_RESULT` | original validation errors, no secret/raw prompt logging |
| MCP read transient failure | transport/Neo4j transient classification | retain operation ID and retry | one retry after 500 ms; then `MCP_READ_TRANSIENT_FAILURE` | LF-70 trace |
| MCP write timeout | timeout after dispatch begins | stop flow and return ambiguous outcome | never retry; `MCP_WRITE_AMBIGUOUS` | operation/correlation IDs for direct graph inspection |
| MCP authentication failure | unauthorized/forbidden response | controlled dependency failure | never retry | error code and dependency health log |
| MCP operation failure | non-transient MCP/tool failure outside the more specific classes | stop the current operation | never retry; `MCP_OPERATION_FAILURE` | operation/correlation IDs and safe dependency log |
| Unexpected write count | confirmed result count is not one request | stop progression | never retry; direct graph assertion fails test | result plus independent query |
| LangFlow/PostgreSQL unavailable | health/API request failure | reject invocation | startup/readiness gate; no application fallback | container health/logs |

Caller-visible errors:

| Condition | Code/result | Safe user message | Recovery |
| --- | --- | --- | --- |
| Invalid input envelope | `INVALID_INPUT` | "I could not process this message safely." | correct caller metadata/input |
| Binding/request mismatch | `BINDING_REQUEST_MISMATCH` | "I could not resume this request safely." | inspect/reset test session |
| Duplicate or contradictory graph continuity | `GRAPH_CONTEXT_INCONSISTENT` | "I could not resume this request safely." | inspect/reset test session |
| Unsupported status | `UNSUPPORTED_PHASE1_STATUS` | "This request cannot be handled by the current intake flow." | continue in the later lifecycle flow |
| Stale expected status | `INVALID_EXPECTED_STATUS` | "The request changed before this update could be applied." | reload authoritative state |
| Concurrent field update | `CONCURRENT_MODIFICATION` | "The request changed before this update could be applied." | reload state, then retry the user action |
| Ambiguous write | `MCP_WRITE_AMBIGUOUS` | "I could not confirm whether the request update was saved." | inspect graph; do not repeat automatically |
| Model authentication failure | `MODEL_AUTHENTICATION_FAILURE` | "I could not process this request right now." | correct trusted provider configuration |
| MCP operation failure | `MCP_OPERATION_FAILURE` | "I could not access the request safely." | inspect dependency health and operation evidence |
| Internal validation failure | `INVALID_CONTRACT` | "I could not produce a safe response." | inspect trace; correct flow/contract |

Exact symbolic codes are centralized in an enum. Logs carry correlation,
session, operation, request, flow, and component IDs but no message text,
credentials, raw prompts, or unrestricted Cypher.

The final reconciled `plan.md` owns one exhaustive executable error matrix. For
every declared trigger it must specify the exact `FailureKind` mapping,
response/fallback, canonical safe message, structured logging fields and level,
and Phase 1 escalation. Escalation is one of: none, hard-gate failure, or manual
ambiguous-write graph inspection. Change 1 defines no production pager,
on-call alert, automated compensation, or recovery worker. The tables above
summarize design intent and do not replace that executable matrix.

### DEC-017: Use a layered verification pyramid

- **Choice:** Many deterministic unit/static tests support fewer deployed-flow
  integrations and minimal full-stack system scenarios. Gherkin is the
  business acceptance spine rather than the origin of every test.
- **Reason:** Unit and contract failures remain fast and diagnostic, while
  deployed tests still prove LangFlow, PostgreSQL, MCP, Neo4j, and restart
  behavior together.
- **Alternatives considered:** An E2E-heavy suite was rejected as slow and hard
  to diagnose. Mock-only tests were rejected because they cannot prove flow
  wiring, MCP access, graph writes, or persisted resumption.

| Level | Scope | Proposed location | Gate |
| --- | --- | --- | --- |
| Unit | contracts, completeness, transitions, identifiers, renderer, retry policy | `tests/unit/hulubul/` | hard |
| Component | LangFlow type conversion and error mapping | `tests/unit/hulubul/request_intake/entrypoints/` | hard |
| Contract/static | generated-schema drift, normalized flows, secrets, level-4 flow validation | `tests/contract/`, `tests/static/` | hard |
| Single flow | LF-70 and LF-10 through deployed API | `tests/integration/langflow/` | hard |
| Multi-flow | LF-00 routing, specialist invocation, trace boundary | `tests/integration/langflow/` | hard |
| System | one-message intake, clarification, restart/resumption | `tests/system/` | hard |
| BDD | actor-observable UC, capability, and NFR acceptance | `tests/features/`, `tests/steps/` | hard |
| Evaluation | recorded/fake and live model | `tests/evaluation/` | recorded hard, live soft |

Gherkin files are exactly:

```text
tests/features/delivery_request_intake.feature
tests/features/conversation_resumption.feature
```

They contain no API, Pydantic, JSON, MCP, Cypher, LFX, or component details.
Step definitions are implementation work and invoke LF-00 while direct Neo4j
queries independently assert request identity and state.

Gherkin covers actor-observable UC behavior and actor-observable capability or
NFR acceptance. UC tags are used only when the example genuinely projects that
use-case path; technical acceptance uses exact capability tags such as
`@CAP-delivery-request-intake`, `@CAP-domain-state-routing`, and
`@CAP-conversation-request-resumption`, plus applicable `@NFR-REL-001`,
`@NFR-REL-002`, `@NFR-DAT-004`, `@NFR-DAT-005`, `@NFR-CON-001`,
`@NFR-CON-002`, and `@NFR-CTL-001`. Internal engineering behavior such as
schema generation, adapter translation, raw-record validation, flow topology,
and retry classification is pytest-only. Every named capability scenario and
every expanded Gherkin example still maps to automated evidence.

The approved features expand to 18 intake examples and 16 resumption examples,
34 total. The five capability specs retain 95 named scenarios after adding the
first-time trusted-Sender case and removing the future-channel-adapter case.

The 20-case evaluation covers routing, missing-field extraction,
one-question selection, same-request resumption, stale transitions, unsupported
states, closed requests, and malformed-output repair. The deterministic gate
requires 20/20 exact decisions, schema-valid results, zero prohibited
operations, and zero extra requests/bindings. The soft NEAR/DeepSeek baseline
targets at least 18/20 exact decisions, 20/20 typed results, field micro-F1 of
at least 0.95, and zero safety-case mutations. Clarification judging remains
non-blocking over five runs with median >=8/10 and no zero criterion in any run.
Sanitized CI evidence is retained for 30 days; native traces and prohibited
message, prompt, credential, raw model/MCP, or unrestricted Cypher content are
not uploaded.

LangFlow 1.10.2 native traces may persist unredacted prompt, message, model, and
tool payloads. Change 1 therefore permits native tracing only with synthetic
simulated-Sender data in disposable acceptance and local environments.
Assertions project allowlisted metadata in memory and upload only that
projection. Real party or client data is prohibited from this Walking Skeleton;
production trace redaction is a later hardening requirement.

### DEC-018: Keep secrets and runtime configuration out of artifacts

- **Choice:** Commit `infra/langflow.env.example` with names and safe
  placeholders; retain `infra/langflow.env` and `infra/.env` as ignored runtime
  files. Rotate the active-looking local provider credential before
  implementation.
- **Reason:** Flow exports, OpenSpec, fixtures, logs, and Git must never contain
  provider, LangFlow, PostgreSQL, or Neo4j credentials.
- **Alternatives considered:** LangFlow database globals containing exported
  literal credentials were rejected because exports can leak values.

Required application configuration names include:

```text
HULUBUL_LLM_PROVIDER
HULUBUL_LLM_MODEL
HULUBUL_LLM_BASE_URL
HULUBUL_LLM_API_KEY
HULUBUL_LLM_TEMPERATURE
HULUBUL_NEO4J_MCP_URL
HULUBUL_OPERATIONAL_SCHEMA_VERSION
HULUBUL_RETRY_MAX_ATTEMPTS
HULUBUL_RETRY_DELAY_MS
HULUBUL_PHASE1_PLAYGROUND_ACTOR_ID
HULUBUL_PHASE1_PLAYGROUND_ACTOR_DISPLAY_NAME
```

The two Playground actor values exist only in ignored local/acceptance
environments. API actor values arrive as the request-variable headers defined
in DEC-013 and are never copied into committed environment maps.

The Change 1 baseline is model
`global/nearai/deepseek-v4-flash`, temperature `0`, MCP URL
`http://mcp-neo4j:8000/mcp/`, schema `1.0.0`, two total attempts, and 500 ms
retry delay. Model/provider values remain configurable; evaluation evidence
records the concrete settings and flow/schema hashes.

### DEC-019: Define component-specific anti-patterns

| Do not | Do instead | Consequence avoided |
| --- | --- | --- |
| Store authoritative lifecycle state in chat memory | Read Neo4j routing context before every route | Restart or model memory cannot send a request down the wrong lifecycle path |
| Give LF-00 or LF-10 raw MCP tools | Expose only typed LF-70 Run Flow operations | Domain agents cannot bypass the data boundary |
| Invent placeholder Receiver, Parcel, or Place nodes | Persist a sparse draft until actual facts arrive | Fabricated domain data does not become authoritative |
| Merge Agents by display name | Use trusted or request-scoped identifiers and deterministic Agent IDs | Different people with the same name are not conflated |
| Retry a write-capable LF-70 run after dispatch | Return an ambiguous result and inspect independently | Duplicate requests and transitions are not created |
| Connect both free-text and structured agent outputs | Render only the validated structured result | Duplicate model calls and divergent responses are avoided |
| Edit flows only in the UI/database | Pull, normalize, validate, review, and commit every change | Runtime behavior remains reproducible from Git |
| Put LangFlow imports in models or policy | Keep framework translation in entrypoints | Core policy remains fast and independently testable |
| Add FastAPI, repository wrappers, or empty layers preemptively | Add a boundary only when a real responsibility exists | Phase 1 does not accumulate architecture-shaped dead code |
| Trust LF-70 to verify its own write | Query Neo4j directly from integration/system tests | Hallucinated success and incorrect Cypher effects are detected |
| Copy provider secrets into globals, flow JSON, fixtures, or docs | Resolve ignored environment variables at runtime | Credentials do not enter Git or exported artifacts |
| Treat `complete` as coordination implemented | Return an informational no-op until Change 2 supplies LF-20 | Change 1 cannot accidentally perform deferred lifecycle work |

## Risks / Trade-offs

- **[Risk] LF-70 can generate unsafe or incorrect Cypher despite typed
  boundaries.** -> Mitigation: non-production database only, closed operations,
  pre-generated IDs, expected status, result validation, record-count checks,
  direct graph assertions, trace inspection, and mandatory replacement in the
  next hardening phase.
- **[Risk] A write timeout leaves outcome ambiguity.** -> Mitigation: never
  retry a dispatched write, retain operation/correlation/request/session IDs,
  return `MCP_WRITE_AMBIGUOUS`, and inspect Neo4j independently.
- **[Risk] Sparse drafts do not satisfy the complete LinkML aggregate.** ->
  Mitigation: make sparse status explicit, use a partial operational snapshot,
  and validate the complete conceptual subset before `complete`.
- **[Risk] Neo4j Community cannot enforce required properties, enums, or
  relationship cardinality.** -> Mitigation: strict input/output validation,
  constrained Cypher, uniqueness constraints where supported, and direct
  postcondition tests.
- **[Risk] A two-operation create/update plus status transition may leave a
  recoverable intermediate state.** -> Mitigation: each operation is atomic,
  routing recognizes `new` and `needsClarification`, completeness is recomputed
  from Neo4j, and results never claim an unconfirmed transition.
- **[Risk] Concurrent first messages or clarification turns race.** ->
  Mitigation: unique session binding, atomic request-plus-binding creation,
  compare-and-set on `updated` and status, exactly-one affected request, and a
  typed conflict that requires authoritative reload rather than write replay.
- **[Risk] LangFlow exports contain noisy or secret-bearing fields.** ->
  Mitigation: pinned LFX normalization, idempotence checks, structural secret
  tests, Gitleaks, and stable manifest IDs.
- **[Risk] Custom components become a hidden parallel application.** ->
  Mitigation: components only adapt types and invoke pure policy; visual flows
  remain the orchestration source; no Python duplicates of LF flows.
- **[Risk] Direct LangFlow API exposes a framework-specific external contract.**
  -> Mitigation: the endpoint is internal and Phase 1-only; operational models
  isolate the semantic contract so a later facade can wrap it.
- **[Risk] Live model behavior is nondeterministic.** -> Mitigation: hard gates
  use recorded/fake cases; live NEAR/DeepSeek checks preserve versioned evidence
  and remain soft until calibrated.
- **[Risk] Runtime versions drift from committed flows.** -> Mitigation: pin
  image/tool versions and digests, record `last_tested_version`, run strict LFX
  upgrade/validation checks, and update runtime plus flows in one reviewed
  change.
- **[Risk] An active-looking provider credential exists in an ignored local
  file.** -> Mitigation: rotate it before implementation, never print/read it
  into agent output, and create a safe committed example plus secret scanning.
  Git ignore prevents normal commits but does not protect a value from local
  processes, logs, backups, screenshots, or prior accidental sharing; this is a
  precaution, not evidence that the credential was committed.
- **[Trade-off] No FastAPI leaves the framework-specific LangFlow run envelope
  at the machine boundary.** -> Accepted because only test harnesses and local
  integration code call it in Change 1. Human users still see chat messages,
  not JSON. A later channel/API facade can translate a stable Hulubul contract
  into LangFlow's `input_value`, `session_id`, and nested output shape.
- **[Trade-off] No write idempotency limits safe retry behavior.** -> Accepted
  to preserve the Walking Skeleton appetite; Phase 2 must introduce stronger
  deterministic operation execution.

## Migration Plan

Here "migration" means moving the current repository and local runtime from
untracked prototype state to the reproducible Change 1 design, including safe
deployment and rollback. It is not the Phase 1-to-Phase 2 product transition;
that later transition is a separate OpenSpec change built on this baseline.

### Preparation

1. Rotate the existing local provider credential without copying its value.
2. Capture current PostgreSQL and Neo4j development backups before replacing
   runtime images or loading tracked flows.
3. Create ignored runtime files from committed examples and validate every
   required variable before startup.
4. Install and lock Python, LFX, testing, generation, linting, and
   import-linter dependencies.

### Additive deployment

1. Generate operational JSON Schemas and require a clean regeneration diff.
2. Normalize, secret-scan, strict-upgrade-check, and level-4 validate LF-70,
   LF-10, and LF-00.
3. Build/pull pinned PostgreSQL, Neo4j, MCP, and LangFlow images.
4. Start PostgreSQL and Neo4j and wait for authenticated health checks.
5. Apply existing domain constraints, then additive
   `operational-schema.cypher`.
6. Start MCP and verify its initialized tool inventory, not only TCP reachability.
7. Start LangFlow with PostgreSQL, read-only tracked component/flow mounts, and
   API-key authentication.
8. Verify exactly the manifest flow IDs and deploy in LF-70, LF-10, LF-00 order.
9. Run unit, architecture, schema-drift, static-flow, and secret gates.
10. Run LF-70, LF-10, and LF-00 integrations against isolated test state.
11. Run one-message intake and clarification/resumption system scenarios.
12. Restart LangFlow while retaining PostgreSQL and Neo4j, continue the same
    session, and assert the same request ID directly in Neo4j.
13. Run the 20-case deterministic evaluation and capture the soft live-model
    evidence, flow hashes, schema hash, image digests, and selected traces.

### Acceptance conditions

- All tracked flows pass strict LFX validation and reproduce in a clean
  LangFlow database.
- Only LF-70 traces show Neo4j MCP tool access.
- A complete first message creates exactly one complete request and binding.
- An incomplete first message creates exactly one draft and asks one focused
  question; a later answer completes that same request.
- Invalid, stale, unsupported, closed, and malformed cases produce their typed
  no-mutation behavior.
- LangFlow restart preserves conversation context and Neo4j request identity.
- Operational schema generation, unit, component, contract, integration,
  system, BDD, architecture, and deterministic evaluation gates pass.

### Rollback

1. Stop new LF-00 invocations and preserve current normalized remote flows and
   traces.
2. Check out the previous accepted Git revision and deploy its pinned LangFlow
   image and components.
3. Push prior flows in LF-70, LF-10, LF-00 order using unchanged stable IDs.
4. Re-run compatibility, smoke, and existing-session resumption checks before
   reopening invocation.
5. Leave additive operational labels, relationships, and properties in place;
   prior code may ignore them. Do not delete persisted request/binding state as
   part of code rollback.
6. Restore PostgreSQL/Neo4j backups only for an incompatible migration or
   verified corruption. Never use volume deletion as rollback outside a
   disposable acceptance environment.
7. Do not compensate or replay ambiguous writes automatically; inspect them by
   operation, correlation, session, and request IDs.

## Open Questions

No blocking design questions remain. The implementation plan must spell out
the exact Pydantic validators, component ports, flow nodes/edges/prompts,
Cypher statements, Make targets, test functions, and CI commands without
changing the decisions above. If a LangFlow 1.10.2 preflight disproves a
required component behavior, stop and re-shape this design rather than silently
substituting another architecture.
