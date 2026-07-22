## ADDED Requirements

### Requirement: Pinned Full LangFlow Runtime
The system SHALL run Change 1 on full LangFlow 1.10.2 with a matching LFX 1.10.2 toolchain and PostgreSQL-backed LangFlow storage. It SHALL pin LangFlow as `langflowai/langflow:1.10.2@sha256:ae6f9afd03bc032dc2989ece49791fcf83871230aff9d6e485c8e1ebada1e70f`, PostgreSQL as `postgres:16-trixie@sha256:33f923b05f64ca54ac4401c01126a6b92afe839a0aa0a52bc5aeb5cc958e5f20`, and Neo4j as `neo4j:5.26-community@sha256:362542416de6c09a971484d1893878016cc3b5cdec166e54b1c824a220ecd6b9` rather than mutable tags.

#### Scenario: Runtime reports the approved versions
- **WHEN** the Change 1 stack starts from the committed infrastructure configuration
- **THEN** LangFlow and LFX report version 1.10.2 and the LangFlow container uses the approved image digest

#### Scenario: Mutable image tag is rejected
- **WHEN** the infrastructure configuration is checked for reproducibility
- **THEN** a LangFlow image specified only as `latest` fails the runtime configuration gate

### Requirement: Three Stable Change 1 Flows
The runtime SHALL deploy exactly LF-70 Data Access, LF-10 Request Intake, and LF-00 Main Router for this change, using their version-1 stable flow identifiers. It SHALL NOT deploy a placeholder LF-20 flow.

#### Scenario: Clean deployment contains the manifest flows
- **WHEN** flows are deployed to an empty LangFlow database
- **THEN** the three manifest identifiers resolve to LF-70, LF-10, and LF-00 respectively
- **AND** no LF-20 flow is introduced by this change

#### Scenario: Stable identifier survives redeployment
- **WHEN** a compatible tracked flow revision is pushed again
- **THEN** the existing flow with the same stable identifier is updated rather than duplicated

### Requirement: Git-Authoritative Flow Lifecycle
The system SHALL treat normalized flow JSON and its manifest in Git as the authoritative flow definition. Every reviewed UI change MUST be pulled, normalized, validated, and committed before it is accepted.

#### Scenario: UI-only drift is detected
- **WHEN** a deployed flow differs from its committed normalized file
- **THEN** the LFX status/drift gate reports the difference and the change cannot pass the hard quality gate

#### Scenario: Normalization is deterministic
- **WHEN** a flow export is normalized twice with the pinned LFX version
- **THEN** the second normalized output is byte-identical to the first

#### Scenario: Volatile metadata does not create source drift
- **WHEN** only timestamps, owner/folder identifiers, or transient canvas selection state change
- **THEN** normalized flow output remains unchanged

### Requirement: Flow Compatibility Validation
Every committed flow SHALL pass strict level-4 LFX validation, required-input and edge compatibility checks, and strict upgrade compatibility before deployment.

#### Scenario: Valid flow passes the static gate
- **WHEN** LF-70, LF-10, and LF-00 contain compatible components, edges, and required inputs
- **THEN** all strict validation and upgrade checks pass

#### Scenario: Incompatible component blocks deployment
- **WHEN** a tracked flow references a missing, blocked, or breaking component
- **THEN** the static gate fails before the flow is pushed

### Requirement: Secret-Free Flow Assets
Committed flow, manifest, environment, fixture, and report files MUST NOT contain literal credentials or non-empty LangFlow secret fields. Environment mapping files SHALL contain environment-variable names only.

#### Scenario: Variable reference is accepted
- **WHEN** a flow references an allowlisted provider credential variable without embedding its value
- **THEN** flow-aware and repository secret checks pass

#### Scenario: Literal credential is rejected
- **WHEN** a flow or fixture contains a provider key, LangFlow key, private key, bearer token, or credential-bearing URL
- **THEN** the hard secret gate fails and identifies the affected artifact without printing the secret value

### Requirement: PostgreSQL-Backed LangFlow Persistence
The acceptance runtime SHALL use PostgreSQL to persist LangFlow messages, flow records, and traces across container restart. Standalone LFX execution SHALL NOT count as persistence or resumption evidence.

#### Scenario: Messages survive LangFlow restart
- **WHEN** LangFlow is restarted while its PostgreSQL data is retained
- **THEN** the existing session's LangFlow message history remains available

#### Scenario: LFX smoke test is not accepted as restart evidence
- **WHEN** a flow succeeds only through standalone `lfx run` or `lfx serve`
- **THEN** the persistence acceptance criterion remains unsatisfied

### Requirement: Authenticated Internal Flow Invocation
Programmatic flow invocation SHALL require a LangFlow API key. API actor metadata SHALL be passed as LangFlow request variables using required `X-LANGFLOW-GLOBAL-VAR-HULUBUL_PHASE1_ACTOR_ID` and optional `X-LANGFLOW-GLOBAL-VAR-HULUBUL_PHASE1_ACTOR_DISPLAY_NAME`; no FastAPI or channel adapter SHALL be required. Local Playground SHALL obtain its simulated actor from ignored `HULUBUL_PHASE1_PLAYGROUND_ACTOR_ID` and optional display-name environment configuration. Local UI auto-login MUST NOT disable API authentication, and host-facing LangFlow ports SHALL be bound to the local development interface for Change 1. These inputs provide simulated Phase 1 trust only and SHALL NOT be represented as production authentication.

#### Scenario: Authenticated request runs LF-00
- **WHEN** an internal client calls LF-00 with a valid API key, explicit valid session, and required actor request variable
- **THEN** LangFlow accepts and executes the request

#### Scenario: Missing API key is rejected
- **WHEN** an internal client invokes LF-00 without a valid API key
- **THEN** LangFlow rejects the request before any Hulubul flow mutation occurs

### Requirement: Dependency Readiness
The local and acceptance stack SHALL start dependencies in readiness order: PostgreSQL and Neo4j, domain and operational Neo4j constraints, initialized Neo4j MCP, then LangFlow and its tracked flows.

#### Scenario: Clean stack becomes ready
- **WHEN** the stack starts from empty disposable volumes with valid configuration
- **THEN** each dependency passes its protocol-level readiness check before the dependent service starts acceptance tests

#### Scenario: Listening socket without MCP initialization is insufficient
- **WHEN** the MCP port accepts TCP connections but its protocol initialization or tool inventory fails
- **THEN** the stack remains unready and integration tests do not start
