# LF-00 (Main Router) — Manual Test Scenarios

Rewritten 2026-08-03, after LF-00 was wired to actually invoke LF-10. Every
expectation below was run against the live flow; where a result was observed
only once, or varied between runs, it says so. Sibling docs:
`lf10-manual-test-scenarios.md` (the specialist LF-00 now delegates to),
`lf70-manual-test-scenarios.md` (the data-access flow both use).

## 1. What to run against

LF-00 (`langflow/flows/30-lf-00-main-router.json`, flow id
`29c624c0-7940-48c3-8164-123620c53562`) has a real `ChatInput`/`ChatOutput`
pair of its own, so there is no `-test` copy and nothing to wire. Runs appear
in the Playground's chat history directly.

```bash
cp infra/.env.example infra/.env   # if not already done; edit passwords
make up                            # Neo4j + MCP + LangFlow + Postgres
make neo4j-seed                    # loads infra/cypher/seed.cypher (idempotent)
```

`HULUBUL_PHASE1_PLAYGROUND_ACTOR_ID` and
`HULUBUL_PHASE1_PLAYGROUND_ACTOR_DISPLAY_NAME` must be set in `infra/.env` —
the trust boundary rejects a Playground message outright without them. Whatever
value you set is the `actor_id` stamped on every envelope; it is **not** taken
from the chat message.

## 2. Session IDs — read this before seeding anything

**`session_id` must be a bare UUID or `p1-<uuid>`.** `ExecutionEnvelope`
normalizes those two forms to lowercase `p1-<uuid>` and rejects everything else
with `INVALID_INPUT: session_id must be a valid UUID`.

That matters because every scenario below seeds an
`OperationalConversationBinding` keyed on `sessionId`, and it has to be the
*normalized* value the envelope produces, or the routing-context prefetch finds
no binding and the scenario silently tests the wrong thing.

An earlier version of this doc seeded `sess-manual-lf00-001` and friends. Those
are not valid session IDs here; the flow would have rejected the message before
any of it ran.

## 3. How to drive it

**Playground:** open the flow, send a message. LangFlow assigns the session ID.
To pin Neo4j state to a specific session, open a new Playground session first,
read its ID from the picker, and seed against that exact value.

**Scripted (recommended — you choose the session ID):**

```python
from types import SimpleNamespace
from tests.support.langflow_client import LangFlowClient

client = LangFlowClient(base_url="http://localhost:7860", api_key="<LANGFLOW_API_KEY>")
conversation = SimpleNamespace(
    actor_id="actor-manual-lf00",
    display_name="Test Sender",
    session_id="p1-3f6e2b1a-0000-4000-8000-000000000001",
)
reply = client.run_lf00(conversation, "I need to send a parcel")
print(reply.chat_text)
```

**API:**

```bash
curl -s -X POST "http://localhost:7860/api/v1/run/29c624c0-7940-48c3-8164-123620c53562?input_type=chat&output_type=chat" \
  -H "x-api-key: $LANGFLOW_API_KEY" -H "Content-Type: application/json" \
  -d '{"input_value": "I need to send a parcel",
       "session_id": "p1-3f6e2b1a-0000-4000-8000-000000000001"}'
```

## 4. What LF-00 does — this changed on 2026-08-03

**Intake routes now actually run intake.** The Router Agent calls
`lf-10-request-intake_tool` when it routes to intake, and LF-10's `IntakeResult`
becomes the turn's answer. Before this, LF-00 decided "route to intake" and
stopped; the sender saw `"routing to intake"` and nothing ever happened.

So the reply to an intake-eligible turn is now **LF-10's** — a clarification
question or a confirmation — never the router's hand-off text. If you see
`"routing to intake"` or `"request intake in progress"` in a reply, the router
delegated and no specialist result came back; that is a bug, and
`ContractResultBoundary` is configured to reject it as `INVALID_CONTRACT`
rather than let it render.

**Non-intake routes are unchanged** and still answer with the router's own
fixed strings.

**The router does not read chat history** (`n_messages: 0`). Its decision comes
entirely from the routing context prefetched from Neo4j for that turn. This was
tightened after a live prompt injection: a sender could plant an instruction in
one turn and have it reclassify their later turns. Multi-turn Playground
sessions therefore do *not* accumulate routing context — each turn is decided
fresh.

## 5. Cheat-sheet: what reply to expect

| Neo4j state for the session | Reply |
|---|---|
| No binding at all | **LF-10's** reply: a clarification question, or a confirmation with a request id |
| Bound, `hasStatus` `new` or `needsClarification` | **LF-10's** reply, same as above |
| Bound, `hasStatus: 'complete'` | `request intake complete` |
| Bound, `.closed` set | `request closed` |
| Bound, any post-intake status, not closed (`optionsProposed`, `waitingResponse`, `accepted`, `rejected`, `pickUpPlanned`, `pickedUp`, `delivered`, `cancelled`) | `request status not supported` |
| Bound, unrecognized status string | `routing context invalid` — never echoes the bad value |

LF-10's replies come from a closed set (`services/rendering.py`). Nothing is
free text:

| | |
|---|---|
| `Who should receive the parcel?` | |
| `Where should the parcel be picked up?` | |
| `Where should the parcel be delivered?` | |
| `What does the parcel contain?` | |
| `What preferred delivery period should I record?` | |
| `Could you tell me a bit more about the delivery?` | the fallback — see below |
| `Your parcel request is confirmed. Reference: <id>.` | |

**If you see the fallback**, LF-10 named a clarification topic the renderer has
no question for. The turn is safe but the sender learns nothing useful. Check
`clarification_field` in LF-10's raw reply via `lf-10-request-intake-test`; it
should be one of the five topics in `lf10-manual-test-scenarios.md` §4.

## 6. Scenarios

Session IDs are fixed so the seed and the message match. Change the last digit
group to re-run a scenario that writes.

### 6.1 Fresh session — no binding

**Given:** nothing.

```cypher
MATCH (b:OperationalConversationBinding {sessionId: 'p1-3f6e2b1a-0000-4000-8000-000000000001'})
RETURN b;
// expect: no rows
```

**Input:** `"I need to send a parcel"`, session
`p1-3f6e2b1a-0000-4000-8000-000000000001`.

**Expected:** a clarification question from LF-10 — the message names no
receiver, pickup or drop-off. Observed: `Who should receive the parcel?`

**After:** nothing persists for a clarification.

```cypher
MATCH (b:OperationalConversationBinding {sessionId: 'p1-3f6e2b1a-0000-4000-8000-000000000001'})
RETURN b;
// expect: no rows -- LF-10 only writes when it has all critical fields
```

### 6.2 Fresh session — a complete request

**Given:** nothing. Use a session you have not used before.

**Input:** `"Send a parcel to Anna Kowalska, pick up from Warsaw
Marszalkowska 10, drop off at Krakow Florianska 5."`, session
`p1-3f6e2b1a-0000-4000-8000-000000000002`.

**Expected:** `Your parcel request is confirmed. Reference: req-<uuid>.`
Takes 60-130s: router turn, LF-10 turn, identifier generation, and a real
Neo4j write.

**After:**

```cypher
MATCH (b:OperationalConversationBinding {sessionId: 'p1-3f6e2b1a-0000-4000-8000-000000000002'})-[:BINDS_ACTIVE_REQUEST]->(r)
RETURN r.id, r.hasStatus, r.created = r.updated AS created_equals_updated;
// expect: the reference from the reply, 'new', true
```

This is the end-to-end UC-1 path. It did not work before 2026-08-03.

### 6.3 Bound to an in-progress request (`new`)

**Given:**

```cypher
CREATE (r:DeliveryRequest {id: 'req-manual-lf00-003', hasStatus: 'new',
        created: datetime(), updated: datetime()})
CREATE (b:OperationalConversationBinding {sessionId: 'p1-3f6e2b1a-0000-4000-8000-000000000003',
        created: datetime()})
CREATE (b)-[:BINDS_ACTIVE_REQUEST]->(r);
```

**Input:** `"still working on it"`, session
`p1-3f6e2b1a-0000-4000-8000-000000000003`.

**Expected:** LF-10's clarification question. Observed `Who should receive the
parcel?` on 3/3 runs.

**Note what does *not* happen:** `req-manual-lf00-003` is untouched. LF-10 has
no update path — it only creates — so a "continuation" starts a fresh intake
and the bound request is ignored. See `lf10-manual-test-scenarios.md` §5.8.

**After:**

```cypher
MATCH (r:DeliveryRequest {id: 'req-manual-lf00-003'}) RETURN r.hasStatus, r.updated;
// expect: unchanged
```

### 6.4 Bound to an in-progress request (`needsClarification`)

Same as §6.3 with `hasStatus: 'needsClarification'` and session
`p1-3f6e2b1a-0000-4000-8000-000000000004`. Same expectation: an LF-10
clarification question, the bound request untouched.

### 6.5 Bound to a completed request

**Given:**

```cypher
CREATE (r:DeliveryRequest {id: 'req-manual-lf00-005', hasStatus: 'complete',
        created: datetime(), updated: datetime()})
CREATE (b:OperationalConversationBinding {sessionId: 'p1-3f6e2b1a-0000-4000-8000-000000000005',
        created: datetime()})
CREATE (b)-[:BINDS_ACTIVE_REQUEST]->(r);
```

**Input:** `"what's the status?"`, session
`p1-3f6e2b1a-0000-4000-8000-000000000005`.

**Expected:** `request intake complete`. Verified.

**After:** unchanged — informational, no write, no LF-10 call.

### 6.6 Bound to a closed request

**Given:** as §6.5 with `hasStatus: 'delivered'`, `closed: datetime()`,
id `req-manual-lf00-006`, session `p1-3f6e2b1a-0000-4000-8000-000000000006`.

**Input:** `"can I still change the address?"`

**Expected:** `request closed`. Verified. `closed` takes precedence over
status.

**After:** unchanged.

### 6.7 Bound to a post-intake request, not closed

**Given:** as §6.5 with `hasStatus: 'waitingResponse'`, id
`req-manual-lf00-007`, session `p1-3f6e2b1a-0000-4000-8000-000000000007`.

**Input:** `"any update?"`

**Expected:** `request status not supported`. Covered by
`test_lf00_main_router.py::TestNoMutationRoutes` for all eight post-intake
statuses.

**After:** unchanged.

### 6.8 Bound to a request with an unrecognized status

**Given:** as §6.5 with `hasStatus: 'totallyBogusStatus'`, id
`req-manual-lf00-008`, session `p1-3f6e2b1a-0000-4000-8000-000000000008`.

**Input:** `"hello"`

**Expected:** `routing context invalid`, and the reply must never contain
`totallyBogusStatus`.

**After:** unchanged.

## 7. Traps

**Do not swap `RunFlow-hlb-lf-00-routing-context-v1` to `HulubulRunFlow`.** It
looks inconsistent with the request-intake node next to it, and swapping it
breaks the routing-context prefetch: the node starts emitting
`component_as_tool` instead of resolving
`HulubulDataOperationResultBoundary-hlb-lf-70-result-v1~response`, the boundary
gets nothing usable, and *every* non-intake route answers `routing context
invalid`. This was done and reverted on 2026-08-03; it cost 13 integration
tests. That node is the project's only non-tool-mode cross-flow call, driven by
a direct edge, and stock `RunFlow` is correct for it.

Quick check: run with `output_type=debug` and confirm that node's output key is
`...-lf-70-result-v1~response`, not `component_as_tool`.

**A stale `Agent` row can block every create for an actor, silently.**
`new_graph_identifiers()` maps an actor deterministically to a
`sender_agent_id`. If a node with that id exists whose `identifier` disagrees
with the actor, LF-70's create query matches zero rows and returns a generic
`MCP_OPERATION_FAILURE` with nothing pointing at the cause. Find them with:

```cypher
MATCH (a:Agent) WHERE a.identifier = a.id AND a.id STARTS WITH 'ag-' RETURN a.id;
```

**Routing decisions are LLM-produced and occasionally flake.** One run during
this rewrite answered `routing context invalid` for a bound `new` request where
3/3 subsequent runs answered correctly. Re-run before investigating a
single anomalous reply; see `checkpoint8-llm-nondeterminism-experience.md`.

## 8. Cleanup

```cypher
MATCH (r:DeliveryRequest) WHERE r.id STARTS WITH 'req-manual-lf00-' DETACH DELETE r;
MATCH (b:OperationalConversationBinding)
WHERE b.sessionId STARTS WITH 'p1-3f6e2b1a-0000-4000-8000-'
DETACH DELETE b;
```

§6.2 creates a request with a generated `req-<uuid>` id that no prefix sweep
catches — delete it by the reference from the reply:

```cypher
MATCH (r:DeliveryRequest {id: '<reference from the §6.2 reply>'}) DETACH DELETE r;
```

Do **not** run a blanket `MATCH (n) DETACH DELETE n` — it would also wipe the
shared `req-001`…`req-009` demo dataset.

## 9. What changed in this rewrite

| Was | Now | Why |
|---|---|---|
| Sessions seeded as `sess-manual-lf00-00N` | `p1-<uuid>` | Those were never valid; the trust boundary rejects them before the flow runs |
| §3 left open whether LF-00 actually invokes LF-10 ("don't assume either way") | §4, answered: it does | The delegation was wired on 2026-08-03 |
| Intake routes expected `routing to intake` / `request intake in progress` | LF-10's reply | An intake turn now ends on the specialist's result; the hand-off text appearing is itself a bug |
| §4.3 checked `r.pickup_location` on the request | Removed | No such property — locations are separate `Place` nodes |
| §4.1 `MATCH (r:DeliveryRequest {id: STARTS WITH ...})` | Rewritten | Not valid Cypher |
| Nothing on the routing-context node | §7 | A cosmetic swap broke it and cost 13 tests |
| Nothing on session/actor rules | §1, §2 | Both are silent-failure sources |
