# Phase 1 Request Intake Thread Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Project routing:** When subagent-driven execution is selected, implementation tasks MUST be dispatched to the project-scoped `implementer` agent, not a generic agent, under `AGENTS.md`. The controller owns worktree setup, task order, scope, and final verification; specification-conformance and code-quality reviews are separate dispatches; the implementer never reviews its own work.

**Goal:** Deliver the first Phase 1 vertical thread in which trusted Sender input creates, clarifies, resumes, and completes one persisted delivery request through exactly LF-00, LF-10, and LF-70, with deterministic hard evidence from contracts through retained-state acceptance.

**Architecture:** Use a proportional Cosmic Python functional core and thin LangFlow shell: strict operational Pydantic contracts in `hulubul.core.models`, pure intake decisions in `hulubul.request_intake.models` and `services`, and framework translation only in LangFlow component `entrypoints`. Git-normalized flows are authoritative, full LangFlow/PostgreSQL is the deployed runtime, Neo4j is authoritative business state, and LF-70 alone owns the temporary non-production LLM-to-MCP exception; there is no FastAPI service, repository abstraction, empty `adapters` package, or Python duplicate of visual-flow orchestration.

**Tech Stack:** Python `>=3.10,<3.15`; Poetry `2.3.2`; Pydantic `2.12.5`; LinkML `1.9.5`; LangFlow/LFX `1.10.2`; pytest `8.4.1`; pytest-bdd `8.1.0`; pytest-cov `7.0.0`; httpx `0.28.1`; Neo4j driver `5.28.2`; Testcontainers `4.10.0`; import-linter `2.3`; Ruff `0.12.5`; mypy `1.17.1`; tox `4.28.4`; Docker Compose; PostgreSQL 16; Neo4j 5.26 Community; `mcp-neo4j-cypher==0.6.0`.

## Global Constraints

- **Exact Change 1 cut line:** "The cut line is the transition of one persisted request to `complete`, including one-message and multi-turn clarification paths." No LF-20, coordination, matching, transporter action, channel adapter, or behavior after `complete` is included.
- Deploy exactly three flows in order: LF-70 Data Access, LF-10 Request Intake, LF-00 Main Router. No LF-20 key, file, UUID, component, edge, remote flow, test stub, or empty flow is permitted.
- Pin LangFlow to `langflowai/langflow:1.10.2@sha256:ae6f9afd03bc032dc2989ece49791fcf83871230aff9d6e485c8e1ebada1e70f`, PostgreSQL to `postgres:16-trixie@sha256:33f923b05f64ca54ac4401c01126a6b92afe839a0aa0a52bc5aeb5cc958e5f20`, Neo4j to `neo4j:5.26-community@sha256:362542416de6c09a971484d1893878016cc3b5cdec166e54b1c824a220ecd6b9`, and MCP Python to `python:3.12-slim@sha256:57cd7c3a7a273101a6485ba99423ee568157882804b1124b4dd04266317710de` (linux/amd64 manifest `sha256:cab2dbf575e971934a81e4622f5aba17aa7929719bd7e31033a3a83b97fd0464`).
- Keep `mcp-neo4j-cypher==0.6.0`, `pip-tools==7.5.2`, and the hash-locked MCP dependency output reproducible; the expected lock SHA-256 from the pinned preflight is `49dbf0d85ec72bfbbe64c0ce0b2558edd8e80c60e2b3c7c1dab2987ff354ad16`.
- Every top-level cross-flow contract carries `schema_version="1.0.0"` and `correlation_id`; all operational models use `extra="forbid"`, `strict=True`, `str_strip_whitespace=True`, and `frozen=True`; absence is `None`, not an empty string.
- Apply one uniform operational Change 1 text boundary after stripping surrounding whitespace: inbound message, Receiver name, pickup text, drop-off text, parcel declared-content text, and a supplied preferred period are each `1..4000` characters. This does not alter LinkML.
- The clarification order is exactly Receiver identity, pickup location, drop-off location, parcel declared content. Report the complete missing set, ask at most one question, and prioritize an invalid field supplied in the current interaction.
- Duplicate bindings, duplicate active-request relationships, duplicate active targets, and contradictory continuity return exactly `GRAPH_CONTEXT_INCONSISTENT`; a binding whose request cannot be resolved returns `BINDING_REQUEST_MISMATCH`; unknown persisted status returns `UNSUPPORTED_REQUEST_STATUS`.
- Retry eligible model calls and MCP reads once after exactly `500 ms`, for two total attempts. Never retry authentication, validation, unsupported operation/status, Cypher client/syntax, constraint, affected-count, stale-state, or dispatched-write failures. A malformed post-write result gets one tool-less repair of existing raw output; a write timeout after dispatch returns `MCP_WRITE_AMBIGUOUS` and is never replayed.
- Native LangFlow tracing is allowed only for generated synthetic data with `identity_assurance=simulated` in disposable acceptance and local Change 1 environments. Real party/client data is prohibited; raw native traces, messages, prompts, model/MCP payloads, credentials, unrestricted Cypher, and arbitrary environment mappings are never uploaded.
- Hard gates: LinkML lint; stable LinkML generation drift excluding byte-unstable OWL/SHACL ordering; operational-schema drift; Ruff, mypy, import-linter; branch coverage `>=80%`; flow normalization/secrets/strict level-4/strict-upgrade checks; unit/component/contract/static tests; recorded evaluation `20/20` exact and typed with zero prohibited operations and zero extra requests/bindings; all integration/system tests; all 34 BDD examples (18 intake and 16 resumption); LF-70-only MCP evidence; and retained-state restart evidence.
- Soft gates: live `global/nearai/deepseek-v4-flash` at temperature `0` targets `>=18/20` exact, `20/20` typed, field micro-F1 `>=0.95`, and zero safety mutations; the clarification judge runs exactly five times and requires median `>=8/10` plus no zero criterion in any run. Both remain manual/non-blocking; latency and token usage are informational only.
- Retain only sanitized CI evidence for exactly 30 days. Never retain or upload raw native traces, message text, prompts, credentials, raw model/MCP content, or unrestricted Cypher.
- **Developer-only precondition for original task 1.1:** an agent cannot complete task 1.1 until the developer rotates the provider credential exposed to the preflight process and explicitly confirms rotation. No agent may inspect, open, print, hash, validate, copy, or otherwise read the old value or any ignored `infra/.env`/`infra/langflow.env` file.
- `model/linkml/` remains the conceptual source of truth. Never hand-edit `model/generated/`; `OperationalConversationBinding` and operational contracts remain application-owned outside LinkML.
- Preserve `make lint` as LinkML lint only. Python lint is `make lint-python`; no task may redefine the existing target's semantics.
- No production or test code reads secrets to verify them. Secret scanners inspect `git ls-files` only and report path plus rule ID, never matching text. Committed examples contain names and empty/safe non-credential values only.
- Every important LF-70 write is asserted independently through the Neo4j driver; LF-70 never verifies itself. No caller contract accepts Cypher. Only LF-70 contains `MCPToolsComponent` and protocol-discovered tools `get_neo4j_schema`, `read_neo4j_cypher`, and `write_neo4j_cypher`.
- Git-normalized JSON and `langflow/flow-manifest.yaml` are authoritative; PostgreSQL contains deployed copies, messages, and traces. Exact serialized edge handles come only from a pinned-runtime export, never from handwritten React Flow JSON.
- Each proposed commit is a review point, not authorization. Before any commit, present fresh focused GREEN output, `git status`, and the focused diff, then wait for explicit developer approval. Never commit automatically and never amend without explicit instruction.

---

## File And Responsibility Map

### Foundation And Generated Contracts

| Path | Action | Responsibility |
| --- | --- | --- |
| `.gitignore` | Modify | Keep runtime environments and generated reports ignored while retaining source datasets/manifests. |
| `infra/langflow.env.example` | Create | Safe application/LangFlow variable names and non-secret defaults only. |
| `pyproject.toml` | Modify | Package `src/hulubul`, pin dependency groups, configure pytest/coverage/Ruff/mypy. |
| `poetry.lock` | Create | Exact resolved Python graph; `make install` never mutates it. |
| `tox.ini` | Create | Default fast/architecture/schema environments plus opt-in integration/system/evaluation environments. |
| `.importlinter` | Create | Enforce inward core, pure intake models, and services-without-entrypoints boundaries. |
| `Makefile` | Modify | Add namespaced Python, schema, flow, acceptance, evaluation, evidence, and CI targets without changing `lint`. |
| `scripts/check_committed_secrets.py` | Create | Scan tracked text only and disclose path/rule, never a matching value. |
| `scripts/gen_operational_schemas.py` | Create | Deterministically generate draft-2020-12 schemas and hash manifest. |
| `schemas/operational/v1/*.schema.json` | Generate | Exactly 11 committed cross-flow schema documents; generated, never manually edited. |
| `schemas/operational/v1/manifest.json` | Generate | Stable schema IDs, versions, filenames, and SHA-256 values without host/time data. |

### Proportional Python Core And Shell

| Path | Action | Responsibility |
| --- | --- | --- |
| `src/hulubul/__init__.py` | Create | Package version only. |
| `src/hulubul/core/models/operational/base.py` | Create | Strict base classes, constrained types, version constants, JSON-mode validation. |
| `src/hulubul/core/models/operational/enums.py` | Create | All semantic vocabulary, prefixes, limits, operation/error/retry enums. |
| `src/hulubul/core/models/operational/errors.py` | Create | Typed errors, canonical safe-message/category/retry maps, validation conversion. |
| `src/hulubul/core/models/operational/envelope.py` | Create | Trusted actor context and main flow input. |
| `src/hulubul/core/models/operational/routing.py` | Create | Raw routing lookup validation, deterministic typed adaptation, RouterInput/IntakeInput wrappers, routing context/result, and contradiction validators. |
| `src/hulubul/core/models/operational/intake.py` | Create | Intake facts/updates/complete facts/result contracts. |
| `src/hulubul/core/models/operational/snapshots.py` | Create | Sparse request snapshot, graph IDs, mutation confirmation. |
| `src/hulubul/core/models/operational/data_operations.py` | Create | Exactly five operation variants, discriminated union, result invariants/adapters. |
| `src/hulubul/request_intake/models/completeness.py` | Create | Required-field order, missing set, immediate/complete validation, one-question selection. |
| `src/hulubul/request_intake/models/transitions.py` | Create | Exact four-edge transition and compare-and-set decision. |
| `src/hulubul/request_intake/services/graph_identifiers.py` | Create | UUID4 graph IDs and UUID5 enduring identities. |
| `src/hulubul/request_intake/services/data_operation_policy.py` | Create | Caller capability plus operation/result pre/postconditions. |
| `src/hulubul/request_intake/services/retry_policy.py` | Create | Two-attempt retry/no-replay/tool-less-repair decisions. |
| `src/hulubul/request_intake/services/rendering.py` | Create | Deterministic safe text from validated results. |
| `src/hulubul/request_intake/entrypoints/langflow/components/hulubul/*.py` | Create | Execution envelope, contract input/result, operation boundary, retry decision, renderer, and request builder LFX adapters. |

No `src/hulubul/**/adapters/`, repository, FastAPI, settings loader, custom MCP wrapper, or Python flow orchestrator is created. Package `__init__.py` files export stable public APIs and are not empty architectural markers.

### Neo4j, Runtime, And Flow Assets

| Path | Action | Responsibility |
| --- | --- | --- |
| `infra/cypher/operational-schema.cypher` | Create | Unique `OperationalConversationBinding.sessionId` only. |
| `infra/scripts/neo4j-setup-schema.sh` | Modify | Apply domain then operational schema and await online constraints. |
| `infra/scripts/mcp-readiness.py` | Create | Initialize MCP and require the exact three-tool inventory through service DNS. |
| `infra/mcp/Dockerfile` | Modify | Pin MCP base digest and install hash-locked dependencies. |
| `infra/mcp/requirements.in` | Create | Direct `mcp-neo4j-cypher==0.6.0` input. |
| `infra/mcp/requirements.txt` | Modify/generated | Hash-locked transitive MCP graph. |
| `infra/docker-compose.yaml` | Modify | Pinned development topology, health/readiness order, read-only source mounts, local ports, persistence, API key mode. |
| `infra/docker-compose.test.yaml` | Create | Unique disposable acceptance override with recorded model and ephemeral volumes. |
| `infra/test/recorded-model.Dockerfile` | Create | Acceptance-only OpenAI-compatible deterministic model service. |
| `langflow/flow-manifest.yaml` | Create | Version-1 three-flow IDs, stable component IDs, references, runtime variable names. |
| `langflow/.lfx/environments.yaml` | Create | Local/CI URLs and API-key environment names only. |
| `langflow/flows/10-lf-70-data-access.json` | Create from pinned export | LF-70 request boundary, model, agent, one MCP toolkit, retry/result boundary. |
| `langflow/flows/20-lf-10-request-intake.json` | Create from pinned export | LF-10 intake agent with LF-70 as its sole logical tool. |
| `langflow/flows/30-lf-00-main-router.json` | Create from pinned export | Chat input, mandatory context prefetch, bounded router, LF-10, structured/rendered outputs. |
| `scripts/inspect_langflow_components.py` | Create | Capture pinned static/dynamic component schemas and generated edge handles without secrets. |
| `scripts/normalize_langflow_flows.py` | Create | Pinned LFX normalization plus restoration of manifest-allowlisted variable names only. |
| `scripts/validate_langflow_assets.py` | Create | Enforce manifest, stable topology, public ports, environment allowlist, no LF-20/no MCP outside LF-70. |

### Test And Evidence Assets

| Path | Responsibility |
| --- | --- |
| `tests/unit/hulubul/core/models/operational/test_*.py` | Strict contracts and invariant matrices. |
| `tests/unit/hulubul/request_intake/models/test_*.py` | Completeness and transition decisions. |
| `tests/unit/hulubul/request_intake/services/test_*.py` | IDs, authorization, retry, rendering. |
| `tests/unit/hulubul/request_intake/entrypoints/langflow/components/hulubul/test_*.py` | Thin LFX translation and safe failures. |
| `tests/contract/test_operational_schema_generation.py` | Operational schema/manifest determinism and drift. |
| `tests/static/test_*.py` | Foundation, secret, pin, flow, CI, and documentation contracts. |
| `tests/fixtures/neo4j/change1_contexts.py` | Isolated all-status, closed-precedence, sparse, concurrency, and constrained continuity fixtures. |
| `tests/support/acceptance_types.py` | Frozen `TrustedActor`, `Conversation`, `FlowReply`, graph and stack fingerprints. |
| `tests/support/langflow_client.py` | Authenticated LF-00 invocation with private API key. |
| `tests/support/graph_probe.py` | Parameterized direct Neo4j assertions, independent of LF-70. |
| `tests/support/postgres_probe.py` | Read-only message metadata projection. |
| `tests/support/trace_metadata_probe.py` | Read-only native trace/span safe-column projection. |
| `tests/support/recorded_model/{app,contracts,controller}.py` | Deterministic OpenAI-compatible scripts, call metadata, barriers. |
| `tests/fixtures/recorded_model/change1_flow_scripts.jsonl` | Synthetic recorded response sequences for flow integration/system tests. |
| `tests/integration/neo4j/*.py` | Operational schema, fixture, Testcontainer, and MCP protocol evidence. |
| `tests/integration/langflow/*.py` | Flow auth/drift/read/write/intake/router/persistence/trace/model evidence. |
| `tests/system/test_request_intake*.py` | End-to-end, race, restart, and negative behavior. |
| `tests/steps/test_delivery_request_intake.py` | Bind all 18 approved intake examples without editing the feature. |
| `tests/steps/test_conversation_resumption.py` | Bind all 16 approved resumption examples without editing the feature. |
| `tests/evaluation/datasets/change1_intake_v1.yaml` | Exact 20-case synthetic decision/effect corpus. |
| `tests/evaluation/fixtures/change1_recorded_model_v1.jsonl` | Deterministic outputs keyed by case/turn. |
| `tests/evaluation/{contracts,metrics,evidence}.py` | Strict corpus types, exact metrics, sanitized hash-addressed evidence. |
| `tests/contract/evidence/change1.yaml` | Capability/spec/Gherkin heading to pytest-node evidence map. |
| `scripts/build_change1_evidence.py` | Allowlisted release evidence with versions, hashes, images, and hard results. |
| `.github/workflows/ci.yaml` | Hard static/recorded gate and hard full-stack acceptance jobs using Make only. |
| `.github/workflows/live-evaluation.yaml` | Manual, non-blocking live model/judge workflow. |

## Locked Shared Interfaces

### Operational Vocabulary And Signatures

```python
MIN_HUMAN_TEXT_LENGTH = 1
MAX_HUMAN_TEXT_LENGTH = 4_000
RETRY_MAX_ATTEMPTS = 2
RETRY_DELAY_MS = 500
SCHEMA_VERSION = "1.0.0"

class RequestStatus(str, Enum):
    NEW = "new"
    NEEDS_CLARIFICATION = "needsClarification"
    COMPLETE = "complete"
    OPTIONS_PROPOSED = "optionsProposed"
    WAITING_RESPONSE = "waitingResponse"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    PICK_UP_PLANNED = "pickUpPlanned"
    PICKED_UP = "pickedUp"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"

POST_INTAKE_STATUSES = (
    RequestStatus.OPTIONS_PROPOSED,
    RequestStatus.WAITING_RESPONSE,
    RequestStatus.ACCEPTED,
    RequestStatus.REJECTED,
    RequestStatus.PICK_UP_PLANNED,
    RequestStatus.PICKED_UP,
    RequestStatus.DELIVERED,
    RequestStatus.CANCELLED,
)

class IntakeField(str, Enum):
    RECEIVER_IDENTITY = "receiver_identity"
    PICKUP_LOCATION = "pickup_location"
    DROP_OFF_LOCATION = "drop_off_location"
    PARCEL_DECLARED_CONTENT = "parcel_declared_content"
    PREFERRED_PERIOD = "preferred_period"

class DataOperation(str, Enum):
    GET_REQUEST_ROUTING_CONTEXT = "getRequestRoutingContext"
    CREATE_DELIVERY_REQUEST = "createDeliveryRequest"
    READ_DELIVERY_REQUEST = "readDeliveryRequest"
    UPDATE_DELIVERY_REQUEST = "updateDeliveryRequest"
    SET_REQUEST_STATUS = "setRequestStatus"

class ErrorCode(str, Enum):
    INVALID_INPUT = "INVALID_INPUT"
    INVALID_CONTRACT = "INVALID_CONTRACT"
    OPERATION_NOT_ALLOWED = "OPERATION_NOT_ALLOWED"
    BINDING_REQUEST_MISMATCH = "BINDING_REQUEST_MISMATCH"
    GRAPH_CONTEXT_INCONSISTENT = "GRAPH_CONTEXT_INCONSISTENT"
    UNSUPPORTED_PHASE1_STATUS = "UNSUPPORTED_PHASE1_STATUS"
    UNSUPPORTED_REQUEST_STATUS = "UNSUPPORTED_REQUEST_STATUS"
    INVALID_EXPECTED_STATUS = "INVALID_EXPECTED_STATUS"
    INVALID_STATUS_TRANSITION = "INVALID_STATUS_TRANSITION"
    CONCURRENT_MODIFICATION = "CONCURRENT_MODIFICATION"
    AFFECTED_RECORD_COUNT_MISMATCH = "AFFECTED_RECORD_COUNT_MISMATCH"
    MODEL_TRANSIENT_FAILURE = "MODEL_TRANSIENT_FAILURE"
    MODEL_AUTHENTICATION_FAILURE = "MODEL_AUTHENTICATION_FAILURE"
    MALFORMED_AGENT_RESULT = "MALFORMED_AGENT_RESULT"
    MCP_READ_TRANSIENT_FAILURE = "MCP_READ_TRANSIENT_FAILURE"
    MCP_WRITE_AMBIGUOUS = "MCP_WRITE_AMBIGUOUS"
    MCP_AUTHENTICATION_FAILURE = "MCP_AUTHENTICATION_FAILURE"
    MCP_OPERATION_FAILURE = "MCP_OPERATION_FAILURE"
    DEPENDENCY_UNAVAILABLE = "DEPENDENCY_UNAVAILABLE"
```

Additional closed enums are `ActorRole(sender)`, `IdentityAssurance(simulated)`, `InvocationSource(api, playground)`, `BindingState(absent, bound, inconsistent)`, `RoutingStage(intake, complete, closed, unsupported, failure)`, `RouterOutcome(routed, informational, failure)`, `RouterTarget(intake, none)`, `RoutingReason(noBinding, intakeInProgress, intakeComplete, requestClosed, unsupportedStatus, invalidContext, lookupFailed)`, `IntakeOutcome(clarificationRequired, requestComplete, failure)`, `DataOperationOutcome(confirmed, rejected, ambiguous)`, `CallerFlow(LF-00, LF-10, LF-70)`, `ErrorCategory(input, contract, authorization, state, concurrency, dependency, internal)`, `ErrorEscalation(none, hardGateFailure, manualAmbiguousWriteGraphInspection)`, `DependencyKind(model, mcpRead, mcpWrite)`, `FailureKind(timeout, connection, protocol, httpStatus, malformedResult, neo4jTransient, serviceUnavailable, authentication, validation, unsupportedOperation, cypherClient, cypherSyntax, constraint, affectedCount)`, and `RetryAction(retry, repairRawResult, fail)`. `ContractKind` contains exactly `main-flow-input`, `router-input`, `intake-input`, `routing-context`, `router-result`, `intake-facts`, `intake-result`, `data-operation-request`, `data-operation-result`, `delivery-request-snapshot`, and `operational-error`.

Exact public signatures:

```text
validate_json_mapping(model_type: type[ModelT], value: Mapping[str, Any]) -> ModelT
operational_error(code: ErrorCode, *, correlation_id: UUID, violations: tuple[FieldViolation, ...] = ()) -> OperationalError
validation_error_to_operational_error(error: ValidationError, *, correlation_id: UUID) -> OperationalError
adapt_routing_lookup(record: RoutingLookupRecord, *, schema_version: Literal["1.0.0"], correlation_id: UUID, session_id: SessionId) -> RoutingContext
missing_required_fields(facts: IntakeFacts) -> tuple[IntakeField, ...]
select_clarification_field(missing_fields: tuple[IntakeField, ...], *, invalid_field: IntakeField | None = None) -> IntakeField | None
validate_complete_facts(facts: IntakeFacts) -> CompleteIntakeFacts
evaluate_transition(*, actual_status: RequestStatus | None, actual_updated_at: datetime | None, expected_status: RequestStatus | None, expected_updated_at: datetime | None, target_status: RequestStatus) -> TransitionDecision
new_graph_identifiers(*, actor_id: str, receiver_stable_id: str | None, include_receiver: bool, include_parcel: bool, include_pickup: bool, include_drop_off: bool, uuid_factory: Callable[[], UUID] = uuid4) -> GraphIdentifiers
enduring_agent_id(stable_identifier: str) -> str
request_scoped_receiver_identifier(request_uuid: UUID) -> str
authorize_operation(caller: CallerFlow, operation: DataOperation) -> OperationalError | None
validate_operation_preconditions(request: DataOperationRequest) -> OperationalError | None
validate_result_postconditions(request: DataOperationRequest, result: DataOperationResult) -> OperationalError | None
decide_retry(context: RetryContext) -> RetryDecision
render_router_result(result: RouterResult) -> str
render_intake_result(result: IntakeResult) -> str
render_operational_error(error: OperationalError) -> str
validate_data_operation_request(value: Mapping[str, Any]) -> DataOperationRequest
data_operation_request_schema() -> dict[str, Any]
```

`ActorContext(actor_id, display_name, actor_role=sender, identity_assurance=simulated)` and `MainFlowInput(schema_version, correlation_id, message_id, session_id, actor, source, message)` separate trusted metadata from prose. `RoutingLookupRecord` is an internal, non-generated strict model over `bindingCount`, `activeRelationshipCount`, `activeTargetCount`, and request rows containing nullable `requestStatusRaw`; only `adapt_routing_lookup` may inspect that raw value. `RoutingContext` carries session, binding state/counts, request ID, typed nullable request status, closed timestamp, routing stage, and typed error. `RouterInput` and `IntakeInput` each wrap `envelope: MainFlowInput` plus `routing_context: RoutingContext`; wrapper/nested versions and correlations and both session IDs must match, while `IntakeInput` additionally accepts only an error-free intake stage with either no binding/no request or exactly one bound `new`/`needsClarification` request. `RouterResult` carries outcome, target, reason, request ID, safe user message, and error. `IntakeFacts` carries Sender IDs/name plus nullable Receiver, pickup, drop-off, content, and period; `IntakeResult` carries outcome, request/status/facts, full missing tuple, at most one clarification field, safe user message, and error. `DeliveryRequestSnapshot` includes persisted `created_at`, authoritative `updated_at`, nullable `closed_at`, sparse facts, and exact missing tuple.

The five request payloads are exactly: routing context `{}`, create `{identifiers, facts}`, read `{request_id}`, update `{request_id, expected_updated_at, expected_status, updates, identifiers}`, status `{request_id, expected_updated_at, expected_status, target_status}`. Create accepts neither `created_at` nor `updated_at`; Neo4j owns both timestamps and a confirmed create result returns equal authoritative `created_at` and `updated_at`. Every operation request adds `operation_id`, caller, session, actor, schema version, and correlation. `DataOperationResult` adds operation/outcome/success/write-dispatched, request/status/count, typed result, and typed error. One module-level `TypeAdapter` validates the discriminated union before caller authorization.

Canonical clarification questions:

```python
CLARIFICATION_QUESTIONS = {
    IntakeField.RECEIVER_IDENTITY: "Who should receive the parcel?",
    IntakeField.PICKUP_LOCATION: "Where should the parcel be picked up?",
    IntakeField.DROP_OFF_LOCATION: "Where should the parcel be delivered?",
    IntakeField.PARCEL_DECLARED_CONTENT: "What does the parcel contain?",
    IntakeField.PREFERRED_PERIOD: "What preferred delivery period should I record?",
}
```

Canonical caller-visible messages are owned only by the following exhaustive policy; callers and models cannot override them. Logging fields are exact subsets of the nine-key allowlist `correlation_id`, `operation_id`, `request_id`, `session_id`, `flow_id`, `component_id`, `retry_attempt`, `error_code`, and `schema_version`. A row's log-field list is its maximum allowed projection: known identifiers are emitted, while an `operation_id`, `request_id`, or retry attempt that does not yet exist or cannot be resolved is omitted rather than set to null or fabricated. `correlation_id`, `flow_id`, `component_id`, `error_code`, and `schema_version` are always available for a controlled error. Escalation is exactly `none`, `hard-gate failure`, or `manual ambiguous-write graph inspection`; Change 1 defines no production pager.

The centralized `ErrorCode` policy is executable and callers cannot override any column:

| Error code | Category | Retryable | Safe message | Log level | Exact log fields | Escalation |
| --- | --- | --- | --- | --- | --- | --- |
| `INVALID_INPUT` | `input` | false | `I could not process this message safely.` | `WARNING` | `correlation_id, session_id, flow_id, component_id, error_code, schema_version` | `none` |
| `INVALID_CONTRACT` | `contract` | false | `I could not produce a safe response.` | `ERROR` | `correlation_id, operation_id, session_id, flow_id, component_id, error_code, schema_version` | `hard-gate failure` |
| `OPERATION_NOT_ALLOWED` | `authorization` | false | `This operation is not allowed.` | `WARNING` | `correlation_id, operation_id, session_id, flow_id, component_id, error_code, schema_version` | `hard-gate failure` |
| `BINDING_REQUEST_MISMATCH` | `state` | false | `I could not resume this request safely.` | `ERROR` | `correlation_id, request_id, session_id, flow_id, component_id, error_code, schema_version` | `hard-gate failure` |
| `GRAPH_CONTEXT_INCONSISTENT` | `state` | false | `I could not resume this request safely.` | `ERROR` | `correlation_id, request_id, session_id, flow_id, component_id, error_code, schema_version` | `hard-gate failure` |
| `UNSUPPORTED_PHASE1_STATUS` | `state` | false | `This request cannot be handled by the current intake flow.` | `INFO` | `correlation_id, request_id, session_id, flow_id, component_id, error_code, schema_version` | `none` |
| `UNSUPPORTED_REQUEST_STATUS` | `state` | false | `I could not resume this request safely.` | `ERROR` | `correlation_id, request_id, session_id, flow_id, component_id, error_code, schema_version` | `hard-gate failure` |
| `INVALID_EXPECTED_STATUS` | `concurrency` | false | `The request changed before this update could be applied.` | `INFO` | `correlation_id, operation_id, request_id, session_id, flow_id, component_id, error_code, schema_version` | `none` |
| `INVALID_STATUS_TRANSITION` | `state` | false | `This request update is not allowed.` | `WARNING` | `correlation_id, operation_id, request_id, session_id, flow_id, component_id, error_code, schema_version` | `hard-gate failure` |
| `CONCURRENT_MODIFICATION` | `concurrency` | false | `The request changed before this update could be applied.` | `INFO` | `correlation_id, operation_id, request_id, session_id, flow_id, component_id, error_code, schema_version` | `none` |
| `AFFECTED_RECORD_COUNT_MISMATCH` | `state` | false | `I could not confirm the request update safely.` | `ERROR` | `correlation_id, operation_id, request_id, session_id, flow_id, component_id, error_code, schema_version` | `hard-gate failure` |
| `MODEL_TRANSIENT_FAILURE` | `dependency` | true | `I could not process this request right now.` | `ERROR` | `correlation_id, session_id, flow_id, component_id, retry_attempt, error_code, schema_version` | `hard-gate failure` |
| `MODEL_AUTHENTICATION_FAILURE` | `dependency` | false | `I could not process this request right now.` | `ERROR` | `correlation_id, session_id, flow_id, component_id, error_code, schema_version` | `hard-gate failure` |
| `MALFORMED_AGENT_RESULT` | `contract` | false | `I could not produce a safe response.` | `ERROR` | `correlation_id, operation_id, session_id, flow_id, component_id, retry_attempt, error_code, schema_version` | `hard-gate failure` |
| `MCP_READ_TRANSIENT_FAILURE` | `dependency` | true | `I could not load this request right now.` | `ERROR` | `correlation_id, operation_id, request_id, session_id, flow_id, component_id, retry_attempt, error_code, schema_version` | `hard-gate failure` |
| `MCP_WRITE_AMBIGUOUS` | `dependency` | false | `I could not confirm whether the request update was saved.` | `ERROR` | `correlation_id, operation_id, request_id, session_id, flow_id, component_id, error_code, schema_version` | `manual ambiguous-write graph inspection` |
| `MCP_AUTHENTICATION_FAILURE` | `dependency` | false | `I could not access the request safely.` | `ERROR` | `correlation_id, operation_id, session_id, flow_id, component_id, error_code, schema_version` | `hard-gate failure` |
| `MCP_OPERATION_FAILURE` | `dependency` | false | `I could not access the request safely.` | `ERROR` | `correlation_id, operation_id, request_id, session_id, flow_id, component_id, error_code, schema_version` | `hard-gate failure` |
| `DEPENDENCY_UNAVAILABLE` | `dependency` | true | `I could not process this request right now.` | `ERROR` | `correlation_id, session_id, flow_id, component_id, retry_attempt, error_code, schema_version` | `hard-gate failure` |

Each ErrorCode has one trigger and response/fallback policy:

| Error code | Exact trigger | Response/fallback |
| --- | --- | --- |
| `INVALID_INPUT` | Invalid Message/session/actor invocation envelope | Reject before model/tool/mutation; caller must correct trusted metadata/input |
| `INVALID_CONTRACT` | Strict cross-flow/operation/result validation failure | Reject boundary value; invoke no downstream model/tool and correct the flow/contract |
| `OPERATION_NOT_ALLOWED` | Known fully valid operation outside typed caller capability | Reject before MCP; no fallback operation |
| `BINDING_REQUEST_MISMATCH` | Binding exists but no one resolvable DeliveryRequest target exists | Fail closed without mutation; inspect/reset the synthetic test session |
| `GRAPH_CONTEXT_INCONSISTENT` | Duplicate/contradictory binding, relationship, target, request cardinality, or null non-closed status | Fail closed without mutation; inspect/reset the synthetic test session |
| `UNSUPPORTED_PHASE1_STATUS` | One of the eight recognized post-intake statuses | Return no-mutation result; continue only in a later lifecycle change |
| `UNSUPPORTED_REQUEST_STATUS` | Unknown non-null raw status on a non-closed request | Set typed status to `None`, fail closed without mutation, and inspect persisted state |
| `INVALID_EXPECTED_STATUS` | Authoritative status differs from exact expected status | Do not mutate/replay; reload authoritative state before a new user action |
| `INVALID_STATUS_TRANSITION` | Requested status edge is outside the exact Change 1 table | Do not mutate/replay; correct the requested transition |
| `CONCURRENT_MODIFICATION` | Authoritative timestamp/fill-only state changed since the snapshot, or unique-binding race loser | Preserve winner, do not replay; reload state before a new user action |
| `AFFECTED_RECORD_COUNT_MISMATCH` | A purported confirmed mutation affects other than exactly one request aggregate | Stop progression; independently inspect graph evidence |
| `MODEL_TRANSIENT_FAILURE` | Eligible model failure remains after the single retry | Stop current interaction without mutation; caller may start a later interaction |
| `MODEL_AUTHENTICATION_FAILURE` | Provider returns unauthorized/forbidden before valid output | Stop without retry/mutation; correct trusted provider configuration |
| `MALFORMED_AGENT_RESULT` | The one tool-less repair remains invalid | Reject output without inferring success; correct model/flow contract behavior |
| `MCP_READ_TRANSIENT_FAILURE` | Eligible MCP read failure remains after the single retry | Stop without mutation; caller may start a later interaction |
| `MCP_WRITE_AMBIGUOUS` | Write dispatch started or cannot be disproved and confirmation is unavailable | Never replay; preserve identifiers and perform manual graph inspection |
| `MCP_AUTHENTICATION_FAILURE` | MCP returns unauthorized/forbidden | Stop without retry/mutation; correct trusted MCP configuration |
| `MCP_OPERATION_FAILURE` | Non-transient, non-authentication MCP/tool/Cypher failure without confirmed effect | Stop without retry/mutation; inspect dependency health and safe operation evidence |
| `DEPENDENCY_UNAVAILABLE` | LangFlow/PostgreSQL or another required startup dependency is unready | Reject invocation through readiness gate; no application fallback |

The retry classifier implements this exhaustive `FailureKind` trigger matrix. "Pre-dispatch" is valid only when dispatch is positively disproved; otherwise an MCP write is treated as dispatched/ambiguous. Every terminal code uses the exact message, logging, and escalation row above.

| Failure kind | Exact trigger/context | Decision and terminal code |
| --- | --- | --- |
| `timeout` | Model attempt 1; model attempt 2 | Retry once after 500 ms; then `MODEL_TRANSIENT_FAILURE` |
| `timeout` | MCP read attempt 1; MCP read attempt 2 | Retry once after 500 ms; then `MCP_READ_TRANSIENT_FAILURE` |
| `timeout` | MCP write dispatch started or cannot be disproved | Never retry; `MCP_WRITE_AMBIGUOUS` |
| `timeout` | MCP write positively pre-dispatch | Never retry; `MCP_OPERATION_FAILURE` |
| `connection` | Model attempt 1/2 | Retry once after 500 ms; then `MODEL_TRANSIENT_FAILURE` |
| `connection` | MCP read attempt 1/2 | Retry once after 500 ms; then `MCP_READ_TRANSIENT_FAILURE` |
| `connection` | MCP write positively pre-dispatch; otherwise | `MCP_OPERATION_FAILURE`; otherwise `MCP_WRITE_AMBIGUOUS`, never retry |
| `protocol` | Model attempt 1/2 | Retry once after 500 ms; then `MODEL_TRANSIENT_FAILURE` |
| `protocol` | MCP read or positively pre-dispatch write | Never retry; `MCP_OPERATION_FAILURE` |
| `protocol` | MCP write dispatch started or cannot be disproved | Never retry; `MCP_WRITE_AMBIGUOUS` |
| `httpStatus` | Model 408/425/429/500/502/503/504 attempt 1/2 | Retry once after 500 ms; then `MODEL_TRANSIENT_FAILURE` |
| `httpStatus` | MCP read 408/425/429/502/503/504 attempt 1/2 | Retry once after 500 ms; then `MCP_READ_TRANSIENT_FAILURE` |
| `httpStatus` | Model or MCP 401/403 | Never retry; `MODEL_AUTHENTICATION_FAILURE` or `MCP_AUTHENTICATION_FAILURE` by dependency |
| `httpStatus` | Any other MCP status, with write dispatch positively disproved | Never retry; `MCP_OPERATION_FAILURE` |
| `httpStatus` | MCP write status after dispatch starts or dispatch cannot be disproved | Never retry; `MCP_WRITE_AMBIGUOUS` |
| `malformedResult` | Existing raw model output, before or after a write | One tool-less repair with no operation replay; second invalid value yields `MALFORMED_AGENT_RESULT` |
| `neo4jTransient` | MCP read attempt 1/2 | Retry once after 500 ms; then `MCP_READ_TRANSIENT_FAILURE` |
| `neo4jTransient` | MCP write positively pre-dispatch; otherwise | `MCP_OPERATION_FAILURE`; otherwise `MCP_WRITE_AMBIGUOUS`, never retry |
| `serviceUnavailable` | Model or MCP read attempt 1/2 | Retry once after 500 ms; then `MODEL_TRANSIENT_FAILURE` or `MCP_READ_TRANSIENT_FAILURE` |
| `serviceUnavailable` | MCP write positively pre-dispatch; otherwise | `MCP_OPERATION_FAILURE`; otherwise `MCP_WRITE_AMBIGUOUS`, never retry |
| `authentication` | Provider or MCP rejects credentials | Never retry; `MODEL_AUTHENTICATION_FAILURE` or `MCP_AUTHENTICATION_FAILURE` by dependency |
| `validation` | Strict inbound/cross-flow/operation contract rejection | Never retry; `INVALID_CONTRACT` |
| `unsupportedOperation` | Known, fully contract-valid operation outside caller capability | Never retry; `OPERATION_NOT_ALLOWED` |
| `cypherClient` | MCP reports a client/data error before a confirmed effect | Never retry; `MCP_OPERATION_FAILURE` |
| `cypherSyntax` | MCP reports generated Cypher syntax failure before a confirmed effect | Never retry; `MCP_OPERATION_FAILURE` |
| `constraint` | Unique session binding loser; any other constraint before confirmed effect | Never retry; classify the expected race as `CONCURRENT_MODIFICATION`, otherwise `MCP_OPERATION_FAILURE` |
| `affectedCount` | Confirmed mutation count is not exactly one request aggregate | Never retry; `AFFECTED_RECORD_COUNT_MISMATCH` |

### Stable Flow Manifest And Topology

```yaml
schema_version: "1.0.0"
langflow_version: "1.10.2"
deployment_order: [lf-70-data-access, lf-10-request-intake, lf-00-main-router]
flows:
  lf-70-data-access:
    id: 94f6774d-ebc7-5bf1-8486-886f91886a5f
    file: flows/10-lf-70-data-access.json
    public_input_component_id: HulubulDataOperationRequestBoundary-hlb-lf-70-request-v1
    public_result_component_id: HulubulDataOperationResultBoundary-hlb-lf-70-result-v1
    chat_output_component_id: null
    run_flow_references: []
  lf-10-request-intake:
    id: 6843ae79-147f-55d4-a25b-01d6143a12cc
    file: flows/20-lf-10-request-intake.json
    public_input_component_id: HulubulContractInputBoundary-hlb-lf-10-input-v1
    public_result_component_id: HulubulContractResultBoundary-hlb-lf-10-result-v1
    chat_output_component_id: null
    run_flow_references:
      - {component_id: RunFlow-hlb-lf-10-data-access-v1, target_flow_id: 94f6774d-ebc7-5bf1-8486-886f91886a5f}
  lf-00-main-router:
    id: 38b7ee64-26c8-5d4d-97e4-6e62a0fcb557
    file: flows/30-lf-00-main-router.json
    public_input_component_id: ChatInput-hlb-lf-00-message-v1
    public_result_component_id: HulubulContractResultBoundary-hlb-lf-00-result-v1
    chat_output_component_id: ChatOutput-hlb-lf-00-chat-v1
    run_flow_references:
      - {component_id: RunFlow-hlb-lf-00-routing-context-v1, target_flow_id: 94f6774d-ebc7-5bf1-8486-886f91886a5f}
      - {component_id: RunFlow-hlb-lf-00-request-intake-v1, target_flow_id: 6843ae79-147f-55d4-a25b-01d6143a12cc}
runtime_bindings:
  - {component_id: OpenAIModel-hlb-lf-70-model-v1, fields: {model_name: HULUBUL_LLM_MODEL, openai_api_base: HULUBUL_LLM_BASE_URL, api_key: HULUBUL_LLM_API_KEY}}
  - {component_id: OpenAIModel-hlb-lf-10-model-v1, fields: {model_name: HULUBUL_LLM_MODEL, openai_api_base: HULUBUL_LLM_BASE_URL, api_key: HULUBUL_LLM_API_KEY}}
  - {component_id: OpenAIModel-hlb-lf-00-model-v1, fields: {model_name: HULUBUL_LLM_MODEL, openai_api_base: HULUBUL_LLM_BASE_URL, api_key: HULUBUL_LLM_API_KEY}}
```

Semantic public boundaries are fixed, while serialized LangFlow field names and edge handles are accepted only from the pinned-runtime inspection in Task 31. LF-70 accepts one canonical `DataOperationRequest` and returns one validated `DataOperationResult`; LF-10 accepts one canonical `IntakeInput` for direct integration invocation and returns one validated `IntakeResult`. During LF-00 orchestration, the LF-10 Run Flow receives validated `envelope` and `routing_context` on fixed advanced inputs that are excluded from the Router model's callable schema; a deterministic boundary assembles `IntakeInput`. Tool Mode exposes only the inspected Run Flow tool, public result nodes have no outgoing edge and emit `JSON`, and no public/model field can replace trusted metadata. Tests freeze the actual 1.10.2 ports after inspection rather than assuming `MessageTextInput` or handwritten handles.

LF-70 component IDs are request boundary, `OpenAIModel-hlb-lf-70-model-v1`, `Agent-hlb-lf-70-data-access-v1`, `MCPTools-hlb-lf-70-neo4j-v1`, `HulubulRetryDecision-hlb-lf-70-retry-v1`, and result boundary. LF-10 IDs are input boundary, `OpenAIModel-hlb-lf-10-model-v1`, `Agent-hlb-lf-10-request-intake-v1`, `RunFlow-hlb-lf-10-data-access-v1`, and result boundary. LF-00 IDs are `ChatInput-hlb-lf-00-message-v1`, `HulubulExecutionEnvelope-hlb-lf-00-envelope-v1`, `HulubulDataOperationRequestBuilder-hlb-lf-00-routing-request-v1`, `RunFlow-hlb-lf-00-routing-context-v1`, `HulubulContractInputBoundary-hlb-lf-00-router-input-v1`, `OpenAIModel-hlb-lf-00-model-v1`, `Agent-hlb-lf-00-router-v1`, `RunFlow-hlb-lf-00-request-intake-v1`, result boundary, `HulubulDeterministicRenderer-hlb-lf-00-renderer-v1`, and `ChatOutput-hlb-lf-00-chat-v1`.

Semantic topology is fixed: LF-70 validated request -> Agent, model -> Agent, one MCP toolkit -> Agent tools, structured response -> retry/result boundary -> public JSON; LF-10 fixed envelope/context edges -> deterministic strict `IntakeInput` assembly -> Agent, model -> Agent, LF-70 Tool Mode -> Agent tools, structured response -> strict result -> public JSON; LF-00 Chat Input -> Message-only trusted envelope -> LF-70 context request -> strict raw lookup validation and typed adaptation -> deterministic strict `RouterInput` assembly -> bounded Router Agent, with LF-10 as its only tool through fixed advanced envelope/context inputs, then RouterResult boundary fans out to public JSON and deterministic renderer -> Chat Output. Context read is a mandatory predecessor, never an optional Router tool. Every model node fixes temperature `0`, `stream=false`, `seed=1`, `max_retries=0`, and reviewed timeout `5` in acceptance.

### Neo4j Operation Intent

The operational schema is exactly:

```cypher
CREATE CONSTRAINT operationalconversationbinding_sessionId_unique IF NOT EXISTS
FOR (n:OperationalConversationBinding) REQUIRE n.sessionId IS UNIQUE;
```

LF-70 generates parameterized Cypher equivalent to these reviewed intents, never accepting query text from callers:

- `getRequestRoutingContext(session_id)`: optional-match binding and `BINDS_ACTIVE_REQUEST`, return binding/relationship/target cardinalities plus DeliveryRequest `id`, `hasStatus`, `updated`, and `closed`; only `0/0/0` or exactly `1/1/1` with one DeliveryRequest is valid.
- `readDeliveryRequest(request_id)`: match one request; optional-match exactly one Sender participation and sparse Receiver/Parcel/pickup/drop-off subgraphs; return request timestamps/status/period and typed arrays; singular duplicates fail validation.
- `createDeliveryRequest`: in one transaction obtain one Neo4j timestamp, merge Sender Agent by pre-generated ID/identifier, create request as `new`, Sender role, unique binding and relationship, and only supplied Receiver/Parcel/Place subgraphs; assign equal request `created`/`updated` plus binding timestamps and return request ID/status/both request timestamps/count. A session uniqueness loser rolls back the entire graph.
- `updateDeliveryRequest`: match request by ID, exact expected `updated`, exact expected status in the intake set, and absent target facts; add only currently absent supplied subgraphs and fill an absent preferred period without replacing/clearing it; set a fresh UTC `updated`; return exactly one. A zero-row result receives one non-mutating classification read and no replay.
- `setRequestStatus`: match by ID, expected `updated`, expected status, and one of `new->needsClarification`, `new->complete`, `needsClarification->complete`; set status and fresh UTC `updated`; return previous/current/count. `none->new` exists only inside atomic create.

Routing/read Cypher shape:

```cypher
OPTIONAL MATCH (binding:OperationalConversationBinding {sessionId: $session_id})
OPTIONAL MATCH (binding)-[bindingRel:BINDS_ACTIVE_REQUEST]->(target)
WITH collect(DISTINCT binding) AS bindings, collect(bindingRel) AS bindingRels,
     collect(DISTINCT target) AS targets
RETURN size(bindings) AS bindingCount, size(bindingRels) AS activeRelationshipCount,
       size(targets) AS activeTargetCount,
        [target IN targets WHERE target:DeliveryRequest |
          {requestId: target.id, requestStatusRaw: target.hasStatus,
          updated: toString(target.updated),
          closed: CASE WHEN target.closed IS NULL THEN null ELSE toString(target.closed) END}] AS requests
```

```cypher
MATCH (request:DeliveryRequest {id: $request_id})
OPTIONAL MATCH (request)-[:HAS_SENDER]->(senderRole:Sender)-[:PLAYED_BY]->(senderAgent:Agent)
OPTIONAL MATCH (request)-[:HAS_RECEIVER]->(receiverRole:Receiver)-[:PLAYED_BY]->(receiverAgent:Agent)
OPTIONAL MATCH (request)-[:HAS_DELIVERY_ITEM]->(parcel:Parcel)
OPTIONAL MATCH (request)-[:HAS_PICK_UP_LOCATION]->(pickup:Place)
OPTIONAL MATCH (request)-[:HAS_DROP_OFF_LOCATION]->(dropoff:Place)
RETURN request, collect(DISTINCT senderRole), collect(DISTINCT receiverRole),
       collect(DISTINCT parcel), collect(DISTINCT pickup), collect(DISTINCT dropoff)
```

Atomic create and all optional subgraphs execute in the same transaction:

```cypher
WITH datetime() AS now
MERGE (senderAgent:Agent {id: $sender.agent_id})
ON CREATE SET senderAgent.identifier = $sender.identifier, senderAgent.name = $sender.name
WITH now, senderAgent WHERE senderAgent.identifier = $sender.identifier
CREATE (request:DeliveryRequest {id: $request_id, hasStatus: 'new', created: now, updated: now, preferredPeriod: $preferred_period})
CREATE (senderRole:Sender {id: $sender.role_id})
CREATE (request)-[:HAS_SENDER]->(senderRole)-[:PLAYED_BY]->(senderAgent)
CREATE (binding:OperationalConversationBinding {sessionId: $session_id, createdAt: now, updatedAt: now})
CREATE (binding)-[:BINDS_ACTIVE_REQUEST]->(request)
FOREACH (_ IN CASE WHEN $receiver IS NULL THEN [] ELSE [1] END |
  MERGE (receiverAgent:Agent {id: $receiver.agent_id})
  ON CREATE SET receiverAgent.identifier = $receiver.identifier, receiverAgent.name = $receiver.name
  CREATE (receiverRole:Receiver {id: $receiver.role_id})
  CREATE (request)-[:HAS_RECEIVER]->(receiverRole)-[:PLAYED_BY]->(receiverAgent))
FOREACH (_ IN CASE WHEN $parcel IS NULL THEN [] ELSE [1] END |
  CREATE (parcel:Parcel {id: $parcel.id, declaredContent: $parcel.declared_content})
  CREATE (request)-[:HAS_DELIVERY_ITEM]->(parcel))
FOREACH (_ IN CASE WHEN $pickup IS NULL THEN [] ELSE [1] END |
  CREATE (pickup:Place {id: $pickup.id, name: $pickup.name,
    hasIdentifier: $pickup.has_identifier, hasType: $pickup.has_type})
  CREATE (request)-[:HAS_PICK_UP_LOCATION]->(pickup))
FOREACH (_ IN CASE WHEN $dropoff IS NULL THEN [] ELSE [1] END |
  CREATE (dropoff:Place {id: $dropoff.id, name: $dropoff.name,
    hasIdentifier: $dropoff.has_identifier, hasType: $dropoff.has_type})
  CREATE (request)-[:HAS_DROP_OFF_LOCATION]->(dropoff))
RETURN request.id AS requestId, request.hasStatus AS currentStatus,
       toString(request.created) AS created, toString(request.updated) AS updated,
       1 AS affectedRequests
```

Optimistic update/status guards:

```cypher
MATCH (request:DeliveryRequest {id: $request_id})
WHERE request.updated = datetime($expected_updated_at)
  AND request.hasStatus = $expected_status
  AND $expected_status IN ['new', 'needsClarification']
  AND ($receiver IS NULL OR NOT EXISTS { MATCH (request)-[:HAS_RECEIVER]->(:Receiver) })
  AND ($parcel IS NULL OR NOT EXISTS { MATCH (request)-[:HAS_DELIVERY_ITEM]->(:Parcel) })
  AND ($pickup IS NULL OR NOT EXISTS { MATCH (request)-[:HAS_PICK_UP_LOCATION]->(:Place) })
  AND ($dropoff IS NULL OR NOT EXISTS { MATCH (request)-[:HAS_DROP_OFF_LOCATION]->(:Place) })
  AND ($preferred_period IS NULL OR request.preferredPeriod IS NULL)
WITH request, datetime() AS now
FOREACH (_ IN CASE WHEN $receiver IS NULL THEN [] ELSE [1] END |
  MERGE (receiverAgent:Agent {id: $receiver.agent_id})
  ON CREATE SET receiverAgent.identifier = $receiver.identifier, receiverAgent.name = $receiver.name
  CREATE (receiverRole:Receiver {id: $receiver.role_id})
  CREATE (request)-[:HAS_RECEIVER]->(receiverRole)-[:PLAYED_BY]->(receiverAgent))
FOREACH (_ IN CASE WHEN $parcel IS NULL THEN [] ELSE [1] END |
  CREATE (parcel:Parcel {id: $parcel.id, declaredContent: $parcel.declared_content})
  CREATE (request)-[:HAS_DELIVERY_ITEM]->(parcel))
FOREACH (_ IN CASE WHEN $pickup IS NULL THEN [] ELSE [1] END |
  CREATE (pickup:Place {id: $pickup.id, name: $pickup.name,
    hasIdentifier: $pickup.has_identifier, hasType: $pickup.has_type})
  CREATE (request)-[:HAS_PICK_UP_LOCATION]->(pickup))
FOREACH (_ IN CASE WHEN $dropoff IS NULL THEN [] ELSE [1] END |
  CREATE (dropoff:Place {id: $dropoff.id, name: $dropoff.name,
    hasIdentifier: $dropoff.has_identifier, hasType: $dropoff.has_type})
  CREATE (request)-[:HAS_DROP_OFF_LOCATION]->(dropoff))
SET request.preferredPeriod = coalesce($preferred_period, request.preferredPeriod), request.updated = now
RETURN request.id AS requestId, request.hasStatus AS currentStatus,
       toString(request.updated) AS updated, 1 AS affectedRequests
```

```cypher
MATCH (request:DeliveryRequest {id: $request_id})
WHERE request.updated = datetime($expected_updated_at)
  AND request.hasStatus = $expected_status
  AND [$expected_status, $target_status] IN [
    ['new', 'needsClarification'], ['new', 'complete'], ['needsClarification', 'complete']]
WITH request, request.hasStatus AS previousStatus, datetime() AS now
SET request.hasStatus = $target_status, request.updated = now
RETURN request.id AS requestId, previousStatus, request.hasStatus AS currentStatus,
       toString(request.updated) AS updated, 1 AS affectedRequests
```

### Acceptance Harness, Persistence, And Observability

```text
LangFlowClient.run_lf00(conversation: Conversation, message: str) -> FlowReply
GraphProbe.snapshot_for_session(session_id: str) -> GraphSnapshot
GraphProbe.request_count_for_session(session_id: str) -> int
GraphProbe.binding_count_for_session(session_id: str) -> int
GraphProbe.orphan_request_ids(namespace: str) -> frozenset[str]
GraphProbe.mutation_fingerprint(request_id: str) -> str
PostgresProbe.messages_for_session(*, flow_id: UUID, session_id: str) -> tuple[PersistedMessageMetadata, ...]
TraceMetadataProbe.spans_for_session(*, flow_ids: tuple[UUID, ...], session_id: str) -> tuple[NativeSpanMetadata, ...]
RecordedModelController.prime(script: RecordedScenarioScript) -> None
RecordedModelController.reset() -> None
RecordedModelController.call_metadata() -> tuple[RecordedCallMetadata, ...]
RecordedModelController.arm_barrier(*, barrier_id: str, participants: int) -> None
StackController.fingerprint() -> StackFingerprint
StackController.restart_langflow_only() -> None
StackController.wait_for_langflow_ready() -> None
```

The PostgreSQL evidence adapter selects only `id, flow_id, run_id, session_id, timestamp, sender, sender_name, is_output, error, edit, category` from `message`, parameterized by flow/session. The trace adapter selects only trace/flow/session IDs and span ID/parent/name/type/status/start/end/latency/kind from joined `trace` and `span`; it never selects `inputs`, `outputs`, `error`, or `attributes`, and it never calls payload-bearing native trace HTTP endpoints.

Allowed observability keys are exactly `correlation_id`, `operation_id`, `request_id`, `session_id`, `flow_id`, `component_id`, `retry_attempt`, `error_code`, and `schema_version`. Prohibited categories are message text/body/content; keys/authorization/cookies/passwords/connection strings; raw prompts/templates; raw model input/output; raw MCP responses/tool arguments; unrestricted query/Cypher text; and arbitrary environment maps. Failures print case/span ID and key category only.

The deterministic model seam retains the production `OpenAIModel` component and supplies acceptance-only values: `HULUBUL_LLM_BASE_URL=http://recorded-model:8080/v1`, `HULUBUL_LLM_MODEL=recorded-change1`, temperature `0`, stream false, seed `1`, SDK retries `0`, timeout `5`. A process-memory random API key is passed only to disposable containers. The server exposes `/healthz`, `/v1/models`, `/v1/chat/completions`, and network-local control endpoints `/__control/v1/scenarios`, `/__control/v1/barriers/{barrier_id}`, `/__control/v1/calls`, and `/__control/v1/state`; it stores only response key, ordinal, HTTP outcome, tool names, and barrier ID, never request bodies, headers, prompts, arguments, or generated content.

LangFlow API authentication uses `LANGFLOW_API_KEY_SOURCE=env`. Tests prove missing/wrong keys return 403 and an environment-sourced key succeeds. API keys are private fields with `repr=False`; values are never command arguments, logs, reports, or committed flow data.

### Evaluation, Make, CI, BDD, And Evidence Contracts

The exact 20-case dataset inventory is C01 complete without period; C02 complete with period; C03 pickup+parcel sparse; C04 minimal intention; C05 Receiver only missing; C06 Receiver/destination/content missing; C07 blank destination; C08 4001 pickup; C09 4000 destination; C10 natural destination reply; C11 multi-turn accumulation; C12 complete no-op; C13 closed no-op; C14 rejected; C15 cancelled; C16 unresolved binding; C17 duplicate active targets; C18 unknown status; C19 stale state; C20 malformed result then one valid tool-less repair. C14 and C15 are representative post-intake unsupported states; exhaustive behavior for all eight recognized post-intake statuses belongs to the parameterized routing unit, integration, and system matrices in Tasks 6, 33, 45, 46, 48, and 55 rather than expanding this locked 20-case corpus. Every dataset case declares exact route, facts, missing set, clarification field, ordered logical operations, status, error, request/binding deltas, extra cardinality, and prohibited-operation count.

Canonical Make targets are `install`, unchanged `lint`, `lint-python`, `format-python`, `format-check-python`, `typecheck`, `check-architecture`, `check-model-generated`, `operational-schemas`, `check-operational-schemas`, `check-secrets`, `check-flows`, `test-unit`, `test-integration`, `test-system`, `test-bdd`, `test-evaluation-recorded`, `test-evaluation-live`, `test-evaluation-judge`, `acceptance-up`, `acceptance-ready`, `acceptance-deploy`, `preflight-langflow-1-10-2`, `acceptance-diagnostics`, `acceptance-down`, `release-evidence`, `ci-static`, `ci-acceptance`, and `ci`. GitHub workflow project logic invokes Make targets only. Hard acceptance always tears down its unique disposable project and volumes; sanitized artifacts retain 30 days.

BDD modules consume the two approved feature files unchanged: `tests/steps/test_delivery_request_intake.py` must collect 18 expanded examples and `tests/steps/test_conversation_resumption.py` must collect 16, totaling 34. Business steps call typed `IntakeWorld` methods; HTTP, LangFlow, MCP, JSON, Cypher, timestamps, and compare-and-set vocabulary remain out of Gherkin. BDD maps actor-observable UC/capability/NFR behavior only; schema generation, raw-record adaptation, topology, retry classification, and other engineering mechanics remain pytest-only.

`tests/contract/evidence/change1.yaml` maps all 38 capability requirement groups, all 95 named capability scenarios, and all 34 expanded Gherkin examples to stable pytest node IDs. Source keys are qualified and collision-proof: `spec:<capability>/<requirement>/<scenario>` for capability scenarios and `feature:<feature-file>/<scenario>/<example-ordinal>` for Gherkin examples; ordinals are one-based in source order, and plain headings or generic test-case IDs are forbidden. The pre-implementation map may point to planned node IDs before collection; execution evidence separately proves each referenced node collects and passes. `scripts/build_change1_evidence.py` emits only change name, git SHA, UTC generation time, versions, dataset/schema/manifest/three-flow SHA-256 values, three pinned image references, and hard test outcomes. The validator parses all five specs and both features, rejects missing/unknown/duplicate assignments, and never includes test data values. Reports live under ignored `reports/change1/`.

---

## Implementation Tasks

### Task 1: Credential Safety Foundation

**Original task IDs:** 1.1

**Files:**
- Create: `infra/langflow.env.example`
- Create: `scripts/check_committed_secrets.py`
- Create: `tests/static/test_committed_secrets.py`
- Modify: `.gitignore`
- Test: `tests/static/test_committed_secrets.py`

**Interfaces:**
- Consumes: developer confirmation that the exposed provider credential was rotated; `git ls-files -z` path inventory only.
- Produces: `scan_tracked_files(repo: Path) -> tuple[SecretFinding, ...]`, where `SecretFinding(path: str, rule_id: str)` contains no matched value; safe names `HULUBUL_LLM_PROVIDER`, `HULUBUL_LLM_MODEL`, `HULUBUL_LLM_BASE_URL`, `HULUBUL_LLM_API_KEY`, `HULUBUL_LLM_TEMPERATURE`, `HULUBUL_NEO4J_MCP_URL`, `HULUBUL_OPERATIONAL_SCHEMA_VERSION`, `HULUBUL_RETRY_MAX_ATTEMPTS`, `HULUBUL_RETRY_DELAY_MS`, `HULUBUL_PHASE1_PLAYGROUND_ACTOR_ID`, `HULUBUL_PHASE1_PLAYGROUND_ACTOR_DISPLAY_NAME`, `LANGFLOW_API_KEY_SOURCE`, `LANGFLOW_API_KEY`.

- [ ] **Step 1: Stop for the developer-only precondition (2-5 min)**

Record only the developer's explicit statement that rotation is complete. If confirmation is absent, stop this task. Do not inspect the old value or open any ignored environment file.

- [ ] **Step 2: Add focused failing tests (2-5 min)**

```python
def test_secret_scan_reports_path_and_rule_without_matching_value(tmp_path):
    finding = run_scan_on_tracked_fixture(tmp_path, "synthetic-provider-token")
    assert finding.path.endswith("tracked.txt")
    assert finding.rule_id == "credential-pattern"
    assert "synthetic-provider-token" not in repr(finding)
```

- [ ] **Step 3: Run RED (2-5 min)**

Run: `poetry run pytest tests/static/test_committed_secrets.py -q`

Expected: FAIL because `scripts/check_committed_secrets.py` and `infra/langflow.env.example` do not exist.

- [ ] **Step 4: Add the minimal scanner and safe example (2-5 min each file)**

```dotenv
HULUBUL_LLM_PROVIDER=near
HULUBUL_LLM_MODEL=global/nearai/deepseek-v4-flash
HULUBUL_LLM_BASE_URL=https://example.invalid/v1
HULUBUL_LLM_API_KEY=
HULUBUL_LLM_TEMPERATURE=0
HULUBUL_NEO4J_MCP_URL=http://mcp-neo4j:8000/mcp/
HULUBUL_OPERATIONAL_SCHEMA_VERSION=1.0.0
HULUBUL_RETRY_MAX_ATTEMPTS=2
HULUBUL_RETRY_DELAY_MS=500
HULUBUL_PHASE1_PLAYGROUND_ACTOR_ID=
HULUBUL_PHASE1_PLAYGROUND_ACTOR_DISPLAY_NAME=
LANGFLOW_API_KEY_SOURCE=env
LANGFLOW_API_KEY=
```

Implement the scanner with `subprocess.run(["git", "ls-files", "-z"], check=True, capture_output=True)`, skip binary files, apply named regex rules, and print only `<path>: <rule_id>`. Keep `infra/langflow.env`, `infra/.env`, and `reports/change1/` ignored.

- [ ] **Step 5: Run GREEN and self-review (2-5 min)**

Run: `poetry run pytest tests/static/test_committed_secrets.py -q && poetry run python scripts/check_committed_secrets.py`

Expected: all scanner/example/ignore tests PASS; the scanner exits 0 and emits no credential value. Review `git diff -- .gitignore infra/langflow.env.example scripts/check_committed_secrets.py tests/static/test_committed_secrets.py` and confirm no ignored environment file was touched.

- [ ] **Step 6: Propose commit and wait (2-5 min)**

Propose `chore(security): add secret-safe LangFlow configuration checks`. Show fresh evidence and wait for explicit developer approval; do not commit automatically.

### Task 2: Locked Python Package Baseline

**Original task IDs:** 1.2

**Files:**
- Modify: `pyproject.toml`
- Create: `poetry.lock`
- Create: `src/hulubul/__init__.py`
- Create: `tests/unit/test_project_foundation.py`
- Test: `tests/unit/test_project_foundation.py`

**Interfaces:**
- Consumes: Poetry `2.3.2`; existing generator entrypoints.
- Produces: importable `hulubul` package with `__version__ = "0.1.0"`; locked groups `langflow`, `test`, `integration`, `quality`; unchanged three existing generator scripts plus `gen-operational-schemas`.

- [ ] **Step 1: Write package/entrypoint tests (2-5 min)**

```python
def test_hulubul_package_is_importable():
    import hulubul
    assert hulubul.__version__ == "0.1.0"

def test_existing_generator_entrypoints_remain_declared(pyproject):
    assert set(pyproject["tool"]["poetry"]["scripts"]) >= {
        "gen-neo4j-constraints", "gen-neomodel", "gen-mermaid-classdiagram"
    }
```

- [ ] **Step 2: Run RED (2-5 min)**

Run: `poetry run pytest tests/unit/test_project_foundation.py -q`

Expected: FAIL with `ModuleNotFoundError: hulubul`.

- [ ] **Step 3: Apply exact dependency/package edits (2-5 min per group)**

```toml
packages = [
  { include = "hulubul", from = "src" },
  { include = "gen_neo4j_constraints.py", from = "scripts" },
  { include = "gen_neomodel.py", from = "scripts" },
  { include = "gen_mermaid_classdiagram.py", from = "scripts" },
  { include = "gen_operational_schemas.py", from = "scripts" },
]
[tool.poetry.dependencies]
python = ">=3.10,<3.15"
linkml = "1.9.5"
pydantic = "2.12.5"
[tool.poetry.group.langflow.dependencies]
lfx = "1.10.2"
[tool.poetry.group.test.dependencies]
pytest = "8.4.1"
pytest-bdd = "8.1.0"
pytest-cov = "7.0.0"
[tool.poetry.group.integration.dependencies]
httpx = "0.28.1"
neo4j = "5.28.2"
testcontainers = {version = "4.10.0", extras = ["neo4j"]}
[tool.poetry.group.quality.dependencies]
import-linter = "2.3"
ruff = "0.12.5"
mypy = "1.17.1"
tox = "4.28.4"
```

Run `poetry lock --regenerate` in the isolated worktree. Stop if LFX `1.10.2` and Pydantic v2 cannot resolve; do not weaken those pins.

- [ ] **Step 4: Run GREEN (2-5 min)**

Run: `poetry check --lock && poetry install --with test,quality,langflow,integration && poetry run pytest tests/unit/test_project_foundation.py -q`

Expected: lock check and install exit 0; foundation tests PASS.

- [ ] **Step 5: Self-review and propose commit (2-5 min)**

Confirm `poetry show --tree` contains exact direct pins and no direct FastAPI/neomodel/settings dependency. Propose `build: add locked Python application package`; wait for developer approval and do not commit automatically.

### Task 3: Python Quality And Tox Configuration

**Original task IDs:** 1.3

**Files:**
- Modify: `pyproject.toml`
- Create: `tox.ini`
- Modify: `tests/unit/test_project_foundation.py`
- Test: `tests/unit/test_project_foundation.py`

**Interfaces:**
- Consumes: locked package/dependencies from Task 2.
- Produces: pytest markers `integration`, `system`, `evaluation`, `live_model`; branch coverage source `hulubul`, hard floor 80; Ruff/mypy config; tox envs `py310`, `architecture`, `schemas`, `integration`, `system`, `evaluation`, `evaluation-live`, with only the first three default.

- [ ] **Step 1: Add configuration assertions (2-5 min)**

```python
def test_default_tox_envs_are_fast(tox_config):
    assert tox_config["tox"]["env_list"] == "py310, architecture, schemas"
    assert "evaluation-live" in tox_config
```

- [ ] **Step 2: Run RED (2-5 min)**

Run: `poetry run pytest tests/unit/test_project_foundation.py::test_default_tox_envs_are_fast -q`

Expected: FAIL because `tox.ini` is absent.

- [ ] **Step 3: Add exact quality settings (2-5 min per config block)**

```toml
[tool.pytest.ini_options]
addopts = "--strict-config --strict-markers"
testpaths = ["tests"]
markers = ["integration", "system", "evaluation", "live_model"]
[tool.coverage.run]
branch = true
source = ["hulubul"]
[tool.coverage.report]
fail_under = 80
show_missing = true
[tool.ruff]
line-length = 100
target-version = "py310"
[tool.ruff.lint]
select = ["E", "F", "I", "N", "UP", "B", "SIM", "RUF"]
[tool.mypy]
python_version = "3.10"
strict = true
```

Configure tox to package the wheel, pin the direct test dependencies, run unit tests by default, and keep live evaluation outside `env_list`.

- [ ] **Step 4: Run GREEN (2-5 min)**

Run: `poetry run pytest tests/unit/test_project_foundation.py -q && poetry run tox -av`

Expected: tests PASS; tox lists all seven environments and marks only `py310`, `architecture`, `schemas` as defaults.

- [ ] **Step 5: Self-review and propose commit (2-5 min)**

Confirm live/model/system environments are not default and overall production branch coverage remains `>=80%`. Propose `build: configure Python quality and test environments`; wait for developer approval.

### Task 4: Canonical Make Targets

**Original task IDs:** 1.4

**Files:**
- Modify: `Makefile`
- Modify: `tests/unit/test_project_foundation.py`
- Test: `tests/unit/test_project_foundation.py`

**Interfaces:**
- Consumes: Poetry, tox, existing LinkML `lint`/generation targets.
- Produces: the canonical Make target set listed under [Locked Shared Interfaces](#locked-shared-interfaces); `lint` still invokes only `linkml-lint`.

- [ ] **Step 1: Add Make contract tests (2-5 min)**

```python
def test_make_lint_still_invokes_linkml_lint_only(makefile_text):
    body = target_body(makefile_text, "lint")
    assert "linkml-lint" in body
    assert "ruff" not in body
```

- [ ] **Step 2: Run RED (2-5 min)**

Run: `poetry run pytest tests/unit/test_project_foundation.py::test_python_make_targets_exist -q`

Expected: FAIL naming missing `lint-python`, `test-unit`, and `ci-static` targets.

- [ ] **Step 3: Add targets without changing existing `lint` (2-5 min per target group)**

```make
install:
	poetry install --with test,quality,langflow,integration
lint-python:
	poetry run ruff check src tests scripts
format-check-python:
	poetry run ruff format --check src tests scripts
typecheck:
	poetry run mypy src/hulubul scripts tests
test-unit:
	poetry run pytest tests/unit --cov=hulubul --cov-branch --cov-fail-under=80
check-architecture:
	poetry run lint-imports
operational-schemas:
	poetry run gen-operational-schemas --output schemas/operational/v1
```

Add every canonical target now with these exact recipes; targets whose source artifacts are introduced by later plan tasks fail naturally until those files exist:

```make
format-python:
	poetry run ruff format src tests scripts
check-model-generated:
	$(MAKE) all
	git diff --exit-code -- model/generated ':(exclude)model/generated/owl/**' ':(exclude)model/generated/shacl/**'
check-operational-schemas:
	poetry run gen-operational-schemas --output schemas/operational/v1 --check
check-secrets:
	poetry run python scripts/check_committed_secrets.py
check-flows:
	poetry run python scripts/normalize_langflow_flows.py --check langflow/flows/*.json
	poetry run python scripts/validate_langflow_assets.py langflow/flow-manifest.yaml
	poetry run lfx validate --level 4 --strict --skip-credentials langflow/flows/*.json
	for flow in langflow/flows/*.json; do poetry run lfx upgrade --strict "$$flow"; done
test-integration:
	poetry run pytest -m integration
test-system:
	poetry run pytest -m system
test-bdd:
	poetry run pytest tests/steps/test_delivery_request_intake.py tests/steps/test_conversation_resumption.py
test-evaluation-recorded:
	poetry run pytest tests/evaluation/test_dataset_contract.py tests/evaluation/test_recorded_intake_evaluation.py
test-evaluation-live:
	poetry run pytest tests/evaluation/test_live_intake_evaluation.py --run-live-evaluation
test-evaluation-judge:
	poetry run pytest tests/evaluation/test_clarification_judge.py --run-live-evaluation
ci-static: lint check-model-generated lint-python format-check-python typecheck check-architecture check-operational-schemas check-secrets check-flows test-unit test-evaluation-recorded
ci-acceptance: test-integration test-system test-bdd release-evidence
ci: ci-static ci-acceptance
```

Add the acceptance/evidence recipes at the same time; before their declared scripts/tests exist they fail nonzero rather than pretending success:

```make
ACCEPTANCE_PROJECT ?= hulubul-change1-$${USER}
ACCEPTANCE_COMPOSE = docker compose -p $(ACCEPTANCE_PROJECT) -f infra/docker-compose.yaml -f infra/docker-compose.test.yaml
acceptance-up:
	$(ACCEPTANCE_COMPOSE) up -d --build postgres neo4j neo4j-schema mcp-neo4j recorded-model langflow
acceptance-ready:
	poetry run pytest tests/integration/runtime/test_readiness_order.py -q
acceptance-deploy: check-flows
	cd langflow && lfx push --env ci --no-normalize --keep-secrets flows/10-lf-70-data-access.json
	cd langflow && lfx push --env ci --no-normalize --keep-secrets flows/20-lf-10-request-intake.json
	cd langflow && lfx push --env ci --no-normalize --keep-secrets flows/30-lf-00-main-router.json
preflight-langflow-1-10-2:
	poetry run pytest tests/integration/langflow/test_langflow_persistence_contract.py tests/integration/langflow/test_recorded_model_compatibility.py tests/integration/langflow/test_native_trace_contract.py -q
acceptance-diagnostics:
	poetry run python scripts/build_change1_evidence.py --diagnostics-only --output reports/change1/diagnostics.json
acceptance-down:
	$(ACCEPTANCE_COMPOSE) down -v --remove-orphans
release-evidence:
	poetry run python scripts/build_change1_evidence.py --output reports/change1/release-evidence.json
```

Task 4's foundation test asserts every recipe and exact ordered push command is present. The scripts/tests become executable in their named owning tasks; the Make contract itself is complete here.

- [ ] **Step 4: Run GREEN (2-5 min)**

Run: `poetry run pytest tests/unit/test_project_foundation.py -q && make lint`

Expected: foundation tests PASS; output mentions LinkML lint and no Ruff invocation.

- [ ] **Step 5: Self-review and propose commit (2-5 min)**

Confirm no target reads `infra/.env` or `infra/langflow.env`, except existing runtime targets that already require the local stack; new quality targets do not. Propose `build: add namespaced Python and CI targets`; wait for developer approval.

### Task 5: Strict Base, Envelope, And Error Contracts

**Original task IDs:** 2.1

**Files:**
- Create: `src/hulubul/core/models/operational/{__init__,base,enums,errors,envelope,routing}.py`
- Create: `tests/unit/hulubul/core/models/operational/{test_base,test_envelope,test_errors,test_wrapped_inputs}.py`
- Test: `tests/unit/hulubul/core/models/operational/test_base.py`, `test_envelope.py`, `test_errors.py`, and `test_wrapped_inputs.py`

**Interfaces:**
- Consumes: Pydantic `2.12.5`; LinkML RequestStatus source for drift test.
- Produces: `StrictModel`, `VersionedContract`, `HumanSuppliedText`, `NonBlankText`, `SessionId`, `ActorUrn`, `RequestId`, exact 11-member `ContractKind`, all `ErrorCode` values including model-authentication/MCP-operation failures, the exhaustive immutable error policy, `ActorContext`, `MainFlowInput`, typed `RoutingContext`, strict `RouterInput`/`IntakeInput`, and validation helpers exactly as defined in [Locked Shared Interfaces](#locked-shared-interfaces).

- [ ] **Step 1: Write strict and boundary tests (2-5 min per test group)**

```python
@pytest.mark.parametrize(("length", "valid"), [(0, False), (1, True), (4000, True), (4001, False)])
def test_human_text_boundary(length, valid):
    payload = valid_main_input(message=f" {'x' * length} ")
    assert_validation(payload, valid)

def test_intake_input_rejects_mismatched_nested_metadata():
    with pytest.raises(ValidationError):
        IntakeInput.model_validate(intake_input_with_different_context_correlation())

@pytest.mark.parametrize("code", tuple(ErrorCode))
def test_every_error_code_has_one_canonical_policy(code):
    assert ERROR_POLICY[code].code is code
    assert ERROR_POLICY[code].escalation in set(ErrorEscalation)

def test_unavailable_context_identifiers_are_omitted_not_fabricated():
    projection = project_error_log(invalid_contract_before_operation())
    assert "operation_id" not in projection
    assert "request_id" not in projection
```

- [ ] **Step 2: Run RED (2-5 min)**

Run: `poetry run pytest tests/unit/hulubul/core/models/operational/test_base.py tests/unit/hulubul/core/models/operational/test_envelope.py tests/unit/hulubul/core/models/operational/test_errors.py tests/unit/hulubul/core/models/operational/test_wrapped_inputs.py -q`

Expected: FAIL with `ModuleNotFoundError: hulubul.core.models.operational`.

- [ ] **Step 3: Implement strict base and trusted envelope (2-5 min per class)**

```python
class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True, frozen=True)

class VersionedContract(StrictModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    correlation_id: UUID4

class MainFlowInput(VersionedContract):
    message_id: UUID4
    session_id: SessionId
    actor: ActorContext
    source: InvocationSource
    message: HumanSuppliedText
```

Implement the exact ErrorCode table from [Locked Shared Interfaces](#locked-shared-interfaces) as immutable enum-keyed data. `OperationalError` rejects noncanonical category/message/retryability; structured logging accepts only each row's allowed fields/level, includes every available required identifier, and omits unavailable operation/request/retry identifiers rather than emitting null or invented values; escalation is the closed three-value enum and contains no pager action; conversion records only normalized field locations plus Pydantic rule IDs, never rejected values.

Implement typed `RoutingContext` fields/invariants needed by both wrappers, then implement `RouterInput(envelope, routing_context)` and `IntakeInput(envelope, routing_context)` as frozen versioned contracts. Both require wrapper/envelope/context schema-version and correlation equality plus envelope/context session equality. `IntakeInput` additionally requires no routing error, stage `intake`, and exactly either absent binding with no request/status or one bound request in `new`/`needsClarification`; all other stages, partial bindings, statuses, and errors fail strict validation. Assert `ContractKind` is exactly the 11-value inventory in [Locked Shared Interfaces](#locked-shared-interfaces).

- [ ] **Step 4: Run GREEN (2-5 min)**

Run the RED command again.

Expected: PASS, including LinkML RequestStatus drift, strict primitive, UUID/session pattern, wrapper equality/intake-state invariants, exact ContractKind/ErrorCode inventory, and safe-error assertions.

- [ ] **Step 5: Self-review and propose commit (2-5 min)**

Run `poetry run pytest tests/unit/hulubul/core/models/operational --cov=hulubul.core.models.operational --cov-fail-under=90 -q`; confirm importing core does not import LFX. Propose `feat(contracts): add strict execution envelope contracts`; wait for developer approval.

### Task 6: Routing Contracts

**Original task IDs:** 2.2

**Files:**
- Modify: `src/hulubul/core/models/operational/routing.py`
- Create: `tests/unit/hulubul/core/models/operational/test_routing.py`
- Modify: `src/hulubul/core/models/operational/__init__.py`
- Test: `tests/unit/hulubul/core/models/operational/test_routing.py`

**Interfaces:**
- Consumes: strict base, RequestStatus, typed errors.
- Produces: strict internal `RoutingLookupRecord`/request row with nullable `requestStatusRaw`, `adapt_routing_lookup`, typed/nullable `RoutingContext.request_status`, and `RouterResult` with the locked invariants and closed-state precedence.

- [ ] **Step 1: Write the route invariant matrix (2-5 min)**

```python
@pytest.mark.parametrize("status", tuple(RequestStatus))
def test_every_recognized_raw_status_adapts_to_enum_identity(status):
    context = adapt_routing_lookup(valid_bound_record(requestStatusRaw=status.value), **METADATA)
    assert context.request_status is status

def test_synthetic_duplicate_binding_fails_closed():
    context = adapt_routing_lookup(valid_bound_record(bindingCount=2), **METADATA)
    assert context.error.code is ErrorCode.GRAPH_CONTEXT_INCONSISTENT
```

- [ ] **Step 2: Run RED (2-5 min)**

Run: `poetry run pytest tests/unit/hulubul/core/models/operational/test_routing.py -q`

Expected: FAIL because `RoutingLookupRecord`, `adapt_routing_lookup`, and `RouterResult` are not implemented yet.

- [ ] **Step 3: Implement contradiction validators (2-5 min per branch)**

```python
if self.binding_state is BindingState.ABSENT:
    require(self.binding_count == self.active_request_count == 0)
    require(self.request_id is self.request_status is self.error is None)
if self.closed_at is not None:
    require(self.routing_stage is RoutingStage.CLOSED)
```

Validate camel-case MCP row keys before interpreting them. Apply precedence exactly: invalid binding/relationship/target/request cardinality; absent binding; non-null closed timestamp over every recognized/unknown/null status; typed `new`, `needsClarification`, and `complete`; all eight typed post-intake statuses; null raw status; unknown raw status. Unknown raw values become `request_status=None` plus `UNSUPPORTED_REQUEST_STATUS` and are never copied into an error, message, log, or trace. Synthetic `bindingCount=2` exists only in this boundary unit suite; constrained graph fixtures use duplicate relationships/targets instead.

- [ ] **Step 4: Run GREEN and self-review (2-5 min)**

Run the RED command again; expect all 11 enum-identity cases, unknown/null status, closed precedence over each recognized/unknown/null status, every valid/invalid cardinality shape, no-binding/intake/complete/unsupported/failure context, and RouterResult contradiction case PASS. Confirm raw text never survives adaptation, failure/informational results target `none`, and routed results preserve the authoritative request ID.

- [ ] **Step 5: Propose commit and wait (2-5 min)**

Propose `feat(contracts): add authoritative routing contracts`; wait for developer approval.

### Task 7: Intake And Sparse Snapshot Contracts

**Original task IDs:** 2.3

**Files:**
- Create: `src/hulubul/core/models/operational/{intake,snapshots}.py`
- Create: `tests/unit/hulubul/core/models/operational/{test_intake,test_snapshots}.py`
- Modify: `src/hulubul/core/models/operational/__init__.py`
- Test: both new test files

**Interfaces:**
- Consumes: strict base, IntakeField, RequestStatus, OperationalError.
- Produces: `IntakeFacts`, `IntakeFactUpdates`, `CompleteIntakeFacts`, `IntakeResult`, `GraphIdentifiers`, `DeliveryRequestSnapshot`, `MutationConfirmation` with locked fields.

- [ ] **Step 1: Write sparse/complete contradiction tests (2-5 min)**

```python
def test_complete_snapshot_rejects_required_omission():
    with pytest.raises(ValidationError):
        snapshot(status=RequestStatus.COMPLETE, facts=sender_only_facts())
```

- [ ] **Step 2: Run RED (2-5 min)**

Run: `poetry run pytest tests/unit/hulubul/core/models/operational/test_intake.py tests/unit/hulubul/core/models/operational/test_snapshots.py -q`

Expected: FAIL because the contract modules are absent.

- [ ] **Step 3: Implement exact fields and validators (2-5 min per model)**

```python
class IntakeFacts(StrictModel):
    sender_actor_id: ActorUrn
    sender_display_name: NonBlankText | None = None
    receiver_name: HumanSuppliedText | None = None
    receiver_stable_id: NonBlankText | None = None
    pickup_location: HumanSuppliedText | None = None
    drop_off_location: HumanSuppliedText | None = None
    parcel_declared_content: HumanSuppliedText | None = None
    preferred_period: HumanSuppliedText | None = None
```

Reject empty updates; enforce nested schema/correlation equality; require complete results/snapshots to have complete facts and no missing/clarification/error; allow sparse facts only for `new` and `needsClarification`.

- [ ] **Step 4: Run GREEN and self-review (2-5 min)**

Run the RED command; expect PASS. Verify all six human text fields share the same 0/1/4000/4001 parameterized boundary and timestamps are aware.

- [ ] **Step 5: Propose commit and wait (2-5 min)**

Propose `feat(contracts): add sparse intake and request snapshots`; wait for developer approval.

### Task 8: Five Data Operation Contracts

**Original task IDs:** 2.4

**Files:**
- Create: `src/hulubul/core/models/operational/data_operations.py`
- Create: `tests/unit/hulubul/core/models/operational/test_data_operations.py`
- Modify: `src/hulubul/core/models/operational/__init__.py`
- Test: `tests/unit/hulubul/core/models/operational/test_data_operations.py`

**Interfaces:**
- Consumes: actor/session/request/snapshot/result contracts.
- Produces: five payload/request classes, `DataOperationRequest` discriminated union, `DataOperationResult`, request validator/schema helpers.

- [ ] **Step 1: Write exact-operation and contradiction tests (2-5 min)**

```python
def test_exactly_five_operations_are_declared():
    assert {member.value for member in DataOperation} == {
        "getRequestRoutingContext", "createDeliveryRequest", "readDeliveryRequest",
        "updateDeliveryRequest", "setRequestStatus",
    }

@pytest.mark.parametrize("extra", [{"cypher": "RETURN 1"}, {"query": "RETURN 1"}, {"undeclared": True}])
def test_malformed_operation_fails_contract_before_capability(extra):
    with pytest.raises(ValidationError):
        validate_data_operation_request({**valid_lf00_create_mapping(), **extra})
```

- [ ] **Step 2: Run RED (2-5 min)**

Run: `poetry run pytest tests/unit/hulubul/core/models/operational/test_data_operations.py -q`

Expected: FAIL because the module is absent.

- [ ] **Step 3: Implement union and result invariants (2-5 min per operation)**

```python
DataOperationRequest = Annotated[
    GetRequestRoutingContextRequest | CreateDeliveryRequestRequest |
    ReadDeliveryRequestRequest | UpdateDeliveryRequestRequest | SetRequestStatusRequest,
    Field(discriminator="operation"),
]
DATA_OPERATION_ADAPTER = TypeAdapter(DataOperationRequest)
```

Confirmed writes require dispatch=true, one affected request, matching typed result/status; confirmed create also requires Neo4j-returned aware `created_at == updated_at`; confirmed reads require dispatch=false and no count; rejected results cannot claim success/status/result; ambiguous results require a dispatched write, no count/result/status, and exactly `MCP_WRITE_AMBIGUOUS`. Create payload timestamps, unknown discriminators, operation/payload mismatches, raw `cypher`/`query`, and every undeclared field fail strict union validation as `INVALID_CONTRACT` before capability policy is callable.

- [ ] **Step 4: Run GREEN and self-review (2-5 min)**

Run the RED command; expect all matching/mismatched/sixth-operation/raw-Cypher/result invariant tests PASS. Confirm JSON-mode validation rejects stringified booleans/integers.

- [ ] **Step 5: Propose commit and wait (2-5 min)**

Propose `feat(contracts): add typed data operation contracts`; wait for developer approval.

### Task 9: Deterministic Operational Schemas

**Original task IDs:** 2.5

**Files:**
- Create: `scripts/gen_operational_schemas.py`
- Create/generated: `schemas/operational/v1/{main-flow-input,router-input,intake-input,routing-context,router-result,intake-facts,intake-result,data-operation-request,data-operation-result,delivery-request-snapshot,operational-error}.schema.json`
- Create/generated: `schemas/operational/v1/manifest.json`
- Create: `tests/contract/test_operational_schema_generation.py`
- Modify: `pyproject.toml`, `Makefile`
- Test: `tests/contract/test_operational_schema_generation.py`

**Interfaces:**
- Consumes: top-level operational model registry/TypeAdapter.
- Produces: `build_schema_documents() -> dict[str, dict[str, object]]`, `build_manifest(schema_documents: Mapping[str, Mapping[str, object]]) -> dict[str, object]`, `write_schemas(output_dir: Path) -> None`, `check_schemas(output_dir: Path) -> bool`, `cli() -> None`; deterministic schema set and manifest.

- [ ] **Step 1: Write drift and manifest tests (2-5 min per test)**

```python
def test_two_generations_are_byte_identical(tmp_path):
    first, second = tmp_path / "first", tmp_path / "second"
    write_schemas(first); write_schemas(second)
    assert tree_bytes(first) == tree_bytes(second)

def test_contract_kind_and_schema_inventory_are_exactly_eleven(schema_documents):
    assert set(schema_documents) == {kind.value for kind in ContractKind}
    assert len(schema_documents) == 11
```

- [ ] **Step 2: Run RED (2-5 min)**

Run: `poetry run pytest tests/contract/test_operational_schema_generation.py -q`

Expected: FAIL because generator and committed schemas are absent.

- [ ] **Step 3: Implement deterministic rendering (2-5 min per function)**

```python
serialized = json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
```

Set draft `https://json-schema.org/draft/2020-12/schema`, stable base ID `https://meaningfy.ws/hulubul/schemas/operational/v1`, generator/version `gen-operational-schemas/1.0.0`, exact Pydantic version, sorted filenames and hashes. Exclude clocks, hosts, paths, and environment values. `--check` reports changed relative paths only.

- [ ] **Step 4: Generate and run GREEN (2-5 min)**

Run: `make operational-schemas && poetry run pytest tests/contract/test_operational_schema_generation.py -q && make check-operational-schemas`

Expected: exactly 11 schemas plus manifest generated; tests PASS; check exits 0. Run a second generation and `git diff --exit-code -- schemas/operational/v1`; expect no diff.

- [ ] **Step 5: Self-review and propose commit (2-5 min)**

Confirm every object branch prohibits additional properties and no LinkML-generated file changed. Propose `feat(contracts): generate versioned operational schemas`; wait for developer approval.

### Task 10: Completeness And Immediate Fact Policy

**Original task IDs:** 3.1

**Files:**
- Create: `src/hulubul/request_intake/models/{__init__,completeness}.py`
- Create: `tests/unit/hulubul/request_intake/models/test_completeness.py`
- Test: `tests/unit/hulubul/request_intake/models/test_completeness.py`

**Interfaces:**
- Consumes: `IntakeFacts`, `CompleteIntakeFacts`, `IntakeField`.
- Produces: `REQUIRED_INTAKE_FIELDS`, `missing_required_fields`, `select_clarification_field`, `validate_complete_facts`.

- [ ] **Step 1: Write fixed-order/immediate tests (2-5 min)**

```python
def test_missing_fields_use_fixed_order():
    assert missing_required_fields(sender_only_facts()) == (
        IntakeField.RECEIVER_IDENTITY, IntakeField.PICKUP_LOCATION,
        IntakeField.DROP_OFF_LOCATION, IntakeField.PARCEL_DECLARED_CONTENT,
    )
```

- [ ] **Step 2: Run RED (2-5 min)**

Run: `poetry run pytest tests/unit/hulubul/request_intake/models/test_completeness.py -q`

Expected: FAIL because `completeness.py` is absent.

- [ ] **Step 3: Implement minimal pure decisions (2-5 min per function)**

```python
REQUIRED_INTAKE_FIELDS = (
    IntakeField.RECEIVER_IDENTITY, IntakeField.PICKUP_LOCATION,
    IntakeField.DROP_OFF_LOCATION, IntakeField.PARCEL_DECLARED_CONTENT,
)
def select_clarification_field(missing_fields, *, invalid_field=None):
    return invalid_field if invalid_field is not None else (missing_fields[0] if missing_fields else None)
```

Receiver name or stable ID satisfies identity; preferred period stays optional; no geocoder/date semantics are invented. Pydantic validates supplied facts immediately; complete validation runs only when the fixed missing tuple is empty.

- [ ] **Step 4: Run GREEN and self-review (2-5 min)**

Run the RED command; expect complete/optional/single-missing/order/invalid-priority/1-4000 cases PASS. Confirm the models layer imports no service/framework.

- [ ] **Step 5: Propose commit and wait (2-5 min)**

Propose `feat(intake): add deterministic completeness policy`; wait for developer approval.

### Task 11: Transition And Compare-And-Set Policy

**Original task IDs:** 3.2

**Files:**
- Create: `src/hulubul/request_intake/models/transitions.py`
- Create: `tests/unit/hulubul/request_intake/models/test_transitions.py`
- Modify: `src/hulubul/request_intake/models/__init__.py`
- Test: `tests/unit/hulubul/request_intake/models/test_transitions.py`

**Interfaces:**
- Consumes: RequestStatus, ErrorCode, aware timestamps.
- Produces: `ALLOWED_TRANSITIONS`, immutable `TransitionDecision(allowed: bool, error_code: ErrorCode | None)`, and `evaluate_transition(*, actual_status: RequestStatus | None, actual_updated_at: datetime | None, expected_status: RequestStatus | None, expected_updated_at: datetime | None, target_status: RequestStatus) -> TransitionDecision`.

- [ ] **Step 1: Write all four positive and sampled negative cases (2-5 min)**

```python
ALLOWED = [(None, NEW), (NEW, NEEDS_CLARIFICATION), (NEW, COMPLETE), (NEEDS_CLARIFICATION, COMPLETE)]
@pytest.mark.parametrize("source,target", ALLOWED)
def test_exact_change1_edges_are_allowed(source, target):
    assert decision_for(source, target).allowed
```

- [ ] **Step 2: Run RED (2-5 min)**

Run: `poetry run pytest tests/unit/hulubul/request_intake/models/test_transitions.py -q`

Expected: FAIL because transition policy is absent.

- [ ] **Step 3: Implement precedence and table (2-5 min)**

```python
if actual_status != expected_status:
    return TransitionDecision(False, ErrorCode.INVALID_EXPECTED_STATUS)
if actual_updated_at != expected_updated_at:
    return TransitionDecision(False, ErrorCode.CONCURRENT_MODIFICATION)
if (actual_status, target_status) not in ALLOWED_TRANSITIONS:
    return TransitionDecision(False, ErrorCode.INVALID_STATUS_TRANSITION)
return TransitionDecision(True, None)
```

- [ ] **Step 4: Run GREEN and self-review (2-5 min)**

Run the RED command; expect exact edges pass; stale status, stale timestamp, `needsClarification->waitingResponse`, and `complete->new` fail with exact codes. Confirm creation alone uses `None->new`.

- [ ] **Step 5: Propose commit and wait (2-5 min)**

Propose `feat(intake): enforce intake transition preconditions`; wait for developer approval.

### Task 12: Deterministic Graph Identifiers

**Original task IDs:** 3.3

**Files:**
- Create: `src/hulubul/request_intake/services/{__init__,graph_identifiers}.py`
- Create: `tests/unit/hulubul/request_intake/services/test_graph_identifiers.py`
- Test: `tests/unit/hulubul/request_intake/services/test_graph_identifiers.py`

**Interfaces:**
- Consumes: `GraphIdentifiers`; UUID factory.
- Produces: `new_graph_identifiers`, `enduring_agent_id`, `request_scoped_receiver_identifier` with prefixes `req-`, `ag-`, `s-`, `r-`, `p-`, `pl-`, `urn:uuid:`, `urn:hulubul:phase1:receiver:`.

- [ ] **Step 1: Write injected-UUID identity tests (2-5 min)**

```python
def test_sparse_facts_allocate_no_placeholder_ids(uuid_sequence):
    ids = new_graph_identifiers(actor_id=ACTOR, receiver_stable_id=None,
        include_receiver=False, include_parcel=False, include_pickup=False,
        include_drop_off=False, uuid_factory=uuid_sequence)
    assert ids.receiver_role_id is ids.parcel_id is ids.pickup_place_id is None
```

- [ ] **Step 2: Run RED (2-5 min)**

Run: `poetry run pytest tests/unit/hulubul/request_intake/services/test_graph_identifiers.py -q`

Expected: FAIL because identifier service is absent.

- [ ] **Step 3: Implement exact allocation order (2-5 min)**

```python
def enduring_agent_id(stable_identifier: str) -> str:
    return f"ag-{uuid5(NAMESPACE_URL, stable_identifier)}"
```

Consume UUID4 values in order request, Sender role, then only present Receiver role, Parcel, pickup Place, drop-off Place. Place URN uses the same UUID. A name-only Receiver uses request-scoped URN; display names never define enduring identity.

- [ ] **Step 4: Run GREEN and self-review (2-5 min)**

Run the RED command; expect prefix/reuse/request-scope/fallback/place/sparse tests PASS. Confirm no random call occurs for absent subgraphs.

- [ ] **Step 5: Propose commit and wait (2-5 min)**

Propose `feat(intake): add deterministic graph identifiers`; wait for developer approval.

### Task 13: Caller Capability And Result Policy

**Original task IDs:** 3.4

**Files:**
- Create: `src/hulubul/request_intake/services/data_operation_policy.py`
- Create: `tests/unit/hulubul/request_intake/services/test_data_operation_policy.py`
- Modify: `src/hulubul/request_intake/services/__init__.py`
- Test: `tests/unit/hulubul/request_intake/services/test_data_operation_policy.py`

**Interfaces:**
- Consumes: DataOperationRequest/Result, transition policy, typed errors.
- Produces: `ALLOWED_OPERATIONS`, `authorize_operation`, `validate_operation_preconditions`, `validate_result_postconditions`.

- [ ] **Step 1: Write capability matrix tests (2-5 min)**

```python
assert ALLOWED_OPERATIONS[CallerFlow.LF_00] == frozenset({DataOperation.GET_REQUEST_ROUTING_CONTEXT})
assert ALLOWED_OPERATIONS[CallerFlow.LF_10] == frozenset({
    DataOperation.CREATE_DELIVERY_REQUEST, DataOperation.READ_DELIVERY_REQUEST,
    DataOperation.UPDATE_DELIVERY_REQUEST, DataOperation.SET_REQUEST_STATUS,
})
```

- [ ] **Step 2: Run RED (2-5 min)**

Run: `poetry run pytest tests/unit/hulubul/request_intake/services/test_data_operation_policy.py -q`

Expected: FAIL because policy module is absent.

- [ ] **Step 3: Implement deterministic checks (2-5 min per function)**

Compare schema/correlation/operation IDs, operation enum, session/request identity, write classification, affected count, and target status. Return typed errors; never mutate a candidate result into success and never inspect raw MCP/Cypher.

```python
if operation not in ALLOWED_OPERATIONS[caller]:
    return operational_error(ErrorCode.OPERATION_NOT_ALLOWED, correlation_id=correlation_id)
```

- [ ] **Step 4: Run GREEN and self-review (2-5 min)**

Run the RED command; expect LF-00/LF-10 capability, precondition, ID mismatch, affected-count, and ambiguous-inspection tests PASS. Confirm no LFX/MCP imports.

- [ ] **Step 5: Propose commit and wait (2-5 min)**

Propose `feat(intake): enforce data operation capabilities`; wait for developer approval.

### Task 14: Retry And Repair Policy

**Original task IDs:** 3.5

**Files:**
- Create: `src/hulubul/request_intake/services/retry_policy.py`
- Create: `tests/unit/hulubul/request_intake/services/test_retry_policy.py`
- Modify: `src/hulubul/request_intake/services/__init__.py`
- Test: `tests/unit/hulubul/request_intake/services/test_retry_policy.py`

**Interfaces:**
- Consumes: DependencyKind, FailureKind, RetryAction, ErrorCode.
- Produces: `RetryContext`, `RetryDecision`, `decide_retry` implementing every row of the locked `FailureKind` matrix and terminal codes including `MODEL_AUTHENTICATION_FAILURE` and `MCP_OPERATION_FAILURE`.

- [ ] **Step 1: Write the complete retry matrix (2-5 min per parameter block)**

```python
@pytest.mark.parametrize("status", [408, 425, 429, 500, 502, 503, 504])
def test_model_http_status_retries_once(status):
    assert decide_retry(model_http(status, attempt=1)).delay_ms == 500
    assert decide_retry(model_http(status, attempt=2)).action is RetryAction.FAIL

@pytest.mark.parametrize("failure", tuple(FailureKind))
def test_every_failure_kind_has_an_executable_decision(failure):
    assert decision_cases_for(failure)
```

- [ ] **Step 2: Run RED (2-5 min)**

Run: `poetry run pytest tests/unit/hulubul/request_intake/services/test_retry_policy.py -q`

Expected: FAIL because retry policy is absent.

- [ ] **Step 3: Implement ordered decisions (2-5 min per branch)**

```python
if context.failure is FailureKind.AUTHENTICATION:
    code = (ErrorCode.MODEL_AUTHENTICATION_FAILURE
            if context.dependency is DependencyKind.MODEL
            else ErrorCode.MCP_AUTHENTICATION_FAILURE)
    return RetryDecision(action=RetryAction.FAIL, delay_ms=0, error_code=code)
```

Implement every locked matrix row without a default/fall-through branch: model statuses include 500; MCP read statuses exclude 500; malformed output permits one repair of existing raw output with delay 0; non-transient MCP protocol/status/Cypher failures become `MCP_OPERATION_FAILURE`; provider authentication becomes `MODEL_AUTHENTICATION_FAILURE`; and a write whose dispatch is not positively disproved becomes ambiguous. Validation-first `INVALID_CONTRACT` and known-valid capability `OPERATION_NOT_ALLOWED` remain distinct.

- [ ] **Step 4: Run GREEN and self-review (2-5 min)**

Run the RED command; expect every `FailureKind`, dependency/attempt/status/dispatch branch, retry/nonretry/no-replay/repair case, and terminal safe-code mapping PASS. Confirm policy returns decisions only: no sleeping, callback, model, MCP, flow call, raw provider/MCP message, or production pager behavior.

- [ ] **Step 5: Propose commit and wait (2-5 min)**

Propose `feat(intake): add bounded retry and repair policy`; wait for developer approval.

### Task 15: Deterministic Rendering

**Original task IDs:** 3.6

**Files:**
- Create: `src/hulubul/request_intake/services/rendering.py`
- Create: `tests/unit/hulubul/request_intake/services/test_rendering.py`
- Modify: `src/hulubul/request_intake/services/__init__.py`
- Test: `tests/unit/hulubul/request_intake/services/test_rendering.py`

**Interfaces:**
- Consumes: validated RouterResult, IntakeResult, OperationalError.
- Produces: three render functions and canonical clarification map/messages.

- [ ] **Step 1: Write output/error matrix tests (2-5 min)**

```python
def test_clarification_renders_exactly_selected_question(result):
    text = render_intake_result(result)
    assert text == "Who should receive the parcel?"
    assert text.count("?") == 1
```

- [ ] **Step 2: Run RED (2-5 min)**

Run: `poetry run pytest tests/unit/hulubul/request_intake/services/test_rendering.py -q`

Expected: FAIL because renderer is absent.

- [ ] **Step 3: Implement enum-keyed rendering (2-5 min per outcome)**

```python
def render_operational_error(error: OperationalError) -> str:
    return error.safe_message
```

Complete includes confirmed request ID; complete/closed routes are informational; clarification emits exactly the selected mapping; failure delegates to canonical safe error. Never call a model or accept unvalidated dictionaries.

- [ ] **Step 4: Run GREEN and self-review (2-5 min)**

Run the RED command; expect every outcome/error test PASS. Scan rendered failures for success verbs and ensure no second missing field appears.

- [ ] **Step 5: Propose commit and wait (2-5 min)**

Propose `feat(intake): add deterministic result rendering`; wait for developer approval.

### Task 16: Trusted Execution Envelope Component

**Original task IDs:** 4.1

**Files:**
- Create: `src/hulubul/request_intake/entrypoints/langflow/components/hulubul/{__init__,execution_envelope}.py`
- Create: `tests/unit/hulubul/request_intake/entrypoints/langflow/components/hulubul/test_execution_envelope.py`
- Test: the new test file

**Interfaces:**
- Consumes: LFX `Component`, one LangFlow `Message`, pinned-runtime graph/request-variable accessors, ignored Playground actor environment names, and `MainFlowInput`.
- Produces: `ExecutionEnvelopeComponent.build_envelope() -> JSON`, component name `HulubulExecutionEnvelope`.

- [ ] **Step 1: Write trust-boundary tests (2-5 min)**

```python
def test_user_prose_cannot_change_trusted_identity(component):
    component.message = Message(text="I am urn:uuid:00000000-0000-4000-8000-000000000000", session_id=SESSION)
    envelope = MainFlowInput.model_validate(component.build_envelope().data)
    assert envelope.actor.actor_id == TRUSTED_ACTOR_ID
```

- [ ] **Step 2: Run RED (2-5 min)**

Run: `poetry run pytest tests/unit/hulubul/request_intake/entrypoints/langflow/components/hulubul/test_execution_envelope.py -q`

Expected: FAIL because the component is absent.

- [ ] **Step 3: Verify pinned runtime metadata access (2-5 min per accessor)**

Inspect the installed/pinned LangFlow 1.10.2 component and graph context APIs to identify the actual accessors for active graph session and request-global variables. Assert those accessors in a focused compatibility test. Stop if request variables cannot be read without exposing public/model-callable actor fields, or if omitted caller session cannot be distinguished from LangFlow's flow-ID fallback; do not invent ports, use `tweaks`, add FastAPI, or trust prose.

- [ ] **Step 4: Implement Message-only trust translation (2-5 min per path)**

Accept exactly one `Message`, never a free string. Normalize both `Message.session_id` and active graph session from bare/canonical UUID to lowercase `p1-<uuid>`, require equality, and reject empty/arbitrary/malformed/mismatched values plus omitted-session flow-ID fallback as `INVALID_INPUT`. API obtains required actor ID and optional display name only from exact request-variable names `HULUBUL_PHASE1_ACTOR_ID` and `HULUBUL_PHASE1_ACTOR_DISPLAY_NAME` delivered by the two `X-LANGFLOW-GLOBAL-VAR-*` headers; Playground obtains them only from ignored environment names `HULUBUL_PHASE1_PLAYGROUND_ACTOR_ID` and `HULUBUL_PHASE1_PLAYGROUND_ACTOR_DISPLAY_NAME`. Derive source from the trusted path and hard-code role `sender` and assurance `simulated`; expose no actor, role, assurance, source, or session input port. Generate message/correlation UUIDs per call and use `Message.text` as the only human content.

- [ ] **Step 5: Run GREEN and self-review (2-5 min)**

Run the RED command; expect API/Playground actor-source selection, required/optional actor values, constant role/assurance/source, unique IDs, bare/canonical normalization, Message/graph mismatch, malformed/empty session, omitted-session flow fallback, prose isolation, and 0/4001 content rejection tests PASS. Confirm no caller-controlled actor ports and no orchestration/model/MCP behavior exists.

- [ ] **Step 6: Propose commit and wait (2-5 min)**

Propose `feat(langflow): add trusted execution envelope component`; wait for developer approval.

### Task 17: Contract Boundary Components

**Original task IDs:** 4.2

**Files:**
- Create: `src/hulubul/request_intake/entrypoints/langflow/components/hulubul/contract_boundary.py`
- Create: `tests/unit/hulubul/request_intake/entrypoints/langflow/components/hulubul/test_contract_boundary.py`
- Modify: component package `__init__.py`
- Test: the new test file

**Interfaces:**
- Consumes: LFX Data/JSON/Message, exact `ContractKind` registry, fixed validated envelope/context edges, strict validation/error conversion.
- Produces: deterministic `RouterInputBoundaryComponent.build_router_input() -> Message`, `IntakeInputBoundaryComponent.build_intake_input() -> Message`, and `ContractResultBoundaryComponent.validate_contract() -> JSON`; model-facing values contain only canonical validated wrappers.

- [ ] **Step 1: Write canonical/error translation tests (2-5 min)**

```python
def test_extra_field_returns_safe_violation(boundary):
    output = boundary.validate_contract_value({**VALID, "extra": "synthetic"})
    error = OperationalError.model_validate(output.data)
    assert error.code is ErrorCode.INVALID_CONTRACT
    assert "synthetic" not in output.data

def test_intake_wrapper_uses_fixed_edges_not_model_value(boundary):
    wrapper = IntakeInput.model_validate_json(boundary.build_intake_input().text)
    assert wrapper.envelope == FIXED_ENVELOPE
    assert wrapper.routing_context == FIXED_ROUTING_CONTEXT
```

- [ ] **Step 2: Run RED (2-5 min)**

Run: `poetry run pytest tests/unit/hulubul/request_intake/entrypoints/langflow/components/hulubul/test_contract_boundary.py -q`

Expected: FAIL because boundaries are absent.

- [ ] **Step 3: Implement registry-driven conversion (2-5 min)**

Use a module constant keyed by all 11 `ContractKind` members. Convert only declared LangFlow Data/JSON values, assemble RouterInput/IntakeInput from separately wired fixed envelope/context edges, catch only validation/type translation failures, and return canonical `Message` input or validated `JSON` result. The envelope/context fields are advanced, absent from model tool schemas, and cannot be overridden by public input, model output, prose, or tweaks. Unexpected programming errors remain exceptions.

```python
CONTRACT_TYPES = {
    ContractKind.MAIN_FLOW_INPUT: MainFlowInput,
    ContractKind.ROUTER_INPUT: RouterInput,
    ContractKind.INTAKE_INPUT: IntakeInput,
    ContractKind.ROUTING_CONTEXT: RoutingContext,
    ContractKind.ROUTER_RESULT: RouterResult,
    ContractKind.INTAKE_FACTS: IntakeFacts,
    ContractKind.INTAKE_RESULT: IntakeResult,
    ContractKind.DATA_OPERATION_REQUEST: DATA_OPERATION_ADAPTER,
    ContractKind.DATA_OPERATION_RESULT: DataOperationResult,
    ContractKind.DELIVERY_REQUEST_SNAPSHOT: DeliveryRequestSnapshot,
    ContractKind.OPERATIONAL_ERROR: OperationalError,
}
```

Complete the explicit registry for every generated contract kind; the test compares its keys to `set(ContractKind)` so omission or surplus fails.

- [ ] **Step 4: Run GREEN and self-review (2-5 min)**

Run the RED command; expect canonical Data/JSON conversion, all-11 registry, strict primitive, extra, blank, unknown-kind, wrapper equality/intake-state, fixed-edge/non-substitution, violation-redaction, and contradiction cases PASS. Confirm no raw dict enters policy after validation.

- [ ] **Step 5: Propose commit and wait (2-5 min)**

Propose `feat(langflow): add operational contract boundaries`; wait for developer approval.

### Task 18: LF-70 Operation Boundary Components

**Original task IDs:** 4.3

**Files:**
- Create: `src/hulubul/request_intake/entrypoints/langflow/components/hulubul/data_operation_boundary.py`
- Create: `tests/unit/hulubul/request_intake/entrypoints/langflow/components/hulubul/test_data_operation_boundary.py`
- Modify: component package `__init__.py`
- Test: the new test file

**Interfaces:**
- Consumes: operation adapters and pure authorization/pre/postcondition policy.
- Produces: `DataOperationRequestBoundaryComponent.validate_request() -> Message|JSON`; `DataOperationResultBoundaryComponent.validate_result() -> JSON` with `validated_message`/`validated_data` flow outputs.

- [ ] **Step 1: Write pre/post-boundary tests (2-5 min)**

```python
def test_lf00_write_is_rejected_before_tool_exists(boundary):
    result = boundary.validate_request_value(lf00_create_request())
    assert result.error.code is ErrorCode.OPERATION_NOT_ALLOWED

def test_malformed_lf00_write_is_invalid_contract_not_authorization(boundary):
    result = boundary.validate_request_value({**lf00_create_mapping(), "query": "RETURN 1"})
    assert result.error.code is ErrorCode.INVALID_CONTRACT
```

- [ ] **Step 2: Run RED (2-5 min)**

Run: `poetry run pytest tests/unit/hulubul/request_intake/entrypoints/langflow/components/hulubul/test_data_operation_boundary.py -q`

Expected: FAIL because boundary module is absent.

- [ ] **Step 3: Implement validate/delegate/serialize only (2-5 min per method)**

Validate the complete strict request union first. Only after successful validation authorize the known operation for its typed caller, then validate expected state and emit canonical Agent message/data. Unknown operations, mismatched payloads, create timestamps, `cypher`/`query`, and undeclared input yield `INVALID_CONTRACT`; only a known fully valid out-of-capability operation yields `OPERATION_NOT_ALLOWED`. Result validation compares request/result IDs, operation, correlation, dispatch, affected count, timestamps, and state; return typed rejection without invoking a callback.

```python
request = validate_data_operation_request(raw_value)
error = authorize_operation(request.caller, request.operation) or validate_operation_preconditions(request)
```

- [ ] **Step 4: Run GREEN and self-review (2-5 min)**

Run the RED command; expect validation-before-authorization precedence, LF-00 valid-write denial, malformed-write `INVALID_CONTRACT`, exact update CAS, ID/timestamp matching, count mismatch, MCP-operation failure, and ambiguous timeout tests PASS. Confirm source contains no MCP import, declared query/Cypher field, Cypher text, sleep, or tool call.

- [ ] **Step 5: Propose commit and wait (2-5 min)**

Propose `feat(langflow): enforce LF-70 operation boundaries`; wait for developer approval.

### Task 19: Retry And Renderer Components

**Original task IDs:** 4.4

**Files:**
- Create: `src/hulubul/request_intake/entrypoints/langflow/components/hulubul/{retry_decision,deterministic_renderer}.py`
- Create: `tests/unit/hulubul/request_intake/entrypoints/langflow/components/hulubul/{test_retry_decision,test_deterministic_renderer}.py`
- Modify: component package `__init__.py`
- Test: both new test files

**Interfaces:**
- Consumes: validated RetryContext and RouterResult/IntakeResult; pure policies.
- Produces: `RetryDecisionComponent.build_decision() -> JSON`; `DeterministicRendererComponent.build_message() -> Message`.

- [ ] **Step 1: Write delegation-equivalence tests (2-5 min)**

```python
def test_retry_component_equals_pure_policy(component, context):
    assert component.build_decision().data == decide_retry(context).model_dump(mode="json")
```

- [ ] **Step 2: Run RED (2-5 min)**

Run: `poetry run pytest tests/unit/hulubul/request_intake/entrypoints/langflow/components/hulubul/test_retry_decision.py tests/unit/hulubul/request_intake/entrypoints/langflow/components/hulubul/test_deterministic_renderer.py -q`

Expected: FAIL because components are absent.

- [ ] **Step 3: Implement thin adapters (2-5 min per component)**

```python
def build_decision(self) -> JSON:
    context = validate_json_mapping(RetryContext, self.retry_context.data)
    return JSON(data=decide_retry(context).model_dump(mode="json"))
```

Renderer validates the selected contract kind, calls the matching pure renderer, and returns one `Message`. Neither component sleeps, retries, invokes models/tools/flows, or reads secrets.

- [ ] **Step 4: Run GREEN and self-review (2-5 min)**

Run the RED command; expect delegation and invalid-result tests PASS. Confirm Agent free text is never an accepted renderer input.

- [ ] **Step 5: Propose commit and wait (2-5 min)**

Propose `feat(langflow): add retry and deterministic rendering components`; wait for developer approval.

### Task 20: Import Boundary Enforcement

**Original task IDs:** 4.5

**Files:**
- Create: `.importlinter`
- Create: `tests/static/test_architecture_boundaries.py`
- Test: `.importlinter`, `tests/static/test_architecture_boundaries.py`

**Interfaces:**
- Consumes: completed Python package graph.
- Produces: three named forbidden-import contracts and subprocess proof that core import does not load LFX.

- [ ] **Step 1: Write architecture subprocess test (2-5 min)**

```python
def test_core_import_does_not_load_lfx():
    output = run_python("import sys; import hulubul.core.models.operational; print('lfx' in sys.modules)")
    assert output.strip() == "False"
```

- [ ] **Step 2: Run RED (2-5 min)**

Run: `poetry run lint-imports`

Expected: FAIL because `.importlinter` is absent.

- [ ] **Step 3: Add exact forbidden contracts (2-5 min per contract)**

```ini
[importlinter]
root_package = hulubul
include_external_packages = True
[importlinter:contract:core-is-inward]
type = forbidden
source_modules = hulubul.core.models
forbidden_modules = hulubul.request_intake
    lfx
    langflow
```

Add model contract forbidding services/entrypoints/LFX/LangFlow and service contract forbidding entrypoints/LFX/LangFlow.

- [ ] **Step 4: Run GREEN and self-review (2-5 min)**

Run: `poetry run lint-imports && poetry run pytest tests/static/test_architecture_boundaries.py tests/unit -q`

Expected: all three contracts kept; subprocess/unit tests PASS. Confirm no adapters/repository/FastAPI package exists.

- [ ] **Step 5: Propose commit and wait (2-5 min)**

Propose `build: enforce Python architecture boundaries`; wait for developer approval.

### Task 21: Operational Conversation Binding Schema

**Original task IDs:** 5.1

**Files:**
- Create: `infra/cypher/operational-schema.cypher`
- Modify: `infra/scripts/neo4j-setup-schema.sh`
- Create: `tests/integration/neo4j/test_operational_schema.py`
- Test: `tests/integration/neo4j/test_operational_schema.py`

**Interfaces:**
- Consumes: existing `infra/cypher/schema.cypher`, disposable Neo4j driver fixture.
- Produces: unique `OperationalConversationBinding.sessionId`; schema setup order domain -> operational -> online wait.

- [ ] **Step 1: Write uniqueness/relationship-only tests (2-5 min)**

```python
def test_binding_uses_relationship_only(driver):
    create_binding(driver, SESSION, REQUEST)
    row = driver.execute_query("MATCH (b:OperationalConversationBinding) RETURN b.activeRequestId AS duplicate").records[0]
    assert row["duplicate"] is None
```

- [ ] **Step 2: Run RED (2-5 min)**

Run: `poetry run pytest tests/integration/neo4j/test_operational_schema.py -q`

Expected: FAIL because duplicate session nodes can commit or operational schema is absent.

- [ ] **Step 3: Add exact additive Cypher and setup order (2-5 min)**

```cypher
CREATE CONSTRAINT operationalconversationbinding_sessionId_unique IF NOT EXISTS
FOR (n:OperationalConversationBinding) REQUIRE n.sessionId IS UNIQUE;
```

Apply `schema.cypher`, then `operational-schema.cypher`, then `CALL db.awaitIndexes(120)`; do not add LinkML/generated changes or an `activeRequestId` property/index.

- [ ] **Step 4: Run GREEN and self-review (2-5 min)**

Run the RED command; expect uniqueness and relationship-only tests PASS. Run `git diff -- model/linkml model/generated`; expect no diff.

- [ ] **Step 5: Propose commit and wait (2-5 min)**

Propose `feat(neo4j): add operational conversation binding schema`; wait for developer approval.

### Task 22: Direct Graph Assertions And Context Fixtures

**Original task IDs:** 5.2

**Files:**
- Create: `tests/fixtures/neo4j/change1_contexts.py`
- Create: `tests/support/graph_probe.py`
- Create: `tests/support/acceptance_types.py`
- Create: `tests/integration/neo4j/test_change1_context_fixtures.py`
- Test: `tests/integration/neo4j/test_change1_context_fixtures.py`

**Interfaces:**
- Consumes: Neo4j Driver and operational/domain graph mapping.
- Produces: isolated factories for no binding, sparse/complete requests, each of all 11 recognized statuses, unknown/null raw status, closed precedence over every recognized/unknown/null value, missing target, constrained duplicate active relationships, constrained duplicate active targets, and concurrent snapshots; GraphProbe signatures are defined in [Acceptance Harness, Persistence, And Observability](#acceptance-harness-persistence-and-observability). Synthetic `binding_count=2` is not a Neo4j fixture and remains in Task 6 only.

- [ ] **Step 1: Write fixture inventory and direct-query tests (2-5 min)**

```python
def test_each_recognized_status_has_an_isolated_graph_fixture(status_context_factories):
    assert set(status_context_factories) == set(RequestStatus)
    assert len({factory().namespace for factory in status_context_factories.values()}) == 11
```

- [ ] **Step 2: Run RED (2-5 min)**

Run: `poetry run pytest tests/integration/neo4j/test_change1_context_fixtures.py -q`

Expected: FAIL because factories and graph probe are absent.

- [ ] **Step 3: Implement parameterized direct assertions (2-5 min per helper)**

```python
def count_requests_for_session(driver: Driver, session_id: str) -> int:
    query = "MATCH (:OperationalConversationBinding {sessionId: $session_id})-[:BINDS_ACTIVE_REQUEST]->(r:DeliveryRequest) RETURN count(r) AS count"
    return driver.execute_query(query, session_id=session_id).records[0]["count"]
```

Use parameter maps for every query. Keep the unique session constraint enabled. Create only inconsistent relationship/target/label shapes that Neo4j Community permits: one binding with duplicate `BINDS_ACTIVE_REQUEST` relationships and one binding with distinct active targets. Do not attempt duplicate `sessionId` fixture construction or weaken/drop the constraint.

- [ ] **Step 4: Run GREEN and self-review (2-5 min)**

Run the RED command; expect all 11 statuses, unknown/null, closed precedence, sparse/complete, missing target, duplicate relationship/target, and typed direct snapshots PASS. Confirm no helper invokes LF-70, fabricates synthetic duplicate binding nodes, weakens uniqueness, or includes a secret.

- [ ] **Step 5: Propose commit and wait (2-5 min)**

Propose `test(neo4j): add direct Change 1 graph fixtures`; wait for developer approval.

### Task 23: Disposable Neo4j Testcontainer

**Original task IDs:** 5.3

**Files:**
- Create: `tests/integration/conftest.py`
- Create: `tests/integration/neo4j/test_neo4j_testcontainer.py`
- Test: `tests/integration/neo4j/test_neo4j_testcontainer.py`

**Interfaces:**
- Consumes: pinned Neo4j digest, both schema files, Neo4j driver.
- Produces: session-scoped `neo4j_container`, `neo4j_driver`, unique network alias and namespaced cleanup; no developer database use.

- [ ] **Step 1: Write isolation/version/schema test (2-5 min)**

```python
def test_disposable_neo4j_has_approved_version_and_schemas(neo4j_driver):
    assert server_version(neo4j_driver) == "5.26.28"
    assert REQUIRED_CONSTRAINTS <= constraint_names(neo4j_driver)
```

- [ ] **Step 2: Run RED (2-5 min)**

Run: `poetry run pytest tests/integration/neo4j/test_neo4j_testcontainer.py -q`

Expected: FAIL because disposable fixture is absent; it must not fall back to localhost.

- [ ] **Step 3: Implement isolated fixture (2-5 min per fixture)**

```python
container = Neo4jContainer(image=NEO4J_IMAGE).with_kwargs(network=network, network_aliases=[alias])
```

Generate a synthetic per-session password in process memory, apply both schemas, and yield typed endpoints. Teardown only the container/network created by this fixture.

- [ ] **Step 4: Run GREEN and self-review (2-5 min)**

Run the RED command; expect PASS from a clean container. Confirm no `infra/.env`, fixed localhost development URI, seed file, or persistent volume is used.

- [ ] **Step 5: Propose commit and wait (2-5 min)**

Propose `test(neo4j): add disposable Neo4j integration fixture`; wait for developer approval.

### Task 24: Isolated MCP Protocol Fixture

**Original task IDs:** 5.4

**Files:**
- Create: `infra/scripts/mcp-readiness.py`
- Create: `tests/support/mcp_client.py`
- Create: `tests/integration/neo4j/test_mcp_readiness.py`
- Modify: `tests/integration/conftest.py`
- Test: `tests/integration/neo4j/test_mcp_readiness.py`

**Interfaces:**
- Consumes: disposable Neo4j network alias; MCP `/mcp/`; allowed-host config.
- Produces: `wait_for_mcp(url: str, expected_server: str, expected_tools: frozenset[str]) -> None`; exact tool set.

- [ ] **Step 1: Write protocol-not-port readiness test (2-5 min)**

```python
EXPECTED_TOOLS = frozenset({"get_neo4j_schema", "read_neo4j_cypher", "write_neo4j_cypher"})
def test_mcp_ready_only_after_initialize_and_exact_inventory(mcp_client):
    assert frozenset(mcp_client.list_tools()) == EXPECTED_TOOLS
```

- [ ] **Step 2: Run RED (2-5 min)**

Run: `poetry run pytest tests/integration/neo4j/test_mcp_readiness.py -q`

Expected: FAIL because a TCP-only check or Host rejection cannot satisfy MCP initialization.

- [ ] **Step 3: Implement networked protocol gate (2-5 min per phase)**

Start MCP on the disposable network with `NEO4J_MCP_SERVER_ALLOWED_HOSTS=<test-alias>,localhost,127.0.0.1`, initialize streamable HTTP, verify server name, then compare tool names exactly. Do not accept architectural shorthand names.

- [ ] **Step 4: Run GREEN and self-review (2-5 min)**

Run the RED command; expect initialization and exact inventory PASS through service DNS. Confirm a localhost-only allowed-host setting causes the focused negative test to fail readiness.

- [ ] **Step 5: Propose commit and wait (2-5 min)**

Propose `test(mcp): add isolated protocol readiness fixture`; wait for developer approval.

### Task 25: Reproducible Runtime Pins

**Original task IDs:** 6.1

**Files:**
- Modify: `infra/docker-compose.yaml`
- Modify: `infra/mcp/Dockerfile`
- Create: `infra/mcp/requirements.in`
- Modify/generated: `infra/mcp/requirements.txt`
- Create: `tests/static/test_runtime_pins.py`
- Test: `tests/static/test_runtime_pins.py`

**Interfaces:**
- Consumes: exact image/dependency pins in Global Constraints.
- Produces: immutable compose/base references and hash-locked MCP install.

- [ ] **Step 1: Write mutable-tag/hash-lock tests (2-5 min)**

```python
def test_runtime_images_are_exactly_approved(compose):
    assert compose["services"]["langflow"]["image"] == LANGFLOW_IMAGE
    assert compose["services"]["postgres"]["image"] == POSTGRES_IMAGE
    assert compose["services"]["neo4j"]["image"] == NEO4J_IMAGE
```

- [ ] **Step 2: Run RED (2-5 min)**

Run: `poetry run pytest tests/static/test_runtime_pins.py -q`

Expected: FAIL on mutable LangFlow/PostgreSQL/Neo4j/MCP base references and unhashed MCP transitive dependencies.

- [ ] **Step 3: Pin and compile lock (2-5 min per artifact)**

```dockerfile
FROM python:3.12-slim@sha256:57cd7c3a7a273101a6485ba99423ee568157882804b1124b4dd04266317710de
COPY requirements.txt .
RUN pip install --no-cache-dir --require-hashes -r requirements.txt
```

Generate with `pip-compile --generate-hashes --resolver=backtracking --strip-extras --allow-unsafe --output-file infra/mcp/requirements.txt infra/mcp/requirements.in`, then rerun to the same path and byte-compare. Stop if the resulting lock SHA differs from the approved preflight without developer review of the dependency graph.

- [ ] **Step 4: Run GREEN and self-review (2-5 min)**

Run: `poetry run pytest tests/static/test_runtime_pins.py -q && docker compose -f infra/docker-compose.yaml config --images`

Expected: tests PASS and command prints only pinned image references. Do not save full interpolated Compose config.

- [ ] **Step 5: Propose commit and wait (2-5 min)**

Propose `build(infra): pin Phase 1 runtime dependencies`; wait for developer approval.

### Task 26: Runtime Readiness And Dependency Order

**Original task IDs:** 6.2

**Files:**
- Modify: `infra/docker-compose.yaml`
- Create: `infra/docker-compose.test.yaml`
- Create: `tests/integration/runtime/test_readiness_order.py`
- Modify: `Makefile`
- Test: `tests/integration/runtime/test_readiness_order.py`

**Interfaces:**
- Consumes: pinned services, schema job, MCP readiness script.
- Produces: ordered readiness PostgreSQL -> Neo4j -> schemas -> MCP -> LangFlow -> deployment; loopback-only ports; long-running restart policies only.

- [ ] **Step 1: Write dependency/health contract test (2-5 min)**

```python
def test_mcp_depends_on_completed_schema(compose):
    assert compose["services"]["mcp-neo4j"]["depends_on"]["neo4j-schema"]["condition"] == "service_completed_successfully"
```

- [ ] **Step 2: Run RED (2-5 min)**

Run: `poetry run pytest tests/integration/runtime/test_readiness_order.py -q`

Expected: FAIL because current MCP readiness is TCP-only and service order is incomplete.

- [ ] **Step 3: Implement topology/readiness (2-5 min per service)**

```yaml
ports:
  - "127.0.0.1:7860:7860"
environment:
  NEO4J_MCP_SERVER_ALLOWED_HOSTS: mcp-neo4j,localhost,127.0.0.1
restart: unless-stopped
```

Use `pg_isready`, authenticated Bolt `RETURN 1`, one-shot dual schema job, protocol MCP readiness, LangFlow `/health` plus database-backed API probe, then exactly three flow IDs. One-shot jobs have no restart policy.

- [ ] **Step 4: Run GREEN and self-review (2-5 min)**

Run: `make acceptance-up && make acceptance-ready`; expect each named readiness stage exits 0 in order from empty disposable volumes. Always run `make acceptance-down`. Confirm all host ports bind `127.0.0.1`.

- [ ] **Step 5: Propose commit and wait (2-5 min)**

Propose `feat(infra): add protocol-ordered Phase 1 readiness`; wait for developer approval.

### Task 27: Read-Only Source Mounts And Persistent Runtime State

**Original task IDs:** 6.3

**Files:**
- Modify: `infra/docker-compose.yaml`
- Modify: `infra/docker-compose.test.yaml`
- Create: `tests/integration/runtime/test_read_only_runtime_assets.py`
- Test: `tests/integration/runtime/test_read_only_runtime_assets.py`

**Interfaces:**
- Consumes: `langflow/`, `src/`, component category path.
- Produces: read-only mounts, `PYTHONPATH=/app/src`, `LANGFLOW_COMPONENTS_PATH=/app/custom_components`, disabled starter creation/update, separate PostgreSQL/Neo4j volumes.

- [ ] **Step 1: Write mount/starter tests (2-5 min)**

```python
def test_source_mounts_are_read_only(compose):
    assert "../langflow:/app/hulubul-langflow:ro" in langflow_volumes(compose)
    assert "../src:/app/src:ro" in langflow_volumes(compose)
```

- [ ] **Step 2: Run RED (2-5 min)**

Run: `poetry run pytest tests/integration/runtime/test_read_only_runtime_assets.py -q`

Expected: FAIL because mounts/path/starter settings are absent.

- [ ] **Step 3: Add exact runtime settings (2-5 min per setting)**

```yaml
environment:
  PYTHONPATH: /app/src
  LANGFLOW_COMPONENTS_PATH: /app/custom_components
  LANGFLOW_CREATE_STARTER_PROJECTS: "false"
  LANGFLOW_UPDATE_STARTER_PROJECTS: "false"
```

Keep LangFlow config/PostgreSQL/Neo4j state on distinct volumes; tracked assets are never writable runtime stores.

- [ ] **Step 4: Run GREEN and self-review (2-5 min)**

Run the RED command against a clean stack; expect custom components import and no starter-flow drift. Confirm writing through each source mount fails and database volumes remain writable.

- [ ] **Step 5: Propose commit and wait (2-5 min)**

Propose `feat(infra): mount tracked LangFlow assets read only`; wait for developer approval.

### Task 28: LangFlow API-Key Enforcement

**Original task IDs:** 6.4

**Files:**
- Modify: `infra/docker-compose.yaml`, `infra/docker-compose.test.yaml`, `infra/langflow.env.example`
- Create: `tests/support/langflow_client.py`
- Create: `tests/integration/langflow/test_api_authentication.py`
- Test: `tests/integration/langflow/test_api_authentication.py`

**Interfaces:**
- Consumes: environment-sourced API key name; LangFlow run endpoint; API actor request-variable headers; ignored Playground actor environment names.
- Produces: `LangFlowClient.run_lf00(conversation: Conversation, message: str) -> FlowReply` with private key field and exact actor request-variable headers; authenticated programmatic invocation while UI auto-login remains local and Playground uses ignored simulated-actor environment values.

- [ ] **Step 1: Write no-key/wrong-key/valid-key tests (2-5 min)**

```python
def test_missing_api_key_is_rejected_before_mutation(stack):
    before = stack.graph.total_request_count()
    assert stack.langflow.run_without_key().status_code == 403
    assert stack.graph.total_request_count() == before

def test_api_actor_uses_request_variable_headers(client, transport, conversation):
    client.run_lf00(conversation, SYNTHETIC_MESSAGE)
    request = transport.requests[-1]
    assert request.headers["X-LANGFLOW-GLOBAL-VAR-HULUBUL_PHASE1_ACTOR_ID"] == conversation.actor.actor_id
```

- [ ] **Step 2: Run RED (2-5 min)**

Run: `poetry run pytest tests/integration/langflow/test_api_authentication.py -q`

Expected: FAIL because unauthenticated API access is accepted or no environment-key mode exists.

- [ ] **Step 3: Configure key source and private client (2-5 min)**

```yaml
environment:
  LANGFLOW_API_KEY_SOURCE: env
  LANGFLOW_FALLBACK_TO_ENV_VAR: "true"
  LANGFLOW_STORE_ENVIRONMENT_VARIABLES: "false"
```

The client resolves the key internally from a named process environment variable, uses `repr=False`, and reports only HTTP status, flow ID, and correlation ID on error. It sends required `X-LANGFLOW-GLOBAL-VAR-HULUBUL_PHASE1_ACTOR_ID` and optional `X-LANGFLOW-GLOBAL-VAR-HULUBUL_PHASE1_ACTOR_DISPLAY_NAME`; those values never enter user text or `tweaks`. Compose passes only ignored `HULUBUL_PHASE1_PLAYGROUND_ACTOR_ID` and optional display name to the local Playground path. Neither actor path exposes caller-controlled component ports.

- [ ] **Step 4: Run GREEN and self-review (2-5 min)**

Run the RED command; expect 403 for missing/wrong key, success for environment key plus exact actor request headers, missing required actor rejection, optional display-name behavior, Playground ignored-environment behavior, and zero unauthorized graph mutation. Search tracked diffs for nonempty key/actor values; expect none.

- [ ] **Step 5: Propose commit and wait (2-5 min)**

Propose `feat(infra): require API keys for LangFlow runs`; wait for developer approval.

### Task 29: Three-Flow Manifest And LFX Environments

**Original task IDs:** 7.1

**Files:**
- Create: `langflow/flow-manifest.yaml`
- Create: `langflow/.lfx/environments.yaml`
- Create: `langflow/README.md`
- Create: `tests/static/test_flow_manifest.py`
- Test: `tests/static/test_flow_manifest.py`

**Interfaces:**
- Consumes: locked flow/component IDs and environment names.
- Produces: the exact version-1 manifest defined in [Stable Flow Manifest And Topology](#stable-flow-manifest-and-topology) and the LFX `local`/`ci` map.

- [ ] **Step 1: Write exact manifest tests (2-5 min)**

```python
def test_manifest_has_exact_change1_flows(manifest):
    assert list(manifest["deployment_order"]) == ["lf-70-data-access", "lf-10-request-intake", "lf-00-main-router"]
    assert set(manifest["flows"]) == set(manifest["deployment_order"])
```

- [ ] **Step 2: Run RED (2-5 min)**

Run: `poetry run pytest tests/static/test_flow_manifest.py -q`

Expected: FAIL because manifest/environment map are absent.

- [ ] **Step 3: Add exact manifest and environment map (2-5 min per file)**

```yaml
environments:
  local: {url: http://127.0.0.1:7860, api_key_env: HULUBUL_LANGFLOW_LOCAL_API_KEY}
  ci: {url: http://127.0.0.1:7860, api_key_env: HULUBUL_LANGFLOW_CI_API_KEY}
defaults: {environment: local}
```

Document LF-70/LF-10/LF-00 deployment order and pull-normalize-validate-push-status loop. Include variable names only.

- [ ] **Step 4: Run GREEN and self-review (2-5 min)**

Run the RED command; expect exact UUIDs, IDs, references, bindings, order, and no-LF-20 assertions PASS. Confirm all three flow files named by manifest are expected but not hand-created in this task.

- [ ] **Step 5: Propose commit and wait (2-5 min)**

Propose `feat(langflow): add stable three-flow manifest`; wait for developer approval.

### Task 30: Deterministic Flow Normalization

**Original task IDs:** 7.2

**Files:**
- Create: `scripts/normalize_langflow_flows.py`
- Create: `tests/static/test_flow_normalization.py`
- Modify: `Makefile`
- Test: `tests/static/test_flow_normalization.py`

**Interfaces:**
- Consumes: pinned `lfx export --in-place --strip-volatile --strip-secrets --strip-node-volatile --indent 2`; manifest runtime bindings.
- Produces: `normalize_paths(paths: Sequence[Path], mode: Literal["check", "write"]) -> tuple[Path, ...]`; idempotent normalized bytes without array reordering.

- [ ] **Step 1: Write idempotence/order/name-restoration tests (2-5 min)**

```python
def test_normalization_preserves_node_and_edge_order(sample_flow):
    before = semantic_array_ids(sample_flow)
    normalized = normalize_fixture(sample_flow)
    assert semantic_array_ids(normalized) == before
```

- [ ] **Step 2: Run RED (2-5 min)**

Run: `poetry run pytest tests/static/test_flow_normalization.py -q`

Expected: FAIL because normalizer is absent.

- [ ] **Step 3: Implement pinned pass and allowlisted restoration (2-5 min per phase)**

Run LFX in a temporary tree; restore only exact manifest-declared variable names to `load_from_db=true` fields; recursively sort objects; retain arrays and ordinary canvas `position`; compare bytes for `--check` and write only for `--write`.

```python
if restored_name not in manifest_runtime_variable_names:
    raise NormalizationError("undeclared runtime variable reference")
```

- [ ] **Step 4: Run GREEN and self-review (2-5 min)**

Run the RED command; expect two-pass byte identity, array order, volatile stripping, and safe name restoration PASS. Confirm no runtime value can be restored.

- [ ] **Step 5: Propose commit and wait (2-5 min)**

Propose `build(langflow): add deterministic flow normalization`; wait for developer approval.

### Task 31: Pinned Component-Schema And Handle Preflight

**Original task IDs:** 7.3

**Files:**
- Create: `scripts/inspect_langflow_components.py`
- Create: `scripts/validate_langflow_assets.py`
- Create: `tests/static/test_flow_security.py`
- Create: `tests/static/test_flow_topology.py`
- Generated/untracked: `build/langflow-component-schemas.json`
- Test: both static files plus pinned-image inspection

**Interfaces:**
- Consumes: pinned LangFlow image, manifest, running disposable MCP, custom component mount.
- Produces: versioned schema snapshot containing component class key/version/module/code hash, static/dynamic ports, Run Flow normal/Tool Mode names, MCP schemas/tool inventory, provider/Agent/Chat behavior, Message/active-graph session access, request-global variable access, omitted-session flow-ID fallback behavior, and serialized handle grammar; `validate_manifest(path: Path) -> ValidationReport`.

- [ ] **Step 1: Write inspector/validator contract tests (2-5 min)**

```python
def test_snapshot_records_runtime_identity(snapshot):
    assert snapshot["langflow_version"] == "1.10.2"
    assert snapshot["lfx_version"] == "1.10.2"
    assert set(snapshot["mcp_tools"]) == EXPECTED_MCP_TOOLS
    assert snapshot["execution_context"]["message_session_accessor"]
    assert snapshot["execution_context"]["graph_session_accessor"]
    assert snapshot["execution_context"]["request_global_accessor"]
```

- [ ] **Step 2: Run RED (2-5 min)**

Run: `poetry run pytest tests/static/test_flow_security.py tests/static/test_flow_topology.py -q`

Expected: FAIL because inspector, validator, and schema snapshot are absent.

- [ ] **Step 3: Execute the pinned-image preflight (2-5 min per command)**

```bash
docker run --rm --entrypoint langflow langflowai/langflow:1.10.2@sha256:ae6f9afd03bc032dc2989ece49791fcf83871230aff9d6e485c8e1ebada1e70f --version
docker run --rm --entrypoint lfx langflowai/langflow:1.10.2@sha256:ae6f9afd03bc032dc2989ece49791fcf83871230aff9d6e485c8e1ebada1e70f --version
poetry run python scripts/inspect_langflow_components.py --image langflowai/langflow:1.10.2@sha256:ae6f9afd03bc032dc2989ece49791fcf83871230aff9d6e485c8e1ebada1e70f --output build/langflow-component-schemas.json
```

Expected output: first two commands report `1.10.2`; snapshot records inspected public/advanced ports, one MCP Tool Mode toolkit with exact tools, LF-70/LF-10 selected-flow dynamic names, `OpenAIModel.model_output`, Agent `structured_response`, accepted JSON/Message custom outputs, and exact runtime accessors/behavior needed for Message session, active graph session, request globals, and omitted-session fallback detection.

- [ ] **Step 4: Apply the mandatory stop condition (2-5 min)**

Stop before Task 32 if any version differs; a required port/output/tool is absent; API-key environment mode fails; Message/graph session or request-global access cannot be verified; omitted session cannot be distinguished from flow-ID fallback; custom JSON/Message outputs fail; inspected selected-flow names cannot carry the required fixed advanced values; MCP Host allowlisting fails; or Agent structured output cannot be validated. Re-shape the design with the developer; do not substitute actor/session tweaks, public actor ports, FastAPI, standalone LFX acceptance, extra flows, or handwritten handles.

- [ ] **Step 5: Implement static validation and run GREEN (2-5 min per rule)**

Validator rules: exact manifest schema/IDs/files; unique stable IDs; exact public ports; only LF-70 may contain MCP; no LF-20; allowlisted environment names with `load_from_db=true`; no nonempty secret fields; no caller Cypher; semantic edges compatible with the generated snapshot. Run tests; expect PASS against synthetic fixtures and the generated snapshot.

- [ ] **Step 6: Self-review and propose commit (2-5 min)**

Confirm `build/` is ignored, snapshot contains schemas/handles but no environment values, and Task 32 explicitly consumes this run's snapshot. Propose `build(langflow): add pinned component and flow validation`; wait for developer approval.

### Task 32: LF-70 Stable Skeleton From Pinned Export

**Original task IDs:** 8.1

**Files:**
- Create from pinned runtime export: `langflow/flows/10-lf-70-data-access.json`
- Modify: `langflow/flow-manifest.yaml`
- Modify: `tests/static/test_flow_topology.py`, `tests/static/test_flow_security.py`
- Test: the two static test files

**Interfaces:**
- Consumes: immediately preceding `build/langflow-component-schemas.json`, generated operation schemas, LF-70 stable IDs.
- Produces: normalized LF-70 with one public input, one result, one OpenAIModel, one Agent, one MCP toolkit, one retry component; exact exported handles frozen by static tests.

- [ ] **Step 1: Add LF-70 topology assertions (2-5 min)**

```python
def test_only_lf70_contains_one_mcp_toolkit(flows):
    assert component_ids(flows.lf70, "MCPTools") == {"MCPTools-hlb-lf-70-neo4j-v1"}
    assert not component_ids(flows.lf10, "MCPTools")
    assert not component_ids(flows.lf00, "MCPTools")
```

- [ ] **Step 2: Run RED (2-5 min)**

Run: `poetry run pytest tests/static/test_flow_topology.py::test_lf70_stable_boundaries -q`

Expected: FAIL because LF-70 flow file is absent.

- [ ] **Step 3: Build in pinned runtime and export (2-5 min per component/edge)**

Create the six semantic nodes/edges from the [locked LF-70 topology](#stable-flow-manifest-and-topology) through LangFlow 1.10.2 UI/API, using the generated component snapshot for ports. Use one `MCPTools` Tool Mode node pointed at `http://mcp-neo4j:8000/mcp/`; model settings use manifest variable names. Export, then run:

```bash
poetry run python scripts/normalize_langflow_flows.py --write langflow/flows/10-lf-70-data-access.json
poetry run python scripts/validate_langflow_assets.py langflow/flow-manifest.yaml
```

Freeze the runtime-exported source/target handles and edge IDs in static semantic assertions. Do not hand-compose serialized edge handles.

- [ ] **Step 4: Add bounded LF-70 prompt (2-5 min)**

```text
Process exactly one validated DataOperationRequest. Accept only the five declared operations. Never accept caller Cypher, invent identifiers, change operation, or affect another aggregate. Use parameters for caller data. Confirmed writes report exactly one affected request. After uncertain write dispatch return MCP_WRITE_AMBIGUOUS and never call write again. Return only DataOperationResult.
```

- [ ] **Step 5: Run GREEN and self-review (2-5 min)**

Run: `poetry run lfx validate --level 4 --strict --skip-credentials langflow/flows/10-lf-70-data-access.json && poetry run lfx upgrade --strict langflow/flows/10-lf-70-data-access.json && poetry run pytest tests/static/test_flow_topology.py tests/static/test_flow_security.py -q`

Expected: all PASS; one MCP toolkit only in LF-70, public ports exact, no Chat Output, no literal secret/query.

- [ ] **Step 6: Propose commit and wait (2-5 min)**

Propose `feat(langflow): add LF-70 typed data-access skeleton`; wait for developer approval.

### Task 33: LF-70 Read Operations

**Original task IDs:** 8.2

**Files:**
- Modify through pinned export: `langflow/flows/10-lf-70-data-access.json`
- Create: `tests/integration/langflow/test_lf70_reads.py`
- Modify: `tests/support/graph_probe.py`
- Create/Modify: `tests/fixtures/recorded_model/change1_flow_scripts.jsonl`
- Test: `tests/integration/langflow/test_lf70_reads.py`

**Interfaces:**
- Consumes: routing/read operation requests, LF-70 flow, direct graph fixtures, retry policy.
- Produces: strict `RoutingLookupRecord`, deterministic `adapt_routing_lookup` output, validated RoutingContext/DeliveryRequestSnapshot; one retry for eligible reads only.

- [ ] **Step 1: Write read matrix tests (2-5 min per case)**

```python
@pytest.mark.parametrize("status", tuple(RequestStatus))
def test_routing_context_read_preserves_enum_identity(status, lf70, graph):
    result = lf70.routing_context(graph.context_for_status(status))
    assert result.request_status is status
```

- [ ] **Step 2: Run RED (2-5 min)**

Run: `poetry run pytest tests/integration/langflow/test_lf70_reads.py -q`

Expected: FAIL because read scripts/prompt/output rows do not yet implement operation intent.

- [ ] **Step 3: Add operation-specific prompt/schema rows (2-5 min per operation)**

For routing, require parameters `{session_id}` and cardinality output with request row key `requestStatusRaw`; validate the internal raw record before calling `adapt_routing_lookup`. For request read, require `{request_id}` and the exact role/subgraph arrays in [Neo4j Operation Intent](#neo4j-operation-intent). Require `read_neo4j_cypher`, never write. Raw status text never enters generated schemas, errors, messages, logs, or traces.

- [ ] **Step 4: Add transient retry evidence (2-5 min)**

Prime recorded responses read-timeout then success; assert two attempts and a 500 ms retry decision. Prime two failures; assert `MCP_READ_TRANSIENT_FAILURE` and no mutating operation.

- [ ] **Step 5: Run GREEN and self-review (2-5 min)**

Run the RED command; expect no-binding/sparse/complete, all 11 recognized statuses, unknown/null, closed precedence over every recognized/unknown/null value, all cardinality failures, constrained duplicate relationship/target, and retry cases PASS. Assert typed status with enum identity (`is`), compare every result to direct Neo4j queries, and confirm raw status never escapes plus model SDK retries remain zero.

- [ ] **Step 6: Propose commit and wait (2-5 min)**

Propose `feat(langflow): add LF-70 request reads`; wait for developer approval.

### Task 34: LF-70 Atomic Request Creation

**Original task IDs:** 8.3

**Files:**
- Modify through pinned export: `langflow/flows/10-lf-70-data-access.json`
- Create/modify: `tests/integration/langflow/test_lf70_writes.py`
- Modify: `tests/fixtures/recorded_model/change1_flow_scripts.jsonl`, `tests/support/graph_probe.py`
- Test: focused create tests

**Interfaces:**
- Consumes: CreateDeliveryRequestRequest with pre-generated IDs/facts and no caller timestamp fields.
- Produces: one transaction creating `new` request, Sender, binding, and only supplied subgraphs; one-count confirmation with Neo4j-owned equal `created_at`/`updated_at`.

- [ ] **Step 1: Write atomicity/sparse tests (2-5 min)**

```python
def test_binding_conflict_rolls_back_orphan_request(lf70, graph, create_request):
    results = run_concurrently(create_request, create_request)
    assert graph.request_count_for_session(create_request.session_id) == 1
    assert graph.orphan_request_ids(create_request.namespace) == frozenset()

def test_create_timestamps_are_owned_by_one_neo4j_transaction(lf70, create_request):
    result = lf70.create(create_request)
    assert result.created_at == result.updated_at
```

- [ ] **Step 2: Run RED (2-5 min)**

Run: `poetry run pytest tests/integration/langflow/test_lf70_writes.py::test_create_request_and_binding_atomically tests/integration/langflow/test_lf70_writes.py::test_binding_conflict_rolls_back_orphan_request -q`

Expected: FAIL because creation is absent or a loser leaves an orphan.

- [ ] **Step 3: Add constrained create intent (2-5 min per subgraph)**

Reject `created_at`/`updated_at` in the strict create payload. Require one parameterized transaction beginning `WITH datetime() AS now`: merge Sender Agent by generated ID/identifier; create request `new` with `created=now` and `updated=now`, Sender role and binding with corresponding timestamps; `FOREACH` only over non-null Receiver/Parcel/pickup/drop-off maps; return request ID/status/created/updated/`affectedRequests=1`. Never merge Receiver by name.

- [ ] **Step 4: Run GREEN and direct assertions (2-5 min)**

Run the RED command plus strict caller-timestamp rejection and sparse/full create cases; expect one committed graph/binding, equal returned/persisted request timestamps, conflict loser rejected, no orphan, and absent facts create no nodes. Verify through GraphProbe only.

- [ ] **Step 5: Self-review and propose commit (2-5 min)**

Confirm no automatic create retry exists after dispatch. Propose `feat(langflow): create requests atomically through LF-70`; wait for developer approval.

### Task 35: LF-70 Optimistic Updates

**Original task IDs:** 8.4

**Files:**
- Modify through pinned export: `langflow/flows/10-lf-70-data-access.json`
- Modify: `tests/integration/langflow/test_lf70_writes.py`
- Test: focused update tests

**Interfaces:**
- Consumes: UpdateDeliveryRequestRequest with expected timestamp/status, nonempty validated updates, generated IDs.
- Produces: additive absent-fact/fill-only preferred-period update, fresh UTC updated timestamp, one-count confirmation, or exact non-mutating zero-row classification.

- [ ] **Step 1: Write winner/loser tests (2-5 min)**

```python
def test_concurrent_update_loser_does_not_overwrite(lf70, graph, same_snapshot_updates):
    first, second = run_concurrently(*same_snapshot_updates)
    assert sorted(r.success for r in (first, second)) == [False, True]
    assert graph.snapshot_for_session(SESSION).facts in EXPECTED_WINNERS
```

- [ ] **Step 2: Run RED (2-5 min)**

Run: `poetry run pytest tests/integration/langflow/test_lf70_writes.py::test_update_uses_expected_updated_at tests/integration/langflow/test_lf70_writes.py::test_concurrent_update_loser_does_not_overwrite -q`

Expected: FAIL because stale update succeeds or update path is absent.

- [ ] **Step 3: Add update intent (2-5 min per guard)**

Match request ID, exact `datetime($expected_updated_at)`, exact `$expected_status` constrained to `new/needsClarification`, absence of each supplied singular subgraph, and absent persisted preferred period when a non-null preferred period is supplied. Add only validated absent fields; null period means no change and existing values are never cleared/replaced. Set `updated=datetime()` and return one count. Empty updates fail before MCP. On zero rows, perform one non-mutating read to distinguish missing/inconsistent request, `INVALID_EXPECTED_STATUS`, or `CONCURRENT_MODIFICATION` (including an accepted fact/period now occupying the fill-only slot); never replay the update.

- [ ] **Step 4: Run GREEN and direct assertions (2-5 min)**

Run the RED command; expect one writer, exact expected-status enforcement, fill-only preferred period, one `CONCURRENT_MODIFICATION`, winner retained, no duplicate/replaced subgraphs, exact zero-row classification, and no replay. Confirm direct graph timestamp changed only once.

- [ ] **Step 5: Self-review and propose commit (2-5 min)**

Confirm no update overwrites an existing accepted fact. Propose `feat(langflow): guard LF-70 optimistic updates`; wait for developer approval.

### Task 36: LF-70 Status Compare-And-Set

**Original task IDs:** 8.5

**Files:**
- Modify through pinned export: `langflow/flows/10-lf-70-data-access.json`
- Modify: `tests/integration/langflow/test_lf70_writes.py`
- Test: focused transition matrix

**Interfaces:**
- Consumes: SetRequestStatusRequest, transition policy, current timestamp/status.
- Produces: previous/current status, fresh updated timestamp, one-count confirmation or exact stale/transition errors.

- [ ] **Step 1: Write all-edge/no-mutation tests (2-5 min)**

```python
@pytest.mark.parametrize("source,target", ALLOWED_POST_CREATE_TRANSITIONS)
def test_set_status_transition_matrix(source, target, lf70, graph):
    result = lf70.set_status(source, target)
    assert result.current_status is target
    assert graph.current_status(result.request_id) is target
```

- [ ] **Step 2: Run RED (2-5 min)**

Run: `poetry run pytest tests/integration/langflow/test_lf70_writes.py::test_set_status_transition_matrix -q`

Expected: FAIL because valid edges are absent or invalid edges mutate.

- [ ] **Step 3: Add exact status intent (2-5 min)**

Require ID, expected updated/status, and pair membership in exactly `new->needsClarification`, `new->complete`, `needsClarification->complete`; set status/updated and return previous/current/count. Classify zero rows with authoritative follow-up read; never rerun the write.

- [ ] **Step 4: Run GREEN and direct assertions (2-5 min)**

Run the RED command plus stale status/timestamp and `needsClarification->waitingResponse`; expect exact errors and unchanged graph for negatives.

- [ ] **Step 5: Self-review and propose commit (2-5 min)**

Confirm Change 1 writes only three statuses and `none->new` is confined to create. Propose `feat(langflow): enforce LF-70 intake transitions`; wait for developer approval.

### Task 37: LF-70 Ambiguity And Tool-Less Repair

**Original task IDs:** 8.6

**Files:**
- Modify through pinned export: `langflow/flows/10-lf-70-data-access.json`
- Create: `tests/integration/langflow/test_lf70_write_failures.py`
- Modify: `tests/fixtures/recorded_model/change1_flow_scripts.jsonl`
- Test: `tests/integration/langflow/test_lf70_write_failures.py`

**Interfaces:**
- Consumes: retry decision, dispatch marker, candidate raw structured result.
- Produces: one-dispatch maximum, ambiguous result identifiers, one tool-less formatter pass.

- [ ] **Step 1: Write one-dispatch/repair tests (2-5 min)**

```python
def test_ambiguous_write_is_not_replayed(lf70, model_controller):
    result = lf70.run(script="write-timeout-after-dispatch")
    assert result.error.code is ErrorCode.MCP_WRITE_AMBIGUOUS
    assert model_controller.write_tool_calls() == 1
```

- [ ] **Step 2: Run RED (2-5 min)**

Run: `poetry run pytest tests/integration/langflow/test_lf70_write_failures.py -q`

Expected: FAIL if write is called twice, raw malformed output claims success, or inspection IDs are absent.

- [ ] **Step 3: Wire retry/result decision (2-5 min per edge)**

Route only pre-dispatch eligible failures to one retry. Route malformed existing output to a formatter Agent/component with no tools and no Run Flow/MCP edge. Route post-dispatch timeout directly to ambiguous typed result.

- [ ] **Step 4: Run GREEN and self-review (2-5 min)**

Run the RED command; expect one write dispatch, zero replay, one tool-less repair maximum, second malformed -> `MALFORMED_AGENT_RESULT`, and preserved operation/correlation/session/request IDs. Inspect topology to prove repair has no tool edge.

- [ ] **Step 5: Propose commit and wait (2-5 min)**

Propose `feat(langflow): guard LF-70 write ambiguity`; wait for developer approval.

### Task 38: LF-10 Stable Skeleton

**Original task IDs:** 9.1

**Files:**
- Create from pinned export: `langflow/flows/20-lf-10-request-intake.json`
- Modify: `tests/static/test_flow_topology.py`, `tests/static/test_flow_security.py`
- Test: focused static topology

**Interfaces:**
- Consumes: LF-70 deployed stable ID, component schema snapshot, fixed validated envelope/context inputs, IntakeInput/IntakeResult schemas.
- Produces: LF-10 deterministic strict IntakeInput assembly, public direct-integration input/result, model, Agent, one LF-70 Run Flow Tool Mode component; no MCP/Chat Output and no model-substitutable trust metadata.

- [ ] **Step 1: Write LF-10 isolation test (2-5 min)**

```python
def test_lf10_has_only_lf70_logical_tool(lf10):
    assert tool_component_ids(lf10) == {"RunFlow-hlb-lf-10-data-access-v1"}
    assert component_ids(lf10, "MCPTools") == set()

def test_lf10_model_cannot_substitute_envelope_or_context(lf10):
    assert advanced_fixed_inputs(lf10) == {"envelope", "routing_context"}
    assert not advanced_fixed_inputs(lf10) & model_callable_fields(lf10)
```

- [ ] **Step 2: Run RED (2-5 min)**

Run: `poetry run pytest tests/static/test_flow_topology.py::test_lf10_has_only_lf70_logical_tool -q`

Expected: FAIL because LF-10 flow is absent.

- [ ] **Step 3: Build/export using snapshot handles (2-5 min per component/edge)**

Build fixed validated envelope/context inputs -> deterministic strict IntakeInput boundary -> Agent, model -> Agent, LF-70 Run Flow `component_as_tool` -> Agent, `structured_response` -> strict IntakeResult boundary. For direct LF-10 integration, accept canonical IntakeInput at the inspected public input; during LF-00 invocation the advanced fixed inputs come only from validated predecessor edges and are absent from the model tool schema. Set public input/result flags/ports from the snapshot. Export and normalize; do not hand-author edge handles or introduce actor/session tweaks.

- [ ] **Step 4: Add bounded intake prompt (2-5 min)**

```text
Use trusted actor/session metadata only. Extract only facts supplied now; never invent domain facts or database success. For no binding create one sparse truthful request/binding, then confirmed status transition. For bound intake read the exact request, merge newly validated facts, and use returned updated timestamps. Report all missing fields and one clarification. Never call MCP/Cypher, replay writes, create a second session request, or act after complete. Return only IntakeResult.
```

- [ ] **Step 5: Run GREEN and self-review (2-5 min)**

Run strict validate/upgrade plus focused topology/security tests; expect PASS, inspected public ports, strict wrapper assembly/equality, fixed non-model-substitutable envelope/context edges, one LF-70 tool, and no MCP/Chat Output/free-text result path.

- [ ] **Step 6: Propose commit and wait (2-5 min)**

Propose `feat(langflow): add LF-10 request intake skeleton`; wait for developer approval.

### Task 39: LF-10 One-Message Completion

**Original task IDs:** 9.2

**Files:**
- Modify through pinned export: `langflow/flows/20-lf-10-request-intake.json`
- Create: `tests/integration/langflow/test_lf10_request_intake.py`
- Modify: `tests/fixtures/recorded_model/change1_flow_scripts.jsonl`
- Test: focused complete intake

**Interfaces:**
- Consumes: complete MainFlowInput/RoutingContext, LF-70 create/status operations.
- Produces: confirmed IntakeResult with persisted ID, complete facts/status, no missing/clarification.

- [ ] **Step 1: Write complete-path direct graph test (2-5 min)**

```python
def test_complete_intake_in_one_message(lf10, graph, complete_envelope):
    result = lf10.run(complete_envelope)
    snapshot = graph.snapshot_for_session(complete_envelope.session_id)
    assert result.request_id == snapshot.request_id
    assert snapshot.status is RequestStatus.COMPLETE
```

- [ ] **Step 2: Run RED (2-5 min)**

Run: `poetry run pytest tests/integration/langflow/test_lf10_request_intake.py::test_complete_intake_in_one_message -q`

Expected: FAIL because extraction/create/transition sequence is absent.

- [ ] **Step 3: Prime exact deterministic operation sequence (2-5 min per call)**

Recorded Agent output extracts trusted Sender plus Receiver/pickup/drop-off/content/optional period; calls LF-70 create once, consumes returned updated timestamp, then calls status `new->complete`; emits only confirmed IntakeResult.

- [ ] **Step 4: Run GREEN and self-review (2-5 min)**

Run the RED command; expect one complete graph and binding, exact operation sequence, returned persisted ID, no clarification, and direct graph equality. Confirm no Python orchestration duplicates this sequence.

- [ ] **Step 5: Propose commit and wait (2-5 min)**

Propose `feat(langflow): complete one-message request intake`; wait for developer approval.

### Task 40: LF-10 Truthful Sparse Draft

**Original task IDs:** 9.3

**Files:**
- Modify through pinned export: `langflow/flows/20-lf-10-request-intake.json`
- Modify: `tests/integration/langflow/test_lf10_request_intake.py`
- Modify: `tests/fixtures/recorded_model/change1_flow_scripts.jsonl`
- Test: focused sparse capture

**Interfaces:**
- Consumes: partial IntakeFacts, completeness policy, LF-70 create/status.
- Produces: one sparse request/binding, only valid supplied subgraphs, `needsClarification`.

- [ ] **Step 1: Write sparse/no-invention tests (2-5 min)**

```python
def test_sparse_first_turn_has_no_placeholders(lf10, graph, pickup_and_parcel_envelope):
    lf10.run(pickup_and_parcel_envelope)
    snapshot = graph.snapshot_for_session(pickup_and_parcel_envelope.session_id)
    assert snapshot.receiver is None and snapshot.drop_off is None
```

- [ ] **Step 2: Run RED (2-5 min)**

Run: `poetry run pytest tests/integration/langflow/test_lf10_request_intake.py::test_sparse_first_turn_has_no_placeholders -q`

Expected: FAIL because sparse creation/status behavior is absent or facts are fabricated.

- [ ] **Step 3: Add sparse operation sequence (2-5 min)**

Extract only valid available facts, generate IDs only for present subgraphs, create as `new`, consume returned updated timestamp, request `new->needsClarification`, emit full missing set. Minimal intention creates Sender/request/binding only.

- [ ] **Step 4: Run GREEN and self-review (2-5 min)**

Run the RED command plus minimal-intention case; expect truthful graph, one binding/request, no absent-fact node, and confirmed `needsClarification`. Direct Neo4j assertions are mandatory.

- [ ] **Step 5: Propose commit and wait (2-5 min)**

Propose `feat(langflow): persist truthful sparse intake drafts`; wait for developer approval.

### Task 41: LF-10 Focused Clarification

**Original task IDs:** 9.4

**Files:**
- Modify through pinned export: `langflow/flows/20-lf-10-request-intake.json`
- Modify: `tests/integration/langflow/test_lf10_request_intake.py`
- Modify: `tests/fixtures/recorded_model/change1_flow_scripts.jsonl`
- Test: focused missing-set/question tests

**Interfaces:**
- Consumes: exact completeness order and renderer question map.
- Produces: complete missing tuple plus zero/one clarification field; invalid current field has priority.

- [ ] **Step 1: Write several-missing/invalid-priority tests (2-5 min)**

```python
def test_reports_all_missing_fields_and_asks_one(lf10, partial_envelope):
    result = lf10.run(partial_envelope)
    assert result.missing_fields == EXPECTED_MISSING
    assert result.clarification_field is IntakeField.RECEIVER_IDENTITY
    assert render_intake_result(result).count("?") == 1
```

- [ ] **Step 2: Run RED (2-5 min)**

Run: `poetry run pytest tests/integration/langflow/test_lf10_request_intake.py::test_reports_all_missing_fields_and_asks_one -q`

Expected: FAIL on missing set, priority, or multiple questions.

- [ ] **Step 3: Bind Agent output to deterministic policy (2-5 min)**

Require extracted candidate facts to pass boundary validation; compute missing/clarification through pure policy before accepting result. A blank/oversized supplied field becomes the current clarification target and is not persisted.

- [ ] **Step 4: Run GREEN and self-review (2-5 min)**

Run focused tests for singleton, three missing fields, and every invalid 0/4001 fact; expect exact full sets and one canonical question. Confirm the Agent does not author free-form question text.

- [ ] **Step 5: Propose commit and wait (2-5 min)**

Propose `feat(langflow): ask deterministic intake clarifications`; wait for developer approval.

### Task 42: LF-10 Multi-Turn Same-Request Completion

**Original task IDs:** 9.5

**Files:**
- Modify through pinned export: `langflow/flows/20-lf-10-request-intake.json`
- Modify: `tests/integration/langflow/test_lf10_request_intake.py`
- Modify: `tests/fixtures/recorded_model/change1_flow_scripts.jsonl`
- Test: focused multi-turn tests

**Interfaces:**
- Consumes: bound RoutingContext, `readDeliveryRequest`, optimistic update/status operations.
- Produces: same request ID across turns, retained valid facts, `needsClarification->complete` using fresh updated timestamps.

- [ ] **Step 1: Write same-ID accumulation test (2-5 min)**

```python
def test_multi_turn_updates_same_request(lf10, graph, conversation):
    first = lf10.run(conversation.turn(FIRST_PARTIAL))
    second = lf10.run(conversation.turn(DESTINATION))
    final = lf10.run(conversation.turn(RECEIVER_AND_CONTENT))
    assert first.request_id == second.request_id == final.request_id
    assert graph.snapshot_for_session(conversation.session_id).status is RequestStatus.COMPLETE
```

- [ ] **Step 2: Run RED (2-5 min)**

Run: `poetry run pytest tests/integration/langflow/test_lf10_request_intake.py::test_multi_turn_updates_same_request -q`

Expected: FAIL because a later turn recreates a request, loses facts, or uses a stale timestamp.

- [ ] **Step 3: Implement resume sequence in the flow (2-5 min per operation)**

For a bound request, call read with authoritative request ID; merge only newly validated facts; update with snapshot `updated_at`; consume returned `updated_at`; recompute completeness; then status-CAS with the newest timestamp. On a conflict, return `CONCURRENT_MODIFICATION` and do not replay.

- [ ] **Step 4: Run GREEN and self-review (2-5 min)**

Run the RED command; expect one request/binding, all accepted facts retained, no repeated requirement, and final complete. Verify the ordered LF-70 calls and graph directly.

- [ ] **Step 5: Propose commit and wait (2-5 min)**

Propose `feat(langflow): resume intake on the same request`; wait for developer approval.

### Task 43: Complete LF-10 API Matrix

**Original task IDs:** 9.6

**Files:**
- Modify: `tests/integration/langflow/test_lf10_request_intake.py`
- Modify: `tests/fixtures/recorded_model/change1_flow_scripts.jsonl`, `tests/support/langflow_client.py`
- Test: `tests/integration/langflow/test_lf10_request_intake.py`

**Interfaces:**
- Consumes: deployed LF-10 boundary and all intake behavior.
- Produces: direct API evidence for complete, partial, invalid fact, several missing, concurrent update, malformed result, and same-request outcomes.

- [ ] **Step 1: Add the named API matrix cases (2-5 min per parameter group)**

```python
CASES = (
    "complete", "partial", "invalid-fact", "several-missing",
    "concurrent-update", "malformed-result", "same-request",
)
```

- [ ] **Step 2: Run RED (2-5 min)**

Run: `poetry run pytest tests/integration/langflow/test_lf10_request_intake.py -q`

Expected: at least one named matrix case FAILS before all boundary/result/graph assertions are present.

- [ ] **Step 3: Complete deterministic fixtures/assertions (2-5 min per case)**

Each recorded script declares exact structured output and logical tool calls. Validate IntakeResult with Pydantic, assert safe chat-independent result, then query Neo4j directly for state/cardinality; malformed failure must not claim success.

- [ ] **Step 4: Run GREEN and self-review (2-5 min)**

Run the RED command; expect all seven named behavior groups PASS. Confirm all data is synthetic and no test relies on developer PostgreSQL/Neo4j/model credentials.

- [ ] **Step 5: Propose commit and wait (2-5 min)**

Propose `test(langflow): cover LF-10 intake API matrix`; wait for developer approval.

### Task 44: LF-00 Stable Router Skeleton

**Original task IDs:** 10.1

**Files:**
- Create from pinned export: `langflow/flows/30-lf-00-main-router.json`
- Modify: `tests/static/test_flow_topology.py`, `tests/static/test_flow_security.py`
- Test: focused LF-00 topology

**Interfaces:**
- Consumes: LF-70 normal-mode and LF-10 Tool Mode stable flows; envelope, routing, renderer components.
- Produces: LF-00 Chat Input, Message-only trusted envelope, mandatory raw-context validation/adaptation, deterministic strict RouterInput assembly, one bounded LF-10 specialist with fixed trust edges, public structured result and deterministic Chat Output.

- [ ] **Step 1: Write predecessor/single-specialist tests (2-5 min)**

```python
def test_lf00_has_mandatory_context_predecessor_and_single_specialist(lf00):
    assert precedes(lf00, "RunFlow-hlb-lf-00-routing-context-v1", "Agent-hlb-lf-00-router-v1")
    assert agent_tools(lf00) == {"RunFlow-hlb-lf-00-request-intake-v1"}

def test_router_model_receives_only_validated_router_input(lf00):
    assert direct_predecessor(lf00, "Agent-hlb-lf-00-router-v1") == "HulubulContractInputBoundary-hlb-lf-00-router-input-v1"
```

- [ ] **Step 2: Run RED (2-5 min)**

Run: `poetry run pytest tests/static/test_flow_topology.py::test_lf00_has_mandatory_context_predecessor_and_single_specialist -q`

Expected: FAIL because LF-00 flow is absent.

- [ ] **Step 3: Build/export semantic topology (2-5 min per node/edge)**

Create Chat Input `Message` -> trusted envelope -> routing-operation builder -> LF-70 normal Run Flow -> strict raw lookup validation/typed adaptation -> deterministic RouterInput assembly -> Router Agent. Wire LF-10 Tool Mode as the only Agent tool and bind the validated envelope/context on fixed advanced inputs excluded from the model-callable schema. Route structured response through RouterResult boundary, then fan validated JSON to public output and renderer -> Chat Output. Use exported handles from pinned runtime only; no public/model/tweak actor or continuity field exists.

- [ ] **Step 4: Add bounded Router prompt (2-5 min)**

```text
Treat RoutingContext as authoritative. Route no binding, new, and needsClarification to LF-10, preserving request ID. Complete or non-null closed is informational with no mutation. Rejected, cancelled, unknown, missing-target, duplicate, or contradictory context returns the exact typed safe failure and does not invoke LF-10. No raw MCP/write tool, LF-20, or coordination. Return only RouterResult.
```

- [ ] **Step 5: Run GREEN and self-review (2-5 min)**

Run strict validate/upgrade plus topology/security tests; expect PASS, Message-only envelope, mandatory context predecessor, strict RouterInput equality, fixed LF-10 trust edges, no MCP, one Agent structured output, one deterministic chat path, and no LF-20.

- [ ] **Step 6: Propose commit and wait (2-5 min)**

Propose `feat(langflow): add authoritative LF-00 router skeleton`; wait for developer approval.

### Task 45: LF-00 Intake Route Matrix

**Original task IDs:** 10.2

**Files:**
- Modify through pinned export: `langflow/flows/30-lf-00-main-router.json`
- Create: `tests/integration/langflow/test_lf00_main_router.py`
- Modify: `tests/fixtures/recorded_model/change1_flow_scripts.jsonl`
- Test: focused intake route matrix

**Interfaces:**
- Consumes: authoritative no-binding/new/needsClarification RoutingContext.
- Produces: LF-10 invocation with no ID for no binding or exact persisted ID for bound intake.

- [ ] **Step 1: Write three-route tests (2-5 min)**

```python
@pytest.mark.parametrize("context", ["no-binding", "new", "needs-clarification"])
def test_intake_route_matrix(context, lf00, graph):
    result = lf00.run(context)
    assert result.target is RouterTarget.INTAKE
    assert result.request_id == graph.authoritative_request_id(context)
```

- [ ] **Step 2: Run RED (2-5 min)**

Run: `poetry run pytest tests/integration/langflow/test_lf00_main_router.py::test_intake_route_matrix -q`

Expected: FAIL because one route is wrong or persisted ID is lost.

- [ ] **Step 3: Bind routing policy to Agent/tool gate (2-5 min)**

Validate RoutingContext before Agent invocation; pure policy authorizes only intake states; supply LF-10 canonical input with authoritative request ID. Chat claims never override context.

- [ ] **Step 4: Run GREEN and self-review (2-5 min)**

Run focused tests including a message claiming `complete` against persisted `needsClarification`; expect all route by Neo4j and preserve ID. Confirm routing lookup precedes specialist.

- [ ] **Step 5: Propose commit and wait (2-5 min)**

Propose `feat(langflow): route active intake from Neo4j state`; wait for developer approval.

### Task 46: LF-00 Informational And Fail-Closed Routes

**Original task IDs:** 10.3

**Files:**
- Modify through pinned export: `langflow/flows/30-lf-00-main-router.json`
- Modify: `tests/integration/langflow/test_lf00_main_router.py`
- Modify: `tests/fixtures/recorded_model/change1_flow_scripts.jsonl`
- Test: focused no-mutation route matrix

**Interfaces:**
- Consumes: complete, all eight recognized post-intake, closed-over-every-status, unknown/null raw, and inconsistent contexts.
- Produces: informational or exact typed failure RouterResult for the exhaustive route matrix; no LF-10 call or graph mutation.

- [ ] **Step 1: Write exact result/no-mutation cases (2-5 min per group)**

```python
@pytest.mark.parametrize("context,error", [
    *[(status.value, ErrorCode.UNSUPPORTED_PHASE1_STATUS) for status in POST_INTAKE_STATUSES],
    ("unknown", ErrorCode.UNSUPPORTED_REQUEST_STATUS),
    ("null-status", ErrorCode.GRAPH_CONTEXT_INCONSISTENT),
    ("duplicate-relationship", ErrorCode.GRAPH_CONTEXT_INCONSISTENT),
    ("duplicate-target", ErrorCode.GRAPH_CONTEXT_INCONSISTENT),
])
def test_no_mutation_route_matrix(context, error, lf00, graph):
    before = graph.fingerprint(context); result = lf00.run(context)
    assert result.error.code is error and graph.fingerprint(context) == before
```

- [ ] **Step 2: Run RED (2-5 min)**

Run: `poetry run pytest tests/integration/langflow/test_lf00_main_router.py::test_no_mutation_route_matrix -q`

Expected: FAIL if exact result differs, LF-10 runs, or graph changes.

- [ ] **Step 3: Wire deterministic no-tool branches (2-5 min per branch)**

Complete returns informational target `none`; closed returns informational target `none` and takes precedence over each of all 11 recognized statuses plus unknown/null raw values. Every one of the eight post-intake statuses uses unsupported Phase 1; unresolved binding uses mismatch; duplicate binding evidence is synthetic in Task 6 while constrained duplicate relationship/target and other contradictions use exact inconsistency; null raw uses inconsistency; unknown raw uses unsupported request status with typed status `None`. All bypass LF-10.

- [ ] **Step 4: Run GREEN and self-review (2-5 min)**

Run focused parameterized tests over all 11 recognized statuses, unknown/null raw, closed precedence over each, missing request, duplicate relationship/target, and contradictory wrappers; expect enum identity, exact messages/codes, and unchanged direct graph fingerprints. Confirm complete does not imply LF-20 or coordination and raw status text appears nowhere in output/evidence.

- [ ] **Step 5: Propose commit and wait (2-5 min)**

Propose `feat(langflow): fail closed on unsupported routing state`; wait for developer approval.

### Task 47: LF-00 Runtime Trace Boundary

**Original task IDs:** 10.4

**Files:**
- Create: `tests/support/trace_metadata_probe.py`
- Create/generated: `tests/fixtures/langflow/trace_topology_v1.json`
- Create: `tests/integration/langflow/test_lf00_traces.py`
- Test: `tests/integration/langflow/test_lf00_traces.py`

**Interfaces:**
- Consumes: safe trace-column query, three deployed flows, synthetic sessions.
- Produces: frozen normalized span topology; evidence context read first, MCP only under LF-70, one Router structured model call.

- [ ] **Step 1: Write safe projection and ordering tests (2-5 min)**

```python
def test_context_lookup_precedes_router(spans):
    assert span_index(spans, "RunFlow-hlb-lf-00-routing-context-v1") < span_index(spans, "Agent-hlb-lf-00-router-v1")
```

- [ ] **Step 2: Run RED (2-5 min)**

Run: `poetry run pytest tests/integration/langflow/test_lf00_traces.py -q`

Expected: FAIL because safe projection/topology fixture is absent.

- [ ] **Step 3: Run the actual-span preflight (2-5 min per invocation)**

Invoke each flow twice with identical synthetic scripts, query only allowed columns, normalize UUIDs to root/parent roles, and compare ordered `(flow_id, parent-presence, name, span_type, span_kind)` tuples. Save only the stable tuple manifest.

- [ ] **Step 4: Apply stop condition (2-5 min)**

Stop if repeated tuples differ, a Run Flow/MCP boundary is absent, an unexpected column is returned, LF-00/LF-10 show MCP tools, or the Router model runs twice. Revise flow wiring/evidence design and rerun; never fetch raw trace payloads to compensate.

- [ ] **Step 5: Run GREEN and self-review (2-5 min)**

Run the RED command; expect context-first, LF-70-only MCP, and single structured model-call assertions PASS. Confirm fixture contains names/types only, no payload.

- [ ] **Step 6: Propose commit and wait (2-5 min)**

Propose `test(langflow): prove LF-00 routing trace boundaries`; wait for developer approval.

### Task 48: Complete LF-00 API Contract

**Original task IDs:** 10.5

**Files:**
- Modify: `tests/integration/langflow/test_lf00_main_router.py`
- Modify: `tests/integration/langflow/test_api_authentication.py`
- Modify: `tests/support/langflow_client.py`
- Test: both integration files

**Interfaces:**
- Consumes: `POST /api/v1/run/{flow_id}` nested request/response, exact API actor request-variable headers, Message/graph session setup.
- Produces: `FlowReply(structured: RouterResult, chat_text, message_id, correlation_id)`; auth, generated metadata, route/safe-failure, structured/chat parity evidence.

- [ ] **Step 1: Add API envelope/parity tests (2-5 min)**

```python
def test_generated_metadata_and_dual_output(client, conversation):
    first = client.run_lf00(conversation, SYNTHETIC_MESSAGE)
    second = client.run_lf00(conversation, SYNTHETIC_REPLY)
    assert first.message_id != second.message_id
    assert first.correlation_id != second.correlation_id
    assert first.chat_text == render_router_result(first.structured)
```

- [ ] **Step 2: Run RED (2-5 min)**

Run: `poetry run pytest tests/integration/langflow/test_lf00_main_router.py tests/integration/langflow/test_api_authentication.py -q`

Expected: FAIL on nested response extraction, metadata uniqueness, auth, safe errors, or output parity.

- [ ] **Step 3: Complete typed API adapter (2-5 min per response branch)**

Send the pinned 1.10.2 run request with chat `input_value`, explicit bare or canonical UUID session, stable output component, API key, required actor request-variable header, and optional display-name header. Do not rely on an empty `tweaks` object for trust or continuity and do not send actor/session/role/assurance/source through tweaks or component ports. Isolate LangFlow's nested `outputs[]` and validate semantic result with Pydantic. Never expose framework dictionaries to BDD.

- [ ] **Step 4: Run GREEN and self-review (2-5 min)**

Run the RED command; expect authenticated execution, exact actor headers, Message/graph session equality, bare/canonical normalization, mismatch/malformed/omitted-flow-fallback rejection, generated IDs, exhaustive route matrix, safe failures, and deterministic chat/structured parity PASS. Confirm user text and tweaks cannot set actor/session/role/assurance/source/correlation.

- [ ] **Step 5: Propose commit and wait (2-5 min)**

Propose `test(langflow): complete LF-00 API contract coverage`; wait for developer approval.

### Task 49: Git/Runtime Flow Lifecycle And Full Runtime Preflight

**Original task IDs:** 7.4

**Files:**
- Modify: `Makefile`, `langflow/README.md`
- Create: `tests/integration/langflow/test_flow_drift.py`
- Create: `tests/integration/langflow/test_langflow_persistence_contract.py`
- Create: `tests/integration/langflow/test_recorded_model_compatibility.py`
- Create: `tests/integration/langflow/test_native_trace_contract.py`
- Create: `tests/support/{postgres_probe,stack_controller}.py`
- Create: `tests/support/recorded_model/{app,contracts,controller}.py`
- Create: `infra/test/recorded-model.Dockerfile`
- Modify: `infra/docker-compose.test.yaml`
- Test: `tests/integration/langflow/test_flow_drift.py`, `tests/integration/langflow/test_langflow_persistence_contract.py`, `tests/integration/langflow/test_recorded_model_compatibility.py`, `tests/integration/langflow/test_native_trace_contract.py`

**Interfaces:**
- Consumes: all three normalized flows, manifest, auth, safe probes, pinned runtime.
- Produces: ordered push/pull/status/drift targets; deterministic model double/controller; migrated persistence/trace schema evidence; clean deployed runtime gate.

- [ ] **Step 1: Write drift and preflight tests (2-5 min per file)**

```python
def test_clean_instance_contains_only_manifest_flows(deployed_flows, manifest):
    assert deployed_flows.ids == manifest.flow_ids
    assert deployed_flows.remote_only == frozenset()
```

- [ ] **Step 2: Run RED (2-5 min)**

Run: `poetry run pytest tests/integration/langflow/test_flow_drift.py tests/integration/langflow/test_langflow_persistence_contract.py tests/integration/langflow/test_recorded_model_compatibility.py tests/integration/langflow/test_native_trace_contract.py -q`

Expected: FAIL because ordered lifecycle, model seam, and migrated safe-column evidence are incomplete.

- [ ] **Step 3: Implement safe lifecycle targets (2-5 min per target)**

Validate -> normalize check -> secret scan -> strict validate/upgrade -> push LF-70/LF-10/LF-00 with `--no-normalize --keep-secrets`; `--keep-secrets` preserves only prevalidated environment names. Add pull/export/status commands from `langflow/`. Drift fails on local/remote content difference, missing/duplicate ID, remote-only flow, or untracked file.

- [ ] **Step 4: Implement deterministic model/persistence probes (2-5 min per module)**

Recorded server supports plain, tool-call, native JSON-schema structured responses, ordered multi-call, transient/malformed responses, script exhaustion, and two-participant barrier. PostgreSQL probe uses the exact safe `message` projection; trace probe uses the exact safe join. No server/probe logs body/header/content.

- [ ] **Step 5: Run mandatory full-runtime preflight (2-5 min per command)**

```bash
make acceptance-up
make acceptance-ready
make acceptance-deploy
poetry run pytest tests/integration/langflow/test_langflow_persistence_contract.py tests/integration/langflow/test_recorded_model_compatibility.py tests/integration/langflow/test_native_trace_contract.py -q
poetry run pytest tests/integration/langflow/test_flow_drift.py -q
make acceptance-down
```

Expected: approved digests and LangFlow/LFX versions; migrated safe columns; authenticated session-scoped message API; plain/tool/structured/multi-call/barrier support; SDK no hidden retry; stable actual span names; distinct correlation IDs; exactly three clean remote flows.

- [ ] **Step 6: Apply stop condition and self-review (2-5 min)**

Stop before Task 50 if a digest/package differs; safe columns differ; repeated span projection differs; boundary is absent; recorded response shape fails; script exhaustion falls through; SDK retries; or concurrent requests lack distinct correlation IDs. Always tear down. Confirm no ignored environment or raw trace was read/uploaded.

- [ ] **Step 7: Propose commit and wait (2-5 min)**

Propose `feat(langflow): add Git-authoritative deployed flow lifecycle`; wait for developer approval.

### Task 50: Delivery Intake BDD Bindings

**Original task IDs:** 11.1

**Files:**
- Keep unchanged: `tests/features/delivery_request_intake.feature`
- Create: `tests/steps/conftest.py`
- Create: `tests/steps/test_delivery_request_intake.py`
- Test: `tests/steps/test_delivery_request_intake.py`

**Interfaces:**
- Consumes: AcceptanceStack, trusted Conversation, LF-00 client, GraphProbe.
- Produces: `IntakeWorld.send(message: str) -> FlowReply`, graph/state assertion methods, all 18 intake examples bound.

- [ ] **Step 1: Bind feature and representative business steps (2-5 min per phrase group)**

```python
scenarios("../features/delivery_request_intake.feature")
@when(parsers.parse("the Sender's first message is \"{message}\""), target_fixture="flow_reply")
def sender_first_message(intake_world, message):
    return intake_world.send(message)
```

- [ ] **Step 2: Run RED (2-5 min)**

Run: `poetry run pytest tests/steps/test_delivery_request_intake.py -q`

Expected: 18 examples collect and fail on undefined steps/world behavior; no import-time developer-stack connection.

- [ ] **Step 3: Implement typed world assertions (2-5 min per step family)**

Normalize feature phrases such as `not supplied`, `Complete`, and comma-separated missing facts into production enums; delegate technical calls to world methods; assert graph cardinality/domain values directly.

- [ ] **Step 4: Run GREEN and self-review (2-5 min)**

Run the RED command; expect `18 passed`. Confirm feature file has no diff and steps contain no user-visible technical ID requirement.

- [ ] **Step 5: Propose commit and wait (2-5 min)**

Propose `test(bdd): bind delivery request intake scenarios`; wait for developer approval.

### Task 51: Conversation Resumption BDD Bindings

**Original task IDs:** 11.2

**Files:**
- Keep unchanged: `tests/features/conversation_resumption.feature`
- Modify: `tests/steps/conftest.py`
- Create: `tests/steps/test_conversation_resumption.py`
- Test: `tests/steps/test_conversation_resumption.py`

**Interfaces:**
- Consumes: same IntakeWorld; model barrier; LangFlow-only restart controller.
- Produces: all 16 resumption examples bound; natural answers use hidden established conversation.

- [ ] **Step 1: Bind natural reply/restart/concurrency steps (2-5 min per phrase group)**

```python
@when("the intake service is restarted while its recorded conversation and request state are retained")
def retained_state_restart(intake_world):
    intake_world.restart_langflow_only()
```

- [ ] **Step 2: Run RED (2-5 min)**

Run: `poetry run pytest tests/steps/test_conversation_resumption.py -q`

Expected: 16 examples collect and fail on continuity/restart/race assertions.

- [ ] **Step 3: Complete semantic world operations (2-5 min per family)**

Natural answers call `send(answer)` on the existing conversation; races arm a two-participant model barrier and use two executor tasks; restart calls only StackController's LangFlow restart. Assertions compare request identity/cardinality and exact safe conflict outcome.

- [ ] **Step 4: Run GREEN and self-review (2-5 min)**

Run the RED command; expect `16 passed`. Confirm no feature diff and no step parses/injects request/session/correlation IDs from user answers.

- [ ] **Step 5: Propose commit and wait (2-5 min)**

Propose `test(bdd): bind conversation resumption scenarios`; wait for developer approval.

### Task 52: Full-Stack Intake Paths

**Original task IDs:** 11.3

**Files:**
- Create: `tests/system/test_request_intake.py`
- Modify: `tests/integration/conftest.py`, `tests/support/recorded_model/controller.py`, `tests/support/graph_probe.py`
- Test: `tests/system/test_request_intake.py`

**Interfaces:**
- Consumes: disposable full stack, LF-00, GraphProbe.
- Produces: four system tests for one-message, multi-turn, partial, and structured/chat consistency.

- [ ] **Step 1: Add four named system tests (2-5 min each)**

```python
def test_multi_turn_intake_accumulates_facts_on_same_request(stack, conversation):
    first = stack.langflow.run_lf00(conversation, FIRST_PARTIAL_MESSAGE)
    final = stack.langflow.run_lf00(conversation, FINAL_DETAILS_MESSAGE)
    graph = stack.graph.snapshot_for_session(conversation.session_id)
    assert final.structured.request_id == first.structured.request_id == graph.request_id
```

- [ ] **Step 2: Run RED (2-5 min)**

Run: `poetry run pytest tests/system/test_request_intake.py -q`

Expected: focused graph/result mismatch against disposable deployed flows; never fallback to developer stack.

- [ ] **Step 3: Complete fixtures/scripts (2-5 min per scenario)**

Prime exact recorded responses, invoke LF-00, and assert request/binding/subgraph/status cardinality directly. Structured/chat test compares deterministic renderer output.

- [ ] **Step 4: Run GREEN and self-review (2-5 min)**

Run the RED command; expect `4 passed`. Confirm each significant write has independent Neo4j evidence.

- [ ] **Step 5: Propose commit and wait (2-5 min)**

Propose `test(system): cover complete and multi-turn intake`; wait for developer approval.

### Task 53: Deterministic Concurrency Acceptance

**Original task IDs:** 11.4

**Files:**
- Create: `tests/system/test_request_intake_concurrency.py`
- Modify: `tests/support/recorded_model/controller.py`, `tests/fixtures/recorded_model/change1_flow_scripts.jsonl`
- Test: `tests/system/test_request_intake_concurrency.py`

**Interfaces:**
- Consumes: two-participant barrier, same-session/snapshot calls, direct graph probe.
- Produces: one first-message winner, no orphan; one clarification winner, exact loser conflict.

- [ ] **Step 1: Add four named race tests (2-5 min each)**

```python
def test_concurrent_first_messages_commit_one_request_and_one_binding(stack, conversation):
    stack.model.arm_barrier(barrier_id="after-no-binding-read", participants=2)
    run_two_first_messages(stack, conversation)
    assert stack.graph.request_count_for_session(conversation.session_id) == 1
```

- [ ] **Step 2: Run RED (2-5 min)**

Run: `poetry run pytest tests/system/test_request_intake_concurrency.py -q`

Expected: duplicate/orphan/lost-update/incorrect-loser failure.

- [ ] **Step 3: Synchronize exact race points (2-5 min per barrier)**

First-message barrier releases only after both no-binding reads; clarification barrier releases only after both use the same request snapshot. No sleeps are used for race ordering.

- [ ] **Step 4: Run GREEN and self-review (2-5 min)**

Run the RED command; expect `4 passed`, one request/binding, no orphan, winner retained, loser `CONCURRENT_MODIFICATION`. Confirm barriers record metadata only.

- [ ] **Step 5: Propose commit and wait (2-5 min)**

Propose `test(system): prove intake concurrency safety`; wait for developer approval.

### Task 54: Retained-State Restart Acceptance

**Original task IDs:** 11.5

**Files:**
- Create: `tests/system/test_request_intake_restart.py`
- Modify: `tests/support/{postgres_probe,stack_controller}.py`
- Test: `tests/system/test_request_intake_restart.py`

**Interfaces:**
- Consumes: LangFlow-only restart, safe PostgreSQL metadata, graph/stack fingerprints.
- Produces: retained messages, same request update, no new binding/request, only LangFlow container identity changes.

- [ ] **Step 1: Add four named restart tests (2-5 min each)**

```python
def test_restart_changes_only_langflow_container_identity(stack):
    before = stack.controller.fingerprint()
    stack.controller.restart_langflow_only(); stack.controller.wait_for_langflow_ready()
    after = stack.controller.fingerprint()
    assert before.postgres == after.postgres and before.neo4j == after.neo4j
    assert before.langflow.container_id != after.langflow.container_id
```

- [ ] **Step 2: Run RED (2-5 min)**

Run: `poetry run pytest tests/system/test_request_intake_restart.py -q`

Expected: FAIL if wrong service restarts, history disappears, or request is recreated.

- [ ] **Step 3: Implement exact retained-state sequence (2-5 min per action)**

Create clarification draft; capture request/graph/message/stack metadata; restart LangFlow only; await authenticated readiness; compare retained stores/messages; send natural same-session answer; assert same request and unchanged request/binding cardinality.

- [ ] **Step 4: Run GREEN and self-review (2-5 min)**

Run the RED command; expect `4 passed`. Confirm PostgreSQL query never selects message text and standalone LFX is not used as evidence.

- [ ] **Step 5: Propose commit and wait (2-5 min)**

Propose `test(system): verify retained-state LangFlow restart`; wait for developer approval.

### Task 55: Negative Full-Stack Matrix

**Original task IDs:** 11.6

**Files:**
- Create: `tests/system/test_request_intake_failures.py`
- Modify: `tests/fixtures/recorded_model/change1_flow_scripts.jsonl`, `tests/support/recorded_model/controller.py`, `tests/support/graph_probe.py`
- Test: `tests/system/test_request_intake_failures.py`

**Interfaces:**
- Consumes: context fixtures, model/read/write failure scripts, graph fingerprints.
- Produces: exhaustive negative groups covering all eight unsupported statuses, closed precedence, unknown/null/inconsistent contexts, stale state, model authentication, MCP operation failure, malformed output, read retry exhaustion, and ambiguous writes with exact typed/no-mutation/no-replay outcomes.

- [ ] **Step 1: Add named failure inventory (2-5 min per parameter group)**

```python
NEGATIVE_CASES = (
    "complete-noop", "closed-precedence", "all-eight-post-intake-statuses",
    "missing-request", "duplicate-relationship", "duplicate-target", "null-status",
    "unknown-status", "stale-update", "model-authentication", "mcp-operation-failure",
    "malformed-after-repair", "read-retry-exhausted", "ambiguous-write-no-replay",
)
```

- [ ] **Step 2: Run RED (2-5 min)**

Run: `poetry run pytest tests/system/test_request_intake_failures.py -q`

Expected: one or more exact error/fingerprint/attempt-count assertions FAIL.

- [ ] **Step 3: Complete deterministic injection/assertions (2-5 min per group)**

Parameterize all eight post-intake statuses and closed precedence over all 11 recognized plus unknown/null raw values. Capture graph fingerprint before/after every no-mutation case; model authentication yields non-retryable `MODEL_AUTHENTICATION_FAILURE`; a non-transient non-authentication MCP failure yields non-retryable `MCP_OPERATION_FAILURE`; read exhaustion requires two attempts and no mutating specialist; ambiguous write requires one dispatch, no affected count, exact error, no replay; malformed second result becomes controlled failure.

- [ ] **Step 4: Run GREEN and self-review (2-5 min)**

Run the RED command; expect every parameterized status/failure ID PASS and prohibited graph fingerprints unchanged. Confirm model-authentication/MCP-operation cases make one attempt, no wall-clock sleep exists in unit policy, and the full-stack read-exhaustion trace reports exactly two attempts.

- [ ] **Step 5: Propose commit and wait (2-5 min)**

Propose `test(system): cover intake failure and no-replay paths`; wait for developer approval.

### Task 56: Versioned 20-Case Evaluation Dataset

**Original task IDs:** 12.1

**Files:**
- Create: `tests/evaluation/datasets/change1_intake_v1.yaml`
- Create: `tests/evaluation/fixtures/change1_recorded_model_v1.jsonl`
- Create: `tests/evaluation/contracts.py`, `tests/evaluation/conftest.py`
- Create: `tests/evaluation/test_dataset_contract.py`
- Test: `tests/evaluation/test_dataset_contract.py`

**Interfaces:**
- Consumes: production enums, exact C01-C20 inventory.
- Produces: strict `EvaluationDataset`, `EvaluationCase`, turns/expected mutation contracts; one unique recorded response key per turn.

- [ ] **Step 1: Write corpus contract tests (2-5 min each)**

```python
def test_dataset_contains_exactly_twenty_unique_cases(dataset):
    assert len(dataset.cases) == 20
    assert len({case.case_id for case in dataset.cases}) == 20
```

- [ ] **Step 2: Run RED (2-5 min)**

Run: `poetry run pytest tests/evaluation/test_dataset_contract.py -q`

Expected: FAIL because dataset/contracts are absent.

- [ ] **Step 3: Author exact synthetic inventory (2-5 min per case group)**

Encode C01-C20 from [Locked Shared Interfaces](#locked-shared-interfaces). C14 and C15 are the corpus's representative unsupported post-intake states; do not claim this dataset replaces the exhaustive all-status route matrices in Tasks 6, 33, 45, 46, 48, and 55. Each expected block contains route, normalized facts, exact missing tuple, clarification, ordered logical operations, final status/unchanged, error/null, request/binding deltas, extras, prohibited count. Messages contain no trusted IDs.

- [ ] **Step 4: Run GREEN and self-review (2-5 min)**

Run the RED command; expect five contract tests PASS and exactly 20 cases. Confirm all symbols resolve to enums, all safety cases forbid extra cardinality, response keys are total/unique, and content is synthetic.

- [ ] **Step 5: Propose commit and wait (2-5 min)**

Propose `test(evaluation): add versioned Change 1 corpus`; wait for developer approval.

### Task 57: Recorded-Model Hard Evaluator

**Original task IDs:** 12.2

**Files:**
- Create: `tests/evaluation/metrics.py`, `tests/evaluation/evidence.py`
- Create: `tests/evaluation/test_recorded_intake_evaluation.py`
- Modify: `Makefile`
- Test: `tests/evaluation/test_recorded_intake_evaluation.py`

**Interfaces:**
- Consumes: dataset, recorded model, disposable stack, graph probe.
- Produces: `EvaluationRun` exact decisions/typed results/field counts/safety mutations; sanitized hash-addressed report.

- [ ] **Step 1: Write exact hard threshold test (2-5 min)**

```python
assert run.case_count == run.exact_decisions == run.typed_results == 20
assert run.prohibited_operations == run.extra_requests == run.extra_bindings == 0
```

- [ ] **Step 2: Run RED (2-5 min)**

Run: `poetry run pytest tests/evaluation/test_recorded_intake_evaluation.py -q`

Expected: FAIL because evaluator/metrics are absent or a case differs.

- [ ] **Step 3: Implement composite exactness and safe report (2-5 min per metric)**

Exact decision is one equality over route, facts, missing, clarification, ordered operations, status, error, and mutation. Failure reports case ID and symbolic field only. Evidence records hashes/aggregates, not messages/model bodies.

- [ ] **Step 4: Run GREEN and self-review (2-5 min)**

Run the RED command; expect 20/20 exact, 20/20 typed, zero prohibited/extra cardinality. Confirm `make test-evaluation-recorded` runs dataset plus evaluator and is a hard gate.

- [ ] **Step 5: Propose commit and wait (2-5 min)**

Propose `test(evaluation): enforce deterministic intake decisions`; wait for developer approval.

### Task 58: Soft NEAR/DeepSeek Evaluation

**Original task IDs:** 12.3

**Files:**
- Create: `tests/evaluation/test_live_intake_evaluation.py`
- Modify: `tests/evaluation/conftest.py`, `metrics.py`, `evidence.py`, `Makefile`
- Test: `tests/evaluation/test_live_intake_evaluation.py`

**Interfaces:**
- Consumes: explicit `--run-live-evaluation`, approved variable names, baseline model.
- Produces: dated sanitized model/settings/dataset/schema/flow hash evidence and four soft metrics.

- [ ] **Step 1: Write opt-in/threshold tests with fake aggregates (2-5 min)**

```python
def test_live_thresholds():
    assert LiveThresholds(exact=18, typed=20, micro_f1=0.95, safety_mutations=0).passes
```

- [ ] **Step 2: Run RED (2-5 min)**

Run: `poetry run pytest tests/evaluation/test_live_intake_evaluation.py -q`

Expected: FAIL because `LiveThresholds` and the live evaluator option/fixture are not defined.

- [ ] **Step 3: Implement explicit live path (2-5 min per output field)**

Use configurable provider/base/key names, model `global/nearai/deepseek-v4-flash`, temperature 0; write only date, provider/model/non-secret settings, hashes, exact/typed/F1/safety aggregates. Threshold misses make this manual command red but never a required CI check.

- [ ] **Step 4: Run deterministic GREEN and self-review (2-5 min)**

Run: `poetry run pytest tests/evaluation/test_live_intake_evaluation.py -q`

Expected: threshold/contract tests PASS and provider execution SKIPS naming missing variable names/flag only. Do not invoke a live provider during ordinary implementation verification.

- [ ] **Step 5: Propose commit and wait (2-5 min)**

Propose `test(evaluation): add soft live intake baseline`; wait for developer approval.

### Task 59: Five-Run Clarification Judge

**Original task IDs:** 12.4

**Files:**
- Create: `tests/evaluation/test_clarification_judge.py`
- Modify: `tests/evaluation/contracts.py`, `evidence.py`, `conftest.py`, `Makefile`
- Test: `tests/evaluation/test_clarification_judge.py`

**Interfaces:**
- Consumes: explicit live opt-in; five rubric criteria.
- Produces: `JudgeResult` with five 0-2 scores/reasons, code-derived total/pass; exactly five-run median/no-zero decision.

- [ ] **Step 1: Write bounded/code-derived tests (2-5 min)**

```python
def test_five_run_rule():
    runs = judge_runs([8, 8, 9, 9, 10], no_zero=True)
    assert len(runs) == 5 and judge_calibration_passes(runs)
```

- [ ] **Step 2: Run RED (2-5 min)**

Run: `poetry run pytest tests/evaluation/test_clarification_judge.py -q`

Expected: FAIL because `JudgeResult` and `judge_calibration_passes` are not defined.

- [ ] **Step 3: Implement exact rubric/calibration (2-5 min per function)**

Criteria are genuinely missing info, unambiguous, concise, no invention, nontechnical suitability; each 0-2. Run exactly five times; pass iff median total >=8 and every criterion in every run >0. Ignore model-supplied pass/total and derive in code.

- [ ] **Step 4: Run deterministic GREEN and self-review (2-5 min)**

Run: `poetry run pytest tests/evaluation/test_clarification_judge.py -q`

Expected: bounded and five-run contract tests PASS; provider execution SKIPS without opt-in. Confirm evidence contains scores/reasons/aggregates only and workflow remains soft.

- [ ] **Step 5: Propose commit and wait (2-5 min)**

Propose `test(evaluation): calibrate soft clarification judge`; wait for developer approval.

### Task 60: Safe Observability Assertions

**Original task IDs:** 12.5

**Files:**
- Create: `tests/integration/langflow/test_safe_observability.py`
- Modify: `tests/support/trace_metadata_probe.py`, `tests/support/recorded_model/controller.py`, `tests/integration/conftest.py`
- Modify: `src/hulubul/request_intake/entrypoints/langflow/components/hulubul/execution_envelope.py`, `contract_boundary.py`, `data_operation_boundary.py`, `retry_decision.py`
- Test: `tests/integration/langflow/test_safe_observability.py`

**Interfaces:**
- Consumes: safe trace projection, allowlisted structured component logs, synthetic fixture guard.
- Produces: required ID propagation, LF-70-only MCP, exhaustive ErrorCode/FailureKind policy evidence, retry/no-replay spans, prohibited-key/canary rejection, raw-trace upload prohibition, and exact Phase 1 escalation values without a pager.

- [ ] **Step 1: Add eight named observability tests (2-5 min per group)**

```python
def test_projected_trace_omits_prohibited_keys_and_canaries(observation):
    assert set(observation) <= OBSERVABILITY_ALLOWLIST
    assert SYNTHETIC_CANARIES.isdisjoint(serialized_values(observation))

@pytest.mark.parametrize("code", tuple(ErrorCode))
def test_every_error_uses_canonical_observability_policy(code):
    assert observed_policy(code) == ERROR_POLICY[code]
```

- [ ] **Step 2: Run RED (2-5 min)**

Run: `poetry run pytest tests/integration/langflow/test_safe_observability.py -q`

Expected: FAIL on missing IDs/tool boundary/retry metadata or prohibited key category, without printing its value.

- [ ] **Step 3: Enforce synthetic-only fixture and projections (2-5 min per guard)**

Reject non-simulated actor, non-fixture actor/session ID, or message outside versioned synthetic corpus. Query safe columns only. Join structured logs to trace topology by session/flow/component/test run. Build output from the nine-key allowlist in memory. Parameterize every ErrorCode row and every FailureKind trigger row, asserting exact category, retryability, safe message, log level, present/absent allowlisted fields, response/fallback, and escalation (`none`, `hard-gate failure`, or `manual ambiguous-write graph inspection`).

- [ ] **Step 4: Assert retry/tool boundaries (2-5 min)**

Require attempts 1/2 for eligible read, one write span maximum after dispatch, and MCP tool span names only under LF-70. Raw trace API paths and payload columns must not appear in report uploader inputs.

- [ ] **Step 5: Run GREEN and self-review (2-5 min)**

Run the RED command; expect all ErrorCode/FailureKind, metadata/boundary/privacy tests PASS. Confirm both newly required dependency codes are present, escalation has no pager/on-call action, failure output exposes case/span/key category only, and no native trace payload file exists.

- [ ] **Step 6: Propose commit and wait (2-5 min)**

Propose `test(observability): enforce synthetic safe trace evidence`; wait for developer approval.

### Task 61: Hard Static CI Gates

**Original task IDs:** 13.1

**Files:**
- Create: `.github/workflows/ci.yaml`
- Create: `tests/static/test_ci_workflows.py`
- Modify: `Makefile`, `tox.ini`, `.gitignore`
- Test: `tests/static/test_ci_workflows.py`

**Interfaces:**
- Consumes: all hard non-Docker targets and reports.
- Produces: `static-quality` job invoking only `make install` and `make ci-static`; sanitized 30-day reports.

- [ ] **Step 1: Write workflow/Make-only tests (2-5 min)**

```python
def test_hard_ci_calls_make_targets_only(workflow):
    assert workflow.project_commands("static-quality") == ("make install", "make ci-static")
```

- [ ] **Step 2: Run RED (2-5 min)**

Run: `poetry run pytest tests/static/test_ci_workflows.py::test_hard_ci_calls_make_targets_only -q`

Expected: FAIL because workflow is absent.

- [ ] **Step 3: Implement `ci-static` and workflow (2-5 min per target/job)**

`ci-static` runs unchanged `lint`, stable LinkML drift excluding OWL/SHACL byte order, operational schema drift, secret scan, Ruff, formatting, mypy, import-linter, flow checks, unit/component/contract/static tests with branch coverage >=80, and recorded 20-case evaluation. Workflow uses checkout/setup-python/pipx Poetry then Make only.

- [ ] **Step 4: Run GREEN and self-review (2-5 min)**

Run: `poetry run pytest tests/static/test_ci_workflows.py -q && make ci-static`

Expected: workflow tests and all current hard static gates PASS. Confirm artifact paths contain only coverage/JUnit/sanitized reports and retention is 30 days.

- [ ] **Step 5: Propose commit and wait (2-5 min)**

Propose `ci: enforce deterministic Phase 1 gates`; wait for developer approval.

### Task 62: Isolated Full-Stack CI Gates

**Original task IDs:** 13.2

**Files:**
- Modify: `.github/workflows/ci.yaml`
- Modify: `tests/static/test_ci_workflows.py`, `Makefile`
- Test: CI workflow tests and acceptance targets

**Interfaces:**
- Consumes: static-quality job, disposable compose, three-flow deploy, integration/system/BDD/evidence.
- Produces: `full-stack-acceptance` hard job with 45-minute timeout, diagnostics, teardown, 30-day sanitized evidence.

- [ ] **Step 1: Write acceptance sequence tests (2-5 min)**

```python
assert workflow.project_commands("full-stack-acceptance") == (
    "make install", "make acceptance-up", "make acceptance-ready",
    "make acceptance-deploy", "make ci-acceptance",
)
```

- [ ] **Step 2: Run RED (2-5 min)**

Run: `poetry run pytest tests/static/test_ci_workflows.py::test_acceptance_ci_uses_disposable_make_sequence -q`

Expected: FAIL because full-stack job is absent.

- [ ] **Step 3: Add hard job and cleanup (2-5 min per step)**

Job needs static quality, starts empty volumes, runs ordered readiness/deploy/`ci-acceptance`, writes sanitized diagnostics on failure, uploads `reports/change1/` for 30 days, and always runs `make acceptance-down`. `ci-acceptance` runs integration, system, all 34 BDD examples, safe observability, and release evidence.

- [ ] **Step 4: Run GREEN and self-review (2-5 min)**

Run workflow tests, then the full local Make sequence from Task 65; expect hard gates PASS and teardown removes only unique disposable volumes. Confirm no developer volume/runtime catalogue dependency.

- [ ] **Step 5: Propose commit and wait (2-5 min)**

Propose `ci: add isolated Phase 1 acceptance gate`; wait for developer approval.

### Task 63: Non-Blocking Live Evaluation Workflow

**Original task IDs:** 13.3

**Files:**
- Create: `.github/workflows/live-evaluation.yaml`
- Modify: `tests/static/test_ci_workflows.py`
- Test: live workflow static tests

**Interfaces:**
- Consumes: live/judge Make targets and approved secret names.
- Produces: manual-only, non-blocking live evidence retained 30 days.

- [ ] **Step 1: Write trigger/soft/secret/path tests (2-5 min)**

```python
def test_live_evaluation_has_manual_trigger_only(workflow):
    assert set(workflow.triggers) == {"workflow_dispatch"}
    assert workflow.required_check is False
```

- [ ] **Step 2: Run RED (2-5 min)**

Run: `poetry run pytest tests/static/test_ci_workflows.py -k live_evaluation -q`

Expected: FAIL because workflow is absent.

- [ ] **Step 3: Add exact soft workflow (2-5 min per section)**

Use only `HULUBUL_LLM_API_KEY` and optional separately approved `HULUBUL_JUDGE_API_KEY`; invoke `make test-evaluation-live` and `make test-evaluation-judge`; evaluator steps use `continue-on-error: true`; upload only `reports/change1/evaluation/` for 30 days; report thresholds/artifact name only.

- [ ] **Step 4: Run GREEN and self-review (2-5 min)**

Run the RED command; expect manual-only, non-blocking, approved-name, sanitized-path tests PASS. Confirm no push/pull_request/workflow_run trigger.

- [ ] **Step 5: Propose commit and wait (2-5 min)**

Propose `ci: add non-blocking live evaluation workflow`; wait for developer approval.

### Task 64: Setup, Flow, Operations, And Cut-Line Documentation

**Original task IDs:** 13.4

**Files:**
- Modify: `README.md`, `infra/README.md`, `langflow/README.md`, `architecture/verification-testing-and-evaluation-strategy.md`
- Create: `docs/phase-1-request-intake-runbook.md`
- Create: `tests/static/test_documentation.py`
- Test: `tests/static/test_documentation.py`

**Interfaces:**
- Consumes: executable Make targets, manifest, rollback/ambiguity policy.
- Produces: canonical safe setup, flow loop, clean acceptance, troubleshooting, rollback, exact Change 1/Change 2 cut line.

- [ ] **Step 1: Write documentation contract tests (2-5 min)**

```python
def test_phase1_docs_reference_exactly_three_flows(docs):
    assert docs.declared_change1_flows == {"LF-70", "LF-10", "LF-00"}
    assert "LF-20" in docs.deferred_only
```

- [ ] **Step 2: Run RED (2-5 min)**

Run: `poetry run pytest tests/static/test_documentation.py -q`

Expected: FAIL on missing commands, exact cut line, soft gate, or secret-safe guidance.

- [ ] **Step 3: Update content ownership (2-5 min per document section)**

README: prerequisites/commands/three-flow scope/runbook/cut line. Infra: safe files, exact API actor headers, ignored Playground actor environment names, local ports, readiness, clean acceptance, restart, diagnostics, rotation without display. LangFlow: IDs/order/pull-normalize-validate-push-status/drift/troubleshooting and Message/session normalization. Architecture strategy: exact three-flow Change 1, 20-case hard/soft split, 34 examples, later-phase separation. Runbook: setup, gates, stage failures, exhaustive safe error/escalation policy without a production pager, evidence, rollback, ambiguous-write independent inspection, and Change 2 dependency.

- [ ] **Step 4: Run GREEN and manual review (2-5 min)**

Run the RED command; expect all docs tests PASS. Verify every documented command exists with `make help`; scan for credential-bearing URLs/values and commands that print environment files; expect none.

- [ ] **Step 5: Propose commit and wait (2-5 min)**

Propose `docs: add Phase 1 intake operations guidance`; wait for developer approval.

### Task 65: Evidence Manifest And Complete Clean Gate

**Original task IDs:** 13.5

**Files:**
- Create: `tests/contract/evidence/change1.yaml`
- Create: `tests/contract/test_change1_evidence_manifest.py`
- Create: `scripts/build_change1_evidence.py`
- Create: `tests/unit/scripts/test_build_change1_evidence.py`
- Modify: `Makefile`, `.gitignore`
- Generated/ignored: `reports/change1/release-evidence.json`
- Test: both evidence test files plus complete gate

**Interfaces:**
- Consumes: five specs, two feature files, collected pytest nodes/JUnit, versions, manifests, images.
- Produces: one-to-many semantic evidence map with qualified source keys; distinct pre-implementation traceability and collected execution evidence; `build_release_evidence(output: Path) -> None`; `build_diagnostics(output: Path) -> None`; CLI modes `--output <path>` and `--diagnostics-only --output <path>`; allowlisted release evidence JSON with all hard gate outcomes.

- [ ] **Step 1: Write manifest/builder rejection tests (2-5 min per group)**

```python
def test_evidence_rejects_prohibited_keys_recursively():
    for key in ("secret", "prompt", "message", "query"):
        with pytest.raises(EvidenceError):
            validate_evidence({key: "synthetic-canary"})

def test_source_keys_are_qualified_and_collision_proof(evidence_map):
    assert all(key.startswith(("spec:", "feature:")) for key in evidence_map)
    assert not any(key.startswith("TC-") for key in evidence_map)
```

- [ ] **Step 2: Run RED (2-5 min)**

Run: `poetry run pytest tests/contract/test_change1_evidence_manifest.py tests/unit/scripts/test_build_change1_evidence.py -q`

Expected: FAIL because mappings/builder are absent.

- [ ] **Step 3: Implement source-heading and node validation (2-5 min per parser)**

Parse all `### Requirement:` and `#### Scenario:` headings in five specs and both Gherkin files with expanded example ordinals. Require exactly 38 requirements, 95 named capability scenarios, 18 intake examples, and 16 resumption examples. Keys are exactly `spec:<capability>/<requirement>/<scenario>` and `feature:<feature-file>/<scenario>/<example-ordinal>` with one-based source-order ordinals; reject unqualified headings, generic TC IDs, missing/unknown/duplicate mappings, and capability/Gherkin key collisions. The committed pre-implementation map establishes intended node IDs without claiming collection or pass; the release builder separately consumes pytest collection/JUnit to prove execution.

- [ ] **Step 4: Implement allowlisted evidence builder (2-5 min per section)**

Emit change, git SHA, UTC time, Python/LangFlow/LFX/schema versions, dataset/schema-manifest/flow-manifest/three-flow hashes, exact three image references, and unit/recorded/integration/system/BDD hard outcomes. If live metrics exist, mark them soft. Recursively reject prohibited keys; do not call/save full `docker compose config`.

- [ ] **Step 5: Run focused GREEN (2-5 min)**

Run the RED command; expect all 95 capability scenario keys and all 34 feature-example keys assigned with no collisions, pre-implementation traceability validated, referenced nodes separately collected, three flow hashes/image pins present, and prohibited evidence rejected.

- [ ] **Step 6: Run complete clean-environment gate (2-5 min per command invocation)**

```bash
make install
make ci-static
make acceptance-up
make acceptance-ready
make acceptance-deploy
make ci-acceptance
make release-evidence
make acceptance-down
git status --short
```

Expected: every hard command exits 0; branch coverage >=80%; recorded evaluation 20/20 exact/typed and safe; 34/34 BDD (18 intake, 16 resumption); all 95 capability scenarios and 34 qualified feature examples have collected passing evidence; engineering mechanics map to pytest-only evidence; exactly three flow hashes and pinned images; no stable generated drift; teardown succeeds; status lists only intended implementation artifacts, not reports/env/runtime state.

- [ ] **Step 7: Self-review and propose commit (2-5 min)**

Inspect release evidence keys/hashes and current worktree diff. Propose `chore(release): add Phase 1 evidence gate`; present fresh complete output and wait for explicit developer approval. Do not commit automatically.

---

## Capability Spec Coverage

| Capability / exact requirement heading | Primary plan tasks |
| --- | --- |
| Delivery intake / Phase 1 Intake Profile | 5, 7, 10, 39-42, 50, 52, 56-57 |
| Delivery intake / Immediate Fact Validation | 5, 7, 10, 40-43, 50, 55 |
| Delivery intake / Truthful Sparse Draft Creation | 12, 34, 40, 50, 52 |
| Delivery intake / Complete Intake In One Message | 34, 36, 39, 45, 50, 52 |
| Delivery intake / Focused Clarification | 10, 15, 41, 50, 56-57 |
| Delivery intake / Incremental Completion Of The Same Request | 42, 51-52 |
| Delivery intake / Domain Graph Mapping | 12, 34, 39, 50, 52 |
| Delivery intake / Intake Status Transitions | 11, 36, 39-42, 55 |
| Delivery intake / Free-Text Place Boundary | 5, 12, 34-35, 40-43, 50 |
| Contracts / Versioned Strict Operational Contracts | 5-8, 17-20 |
| Contracts / Internally Managed Execution Metadata | 5, 16, 44, 48, 50-51 |
| Contracts / Typed Logical Data Operations | 8, 13, 18, 32-37 |
| Contracts / Data Operation Result Invariants | 8, 13, 18, 34-37 |
| Contracts / Sparse Request Snapshot | 7, 10, 33, 40, 42 |
| Contracts / Generated JSON Schema Consistency | 9, 61, 65 |
| Contracts / Controlled Model Result Repair | 14, 19, 37, 55, 57 |
| Contracts / Deterministic User Rendering | 15, 19, 44, 48, 52 |
| Routing / Mandatory Authoritative Routing Lookup | 6, 13, 44-48, 55 |
| Routing / Intake Routing Matrix | 6, 44-45, 56-57 |
| Routing / Change 1 No-Mutation Routing Results | 6, 15, 46, 55-57 |
| Routing / Inconsistent Context Fails Closed | 6, 13, 22, 33, 46, 55-57 |
| Routing / Caller-Scoped Logical Operations | 8, 13, 18, 31-32, 38, 47, 60 |
| Routing / LF-70 MCP Isolation Evidence | 24, 31-33, 38, 44, 47, 60, 62, 65 |
| Resumption / Unique Session Binding | 21-23, 34, 40, 53 |
| Resumption / Atomic Request And Binding Creation | 21, 34, 53 |
| Resumption / Same Request Across Clarification Turns | 22, 33, 42, 51-54 |
| Resumption / Optimistic Concurrency For Mutations | 11, 13, 18, 35-36, 42, 53, 55 |
| Resumption / No Automatic Write Replay | 14, 18-19, 37, 47, 55, 60 |
| Resumption / LangFlow Restart Resumption | 27, 49, 51, 54, 62, 65 |
| Resumption / Human-Transparent Session Continuity | 5, 16, 42, 48, 50-51 |
| Runtime / Pinned Full LangFlow Runtime | 2-4, 25-27, 31, 49, 61-65 |
| Runtime / Three Stable Change 1 Flows | 29, 32, 38, 44, 49, 61-65 |
| Runtime / Git-Authoritative Flow Lifecycle | 29-32, 49, 61, 64-65 |
| Runtime / Flow Compatibility Validation | 30-32, 38, 44, 49, 61, 65 |
| Runtime / Secret-Free Flow Assets | 1, 28-32, 49, 60-65 |
| Runtime / PostgreSQL-Backed LangFlow Persistence | 26-28, 49, 54, 62, 65 |
| Runtime / Authenticated Internal Flow Invocation | 1, 28, 48-49, 62, 64 |
| Runtime / Dependency Readiness | 24-28, 49, 62, 64-65 |

The evidence manifest in Task 65 expands these 38 requirement groups to every named `#### Scenario:` and to every approved Gherkin scenario/example row; this table proves that each requirement has an implementation and verification home before execution begins.

---

## Original Task Coverage

Every checklist item from `tasks.md` is assigned exactly once:

| Original ID | Plan task | Original ID | Plan task | Original ID | Plan task |
| --- | ---: | --- | ---: | --- | ---: |
| 1.1 | 1 | 1.2 | 2 | 1.3 | 3 |
| 1.4 | 4 | 2.1 | 5 | 2.2 | 6 |
| 2.3 | 7 | 2.4 | 8 | 2.5 | 9 |
| 3.1 | 10 | 3.2 | 11 | 3.3 | 12 |
| 3.4 | 13 | 3.5 | 14 | 3.6 | 15 |
| 4.1 | 16 | 4.2 | 17 | 4.3 | 18 |
| 4.4 | 19 | 4.5 | 20 | 5.1 | 21 |
| 5.2 | 22 | 5.3 | 23 | 5.4 | 24 |
| 6.1 | 25 | 6.2 | 26 | 6.3 | 27 |
| 6.4 | 28 | 7.1 | 29 | 7.2 | 30 |
| 7.3 | 31 | 7.4 | 49 | 8.1 | 32 |
| 8.2 | 33 | 8.3 | 34 | 8.4 | 35 |
| 8.5 | 36 | 8.6 | 37 | 9.1 | 38 |
| 9.2 | 39 | 9.3 | 40 | 9.4 | 41 |
| 9.5 | 42 | 9.6 | 43 | 10.1 | 44 |
| 10.2 | 45 | 10.3 | 46 | 10.4 | 47 |
| 10.5 | 48 | 11.1 | 50 | 11.2 | 51 |
| 11.3 | 52 | 11.4 | 53 | 11.5 | 54 |
| 11.6 | 55 | 12.1 | 56 | 12.2 | 57 |
| 12.3 | 58 | 12.4 | 59 | 12.5 | 60 |
| 13.1 | 61 | 13.2 | 62 | 13.3 | 63 |
| 13.4 | 64 | 13.5 | 65 |  |  |

Coverage arithmetic: sections contain `4 + 5 + 6 + 5 + 4 + 4 + 4 + 6 + 6 + 5 + 6 + 5 + 5 = 65` original checklist IDs; the table assigns each ID to one plan task and no plan task claims a second original ID.

## Plan Self-Review Record

- **Spec coverage:** the evidence strategy maps all 38 requirement groups and all 95 named scenarios from the five specs plus all 34 expanded examples from both approved features. The implementation tasks cover strict wrappers, trusted metadata, exact five operations, sparse state, 11 generated schemas, raw-status adaptation, exhaustive routing, retry/repair/rendering, caller/MCP isolation, atomic binding, optimistic concurrency, no replay, restart, pinned/Git-authoritative runtime, authentication/readiness, BDD, evaluation, observability, CI, docs, and release evidence.
- **Scope coverage:** exactly LF-70/LF-10/LF-00 are planned; LF-20 and post-`complete` behavior remain deferred. No FastAPI, repository, empty adapter layer, LinkML-generated edit, OpenTelemetry stack, SonarCloud gate, deployment, or release publication is introduced.
- **Dynamic-runtime consistency:** component ports, runtime metadata accessors, omitted-session behavior, and handles are discovered from LangFlow 1.10.2 and frozen by Task 31; Task 32 consumes that snapshot immediately. Actual trace span tuples and migrated safe columns are executable stop gates before BDD/evaluation/CI evidence.
- **Type/signature consistency:** `MainFlowInput`, `RouterInput`, `IntakeInput`, `RoutingLookupRecord`, `RoutingContext`, `RouterResult`, `IntakeResult`, `DataOperationRequest`, `DataOperationResult`, `FlowReply`, probes, and controller names are defined once in [Locked Shared Interfaces](#locked-shared-interfaces) and used consistently by later tasks. Stable component IDs match the version-1 manifest; serialized ports/handles come only from pinned-runtime inspection.
- **Security consistency:** only synthetic values and secret names occur in this plan. Task 1 cannot proceed before developer-confirmed rotation, and agents are forbidden from reading the old or ignored values.
- **Commit control:** all 65 tasks end at a proposed Conventional Commit review point requiring explicit developer approval; none authorizes automatic commit.

## Execution Handoff

After developer approval of this plan, use subagent-driven development task by task. Under `AGENTS.md`, dispatch implementation to the project `implementer` agent, keep specification-conformance and code-quality reviews separate, and rerun each task's focused RED/GREEN evidence before presenting its commit proposal.
