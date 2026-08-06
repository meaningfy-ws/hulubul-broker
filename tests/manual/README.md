# Manual test scenarios

Human-driven scenarios for the three LangFlow flows. Each one is black-box:
put a message in, read the reply, check what did or did not change in Neo4j.

These are **not** collected by pytest and are not part of `make ci-static` or
`make ci`. They need the full local stack and they call a real model, so every
run costs time and money and no two runs are byte-identical. Their job is the
part the automated suites cannot cover: whether a flow behaves sensibly for a
person talking to it.

Automated coverage lives elsewhere: `tests/unit/` for pure logic, `tests/static/`
for flow-JSON structure, `tests/integration/langflow/` for pinned end-to-end
assertions against the live stack.

## Before any of them

```bash
cp infra/.env.example infra/.env   # once; edit passwords
make up                            # Neo4j + MCP + LangFlow + Postgres
make neo4j-seed                    # loads infra/cypher/seed.cypher (idempotent)
```

LangFlow UI `http://localhost:7860`, Neo4j Browser `make neo4j-browser`, API key
in `infra/.env` → `LANGFLOW_API_KEY`.

Read the flow's own "what it actually does" section before writing an
expectation. All three docs have one, and all three exist because an earlier
version of these scenarios asserted behaviour the flow never had.

## The three flows

A sender's message enters at LF-00 and travels down:

```
LF-00 main router  --(tool)-->  LF-10 request intake  --(tool)-->  LF-70 data access  -->  Neo4j
```

### [LF-00 — Main Router](lf00-manual-test-scenarios.md)

Chat entry point. Prefetches routing context from Neo4j, decides whether intake
applies, and — since 2026-08-03 — actually invokes LF-10 and renders its result.

- [What to run against](lf00-manual-test-scenarios.md#1-what-to-run-against) — has its own chat I/O, no test copy needed
- [Session IDs](lf00-manual-test-scenarios.md#2-session-ids--read-this-before-seeding-anything) — **read first**; must be a bare UUID or `p1-<uuid>`, or the flow rejects the message before it runs
- [What LF-00 does](lf00-manual-test-scenarios.md#4-what-lf-00-does--this-changed-on-2026-08-03) — the delegation change, and why the router ignores chat history
- [Cheat-sheet: what reply to expect](lf00-manual-test-scenarios.md#5-cheat-sheet-what-reply-to-expect) — every reply the flow can produce
- Scenarios: [fresh session](lf00-manual-test-scenarios.md#61-fresh-session--no-binding) · [complete request](lf00-manual-test-scenarios.md#62-fresh-session--a-complete-request) · [in progress](lf00-manual-test-scenarios.md#63-bound-to-an-in-progress-request-new) · [completed](lf00-manual-test-scenarios.md#65-bound-to-a-completed-request) · [closed](lf00-manual-test-scenarios.md#66-bound-to-a-closed-request) · [post-intake](lf00-manual-test-scenarios.md#67-bound-to-a-post-intake-request-not-closed) · [unrecognized status](lf00-manual-test-scenarios.md#68-bound-to-a-request-with-an-unrecognized-status)
- [Traps](lf00-manual-test-scenarios.md#7-traps) — the routing-context node must stay on stock `RunFlow`; a stale `Agent` row can block an actor
- [Cleanup](lf00-manual-test-scenarios.md#8-cleanup)

### [LF-10 — Request Intake](lf10-manual-test-scenarios.md)

Extracts delivery facts from prose and creates the request. Invoked by LF-00 as
a tool; driven directly here through a chat-wrapped copy.

- [What to run against](lf10-manual-test-scenarios.md#1-what-to-run-against) — use `lf-10-request-intake-test`, not the deployed flow
- [What LF-10 actually does](lf10-manual-test-scenarios.md#3-what-lf-10-actually-does--read-before-writing-expectations) — the boundary enforces `routing_context`, the agent ignores it; LF-10 only ever *creates*
- [The input contract](lf10-manual-test-scenarios.md#4-the-input-contract) — the `IntakeInput` shape, and the two field vocabularies
- Scenarios: [complete](lf10-manual-test-scenarios.md#51-complete-intake--everything-up-front) · [second corridor](lf10-manual-test-scenarios.md#52-complete-intake--second-corridor) · [partial: receiver](lf10-manual-test-scenarios.md#53-partial--receiver-only) · [partial: pickup](lf10-manual-test-scenarios.md#54-partial--pickup-only) · [not an IntakeInput](lf10-manual-test-scenarios.md#55-rejected--not-an-intakeinput-at-all) · [invalid payload](lf10-manual-test-scenarios.md#56-rejected--structurally-invalid-payload) · [ineligible routing context](lf10-manual-test-scenarios.md#57-rejected--routing-context-that-is-not-intake-eligible) · [the update gap](lf10-manual-test-scenarios.md#58-accepted-but-not-continued--the-update-gap)
- [Cleanup](lf10-manual-test-scenarios.md#6-cleanup)

Every payload here is copy-pasteable and was validated against the real
`IntakeInput` model when the doc was generated.

### [LF-70 — Data Access](lf70-manual-test-scenarios.md)

The only flow that touches Neo4j. Takes a typed `DataOperationRequest`, returns
a typed `DataOperationResult`. Not conversational — you write the contract
yourself.

- [Wiring chat I/O](lf70-manual-test-scenarios.md#2-wiring-chat-input--chat-output-for-manual-testing)
- [Request envelope cheat-sheet](lf70-manual-test-scenarios.md#3-request-envelope-cheat-sheet) — includes the caller authorization matrix
- Operations: [routing context, unbound](lf70-manual-test-scenarios.md#41-getrequestroutingcontext--no-binding-present) · [routing context, bound](lf70-manual-test-scenarios.md#42-getrequestroutingcontext--bound-to-an-open-request) · [read](lf70-manual-test-scenarios.md#43-readdeliveryrequest--sparse-new-request) · [create](lf70-manual-test-scenarios.md#44-createdeliveryrequest--full-happy-path) · [create, rollback](lf70-manual-test-scenarios.md#44b-createdeliveryrequest--atomicity-on-binding-conflict) · [update](lf70-manual-test-scenarios.md#45-updatedeliveryrequest--additive-update--concurrency) · [status transitions](lf70-manual-test-scenarios.md#47-setrequeststatus--valid-and-invalid-transitions)
- [Authorization negatives](lf70-manual-test-scenarios.md#48-authorization-guardrail-negatives) — the caller matrix, exercised
- [Trap: stale `Agent` row](lf70-manual-test-scenarios.md#410-trap-a-stale-agent-row-silently-blocks-every-create-for-an-actor) — one bad row blocks every create for an actor, reported only as a generic failure
- [Cleanup](lf70-manual-test-scenarios.md#5-cleanup)

## Two things that will bite you

**A session is single-use once it reaches LF-70.** `createDeliveryRequest`
writes an `OperationalConversationBinding` keyed on `session_id`, and that key is
unique. Re-running a *complete* intake on a session that already has one rolls
the whole write back and reports `MCP_OPERATION_FAILURE`, which looks like an
outage. Change the session id, or run the flow's cleanup first. Scenarios that
stop at a clarification never reach LF-70, so those sessions are reusable.

**Replies are model-produced and occasionally flake.** A single odd answer is
not a finding — re-run before investigating. Each doc marks which expectations
were observed once and which held across runs. See
`DEV/reports/checkpoint8-llm-nondeterminism-experience.md`.

## Never run this

```cypher
MATCH (n) DETACH DELETE n
```

It wipes the shared `req-001`…`req-009` demo dataset that several scenarios
read from. Use the per-flow cleanup sections, which are scoped by id prefix or
session prefix.
