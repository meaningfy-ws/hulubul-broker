## ADDED Requirements

### Requirement: Mandatory Authoritative Routing Lookup
LF-00 SHALL invoke LF-70 `getRequestRoutingContext` before every routing decision. LF-70 SHALL first validate a strict internal raw lookup record containing nullable `requestStatusRaw`, then deterministically adapt it to a `RoutingContext` whose `request_status` is typed and nullable. Raw status text MUST NOT cross that boundary or appear in an error, message, log, or trace. LF-00 MUST NOT infer the lifecycle stage or mutation permission from chat history, user prose, or model memory.

#### Scenario: New interaction loads Neo4j context
- **WHEN** LF-00 receives a valid message
- **THEN** a routing-context read completes before LF-00 selects LF-10 or returns a no-op result

#### Scenario: Chat text conflicts with persisted status
- **WHEN** user text claims that a request is complete but Neo4j records `needsClarification`
- **THEN** LF-00 routes according to `needsClarification`

#### Scenario: Routing lookup fails
- **WHEN** authoritative routing context cannot be obtained after the one permitted read retry
- **THEN** LF-00 returns a controlled failure and invokes no mutating specialist

### Requirement: Intake Routing Matrix
LF-00 SHALL apply a closed exhaustive route. No binding, `new`, and `needsClarification` contexts SHALL route to LF-10. `complete` SHALL be informational. A non-null closed timestamp SHALL be informational and take precedence over every recognized or unknown status. Each of `optionsProposed`, `waitingResponse`, `accepted`, `rejected`, `pickUpPlanned`, `pickedUp`, `delivered`, and `cancelled` SHALL be unsupported with no mutation. A bound request MUST retain its persisted request identifier through any typed result.

#### Scenario: No binding routes to intake
- **WHEN** the session has no conversation binding
- **THEN** LF-00 routes to LF-10 as a new intake

#### Scenario: New request resumes intake
- **WHEN** the active request status is `new`
- **THEN** LF-00 routes to LF-10 with the same request identifier

#### Scenario: Clarification request resumes intake
- **WHEN** the active request status is `needsClarification`
- **THEN** LF-00 routes to LF-10 with the same request identifier
- **AND** parameterized route tests cover all 11 recognized statuses, null status, and closed precedence over each recognized status

### Requirement: Change 1 No-Mutation Routing Results
LF-00 SHALL return an informational no-mutation result for a `complete` or closed request because coordination is outside Change 1. It SHALL return `UNSUPPORTED_PHASE1_STATUS` without mutation for all eight recognized post-intake statuses: `optionsProposed`, `waitingResponse`, `accepted`, `rejected`, `pickUpPlanned`, `pickedUp`, `delivered`, and `cancelled`.

#### Scenario: Complete request is not coordinated
- **WHEN** the active request status is `complete`
- **THEN** LF-00 reports that intake is complete and invokes no mutating Change 1 operation

#### Scenario: Closed request remains unchanged
- **WHEN** the active request has a non-null closed timestamp with any recognized or unknown raw status
- **THEN** LF-00 returns a closed informational result and performs no mutation

#### Scenario: Rejected status is unsupported
- **WHEN** the active request status is one of `optionsProposed`, `waitingResponse`, `accepted`, or `rejected`
- **THEN** LF-00 returns `UNSUPPORTED_PHASE1_STATUS` and performs no mutation

#### Scenario: Cancelled status is unsupported
- **WHEN** the active request status is one of `pickUpPlanned`, `pickedUp`, `delivered`, or `cancelled`
- **THEN** LF-00 returns `UNSUPPORTED_PHASE1_STATUS` and performs no mutation

### Requirement: Inconsistent Context Fails Closed
LF-00 MUST return a typed failure and perform no mutation when a binding lacks a request, a session has duplicate bindings or active-request targets, a non-closed bound request has null raw status, a request has an unknown status, or routing fields contradict each other. It MUST NOT guess a route.

#### Scenario: Binding references no request
- **WHEN** an operational binding has no resolvable active request
- **THEN** LF-00 returns `BINDING_REQUEST_MISMATCH` and invokes no specialist mutation

#### Scenario: Duplicate active requests are detected
- **WHEN** one binding resolves to more than one active request
- **THEN** LF-00 returns `GRAPH_CONTEXT_INCONSISTENT` and invokes no specialist mutation

#### Scenario: Unknown status is detected
- **WHEN** `requestStatusRaw` is outside the RequestStatus enum and the request is not closed
- **THEN** adaptation sets `request_status` to null, returns failure stage with `UNSUPPORTED_REQUEST_STATUS`, and does not infer the nearest lifecycle stage or expose the raw text
- **AND** a null raw status on a non-closed bound request instead returns `GRAPH_CONTEXT_INCONSISTENT`

### Requirement: Caller-Scoped Logical Operations
The system SHALL validate the complete strict operation contract before enforcing operation capabilities by calling flow. Unknown operations, mismatched payloads, raw `cypher`/`query`, and undeclared fields SHALL return `INVALID_CONTRACT`. Only a known contract-valid operation outside the caller's declared capability SHALL return `OPERATION_NOT_ALLOWED`. LF-00 may request only routing context; LF-10 may request request creation, reading, updating, and intake status transitions; no caller other than LF-70 may receive raw Neo4j MCP tools.

#### Scenario: LF-00 requests an intake write
- **WHEN** LF-00 submits a contract-valid `createDeliveryRequest` directly
- **THEN** the operation boundary returns `OPERATION_NOT_ALLOWED` before MCP invocation

#### Scenario: LF-10 requests an allowed update
- **WHEN** LF-10 submits a contract-valid `updateDeliveryRequest`
- **THEN** LF-70 may process the operation through its constrained data-access path
- **AND** malformed or undeclared operation fields are tested separately as `INVALID_CONTRACT`, not capability failures

#### Scenario: Domain flow contains raw MCP tool
- **WHEN** static or trace verification finds an MCP tool attached to LF-00 or LF-10
- **THEN** the hard data-boundary gate fails

### Requirement: LF-70 MCP Isolation Evidence
Automated verification SHALL prove from tracked flow structure and runtime traces that LF-70 is the only flow invoking Neo4j MCP and that structured results, not raw MCP responses, cross back to domain flows.

#### Scenario: Expected MCP trace is observed
- **WHEN** LF-10 persists an intake request
- **THEN** the trace shows LF-10 invoking LF-70 and LF-70 invoking Neo4j MCP
- **AND** LF-10 receives a validated `DataOperationResult`

#### Scenario: Unexpected MCP caller fails verification
- **WHEN** a runtime trace shows LF-00 or LF-10 invoking Neo4j MCP directly
- **THEN** the hard trace-boundary assertion fails
