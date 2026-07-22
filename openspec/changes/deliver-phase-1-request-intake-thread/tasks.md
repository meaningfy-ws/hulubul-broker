## 1. Security And Project Foundation

- [ ] 1.1 Rotate the active local model-provider credential, create `infra/langflow.env.example` with safe placeholders, and add automated checks that reject literal secrets without printing their values
- [ ] 1.2 Convert `pyproject.toml` from generator-only packaging to include `src/hulubul`, lock the approved runtime/test/quality dependencies, and preserve the existing LinkML generator commands
- [ ] 1.3 Add pytest, coverage, lint, formatting, import-linter, and tox configuration with separate fast, integration, system, and soft-evaluation environments
- [ ] 1.4 Extend the Makefile with non-conflicting Python, architecture, schema-generation, flow, test, and CI targets while preserving `make lint` as LinkML lint

## 2. Operational Contract Foundation

- [ ] 2.1 Implement the strict operational contract base, schema version, actor context, execution envelope, and centralized enums/error codes with focused unit tests
- [ ] 2.2 Implement and unit-test `RoutingContext` and `RouterResult` invariants for no binding, intake, complete, closed, unsupported, and inconsistent states
- [ ] 2.3 Implement and unit-test `IntakeFacts`, missing-field selection, `IntakeResult`, and sparse `DeliveryRequestSnapshot` contracts
- [ ] 2.4 Implement and unit-test the discriminated `DataOperationRequest` union and `DataOperationResult` confirmed/rejected/ambiguous invariants for exactly five operations
- [ ] 2.5 Implement deterministic operational JSON Schema generation, commit the version-1 schemas and manifest, and add regeneration drift tests

## 3. Pure Intake And Control Policy

- [ ] 3.1 Implement the required-field completeness policy with immediate single-field and available cross-field validation, including free-text Place boundaries
- [ ] 3.2 Implement the exact Change 1 transition table and compare-and-set precondition policy with positive and negative parameterized tests
- [ ] 3.3 Implement deterministic graph identifier generation for requests, roles, parcels, places, trusted Senders, and stable/request-scoped Receivers
- [ ] 3.4 Implement caller-to-operation authorization and operation/result postcondition policy without importing LangFlow or MCP
- [ ] 3.5 Implement the two-attempt retry classifier, 500 ms delay policy, write-dispatch prohibition, and tool-less malformed-result repair decision
- [ ] 3.6 Implement deterministic success, clarification, informational, concurrency, ambiguous-write, and failure rendering with no model dependency

## 4. LangFlow Component Entrypoints

- [ ] 4.1 Implement and unit-test the execution-envelope component so humans provide only message text while trusted context supplies session/actor data and Python generates message/correlation IDs
- [ ] 4.2 Implement and unit-test contract-boundary components that translate LangFlow Data/JSON values to strict operational models and safe typed failures
- [ ] 4.3 Implement and unit-test the LF-70 data-operation boundary enforcing caller capabilities, expected state, optimistic concurrency values, dispatch state, and affected-record policy
- [ ] 4.4 Implement and unit-test retry-decision and deterministic-renderer components without duplicating visual-flow orchestration
- [ ] 4.5 Add import-linter contracts proving that core/intake models do not import services or LangFlow entrypoints and services do not import entrypoints

## 5. Neo4j Operational Schema And Test Isolation

- [ ] 5.1 Add the unique `OperationalConversationBinding.sessionId` constraint and relationship-backed `BINDS_ACTIVE_REQUEST` operational schema outside LinkML-generated files
- [ ] 5.2 Add direct Neo4j assertion helpers and deterministic request/binding fixtures that support sparse drafts, complete requests, unsupported statuses, closed requests, and inconsistent contexts
- [ ] 5.3 Add a disposable Neo4j Testcontainer fixture, initialize domain plus operational constraints, and seed only deterministic Change 1 test data
- [ ] 5.4 Add an isolated MCP test service pointed at the disposable Neo4j instance and verify protocol initialization plus exact schema/read/write tool inventory

## 6. Reproducible LangFlow Infrastructure

- [ ] 6.1 Pin LangFlow, PostgreSQL, Neo4j, MCP base/runtime dependencies, and LFX to the approved versions/digests with an explicit reviewed upgrade path
- [ ] 6.2 Add PostgreSQL and LangFlow health checks, protocol-level MCP readiness, dependency ordering, restart policies, local-only host bindings, and required-variable validation
- [ ] 6.3 Mount tracked flows and custom components read-only, configure `PYTHONPATH`, disable starter-flow drift, and retain PostgreSQL/Neo4j persistence separately from Git source assets
- [ ] 6.4 Add local and CI LangFlow API-key configuration that preserves local UI usability while rejecting unauthenticated programmatic flow invocation

## 7. Flow-As-Code Toolchain

- [ ] 7.1 Add the LangFlow directory, stable UUIDv5 flow manifest, LFX local/CI environment map, deployment order, and developer workflow documentation
- [ ] 7.2 Implement deterministic LFX export normalization and idempotence checks without reordering semantic node/edge arrays
- [ ] 7.3 Add strict level-4 flow validation, strict upgrade compatibility, required-input/edge checks, and structural environment-variable/secret validation
- [ ] 7.4 Add LFX push/pull/status targets and a clean-instance drift check that fails for UI-only, missing, duplicate, or untracked remote flows

## 8. LF-70 Data Access Flow

- [ ] 8.1 Build the stable-ID LF-70 skeleton with typed request/result boundaries and Neo4j schema/read/write MCP tools exposed only inside this flow
- [ ] 8.2 Implement `getRequestRoutingContext` and `readDeliveryRequest` with sparse snapshot support, one safe transient read retry, and direct Neo4j integration assertions
- [ ] 8.3 Implement atomic `createDeliveryRequest` with trusted/pre-generated IDs, truthful available subgraphs, and request-plus-binding transaction rollback on conflict
- [ ] 8.4 Implement optimistic `updateDeliveryRequest` using `expected_updated_at`, immediate fact validation, exactly-one-request postconditions, and concurrent-update rejection
- [ ] 8.5 Implement `setRequestStatus` with expected timestamp/status, the exact Change 1 transition table, updated timestamp return, and invalid-transition no-mutation tests
- [ ] 8.6 Implement LF-70 ambiguous-write and malformed-result behavior so dispatched writes are never replayed and only existing raw output may enter tool-less repair

## 9. LF-10 Request Intake Flow

- [ ] 9.1 Build the stable-ID LF-10 skeleton with intake extraction, strict result boundaries, LF-70 Run Flow access, and no raw MCP component
- [ ] 9.2 Implement one-message complete intake from trusted Sender context through complete graph persistence and confirmed `new -> complete` transition
- [ ] 9.3 Implement sparse draft capture that persists every valid supplied fact, creates no placeholder domain nodes, and confirms `new -> needsClarification`
- [ ] 9.4 Implement focused clarification selection that reports the complete missing set while asking for exactly one field
- [ ] 9.5 Implement multi-turn accumulation against the same sparse snapshot, immediate validation on each turn, optimistic updates, and final `needsClarification -> complete`
- [ ] 9.6 Add direct LF-10 API tests for complete, partial, invalid-fact, several-missing-field, concurrent-update, malformed-result, and same-request outcomes

## 10. LF-00 Main Router Flow

- [ ] 10.1 Build the stable-ID LF-00 skeleton with Chat Input, internally managed envelope metadata, mandatory LF-70 context prefetch, LF-10 Run Flow access, structured result, and deterministic Chat Output
- [ ] 10.2 Implement no-binding, `new`, and `needsClarification` routes to LF-10 using the authoritative request identifier
- [ ] 10.3 Implement informational no-mutation results for `complete` and closed requests and typed no-mutation failures for `rejected`, `cancelled`, unknown, or inconsistent contexts
- [ ] 10.4 Add static and runtime trace assertions proving LF-00 always loads routing context first, invokes no raw MCP tool, and does not trigger duplicate model calls
- [ ] 10.5 Add direct LF-00 API contract tests for authenticated execution, generated metadata, route matrix, safe failures, and deterministic dual structured/chat output

## 11. BDD And Full-Stack Acceptance

- [ ] 11.1 Implement pytest-bdd step definitions for the approved `delivery_request_intake.feature` without leaking API, LangFlow, MCP, or Cypher details into business steps
- [ ] 11.2 Implement pytest-bdd step definitions for the approved `conversation_resumption.feature`, including natural clarification replies without technical identifiers
- [ ] 11.3 Add full-stack one-message and multi-turn system tests through LF-00 with independent Neo4j graph/cardinality assertions
- [ ] 11.4 Add concurrent first-message and clarification tests proving one binding/request winner, no orphan graph, no lost update, and typed conflict for the loser
- [ ] 11.5 Add retained-state restart acceptance that restarts LangFlow only, resumes the same session/request, and verifies PostgreSQL messages plus Neo4j state
- [ ] 11.6 Add negative full-stack tests for unsupported/closed/inconsistent context, stale state, malformed output, read retry exhaustion, and ambiguous writes with no prohibited mutation/replay

## 12. Evaluation And Observability

- [ ] 12.1 Create the versioned 20-case Change 1 intake dataset with exact expected routes, facts, missing sets, operations, statuses, errors, and mutation assertions
- [ ] 12.2 Implement the recorded/fake-model hard evaluator requiring 20/20 contract-valid exact decisions, zero prohibited operations, and zero extra requests/bindings
- [ ] 12.3 Implement the soft NEAR/DeepSeek evaluator recording model settings, date, dataset/schema/flow hashes, exact-decision score, field micro-F1, and safety outcomes
- [ ] 12.4 Implement the non-blocking clarification-quality judge calibration with median at least 8/10, no zero criterion, and bounded score range
- [ ] 12.5 Add structured trace/log assertions for correlation, operation, request, session, flow, component, retry, and error identifiers without message text, credentials, raw prompts, or unrestricted Cypher

## 13. CI, Documentation, And Release Gate

- [ ] 13.1 Add CI stages for dependency installation, LinkML checks, operational schema drift, unit/component tests, architecture checks, flow normalization/validation/secrets, and deterministic evaluation
- [ ] 13.2 Add isolated integration/system CI stages that start the clean stack, apply schemas, deploy exactly three flows, run API/graph/restart assertions, and preserve diagnostic reports
- [ ] 13.3 Keep live model and LLM-judge workflows explicitly soft/non-blocking while documenting the manual trigger, required secret names, and evidence retention
- [ ] 13.4 Update repository and infrastructure documentation for setup, flow development, clean test execution, credential handling, troubleshooting, rollback, and the Change 1/Change 2 cut line
- [ ] 13.5 Run the complete clean-environment gate, verify every capability requirement and Gherkin scenario has automated evidence, and record flow/schema/image hashes for review
