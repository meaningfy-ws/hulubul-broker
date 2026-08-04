# LF-70 (Data Access) — Manual Test Scenarios

LF-70 (`langflow/flows/10-lf-70-data-access.json`, stable flow ID
`94f6774d-ebc7-5bf1-8486-886f91886a5f`) is not designed to be talked to in
natural language. Its entry point is `HulubulDataOperationRequestBoundaryComponent`,
which expects the chat message text to be a JSON `DataOperationRequest` —
one of exactly five typed operations
(`getRequestRoutingContext`, `createDeliveryRequest`, `readDeliveryRequest`,
`updateDeliveryRequest`, `setRequestStatus`). Its exit point is
`HulubulDataOperationResultBoundaryComponent`, which emits a JSON
`DataOperationResult`. In production this contract is filled in by an
upstream agent flow (LF-00/LF-10); for manual testing you fill it in
yourself and read the JSON straight off the Playground.

This document gives you ready-to-paste input for each operation, grounded
in real rows already sitting in the dev Neo4j graph (or freshly seeded rows
in the same shape LF-70's agent actually writes), plus Cypher to check state
before/after and the output you should see.

## 1. Prerequisites

```bash
cp infra/.env.example infra/.env   # if not already done; edit passwords
make up                            # Neo4j + MCP + LangFlow + Postgres
make neo4j-seed                    # loads infra/cypher/seed.cypher (idempotent)
```

- LangFlow UI: `http://localhost:7860`
- Neo4j Browser: `make neo4j-browser` (or `http://localhost:7474`)
- LangFlow API key: `infra/.env` → `LANGFLOW_API_KEY` (tests default to
  `local-dev-key-xyz` / `local-dev-key-hulubul-phase1` depending on which
  `.env` you're running — check yours)
- The flow's stable ID may differ from the one above if it was
  regenerated; confirm via LangFlow UI → LF-70 flow → Share/API, or by
  reading `"id"` at the top of `langflow/flows/10-lf-70-data-access.json`.

## 2. Wiring Chat Input / Chat Output for manual testing

LF-70's request boundary uses a `MessageTextInput`, deliberately chosen
(see the component's docstring) because it accepts **both** a literal
value and a real edge from a Chat Input node — that's what makes plugging
a Chat Input into it possible at all (a `HandleInput` would not work here).

1. Open the LF-70 flow in the LangFlow builder.
2. Drag in a **Chat Input** component. Wire its `Message` output into the
   **Data Operation Request** input of `HulubulDataOperationRequestBoundary`.
3. Drag in a **Chat Output** component. Wire it from the **Result** output
   of `HulubulDataOperationResultBoundary`. That output is typed `JSON`;
   if Chat Output rejects a direct `JSON` edge in your LangFlow version,
   insert a **Parser** component in between (already listed as a supported
   native component for LF-70 in the blueprint) to render it to text.
4. Open **Playground**. Paste one of the JSON payloads below as your chat
   message and send it. The reply is the raw `DataOperationResult` JSON.

This wiring is for manual/exploratory use only — leave it disconnected (or
on a duplicated copy of the flow) before committing, since production LF-70
must only be invoked via `Run Flow` from LF-00/LF-10, not a standing chat
surface.

**Scripted alternative** (no UI clicking, good for repeating a scenario):
reuse `tests/support/langflow_client.py`, the same client the integration
tests use — `LangFlowClient(base_url=..., api_key=...).run_flow_with_actor(flow_uuid=..., input_data=<dict below>)`.
This avoids guessing the exact HTTP body shape of LangFlow's `/api/v1/run/{id}`
endpoint by hand.

## 3. Request envelope cheat-sheet

Every payload shares this envelope plus operation-specific fields:

```json
{
  "operation": "one of the five operation strings",
  "operation_id": "any string, unique per call",
  "caller": "LF-70",
  "session_id": "any string",
  "actor_id": "any string",
  "schema_version": "1.0.0",
  "correlation_id": "<uuid4>"
}
```

**Caller authorization matrix** (`data_operation_policy.py`):

| Operation | LF-00 | LF-10 | LF-70 |
|---|---|---|---|
| `getRequestRoutingContext` | ✅ | ❌ | ✅ |
| `createDeliveryRequest` | ❌ | ✅ | ✅ |
| `readDeliveryRequest` | ❌ | ✅ | ✅ |
| `updateDeliveryRequest` | ❌ | ✅ | ✅ |
| `setRequestStatus` | ❌ | ✅ | ✅ |

`caller: "LF-70"` is authorized for all five, which is why every happy-path
scenario below uses it — it's the only caller value that lets you exercise
every operation without tripping `OPERATION_NOT_ALLOWED`. Section 4.6 uses
the *wrong* caller on purpose to demonstrate that guardrail.

**Neo4j property names actually used** (from `model/linkml/hulubul_request.yaml`
and the indexes in `infra/cypher/schema.cypher` — this is the ground truth,
not the property names some of the still-unverified integration tests
guessed): `DeliveryRequest.id`, `.hasStatus`, `.created`, `.updated`,
`.closed`. Use these in your verification Cypher.

## 4. Scenarios

Two tiers, by design:

- **Tier 1 (§4.1–4.5, 4.7)** — fixtures seeded directly with the flat
  properties LF-70's agent actually reads/writes for the Phase-1 operational
  contract (`facts` as literal strings on the `DeliveryRequest` node). These
  give you a deterministic, pinned expected output.
- **Tier 2 (§4.6)** — reads against the pre-existing demo dataset
  (`req-001`…`req-009`, real Senders/Receivers/Transporters/Addresses from
  `infra/cypher/seed.cypher`), which models the full target conceptual graph
  (separate `Address`/`Agent` nodes via relationships) rather than flat
  operational properties. This exercises whether the LLM agent can traverse
  those relationships into an `IntakeFacts` snapshot — genuinely
  exploratory; only the structurally-guaranteed fields are pinned.

### 4.1 `getRequestRoutingContext` — no binding present

**Given:** a session ID nothing is bound to.

```cypher
// before — confirm nothing exists for this session
MATCH (b:OperationalConversationBinding {sessionId: 'sess-manual-001'})
RETURN b;
// expect: no rows
```

**Input** (paste as chat message):

```json
{
  "operation": "getRequestRoutingContext",
  "operation_id": "op-manual-001",
  "caller": "LF-70",
  "session_id": "sess-manual-001",
  "actor_id": "actor-manual-001",
  "schema_version": "1.0.0",
  "correlation_id": "3f6e2b1a-0000-4000-8000-000000000001"
}
```

**Expected output:** `RoutingContext` with `binding_state: "absent"`,
`binding_count: 0`, `active_relationship_count: 0`, `active_target_count: 0`,
`request_id: null`, `request_status: null`, `closed_at: null`.

**After:** no Cypher needed — this is a pure read; re-running the "before"
query still returns no rows.

### 4.2 `getRequestRoutingContext` — bound to an open request

**Given:** a fresh binding pointing at a `new` request.

```cypher
// before — seed a minimal open request + binding
MERGE (b:OperationalConversationBinding {sessionId: 'sess-manual-002'})
  SET b.createdAt = datetime(), b.actor = 'actor-manual-002', b.source = 'api'
MERGE (r:DeliveryRequest {id: 'req-manual-002'})
  SET r.created = datetime(), r.updated = datetime(), r.hasStatus = 'new'
MERGE (b)-[:BINDS_ACTIVE_REQUEST]->(r)
RETURN b.sessionId, r.id, r.hasStatus;
```

**Input:**

```json
{
  "operation": "getRequestRoutingContext",
  "operation_id": "op-manual-002",
  "caller": "LF-70",
  "session_id": "sess-manual-002",
  "actor_id": "actor-manual-002",
  "schema_version": "1.0.0",
  "correlation_id": "3f6e2b1a-0000-4000-8000-000000000002"
}
```

**Expected output:** `binding_state: "bound"`, `binding_count: 1`,
`active_relationship_count: 1`, `active_target_count: 1`,
`request_id: "req-manual-002"`, `request_status: "new"`, `closed_at: null`.

**After:** re-run the seed query's `MATCH` half — same values, nothing
mutated (read-only operation).

```cypher
MATCH (b:OperationalConversationBinding {sessionId: 'sess-manual-002'})-[:BINDS_ACTIVE_REQUEST]->(r:DeliveryRequest)
RETURN r.hasStatus, r.updated;
// expect: hasStatus unchanged, updated timestamp unchanged
```

### 4.3 `readDeliveryRequest` — sparse new request

**Given:** a request with only two of the eight intake fields captured
(mirrors an early-intake conversation, e.g. UC-1 before completeness is
reached).

```cypher
// before
MERGE (r:DeliveryRequest {id: 'req-manual-003'})
  SET r.created = datetime(), r.updated = datetime(), r.hasStatus = 'new',
      r.pickup_location = 'Chișinău, Ștefan cel Mare 31',
      r.parcel_declared_content = 'Books'
RETURN r;
```

**Input:**

```json
{
  "operation": "readDeliveryRequest",
  "operation_id": "op-manual-003",
  "caller": "LF-70",
  "session_id": "sess-manual-003",
  "actor_id": "actor-manual-003",
  "schema_version": "1.0.0",
  "correlation_id": "3f6e2b1a-0000-4000-8000-000000000003",
  "request_id": "req-manual-003"
}
```

**Expected output:** `outcome: "confirmed"`, `success: true`,
`write_dispatched: false`, `result.request_id: "req-manual-003"`,
`result.status: "new"`, `result.facts.pickup_location: "Chișinău, Ștefan cel Mare 31"`,
`result.facts.parcel_declared_content: "Books"`, other fact fields absent/null,
`result.missing_fields` non-empty (should list the still-missing intake
fields: `receiver_identity`/`drop_off_location`/`preferred_period` etc. per
`IntakeField`), `result.updated_at` present.

**After:** read again directly — no mutation.

```cypher
MATCH (r:DeliveryRequest {id: 'req-manual-003'}) RETURN r.updated;
// expect: same timestamp as before the call
```

### 4.4 `createDeliveryRequest` — full happy path

Content flavored on the real demo geography (München → Chișinău, same
corridor as `req-001`/`req-005`/`req-007`) so the scenario reads like a
plausible Sender message, without colliding with real demo IDs.

**Given:** nothing — this creates fresh nodes. Change **both**
`identifiers.request_id` **and** `session_id` each run, or run §5 Cleanup
first.

`session_id` is the one that actually bites. `OperationalConversationBinding.sessionId`
is unique (`operationalconversationbinding_sessionid_unique`), and this write
creates the binding in the same transaction as the request — so a second run
against a `session_id` that is already bound violates the constraint, the whole
transaction rolls back, and you get §4.4b's behaviour no matter how fresh
`request_id` is: `outcome: "rejected"`, `write_dispatched: true`,
`error_code: "MCP_OPERATION_FAILURE"`, and no `req-…` node in the graph.

That is correct fail-closed behaviour, not a flow defect — but it is easy to
mistake for one, because the error code is the generic dependency-failure
bucket and says nothing about a conflict. Before investigating a failed §4.4,
check whether the session is already bound:

```cypher
MATCH (b:OperationalConversationBinding {sessionId: 'sess-manual-004'})-[:BINDS_ACTIVE_REQUEST]->(r)
RETURN r.id;
// any row here means §4.4 cannot pass for this session_id until §5 Cleanup runs
```

(Earlier guidance said to freshen only `request_id`. That is not sufficient:
the `Input` block below hardcodes `session_id`, so following it literally made
every run after the first fail.)

**Input:**

```json
{
  "operation": "createDeliveryRequest",
  "operation_id": "op-manual-004",
  "caller": "LF-70",
  "session_id": "sess-manual-004",
  "actor_id": "actor-manual-004",
  "schema_version": "1.0.0",
  "correlation_id": "3f6e2b1a-0000-4000-8000-000000000004",
  "identifiers": {
    "request_id": "req-manual-004",
    "sender_id": "s-manual-004",
    "sender_agent_id": "ag-manual-sender-004"
  },
  "facts": {
    "receiver_identity": "Maria, sister",
    "pickup_location": "München Hauptbahnhof",
    "drop_off_location": "Chișinău, Ștefan cel Mare 31",
    "parcel_declared_content": "Winter clothes and documents",
    "preferred_period": "mid-August 2026"
  }
}
```

**Expected output:** `outcome: "confirmed"`, `success: true`,
`write_dispatched: true`, `request_id: "req-manual-004"`, `status: "new"`,
`count: 1`, `created_at == updated_at` (both fresh, Neo4j transaction time —
not any timestamp you supplied, since the model rejects caller-supplied
timestamps outright).

**After:**

```cypher
MATCH (r:DeliveryRequest {id: 'req-manual-004'})
RETURN r.hasStatus, r.created, r.updated;
// expect: hasStatus='new', created == updated

MATCH (b:OperationalConversationBinding {sessionId: 'sess-manual-004'})-[:BINDS_ACTIVE_REQUEST]->(r:DeliveryRequest)
RETURN r.id;
// expect: 'req-manual-004' — binding created in the same transaction
```

### 4.4b `createDeliveryRequest` — atomicity on binding conflict

**Given:** re-run 4.4 a second time with the **same** `session_id` but a
different `request_id` (change `identifiers.request_id` and
`identifiers.sender_id` to `-004b` suffixes, keep `session_id: "sess-manual-004"`).

**Expected output:** `success: false`, `outcome` not `"confirmed"` (the
`OperationalConversationBinding.sessionId` uniqueness constraint in
`infra/cypher/operational-schema.cypher` rejects the second binding, and the
whole write — request node included — must roll back).

**After:**

```cypher
MATCH (r:DeliveryRequest {id: 'req-manual-004b'}) RETURN r;
// expect: no rows — no orphan request left behind by the rolled-back transaction

MATCH (b:OperationalConversationBinding {sessionId: 'sess-manual-004'})-[:BINDS_ACTIVE_REQUEST]->(r:DeliveryRequest)
RETURN r.id;
// expect: still 'req-manual-004' — the first binding, untouched
```

### 4.5 `updateDeliveryRequest` — additive update + concurrency

**Given:** the request created in §4.4 (`req-manual-004`), status `new`.
First, read its current `updated_at` via §4.3-style read or from the §4.4
response — you need the exact value for the compare-and-set.

```cypher
MATCH (r:DeliveryRequest {id: 'req-manual-004'}) RETURN r.updated;
```

**Input** (substitute `<updated_at_from_above>`):

```json
{
  "operation": "updateDeliveryRequest",
  "operation_id": "op-manual-005",
  "caller": "LF-70",
  "session_id": "sess-manual-004",
  "actor_id": "actor-manual-004",
  "schema_version": "1.0.0",
  "correlation_id": "3f6e2b1a-0000-4000-8000-000000000005",
  "request_id": "req-manual-004",
  "expected_updated_at": "<updated_at_from_above>",
  "expected_status": "new",
  "updates": {
    "drop_off_location": "Chișinău, Ștefan cel Mare 31, apt. 12"
  },
  "identifiers": {}
}
```

**Expected output:** `success: true`, `outcome: "confirmed"`, `count: 1`,
a fresh `updated_at` strictly later than the one you passed in.

**After:**

```cypher
MATCH (r:DeliveryRequest {id: 'req-manual-004'})
RETURN r.drop_off_location, r.updated;
// expect: drop_off_location updated, r.updated newer than before
```

**Then, negative case (concurrent modification):** replay the *exact same*
payload again (same stale `expected_updated_at`, now outdated after the
successful update above).

**Expected output:** `success: false`, `outcome: "rejected"`,
`error_code: "CONCURRENT_MODIFICATION"`, `count: 0` (or absent).

**After:** unchanged — `drop_off_location` and `updated` still hold the
values from the *first* successful update, not touched by the rejected replay.

### 4.6 (Tier 2, exploratory) `readDeliveryRequest` — real demo request

**Given:** `req-006` from the seeded demo dataset — status `complete`,
sender `s-006` (Agent `ag-sender-02`, Andrei), receiver `r-006` (Agent
`ag-receiver-02`, Ion), parcel `p-006` ("Food package"), pickup
`addr-it-rome-1` (Roma), drop-off `addr-md-balti-1` (Bălți).

```cypher
// before — confirm the demo row and its relationships are present
MATCH (r:DeliveryRequest {id: 'req-006'})
OPTIONAL MATCH (r)-[:HAS_SENDER]->(s)-[:PLAYED_BY]->(sa)
OPTIONAL MATCH (r)-[:HAS_RECEIVER]->(rc)-[:PLAYED_BY]->(ra)
OPTIONAL MATCH (r)-[:HAS_DELIVERY_ITEM]->(p)
RETURN r.hasStatus, sa.name, ra.name, p.declaredContent;
// expect: 'complete', 'Andrei (sender)', 'Ion (receiver)', 'Food package'
```

**Input:**

```json
{
  "operation": "readDeliveryRequest",
  "operation_id": "op-manual-006",
  "caller": "LF-70",
  "session_id": "sess-manual-006",
  "actor_id": "actor-manual-006",
  "schema_version": "1.0.0",
  "correlation_id": "3f6e2b1a-0000-4000-8000-000000000006",
  "request_id": "req-006"
}
```

**Expected output (pinned):** `outcome: "confirmed"`, `success: true`,
`write_dispatched: false`, `result.request_id: "req-006"`,
`result.status: "complete"`.

**Expected output (exploratory, not pinned):** whether `result.facts`
contains synthesized values (e.g. a `pickup_location` string derived from
the `addr-it-rome-1` Address node's street/city fields) depends entirely on
the Cypher the LLM Data Access Agent writes against the schema it discovers
at runtime — `req-006` has no flat `pickup_location`/`drop_off_location`/
`receiver_identity` properties, only relationships to `Address`/`Receiver`
nodes. Record whatever you actually see here; a `missing_fields` list that
treats these as absent is equally plausible and equally "correct" given the
current contract. This scenario's real purpose is surfacing that gap, not
asserting a specific shape.

**After:** no mutation expected regardless — confirm with the same
"before" query.

### 4.7 `setRequestStatus` — valid and invalid transitions

Transition table (`ALLOWED_TRANSITIONS` in `transitions.py`): only
`None→new`, `new→needsClarification`, `new→complete`,
`needsClarification→complete` are allowed. Everything else, including any
transition out of `complete`, is rejected.

**Given:** a fresh request in `new` status.

```cypher
MERGE (r:DeliveryRequest {id: 'req-manual-007'})
  SET r.created = datetime(), r.updated = datetime(), r.hasStatus = 'new'
RETURN r.hasStatus, r.updated;
```

**Input — valid `new → complete`** (substitute `<updated_at_from_above>`):

```json
{
  "operation": "setRequestStatus",
  "operation_id": "op-manual-007a",
  "caller": "LF-70",
  "session_id": "sess-manual-007",
  "actor_id": "actor-manual-007",
  "schema_version": "1.0.0",
  "correlation_id": "3f6e2b1a-0000-4000-8000-000000000007",
  "request_id": "req-manual-007",
  "expected_updated_at": "<updated_at_from_above>",
  "expected_status": "new",
  "target_status": "complete"
}
```

**Expected output:** `success: true`, `outcome: "confirmed"`,
`status: "complete"`, `count: 1`.

**After:**

```cypher
MATCH (r:DeliveryRequest {id: 'req-manual-007'}) RETURN r.hasStatus;
// expect: 'complete'
```

**Input — invalid `complete → new`** (same request, now genuinely
`complete`; fetch the new `updated_at` first):

```json
{
  "operation": "setRequestStatus",
  "operation_id": "op-manual-007b",
  "caller": "LF-70",
  "session_id": "sess-manual-007",
  "actor_id": "actor-manual-007",
  "schema_version": "1.0.0",
  "correlation_id": "3f6e2b1a-0000-4000-8000-000000000008",
  "request_id": "req-manual-007",
  "expected_updated_at": "<updated_at_after_previous_call>",
  "expected_status": "complete",
  "target_status": "new"
}
```

**Expected output:** `success: false`, `outcome: "rejected"`,
`error_code: "INVALID_STATUS_TRANSITION"`.

**After:** `r.hasStatus` still `'complete'` — zero mutation on a rejected
transition, confirmed via the same query.

### 4.8 Authorization guardrail negatives

Same payload as §4.4, wrong caller:

```json
{ "...": "as in 4.4", "caller": "LF-00" }
```

**Expected output:** `success: false`, `outcome: "rejected"`,
`error_code: "OPERATION_NOT_ALLOWED"` — LF-00 may only call
`getRequestRoutingContext`.

Same payload as §4.1, wrong caller:

```json
{ "...": "as in 4.1", "caller": "LF-10" }
```

**Expected output:** `success: false`, `outcome: "rejected"`,
`error_code: "OPERATION_NOT_ALLOWED"` — LF-10 may not call
`getRequestRoutingContext`.

**After (both):** no Cypher needed — a rejected-at-the-boundary request
never reaches the MCP tools, so nothing to verify beyond "graph unchanged."

### 4.9 End-to-end walkthrough (bonus)

Chains §4.4 → §4.5 → §4.7's valid transition against one fresh request
(`req-manual-009`, changing all the `req-manual-004`/`-007` IDs above to
`-009`) to sanity-check the full UC-1 intake happy path — create, patch in
the missing field, mark complete — the way LF-10 would actually drive
LF-70 across a real conversation. Cross-check the final state:

```cypher
MATCH (r:DeliveryRequest {id: 'req-manual-009'})
RETURN r.hasStatus, r.pickup_location, r.drop_off_location,
       r.parcel_declared_content, r.created, r.updated;
// expect: hasStatus='complete', all facts present, created < updated
```

### 4.10 Trap: a stale `Agent` row silently blocks every create for an actor

`createDeliveryRequest` starts with:

```
MERGE (senderAgent:Agent {id: $p.sender_agent_id})
ON CREATE SET senderAgent.identifier = $p.sender_identifier, ...
WITH now, senderAgent WHERE senderAgent.identifier = $p.sender_identifier
CREATE (request:DeliveryRequest ...)
```

`ON CREATE SET` does not fire for a node that already exists, so if an `Agent`
with that id is present whose `identifier` disagrees with the one you pass, the
`WHERE` filters the row out, the `CREATE` never runs, and the write affects
nothing. You get `outcome: "rejected"`, `error_code: "MCP_OPERATION_FAILURE"`
and no clue as to why — it looks identical to a dependency outage.

`sender_agent_id` is derived deterministically from `actor_id`
(`new_graph_identifiers()`), so this is permanent for that actor until the row
is repaired: every future create for them fails the same way.

Find the bad rows:

```cypher
MATCH (a:Agent) WHERE a.identifier = a.id AND a.id STARTS WITH 'ag-'
RETURN a.id, a.identifier, a.name;
```

Repair one by setting `identifier` to the actor it represents:

```cypher
MATCH (a:Agent {id: '<the ag- id>'}) SET a.identifier = '<the actor_id>';
```

Hit live on 2026-08-03: every LF-00 intake failed this way until the row was
repaired. Two more such rows still exist in the dev graph.

**Do not change `actor_id` alone between runs.** It feeds `sender_identifier`
*and* derives `sender_agent_id`. Changing one without the other is exactly how
a mismatched row gets created in the first place.

## 5. Cleanup

Every manual fixture above uses an `req-manual-*` / `sess-manual-*`
namespace so it's trivially separable from the demo dataset:

```cypher
MATCH (r:DeliveryRequest) WHERE r.id STARTS WITH 'req-manual-' DETACH DELETE r;
MATCH (b:OperationalConversationBinding) WHERE b.sessionId STARTS WITH 'sess-manual-' DETACH DELETE b;
```

Do **not** run a blanket `MATCH (n) DETACH DELETE n` — it would also wipe
the `req-001`…`req-009` demo dataset from `infra/cypher/seed.cypher`,
which other manual/automated testing on this shared dev instance may still
depend on. Re-seed with `make neo4j-seed` if the demo data ever needs
restoring (idempotent `MERGE`, safe to re-run).
