## ADDED Requirements

### Requirement: Phase 1 Intake Profile
Request intake SHALL consider a request complete only when it has a trusted Sender identity, Receiver name or stable identifier, pickup location text, drop-off location text, parcel declared-content description, and an optional preferred period if supplied. After surrounding whitespace is stripped, each human-supplied Receiver name, pickup location, drop-off location, parcel declared-content description, and supplied preferred period SHALL contain 1-4,000 characters.

#### Scenario: Required intake profile is complete
- **WHEN** all five mandatory facts are valid
- **THEN** completeness reports no missing fields regardless of whether a preferred period was supplied

#### Scenario: Optional preferred period is absent
- **WHEN** every mandatory fact is valid and no preferred period is supplied
- **THEN** the request remains eligible for `complete`

#### Scenario: One mandatory fact is absent
- **WHEN** parcel declared content is the only absent mandatory fact
- **THEN** completeness reports exactly `parcel_declared_content` as missing

### Requirement: Immediate Fact Validation
Every supplied fact SHALL be validated during the interaction that captures it. Single-field rules MUST run immediately, and cross-field rules MUST run as soon as all facts required by the rule are available. Invalid supplied facts MUST NOT be accepted as valid persisted facts.

#### Scenario: Blank destination is rejected immediately
- **WHEN** a message supplies a blank or whitespace-only drop-off location
- **THEN** that interaction returns a focused destination clarification and does not persist the value as valid

#### Scenario: Valid partial fact is retained
- **WHEN** a message supplies a valid pickup location but other mandatory facts are absent
- **THEN** the pickup fact is persisted and does not need to be supplied again

#### Scenario: Cross-field rule runs when inputs become available
- **WHEN** a later interaction supplies the final fact needed by a defined cross-field rule
- **THEN** that rule is evaluated during the same interaction before the new fact is accepted

### Requirement: Truthful Sparse Draft Creation
On the first valid interaction, intake SHALL create one `DeliveryRequest`, one Sender participation, the trusted Sender Agent, and one session binding. It SHALL persist each available valid Receiver, Parcel, pickup, or drop-off fact and MUST NOT create placeholder domain nodes for missing facts. When a first-time trusted simulated Sender has no existing Sender Agent, intake SHALL create the minimum enduring Sender Agent and request-specific participation required for the request. For this Walking Skeleton, trusted simulated actor metadata satisfies UC-1's Sender-identity prerequisite but does not claim a complete UC-13 profile; no profile registration or maintenance, contact-point management, verification, or profile editing is implemented.

#### Scenario: Incomplete first message creates one sparse draft
- **WHEN** the first message contains valid pickup and parcel data but no Receiver or drop-off data
- **THEN** exactly one request and binding are created with only truthful supplied domain facts
- **AND** no placeholder Receiver or drop-off Place is created

#### Scenario: Minimal first message still creates a durable draft
- **WHEN** a valid trusted Sender submits text with none of the other mandatory facts
- **THEN** one `new` request and binding are created for that Sender before clarification continues

#### Scenario: First-time trusted Sender creates only intake identity
- **WHEN** a first-time trusted simulated Sender submits a valid parcel intention without an existing Sender Agent
- **THEN** one enduring Sender Agent and one request-specific Sender participation are created with the truthful sparse request
- **AND** no broader party profile, contact point, or profile-maintenance workflow is created

### Requirement: Complete Intake In One Message
When the first message supplies a valid complete intake profile, intake SHALL persist the complete request graph, transition the request from `new` to `complete`, and return the confirmed request identifier.

#### Scenario: One-message request completes
- **WHEN** a Sender supplies valid Receiver, pickup, drop-off, and parcel-content facts in the first message
- **THEN** one request graph and binding are persisted
- **AND** the request reaches `complete`
- **AND** the result returns that persisted request identifier with no clarification field

### Requirement: Focused Clarification
When mandatory facts are missing, intake SHALL report the complete missing-field set but MUST select and ask for at most one clarification field per response. It SHALL select the first missing field in this order: Receiver identity, pickup location, drop-off location, parcel declared content. A supplied invalid field SHALL take priority during its interaction so it is corrected immediately. The request SHALL transition from `new` to `needsClarification` after the initial incomplete capture.

#### Scenario: One missing fact produces one focused question
- **WHEN** Receiver identity is the only missing mandatory fact
- **THEN** the result reports that missing field, selects it as the clarification field, and asks only for Receiver information

#### Scenario: Several missing facts still produce one question
- **WHEN** Receiver identity, drop-off location, and parcel content are missing
- **THEN** all three appear in the missing-field set
- **AND** Receiver identity appears as the clarification field and user question

### Requirement: Incremental Completion Of The Same Request
Each clarification interaction SHALL load the persisted request, merge only newly validated absent facts, recompute completeness from persisted state, and return the same request identifier. It MUST NOT require already valid facts to be repeated or replace an accepted fact. A null preferred period SHALL mean no change; a non-null preferred period MAY fill an absent value but MUST NOT clear or replace an existing value in Change 1.

#### Scenario: Several clarification turns accumulate facts
- **WHEN** destination is supplied first, parcel content second, and Receiver identity third across one session
- **THEN** each valid fact is retained after its interaction
- **AND** all three turns reference the same request identifier
- **AND** the request reaches `complete` after the final mandatory fact passes validation

#### Scenario: Earlier invalid fact is addressed before completion
- **WHEN** a supplied fact violates a rule that can be evaluated during its interaction
- **THEN** intake requests correction during that interaction rather than waiting for unrelated mandatory facts

### Requirement: Domain Graph Mapping
Completed intake SHALL persist one Sender and one Receiver participation linked to enduring Agents, one Parcel, one pickup Place, and one drop-off Place through the LinkML-defined request relationships. Agent identity MUST be based on trusted or request-scoped identifiers and MUST NOT merge parties by display name.

#### Scenario: Complete graph uses role participation pattern
- **WHEN** a request reaches `complete`
- **THEN** the request links to Sender and Receiver role nodes whose `PLAYED_BY` relationships identify enduring Agent nodes

#### Scenario: Same receiver name does not imply same Agent
- **WHEN** two requests provide the same Receiver display name without a shared stable Receiver identifier
- **THEN** each request receives its own request-scoped Receiver Agent identity

#### Scenario: Same trusted Sender is reused safely
- **WHEN** the same trusted Sender actor creates requests in different sessions
- **THEN** both Sender participations link to the same deterministic enduring Sender Agent identity

### Requirement: Intake Status Transitions
Change 1 intake SHALL write only `new`, `needsClarification`, and `complete`, using only `none -> new`, `new -> needsClarification`, `new -> complete`, and `needsClarification -> complete`. It MUST NOT write a coordination or terminal status.

#### Scenario: Valid initial incomplete transition
- **WHEN** an incomplete draft has status `new`
- **THEN** the compare-and-set transition to `needsClarification` is permitted

#### Scenario: Clarified request completes
- **WHEN** a `needsClarification` request becomes complete and concurrency expectations match
- **THEN** the compare-and-set transition to `complete` is permitted

#### Scenario: Unsupported intake transition is rejected
- **WHEN** intake requests a transition from `needsClarification` directly to `waitingResponse`
- **THEN** the operation returns `INVALID_STATUS_TRANSITION` and the status remains unchanged

### Requirement: Free-Text Place Boundary
Change 1 SHALL represent supplied pickup and drop-off text as `Place` nodes with generated identifiers and the declared `unclassifiedPlace` type. It MUST validate text structure immediately but SHALL NOT claim real-world address verification.

#### Scenario: Valid free-text location is persisted
- **WHEN** a location containing 1-4,000 characters after surrounding whitespace is stripped is supplied
- **THEN** a Place with that text, a generated identifier, and `unclassifiedPlace` type is persisted through the appropriate request relationship

#### Scenario: Oversized free-text location is rejected
- **WHEN** a supplied location contains more than 4,000 characters after surrounding whitespace is stripped
- **THEN** that interaction requests a corrected location and does not persist the oversized value

#### Scenario: Nonexistent-address claim is avoided
- **WHEN** a syntactically valid free-text location has not been checked by a geocoder
- **THEN** the system treats it as supplied location text and does not claim that the physical address was verified
