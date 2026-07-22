## ADDED Requirements

### Requirement: Versioned Strict Operational Contracts
All cross-flow inputs and outputs SHALL validate against Pydantic-owned operational contracts with schema version `1.0.0`. `RouterInput` and `IntakeInput` SHALL be strict top-level contracts that each wrap `MainFlowInput envelope` plus `RoutingContext routing_context`. Their wrapper and both nested schema versions and correlation identifiers MUST match, and the nested session identifiers MUST match. `IntakeInput` SHALL accept only an intake-stage context with no error and either no binding/no request or one binding to one `new` or `needsClarification` request. Unknown fields, implicit type coercion, blank required strings, metadata mismatches, invalid intake contexts, and contradictory success/error combinations MUST be rejected.

#### Scenario: Valid version-1 contract is accepted
- **WHEN** a cross-flow value, including a `RouterInput` or valid intake-only `IntakeInput`, has schema version `1.0.0`, matching nested metadata/session identity, exact required types, and only declared fields
- **THEN** it is accepted and converted to its canonical representation

#### Scenario: Undeclared or mismatched wrapper field is rejected
- **WHEN** an otherwise valid cross-flow value contains an undeclared field, mismatched nested version/correlation/session, or a non-intake context inside `IntakeInput`
- **THEN** validation returns `INVALID_CONTRACT` with a field-level violation

#### Scenario: Coerced primitive is rejected
- **WHEN** a contract expects an integer or Boolean but receives a string representation
- **THEN** strict validation rejects the value rather than coercing it

#### Scenario: Failure cannot claim success
- **WHEN** a data-operation result contains an error and also claims a confirmed successful mutation
- **THEN** result validation rejects the contradiction

### Requirement: Internally Managed Execution Metadata
The human user SHALL provide message content only. The execution boundary MUST accept one LangFlow `Message`, generate a unique message identifier and correlation identifier per interaction, and compare the Message session with the active graph session. It SHALL accept only a bare UUID or canonical `p1-<UUID>`, normalize either to lowercase `p1-<uuid>`, and reject empty, arbitrary, mismatched, malformed, or flow-ID fallback sessions. API actor identity SHALL arrive through required request variable header `X-LANGFLOW-GLOBAL-VAR-HULUBUL_PHASE1_ACTOR_ID` and optional `X-LANGFLOW-GLOBAL-VAR-HULUBUL_PHASE1_ACTOR_DISPLAY_NAME`. Playground actor identity SHALL arrive through ignored required environment variable `HULUBUL_PHASE1_PLAYGROUND_ACTOR_ID` and optional `HULUBUL_PHASE1_PLAYGROUND_ACTOR_DISPLAY_NAME`. Actor role `sender`, assurance `simulated`, and invocation source `api` or `playground` SHALL be constants for their paths and MUST NOT be user/model supplied. This is simulated Phase 1 trust, not production authentication.

#### Scenario: Human message receives internal identifiers
- **WHEN** a Sender submits ordinary parcel-request text through a valid session
- **THEN** the internal envelope contains generated message and correlation UUIDs without asking the Sender for them

#### Scenario: User prose cannot change actor identity
- **WHEN** message text claims a different actor identifier, role, session, or assurance level
- **THEN** the internal envelope retains the trusted invocation metadata

#### Scenario: Trusted invocation paths supply actor and continuity
- **WHEN** an authenticated API client uses a valid Message/graph session and required actor request variable, or Playground uses a valid chat session and its ignored required actor environment value
- **THEN** API uses only the request-variable actor and Playground uses only the environment actor, with constant role, assurance, and source for each path
- **AND** two API interactions in the same session carry different message and correlation identifiers
- **AND** the canonical session is lowercase and prefixed with `p1-`
- **AND** omitting the session cannot substitute the LF-00 flow identifier
- **AND** the conversational message cannot replace those values

### Requirement: Typed Logical Data Operations
Data access SHALL use a discriminated union containing exactly `getRequestRoutingContext`, `createDeliveryRequest`, `readDeliveryRequest`, `updateDeliveryRequest`, and `setRequestStatus`. The operation payload MUST match the selected operation and MUST NOT contain caller-supplied Cypher. Create payloads SHALL contain identifiers and facts but no caller-owned creation/update timestamp. Update payloads SHALL contain both `expected_updated_at` and `expected_status`; a null preferred-period update means no change, and a non-null value may fill only an absent preferred period. Status payloads SHALL contain expected timestamp, expected status, and target status.

#### Scenario: Matching operation payload is accepted
- **WHEN** a request selects `setRequestStatus` and supplies the required request identity, expected state, concurrency value, and target state
- **THEN** contract validation accepts the logical operation

#### Scenario: Mismatched payload is rejected
- **WHEN** an operation discriminator and payload shape refer to different operations
- **THEN** validation returns `INVALID_CONTRACT` before LF-70 can invoke MCP

#### Scenario: Arbitrary operation is rejected
- **WHEN** a caller submits an unknown operation, a mismatched payload, `cypher` or `query`, or any undeclared field
- **THEN** validation returns `INVALID_CONTRACT` before caller capability evaluation or MCP invocation

### Requirement: Data Operation Result Invariants
A confirmed write result SHALL identify its operation and correlation, report the request identity and resulting state when applicable, set `write_dispatched=true`, and report exactly one affected request aggregate. A rejected or ambiguous result MUST NOT claim a confirmed mutation.

#### Scenario: Confirmed request mutation is accepted
- **WHEN** LF-70 returns a confirmed result for one request with matching operation/correlation identifiers and a valid resulting status
- **THEN** the result passes contract validation

#### Scenario: Unexpected affected count is rejected
- **WHEN** a confirmed write reports zero or more than one affected request aggregate
- **THEN** validation returns `AFFECTED_RECORD_COUNT_MISMATCH` and progression stops

#### Scenario: MCP failures have no success claim
- **WHEN** MCP either times out after write dispatch or reports a non-transient, non-authentication operation failure without a confirmed effect
- **THEN** neither result claims success or mutation
- **AND** the dispatched timeout is `ambiguous` with no affected count and `MCP_WRITE_AMBIGUOUS`
- **AND** the operation failure is rejected, not retried, and uses `MCP_OPERATION_FAILURE`

### Requirement: Sparse Request Snapshot
The request snapshot SHALL expose all persisted intake facts and explicitly represent absent Receiver, Parcel, pickup, or drop-off data while status is `new` or `needsClarification`. It MUST include the request's current `updated` value for optimistic concurrency.

#### Scenario: Partial draft snapshot is valid
- **WHEN** a persisted draft contains Sender and pickup data but no Receiver, Parcel, or drop-off data
- **THEN** the snapshot validates with those facts explicitly absent and exposes their missing-field result

#### Scenario: Complete snapshot has no required omissions
- **WHEN** a request has valid Sender, Receiver, pickup, drop-off, and declared parcel content
- **THEN** its snapshot reports no required missing fields

### Requirement: Generated JSON Schema Consistency
Operational JSON Schemas SHALL be generated deterministically from the Pydantic source models, use JSON Schema draft 2020-12, prohibit additional properties, and include a manifest of schema and generator versions. `ContractKind` and the generated inventory SHALL contain exactly 11 schemas: `main-flow-input`, `router-input`, `intake-input`, `routing-context`, `router-result`, `intake-facts`, `intake-result`, `data-operation-request`, `data-operation-result`, `delivery-request-snapshot`, and `operational-error`.

#### Scenario: Regeneration has no drift
- **WHEN** schemas are regenerated with the locked dependencies and unchanged Pydantic models
- **THEN** committed schema files and manifest remain byte-identical

#### Scenario: Contract change requires regenerated schema
- **WHEN** a Pydantic operational contract changes without updating generated schemas
- **THEN** the schema drift gate fails

### Requirement: Controlled Model Result Repair
A malformed model result SHALL receive at most one tool-less repair attempt. The repair path MUST NOT repeat a dispatched data operation, and an invalid repaired value SHALL become `MALFORMED_AGENT_RESULT`.

#### Scenario: Malformed read-only result is repaired
- **WHEN** a model returns malformed structured output before any write dispatch and the single repair produces a valid contract
- **THEN** processing continues with the validated repaired result

#### Scenario: Write-capable action is not rerun
- **WHEN** a model result is malformed after its write was dispatched
- **THEN** only the existing raw result is passed to a tool-less formatter and the write-capable agent is not invoked again

#### Scenario: Terminal model failure becomes controlled failure
- **WHEN** the one repair attempt still fails contract validation or the model provider rejects authentication before a valid result exists
- **THEN** no success or model result is accepted
- **AND** repair exhaustion returns `MALFORMED_AGENT_RESULT`
- **AND** provider authentication rejection returns non-retryable `MODEL_AUTHENTICATION_FAILURE`

### Requirement: Deterministic User Rendering
User-facing output SHALL be rendered from a validated `RouterResult` or `IntakeResult` without another model call. The rendered message MUST correspond to the structured outcome and typed error.

#### Scenario: Clarification result renders one question
- **WHEN** a validated intake result selects one clarification field
- **THEN** deterministic rendering asks only for that field

#### Scenario: Invalid structured result is not rendered as success
- **WHEN** structured result validation fails
- **THEN** deterministic rendering emits the controlled safe failure message rather than an inferred success
