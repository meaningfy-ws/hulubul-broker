# LF-10 (Request Intake) — Manual Test Scenarios

Rewritten 2026-08-03 against live behaviour. Every payload below was validated
against the real `IntakeInput` model and every scenario run end to end; the
expected outputs are copied from real replies, not inferred. Sibling docs:
`lf70-manual-test-scenarios.md` (the flow LF-10 calls),
`lf00-manual-test-scenarios.md` (the flow that calls LF-10).

## 1. What to run against

Use **`lf-10-request-intake-test`**, flow id
`2b0ed901-f1ec-5647-9bda-346514544c27` — the canonical LF-10 graph with a
`ChatInput` feeding the contract boundary and a `ChatOutput` fed by the result
boundary, nothing else changed. See `langflow/test-flows/README.md`. Runs land
in the Playground's chat history so you can read them turn by turn.

Do **not** wire chat nodes into `langflow/flows/20-lf-10-request-intake.json`
(flow id `6843ae79-147f-55d4-a25b-01d6143a12cc`). That is the deployed flow
LF-00 invokes through `HulubulRunFlow`; it has no chat I/O by design.

```bash
cp infra/.env.example infra/.env   # if not already done; edit passwords
make up                            # Neo4j + MCP + LangFlow + Postgres
make neo4j-seed                    # loads infra/cypher/seed.cypher (idempotent)
```

LangFlow UI `http://localhost:7860`, Neo4j Browser `make neo4j-browser`,
API key in `infra/.env` → `LANGFLOW_API_KEY`.

## 2. How to drive it

**Playground:** open the flow, paste a payload from §5 as the chat message,
send. The reply is the raw `IntakeResult` (or `OperationalError`) JSON — LF-10
has no rendering step of its own, that only happens downstream in LF-00.

**API:**

```bash
curl -s -X POST "http://localhost:7860/api/v1/run/2b0ed901-f1ec-5647-9bda-346514544c27" \
  -H "x-api-key: $LANGFLOW_API_KEY" -H "Content-Type: application/json" \
  -d '{"input_value": "<the IntakeInput JSON, as a string>",
       "input_type": "chat", "output_type": "chat",
       "session_id": "<one per case, so each is its own Playground thread>"}'
```

**Scripted:**

```python
from tests.support.langflow_client import LangFlowClient

client = LangFlowClient(base_url="http://localhost:7860", api_key="<LANGFLOW_API_KEY>")
reply = client.run_flow_with_actor(
    flow_uuid="2b0ed901-f1ec-5647-9bda-346514544c27",
    input_data=<intake_input_dict>,
    actor_id="actor-manual-lf10",
)
```

## 3. What LF-10 actually does — read before writing expectations

Two different components make two different kinds of decision, and conflating
them produces wrong expectations.

**The contract boundary enforces `routing_context` strictly.** It builds an
`IntakeInput`, and that model rejects, with `INVALID_CONTRACT`:

- `routing_stage` anything other than `intake`
- a non-null `routing_context.error`
- `binding_state: "inconsistent"` — always
- `binding_state: "absent"` carrying a `request_id` or `request_status`
- `binding_state: "bound"` **missing** `request_id` or `request_status`
- `binding_state: "bound"` whose `request_status` is post-intake:
  `accepted`, `cancelled`, `delivered`, `optionsProposed`, `pickUpPlanned`,
  `pickedUp`, `rejected`, `waitingResponse`
  (intake-eligible: `new`, `needsClarification`, `complete`)
- `schema_version` or `correlation_id` disagreeing between wrapper and envelope
- `envelope.session_id` ≠ `routing_context.session_id`

**The agent ignores `routing_context` completely.** The words
`routing_context` and `binding` do not appear in its prompt. So once the
boundary lets a payload through, nothing downstream reacts to what the routing
context *said* — see §5.8.

**LF-10 only ever creates.** Its agent knows exactly two tools: the Graph
Identifiers Generator and LF-70's `createDeliveryRequest`. The strings
`updateDeliveryRequest`, `setRequestStatus` and `readDeliveryRequest` do not
appear in its prompt. There is no "continue an existing request" path — a
follow-up message creates a **second** request.

**Each complete intake needs a fresh `envelope.session_id`.** LF-10 passes it
verbatim to LF-70's `createDeliveryRequest`, which creates an
`OperationalConversationBinding` keyed on it, and `sessionId` is unique.
Re-running a complete intake on an already-bound session violates that
constraint, the whole write rolls back, and you get `MCP_OPERATION_FAILURE` —
see `lf70-manual-test-scenarios.md` §4.4 for the same trap on the LF-70 side.
Cases that stop at clarification never reach LF-70, so their sessions are
reusable.

## 4. The input contract

Every payload is a full `IntakeInput`:

- `actor.actor_id` and `actor.display_name` are required; `actor_role` and
  `identity_assurance` are optional and default.
- `source` is `"api"` or `"playground"`.
- `session_id` is a free string here. (LF-00 is stricter — its
  `ExecutionEnvelope` requires a bare UUID. LF-10 is not.)
- `correlation_id` must be a real UUID, and the same value in all three places
  it appears.

**Critical fields the agent looks for**, from its prompt: `receiver_name` **or**
`receiver_stable_id`, `pickup_location`, `drop_off_location`. All present →
`requestComplete`. Any missing → `clarificationRequired`.

**Two vocabularies, deliberately different.** `facts` uses the field names
above. `clarification_field` uses the renderer's question topics, which are a
different set:

| topic | question LF-00 renders |
|---|---|
| `receiver_identity` | Who should receive the parcel? |
| `pickup_location` | Where should the parcel be picked up? |
| `drop_off_location` | Where should the parcel be delivered? |
| `parcel_declared_content` | What does the parcel contain? |
| `preferred_period` | What preferred delivery period should I record? |

`receiver_identity` is the topic covering *both* `receiver_name` and
`receiver_stable_id`, which is why it has no matching fact field. LF-10's
prompt constrains `clarification_field` to these five names.

Anything outside them renders as the fallback **"Could you tell me a bit more
about the delivery?"** — safe, but useless to the sender. If you see that
string, LF-10 named a topic the renderer does not know; check
`clarification_field` in the raw reply. Before the constraint was added, LF-10
emitted `receiver_name` here, which raised inside the renderer and took the
whole LF-00 turn down with an `INVALID_CONTRACT` 500.

## 5. Scenarios

Every payload is complete and copy-pasteable as-is. Change the `session_id`
suffix before re-running a case that reaches LF-70 (§5.1, §5.2); the rest stop
earlier and can be replayed freely.

### 5.1 Complete intake — everything up front

**Given:** nothing. Fresh session.

```json
{
  "schema_version": "1.0.0",
  "correlation_id": "3f6e2b1a-1000-4000-8000-000000000101",
  "envelope": {
    "schema_version": "1.0.0",
    "correlation_id": "3f6e2b1a-1000-4000-8000-000000000101",
    "message_id": "3f6e2b1a-1000-4000-8000-000000000102",
    "session_id": "sess-manual-lf10-101",
    "actor": {
      "actor_id": "actor-manual-lf10",
      "display_name": "Andrei",
      "actor_role": "sender",
      "identity_assurance": "simulated"
    },
    "source": "api",
    "message": "Hi, I need to send a parcel. Receiver is Anna Kowalska. Pick up from Warsaw, Marszalkowska 10. Drop off at Krakow, Florianska 5. It's a box of books."
  },
  "routing_context": {
    "schema_version": "1.0.0",
    "correlation_id": "3f6e2b1a-1000-4000-8000-000000000101",
    "session_id": "sess-manual-lf10-101",
    "binding_state": "absent",
    "binding_count": 0,
    "active_relationship_count": 0,
    "active_target_count": 0,
    "request_id": null,
    "request_status": null,
    "closed_at": null,
    "routing_stage": "intake",
    "error": null
  }
}
```

**Expected:** `outcome: "requestComplete"`, `request_id` a fresh `req-<uuid>`,
`status: "new"`, `missing_fields: []`, `clarification_field: null`,
`error: null`, `facts` carrying the extracted values back. Takes 50-80s — two
model round trips plus a real Neo4j write.

Observed: `req-3449a67f-11fe-4a6c-a064-1165398a8e82`.

**After:**

```cypher
MATCH (r:DeliveryRequest {id: '<request_id from the reply>'})
RETURN r.hasStatus, r.created, r.updated;
// expect: 'new', created == updated

MATCH (b:OperationalConversationBinding {sessionId: 'sess-manual-lf10-101'})-[:BINDS_ACTIVE_REQUEST]->(r)
RETURN r.id;
// expect: the same request_id — binding written in the same transaction
```

Run that second query. `outcome: "requestComplete"` alone does not prove the
binding landed, and requests without bindings have been observed.

### 5.2 Complete intake — second corridor

**Given:** nothing. Fresh session, distinct from §5.1.

```json
{
  "schema_version": "1.0.0",
  "correlation_id": "3f6e2b1a-1000-4000-8000-000000000201",
  "envelope": {
    "schema_version": "1.0.0",
    "correlation_id": "3f6e2b1a-1000-4000-8000-000000000201",
    "message_id": "3f6e2b1a-1000-4000-8000-000000000202",
    "session_id": "sess-manual-lf10-102",
    "actor": {
      "actor_id": "actor-manual-lf10",
      "display_name": "Andrei",
      "actor_role": "sender",
      "identity_assurance": "simulated"
    },
    "source": "api",
    "message": "Please arrange a delivery to Piotr Nowak, collect from Gdansk Dluga 3 and deliver to Poznan Polwiejska 12. Contents: winter jacket."
  },
  "routing_context": {
    "schema_version": "1.0.0",
    "correlation_id": "3f6e2b1a-1000-4000-8000-000000000201",
    "session_id": "sess-manual-lf10-102",
    "binding_state": "absent",
    "binding_count": 0,
    "active_relationship_count": 0,
    "active_target_count": 0,
    "request_id": null,
    "request_status": null,
    "closed_at": null,
    "routing_stage": "intake",
    "error": null
  }
}
```

**Expected:** as §5.1, with a *different* `request_id`. Observed:
`req-609f1893-8f70-4440-8bb1-f31f259cb848`. The point of the case: two intakes
on distinct sessions must not collide or reuse identifiers.

**After:** as §5.1, with `sessionId: 'sess-manual-lf10-102'`.

### 5.3 Partial — receiver only

**Given:** nothing.

```json
{
  "schema_version": "1.0.0",
  "correlation_id": "3f6e2b1a-1000-4000-8000-000000000301",
  "envelope": {
    "schema_version": "1.0.0",
    "correlation_id": "3f6e2b1a-1000-4000-8000-000000000301",
    "message_id": "3f6e2b1a-1000-4000-8000-000000000302",
    "session_id": "sess-manual-lf10-103",
    "actor": {
      "actor_id": "actor-manual-lf10",
      "display_name": "Andrei",
      "actor_role": "sender",
      "identity_assurance": "simulated"
    },
    "source": "api",
    "message": "I want to send a package to my sister."
  },
  "routing_context": {
    "schema_version": "1.0.0",
    "correlation_id": "3f6e2b1a-1000-4000-8000-000000000301",
    "session_id": "sess-manual-lf10-103",
    "binding_state": "absent",
    "binding_count": 0,
    "active_relationship_count": 0,
    "active_target_count": 0,
    "request_id": null,
    "request_status": null,
    "closed_at": null,
    "routing_stage": "intake",
    "error": null
  }
}
```

**Expected:** `outcome: "clarificationRequired"`, `request_id: null`,
`status: null`, a non-null `clarification_field`, `error: null`. Fast, 6-15s:
no LF-70 call.

`missing_fields` and `clarification_field` **vary between runs** — which field
the agent asks about first is not stable, and whether it accepts "my sister" as
a usable receiver changes too. Assert on the outcome and on `request_id` being
null; treat the specific field as informational.

Most recently observed, after the vocabulary constraint:
`clarification_field: "receiver_identity"`,
`missing_fields: ["receiver_identity", "pickup_location", "drop_off_location"]`.
Note the agent generalised the constraint to `missing_fields` as well, even
though only `clarification_field` is constrained — so `missing_fields` may
carry either vocabulary. Do not assert on its exact contents.

**After:** nothing should exist for this session.

```cypher
MATCH (b:OperationalConversationBinding {sessionId: 'sess-manual-lf10-103'}) RETURN b;
// expect: no rows — a clarification must not persist anything
```

### 5.4 Partial — pickup only

**Given:** nothing.

```json
{
  "schema_version": "1.0.0",
  "correlation_id": "3f6e2b1a-1000-4000-8000-000000000401",
  "envelope": {
    "schema_version": "1.0.0",
    "correlation_id": "3f6e2b1a-1000-4000-8000-000000000401",
    "message_id": "3f6e2b1a-1000-4000-8000-000000000402",
    "session_id": "sess-manual-lf10-104",
    "actor": {
      "actor_id": "actor-manual-lf10",
      "display_name": "Andrei",
      "actor_role": "sender",
      "identity_assurance": "simulated"
    },
    "source": "api",
    "message": "Send a parcel from Wroclaw, Rynek 1 please."
  },
  "routing_context": {
    "schema_version": "1.0.0",
    "correlation_id": "3f6e2b1a-1000-4000-8000-000000000401",
    "session_id": "sess-manual-lf10-104",
    "binding_state": "absent",
    "binding_count": 0,
    "active_relationship_count": 0,
    "active_target_count": 0,
    "request_id": null,
    "request_status": null,
    "closed_at": null,
    "routing_stage": "intake",
    "error": null
  }
}
```

**Expected:** `outcome: "clarificationRequired"`, `request_id: null`,
`facts.pickup_location: "Wroclaw, Rynek 1"`, a non-null `clarification_field`
(observed `"drop_off_location"`), `missing_fields` listing the receiver and
drop-off in one vocabulary or the other. Same variance caveat as §5.3.

**After:** as §5.3, with `sessionId: 'sess-manual-lf10-104'`.

### 5.5 Rejected — not an `IntakeInput` at all

**Given:** nothing. Send plain prose as the entire chat message, no JSON:

```text
just send my parcel already, thanks
```

**Expected:** an `OperationalError`, not an `IntakeResult`:

```json
{
  "schema_version": "1.0.0",
  "correlation_id": "<generated>",
  "code": "INVALID_CONTRACT",
  "category": "contract",
  "message": "I could not produce a safe response.",
  "retryable": false,
  "violations": []
}
```

**After:** nothing changes.

### 5.6 Rejected — structurally invalid payload

**Given:** nothing. This is §5.1's payload with the required `envelope.actor`
removed. Everything else is well-formed JSON.

```json
{
  "schema_version": "1.0.0",
  "correlation_id": "3f6e2b1a-1000-4000-8000-000000000601",
  "envelope": {
    "schema_version": "1.0.0",
    "correlation_id": "3f6e2b1a-1000-4000-8000-000000000601",
    "message_id": "3f6e2b1a-1000-4000-8000-000000000602",
    "session_id": "sess-manual-lf10-106",
    "source": "api",
    "message": "Receiver is Anna Kowalska, pick up from Warsaw Marszalkowska 10, drop off at Krakow Florianska 5."
  },
  "routing_context": {
    "schema_version": "1.0.0",
    "correlation_id": "3f6e2b1a-1000-4000-8000-000000000601",
    "session_id": "sess-manual-lf10-106",
    "binding_state": "absent",
    "binding_count": 0,
    "active_relationship_count": 0,
    "active_target_count": 0,
    "request_id": null,
    "request_status": null,
    "closed_at": null,
    "routing_stage": "intake",
    "error": null
  }
}
```

**Expected:** the same `INVALID_CONTRACT` `OperationalError` as §5.5. The
boundary refuses before the agent runs, so this returns in ~6s rather than
~60s — the latency itself tells you the rejection was structural.

Other single-field variants worth trying: drop `envelope.message`, drop
`routing_context.binding_state`, set `source` outside `{"api", "playground"}`,
or make `envelope.session_id` differ from `routing_context.session_id`.

**After:** nothing changes.

### 5.7 Rejected — routing context that is not intake-eligible

**Given:** nothing. A complete, well-formed message, but a `routing_context`
asserting the session is already bound to a completed request and that routing
has moved past intake.

```json
{
  "schema_version": "1.0.0",
  "correlation_id": "3f6e2b1a-1000-4000-8000-000000000701",
  "envelope": {
    "schema_version": "1.0.0",
    "correlation_id": "3f6e2b1a-1000-4000-8000-000000000701",
    "message_id": "3f6e2b1a-1000-4000-8000-000000000702",
    "session_id": "sess-manual-lf10-107",
    "actor": {
      "actor_id": "actor-manual-lf10",
      "display_name": "Andrei",
      "actor_role": "sender",
      "identity_assurance": "simulated"
    },
    "source": "api",
    "message": "Receiver is Elena Popescu, pick up from Cluj-Napoca Piata Unirii 4, drop off at Iasi Stefan cel Mare 8."
  },
  "routing_context": {
    "schema_version": "1.0.0",
    "correlation_id": "3f6e2b1a-1000-4000-8000-000000000701",
    "session_id": "sess-manual-lf10-107",
    "binding_state": "bound",
    "binding_count": 1,
    "active_relationship_count": 1,
    "active_target_count": 1,
    "request_id": "req-manual-lf10-bogus",
    "request_status": "complete",
    "closed_at": null,
    "routing_stage": "complete",
    "error": null
  }
}
```

**Expected:** `INVALID_CONTRACT`. Two independent constraints are violated at
once — `routing_stage` is not `intake`, and a `bound` binding carries a
`complete` status — and either alone is enough. The agent never runs.

This is LF-10 failing closed on trusted context it was handed, which is the
behaviour to protect: it is the only thing standing between a bad routing
decision upstream and a spurious delivery request.

**After:** nothing changes. Verify it:

```cypher
MATCH (b:OperationalConversationBinding {sessionId: 'sess-manual-lf10-107'}) RETURN b;
// expect: no rows
```

### 5.8 Accepted but not continued — the update gap

**Given:** nothing seeded. `binding_state: "bound"` with an intake-eligible
`request_status`, which the contract *does* allow.

```json
{
  "schema_version": "1.0.0",
  "correlation_id": "3f6e2b1a-1000-4000-8000-000000000801",
  "envelope": {
    "schema_version": "1.0.0",
    "correlation_id": "3f6e2b1a-1000-4000-8000-000000000801",
    "message_id": "3f6e2b1a-1000-4000-8000-000000000802",
    "session_id": "sess-manual-lf10-108",
    "actor": {
      "actor_id": "actor-manual-lf10",
      "display_name": "Andrei",
      "actor_role": "sender",
      "identity_assurance": "simulated"
    },
    "source": "api",
    "message": "The pickup is at Krakow Glowny station."
  },
  "routing_context": {
    "schema_version": "1.0.0",
    "correlation_id": "3f6e2b1a-1000-4000-8000-000000000801",
    "session_id": "sess-manual-lf10-108",
    "binding_state": "bound",
    "binding_count": 1,
    "active_relationship_count": 1,
    "active_target_count": 1,
    "request_id": "req-manual-lf10-existing",
    "request_status": "needsClarification",
    "closed_at": null,
    "routing_stage": "intake",
    "error": null
  }
}
```

**Expected:** the boundary accepts this (unlike §5.7 — `needsClarification` is
intake-eligible and `routing_stage` is `intake`), and the agent then treats it
as a brand-new intake: `outcome: "clarificationRequired"`, `request_id: null`,
asking for whatever the one-line message does not supply. Observed:
`clarification_field: "receiver_name"`, 8s.

The point of the case: `req-manual-lf10-existing` is named in the routing
context and **nothing happens to it**. LF-10 has no update path, so a
"continuation" is not a continuation. Had the message carried all critical
fields, this would have created a *second* request for a session already bound
to the first — and the binding constraint would then have failed the write.

**After:** nothing should exist for this session.

## 6. Cleanup

Complete intakes create requests with generated `req-<uuid>` ids, so they
cannot be swept by an id prefix. Sweep by session instead:

```cypher
MATCH (b:OperationalConversationBinding)-[:BINDS_ACTIVE_REQUEST]->(r:DeliveryRequest)
WHERE b.sessionId STARTS WITH 'sess-manual-lf10-'
DETACH DELETE r, b;

MATCH (b:OperationalConversationBinding) WHERE b.sessionId STARTS WITH 'sess-manual-lf10-'
DETACH DELETE b;
```

The second statement catches bindings whose request was already removed. If a
run produced a request but **no** binding, that sweep misses it — delete those
by the `request_id` from the reply:

```cypher
MATCH (r:DeliveryRequest {id: '<request_id from a reply>'}) DETACH DELETE r;
```

Do **not** run a blanket `MATCH (n) DETACH DELETE n` — it would also wipe the
shared `req-001`…`req-009` demo dataset. See LF-70 doc §5.

## 7. What changed in this rewrite, and why

Recorded so the old expectations are not reintroduced from memory.

| Was | Now | Why |
|---|---|---|
| "LF-10 has no chat I/O — wire it yourself" | Use `lf-10-request-intake-test` | The copy exists; hand-wiring the deployed flow risks committing test wiring |
| "insert a Parser if Chat Output rejects the JSON edge" | Not needed | LF-10's result boundary emits `Message`, which `ChatOutput` accepts directly |
| §4.3 "continue a request that's already mid-intake" | §5.8, inverted | LF-10 has no update path; the named request is untouched. The old seed also set `pickup_location`/`drop_off_location` as `DeliveryRequest` properties, which do not exist — those are separate `Place` nodes |
| §4.4 "inconsistent routing context → `INVALID_CONTRACT`" | §5.7, **unchanged — it was right** | Briefly "corrected" to the opposite during this rewrite, on the strength of a run that created a request. That run was wrong: the `-test` copy's `ChatInput` stored the raw payload in session history and its agent read it back with `n_messages: 100`, routing the payload around the rejecting boundary. Fixed in `make_chat_test_flow.py` (history window forced to 0); the copy now fails closed exactly as production does |
| No mention of session reuse | §3, §5 | Re-running a complete intake on a bound session fails with `MCP_OPERATION_FAILURE` |
| Scenario inputs given as prose deltas | Full copy-pasteable JSON per scenario | Each payload is now validated against `IntakeInput` when this doc is generated |
| Nothing on what the boundary enforces | §3 | The boundary checks nine distinct routing-context constraints; knowing which one a payload trips is the difference between a real finding and a typo |
