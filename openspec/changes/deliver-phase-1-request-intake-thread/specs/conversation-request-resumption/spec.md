## ADDED Requirements

### Requirement: Unique Session Binding
The system SHALL persist one `OperationalConversationBinding` per LangFlow session, identified by a unique `sessionId`, and SHALL link it to exactly one active `DeliveryRequest` through `BINDS_ACTIVE_REQUEST`.

#### Scenario: First request creates one binding
- **WHEN** a valid session begins request intake without an existing binding
- **THEN** exactly one binding is created and linked to the new request

#### Scenario: Existing session cannot commit a second binding
- **WHEN** another creation attempts to use the same `sessionId`
- **THEN** the uniqueness constraint prevents a second committed binding
- **AND** the constraint remains enabled in every constrained integration fixture

#### Scenario: Binding cardinality violation is detected
- **WHEN** a boundary receives a synthetic `binding_count=2`, or a constrained graph has duplicate active-request relationships or targets
- **THEN** routing returns a typed inconsistent-context failure and performs no mutation

### Requirement: Atomic Request And Binding Creation
The first request and its session binding SHALL be created in one Neo4j transaction. The caller MUST NOT supply creation timestamps. One Neo4j transaction timestamp SHALL set equal request `created` and `updated` values, SHALL set the binding timestamps, and SHALL return both request timestamps. A failed binding constraint or graph write MUST roll back the request creation so that no orphan request remains.

#### Scenario: Request and binding commit together
- **WHEN** first-turn request creation succeeds
- **THEN** the request, binding, and active-request relationship are visible together

#### Scenario: Binding conflict rolls back request
- **WHEN** request creation races with another transaction for the same unique session binding
- **THEN** the losing transaction commits neither its binding nor its request graph

### Requirement: Same Request Across Clarification Turns
Every valid interaction in a bound session SHALL resolve and update the same request identifier until intake is complete. Intake MUST NOT create a second request because later messages supply additional facts.

#### Scenario: Clarification retains request identity
- **WHEN** an incomplete request receives its next missing fact in the same session
- **THEN** the persisted request identifier before and after the interaction is identical

#### Scenario: Three-turn intake creates one request
- **WHEN** mandatory facts arrive across three messages in one session
- **THEN** Neo4j contains one active request and one binding for that session

### Requirement: Optimistic Concurrency For Mutations
Every request update and status transition SHALL compare both the previously read `updated` value and expected status. A mutation SHALL succeed only when it affects exactly one current request. A zero-row result SHALL be classified by a non-mutating authoritative read as missing/inconsistent request, stale status, stale timestamp, or invalid transition without replaying the write.

#### Scenario: Current snapshot update succeeds
- **WHEN** an update carries the request's current `updated` value and expected status
- **THEN** exactly one request is mutated and a new `updated` value is returned

#### Scenario: Concurrent update loses safely
- **WHEN** two updates use the same previously read `updated` value
- **THEN** at most one update succeeds
- **AND** the other returns `CONCURRENT_MODIFICATION` without overwriting the winner

#### Scenario: Stale transition is rejected
- **WHEN** a transition carries a stale `updated` value or expected status
- **THEN** zero requests are mutated and the caller is instructed to reload authoritative state
- **AND** a non-mutating read classifies the outcome without replaying the transition

### Requirement: No Automatic Write Replay
A write SHALL NOT be retried automatically after it is dispatched or when dispatch cannot be disproved. An ambiguous write result MUST preserve operation, correlation, session, and request identifiers for independent inspection.

#### Scenario: Dependency failures follow the declared retry boundary
- **WHEN** a routing or request read fails with a declared transient condition
- **THEN** it is retried once after 500 milliseconds
- **AND WHEN** model authentication fails or an MCP operation has a declared non-transient failure
- **THEN** it returns `MODEL_AUTHENTICATION_FAILURE` or `MCP_OPERATION_FAILURE` respectively without retry or mutation

#### Scenario: Dispatched write timeout is not replayed
- **WHEN** a write times out after dispatch begins
- **THEN** no automatic second write is issued
- **AND** the result is `MCP_WRITE_AMBIGUOUS` with identifiers needed for graph inspection

### Requirement: LangFlow Restart Resumption
The system SHALL resume a bound session after restarting the LangFlow container while retaining PostgreSQL and Neo4j. The resumed interaction MUST use the same request and persisted lifecycle state.

#### Scenario: Clarification continues after restart
- **WHEN** a request is `needsClarification`, LangFlow is restarted with PostgreSQL and Neo4j retained, and the Sender answers in the same session
- **THEN** LF-00 resolves the pre-restart request identifier and LF-10 updates that request

#### Scenario: Restart does not recreate request
- **WHEN** the first post-restart interaction resumes an existing bound session
- **THEN** no new request or conversation binding is created

### Requirement: Human-Transparent Session Continuity
The conversational user SHALL NOT be asked to provide or manage a session identifier, request identifier, message UUID, or correlation UUID. Trusted infrastructure SHALL maintain continuity and generated identifiers behind the chat interaction.

#### Scenario: Sender answers clarification naturally
- **WHEN** the system asks for a destination and the Sender replies with destination text only
- **THEN** the reply is associated with the existing session and request without requesting technical identifiers
