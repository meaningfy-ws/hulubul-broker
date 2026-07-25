**Document type:** Implementation (design + operational specification for
`build-telegram-gateway`). `proposal.md` is the Strategic/EPIC document this elaborates.

## Context

Hulubul's target architecture (ADR-003, ADR-008) already decides that party interaction is
channel-abstracted — Telegram in dev/test, WhatsApp in prod — behind one `ChannelPort`
interface with per-provider adapters. `architecture/task-2-frameworks-exploration.md`
already picked aiogram 3.x for Telegram and 360dialog for WhatsApp, and disqualified
unofficial WhatsApp APIs (WAHA etc.) on ToS/ban-risk grounds. None of this has been built —
Phase 1's Walking Skeleton has no real channel; trusted actor context is injected by a test
harness (`architecture/agentic-system-blueprint-phase-1.md`).

Session/request routing is already centralized inside LangFlow, not in any gateway: `LF-00
Main Router` + `LF-70 Data Access`, backed by Neo4j's `OperationalConversationBinding(sessionId,
activeRequestId)` (`architecture/agentic-system-blueprint-phase-1.md` §4, the Phase 1 flow
description; `architecture/agentic-system-blueprint.md` §8.1, the target-architecture Router
Agent spec — two different documents, not one with two section numbers).
`getRequestRoutingContext(session_id)` and `resolve_channel_actor(medium, systemID)` run as
mandatory preprocessing before the Router Agent. This means the gateway's responsibility is
narrow by design: own the channel
connection, derive a session_id, attach a trusted channel identity, call LangFlow, relay the
reply — not reimplement routing.

Two prior-art repos were reviewed and found not reusable: `fauzaanu/langflow-bot` (proves
the external-gateway shape works in ~90 lines, but has no session_id derivation and hardcodes
flow-specific tweaks) and `Empreiteiro/langflow-factory` (outbound-only LangFlow components,
no inbound webhook handling in any of Telegram/Slack/WhatsApp-Evolution/WhatsApp-Z-API).

This work is Phase 3 (Field Pilot) territory per `architecture/incremental-system-development-strategy.md`
§6, explicitly marked "prepare later" relative to the current active change
(`deliver-phase-1-request-intake-thread`, Phase 1). It is being pulled forward deliberately
to de-risk the Phase 3 cutover, not to redirect Phase 1 work.

## Goals / Non-Goals

**Goals:**
- A working Telegram gateway: receives inbound messages (polling or webhook), calls
  LangFlow's Run API with a deterministic `session_id` and trusted channel identity, relays
  the structured reply back to Telegram.
- A `ChannelPort` interface that a future WhatsApp adapter can implement without changing the
  gateway core, proven by a stub `WhatsAppAdapter`.
- Architecture documentation (`architecture/channel-gateway-blueprint.md`,
  `architecture/channel-gateway-runbook.md`) elaborating ADR-003/ADR-008 into a concrete,
  buildable design and an operational runbook.
- A three-tier local test suite (unit / feature / e2e) and a local Docker Compose deployment,
  including webhook-mode testing via a local ngrok tunnel.

**Non-Goals:**
- Redesigning `OperationalConversationBinding` for concurrent requests per channel — documented
  as a forward-looking design note only; implementation stays single-active-request.
- Cross-channel identity merge (unifying a person's Telegram and WhatsApp `Channel`s) — phone
  number is not a valid join key for this (Telegram's `systemID` is `chat_id`, not a phone
  number) and no merge mechanism is designed here.
- Live WhatsApp integration (360dialog account/BSP onboarding, template/opt-in accounting).
- Running live-Telegram tests in CI.
- Any change to LF-00/LF-70, the Neo4j domain schema, or existing Phase 1 flows.

## Decisions

### D1 — External gateway process (shape B), not a LangFlow-native component
- **Choice**: a standalone process owns the Telegram connection and calls LangFlow's Run API
  as a plain HTTP client, rather than a LangFlow Component wired to LangFlow's own webhook
  trigger.
- **Rationale**: shape B lets a mature bot framework (aiogram) own Telegram-specific concerns
  (secret-token validation, retries, rate limits) instead of hand-rolling them as flow
  components; it's also the only shape that supports one shared `ChannelPort` interface
  across channels, since LangFlow-native components would each be separate, non-abstracted
  flow nodes with no enforced common contract.
- **Alternatives considered**: LangFlow-native component (shape A) — rejected because Telegram
  quirks would have to be hand-rolled per flow, and outbound replies require an explicit
  side-effecting `sendMessage` call anyway (Telegram doesn't treat the webhook response as
  the reply), so shape A doesn't actually avoid that complexity, it just loses the shared
  interface.

### D2 — aiogram 3.x for the Telegram adapter
- **Choice**: aiogram 3.x, per the earlier `task-2-frameworks-exploration.md` decision.
- **Rationale**: modern async-first, native polling and webhook support, actively maintained.
- **Alternatives considered**: `python-telegram-bot` — used by the one working prior-art
  example (`fauzaanu/langflow-bot`), also viable, but picking it would reverse the earlier
  framework decision without a concrete reason to.

### D3 — `ChannelPort` interface with a WhatsApp stub, not a full second adapter
- **Choice**: define `ChannelPort` now; implement `TelegramAdapter` fully; implement
  `WhatsAppAdapter` as a stub that matches the interface shape (360dialog payload structure)
  but raises `NotImplementedError` on send/receive bodies.
- **Rationale**: proves the interface actually generalizes to WhatsApp without paying the
  cost of building 360dialog integration, template/opt-in accounting, and WhatsApp-specific
  testing before it's needed.
- **Alternatives considered**: interface-only (no stub) — rejected, doesn't prove interface
  fit. Full second adapter — rejected as premature scope given WhatsApp isn't on the near
  roadmap.

### D4 — Single-active-request session binding, concurrent-request design deferred
- **Choice**: `session_id` is derived locally and deterministically as `f(medium, systemID)`;
  the gateway is built against the current, Phase-1-only `OperationalConversationBinding`
  shape (one active request per channel at a time).
- **Rationale**: this equivalence holds correctly for sequential channel reuse (a request
  closes, the binding frees, the next message rebinds) — the common case. It breaks only for
  concurrent requests on one channel, which is explicitly out of scope for Phase 1's binding
  shape and flagged in `incremental-system-development-strategy.md` §3.1/§6.1 as needing its
  own future redesign (mechanism already named for later: `resolve_reply_reference` for
  deterministic reply correlation, falling back to `ask_request_disambiguation`).
- **Alternatives considered**: redesigning the binding now — rejected as disproportionate
  scope for a gateway-focused change; would also touch Neo4j schema and LF-00/LF-70 flow
  logic well beyond the gateway boundary.

### D5 — One gateway container hosting all channel adapters
- **Choice**: a single service/Dockerfile (sibling to `mcp-neo4j` in `infra/docker-compose.yaml`)
  hosts both the Telegram adapter (polling or webhook, per `GATEWAY_MODE`) and the WhatsApp
  stub, behind the shared `ChannelPort` interface.
- **Rationale**: simpler to deploy and reason about than per-channel containers; matches the
  interface design; WhatsApp isn't live code yet so fault isolation between channels isn't
  yet a real concern.
- **Alternatives considered**: one container per channel — rejected for now; better fault
  isolation but doubles deployment surface for no current need. Revisit if a real
  scaling/blast-radius reason emerges.

### D6 — Local dev supports both polling and webhook mode, via an ngrok tunnel
- **Choice**: `GATEWAY_MODE=polling|webhook`; webhook mode adds an `ngrok` service to the
  local Compose stack so the production code path is exercisable locally, not just polling.
- **Rationale**: polling alone needs no inbound port and would be the cheaper default, but
  the user specifically wants webhook mode exercised locally, not deferred to a future real
  deployment. ngrok chosen over cloudflared per prior use in another project (both are
  otherwise equivalent quick-tunnel options).
- **Alternatives considered**: polling-only for local dev, webhook deferred — rejected per
  explicit preference to test the real code path locally.

### D7 — Module layout follows cosmic-python layering strictly
- **Choice**:
  ```
  src/hulubul/channel_gateway/
    models/message.py       # InboundMessage/TextMessage/MediaMessage — pure value objects
    models/channel.py        # ChannelRef value object + derive_session_id(medium, systemID) — pure
    adapters/channel_port.py # ChannelPort ABC
    adapters/telegram_adapter.py
    adapters/whatsapp_adapter.py
    adapters/langflow_client.py
    services/relay_message.py # orchestrates adapter.receive() -> langflow_client.run() -> adapter.send()
    entrypoints/telegram_bot.py # process entrypoint; wires aiogram Dispatcher -> services

  src/hulubul/core/models/domain/hulubul_models.py  # GENERATED (make pydantic), see D9 — Channel, Medium, etc.
  ```
- **Rationale**: per the `cosmic-python` skill's canonical layers, `adapters/` implements
  "repositories, gateways, clients" and depends only on `models/`; `services/` orchestrates
  models+adapters and owns no I/O of its own; `models/` is pure domain logic with no I/O. The
  LangFlow Run API client and `session_id` derivation were initially mis-placed in `services/`
  during the first design pass and corrected against this catalogue.
- **Alternatives considered**: `aiogram_bot.py` as the entrypoint name, following the
  cosmic-python book's convention of naming entrypoints after their concrete technology
  (`flask_app.py`, `redis_eventconsumer.py`) — rejected by the user in favor of
  `telegram_bot.py`, to keep the aiogram/SDK choice an implementation detail hidden behind
  the stable channel concept rather than exposed in the module name.

**Post-brainstorm correction (model-source review):** the initial pass named the gateway's
local value object `Channel(medium, system_id)`, colliding with the name of the real business
entity already modeled in `model/linkml/hulubul_channel.yaml`. Two independent checks were
run against the actual generated class (`Channel(id, description, alias, systemID, email,
telephone, hasMedium, validationStatus)`), not just a naming judgment call:

1. `validationStatus` is required, but this alone doesn't block reuse — the gateway *does*
   know the correct value at message-receipt time. Per the already-decided rule from a prior
   session (an inbound message is itself proof of control), it would always construct
   `validationStatus=valid`. Not a blocker on its own.
2. `id` is also required and is the **graph node identity** ("distinct from any business
   identifier") — meaningless before the node is persisted in Neo4j. The gateway cannot
   supply it honestly without either minting a fake placeholder (risks colliding with a real
   node's id once `resolve_channel_actor` runs its lookup) or taking over id-assignment from
   `resolve_channel_actor` entirely (a materially bigger change than scoped here). **This is
   the actual blocker** — a full `Channel` genuinely cannot be constructed pre-persistence.

Renamed to `ChannelRef`: an identity/reference value object (the `(medium, systemID)` natural
key only) distinct from the full `Channel` entity it refers to — a standard DDD pattern (e.g.
`CustomerId` vs `Customer`), not a duplicate model. The real `Channel` (with a real `id` and
`validationStatus`) is only ever constructed where a graph node backs it, inside
`resolve_channel_actor`. `Channel` remains reserved exclusively for the LinkML-generated
entity; nothing in this change adds to or regenerates the LinkML schema itself.

### D8 — Three-tier test suite (unit / feature / e2e), CI runs unit + feature only
- **Choice**:
  - `tests/unit/` — models + adapters with mocks, nothing real, always in CI.
  - `tests/features/*.feature` (Gherkin, pytest-bdd) + new `tests/feature/` step-definitions —
    real local LangFlow container, synthetic inbound (no real Telegram); traces back to a use
    case in `architecture/use-cases/` per the `bdd-gherkin` skill; runs in CI.
  - `tests/e2e/` (new) — real Telegram test bot + real local LangFlow, dev/staging-like full
    stack up; local/manual only, excluded from CI. Covers both the full round-trip and a
    Telegram-only isolation scenario (LangFlow response stubbed) as sub-cases within this
    suite rather than a fourth top-level category.
- **Rationale**: matches the user's preferred three-category taxonomy while still covering
  all four dependency states (LangFlow×Telegram, connected/disconnected) from the original
  brainstorm; reuses the existing `tests/features/` Gherkin convention and `pytest-bdd`
  dependency already in the repo; avoids adding a Telegram bot-token secret to CI.
- **Alternatives considered**: running live-Telegram tests in CI with a bot-token secret —
  rejected (secret management, flakiness, rate-limit exposure for no current need).

### D9 — Relocate LinkML→Pydantic generation into an importable domain package
- **Choice**: `make pydantic`'s output moves from `model/generated/pydantic/hulubul_models.py`
  to `src/hulubul/core/models/domain/hulubul_models.py`, still fully generated (never
  hand-edited — a banner in the new package's `__init__.py` states this), still regenerated
  by the same `make pydantic` target, just written somewhere the `hulubul` package can
  actually import from.
- **Rationale**: `model/generated/pydantic/` is **not** part of the installed `hulubul`
  package today — `pyproject.toml`'s `packages` list only includes `src/hulubul` — so nothing
  under `src/hulubul/` can import the generated domain models (`Channel`, `Medium`, etc.)
  without a path hack. This is what pushed prior hand-written code (the `core/models/operational/`
  layer, and this change's own first-draft `Medium` enum redefinition in
  `channel_gateway/models/message.py`) toward duplicating concepts that already exist in
  LinkML, rather than reusing them. Fixing the import path is a prerequisite for `ChannelRef`
  and `InboundMessage` to reuse the real `Medium` enum (D7) instead of redefining a second,
  smaller one (the earlier draft only had `TELEGRAM`/`WHATSAPP`, missing `GSM`/`Viber`/`email`
  from the real enum — exactly the drift the model-source review was trying to prevent).
- **Alternatives considered**: leave generation output where it is and have the gateway
  import it via a `sys.path` hack (matches how `tests/conftest.py` currently adds `src/` to
  `sys.path`) — rejected as a workaround that doesn't fix the underlying unreachability for
  any other future consumer, just this one call site. Scoping the relocation as its own
  separate change — considered, but the gateway is the first real consumer that needs it, and
  deferring would mean building `ChannelRef`/`Medium` reuse against a path that doesn't exist
  yet.
- **Scope boundary**: only the `pydantic` generation target moves. OWL/SHACL/JSON
  Schema/diagrams/Cypher/neomodel outputs stay under `model/generated/` — untouched. The
  single-file output (`hulubul_models.py`, one file for the whole merged schema) is also kept
  as-is; splitting into one generated file per LinkML module (the Meaningfy-recommended
  per-module pattern) is a further, separate improvement, not taken on here.

## Anti-Patterns (DO NOT)

Specific to this bounded context (`src/hulubul/channel_gateway/` and the new
`hulubul.core.models.domain` package) — not generic advice.

| ❌ Don't | ✅ Do instead | Why |
|---|---|---|
| Redefine `Medium` or `Channel` as a local dataclass anywhere under `channel_gateway/` | Import `Medium` from `hulubul.core.models.domain.hulubul_models`; use `ChannelRef` only for the `(medium, systemID)` identity pair, never redeclare `Channel` | Caused two real near-duplications while designing this change: a `Medium` enum missing `GSM`/`Viber`/`email`, and a `Channel` colliding with the LinkML entity (D7/D9) |
| Put HTTP/API calls (LangFlow, Telegram, WhatsApp) in `services/` or `models/` | HTTP/API clients live only in `adapters/` (`adapters/langflow_client.py`, `adapters/telegram_adapter.py`) | Violates cosmic-python's dependency direction; `models/`/`services/` must stay testable with no real I/O — caught once already when `LangflowClient` was mis-placed in the first design pass (D7) |
| Construct a full `Channel(id=..., validationStatus=...)` anywhere in gateway code | Use `ChannelRef(medium, system_id)`; let `resolve_channel_actor` construct the real `Channel` where a graph node backs it | `Channel.id` is a Neo4j graph node identity that doesn't exist pre-persistence — a gateway-minted id risks colliding with the real one once resolution runs (D7) |
| Derive `session_id` from anything other than `(medium, systemID)` — e.g. `request_id`, a random UUID per message | `session_id = f"{medium}:{systemID}"`, pure and deterministic, computed locally from the inbound payload | `OperationalConversationBinding` lookups need the same `session_id` across a channel's messages to hit the same binding — non-determinism silently breaks routing continuity (D4) |
| Reply to a stored default contact point instead of the channel a message physically arrived on | `adapter.send(inbound.system_id, ...)` always targets the exact `system_id` of the triggering `InboundMessage` | A prior session's decision requires replies go to the channel of arrival, never `hasMainContactPoint` — misrouting could leak a conversation to the wrong chat |
| Let a LangFlow or channel-send failure raise unhandled inside `relay_inbound_message` | Catch and log both failure points (`langflow_client.run` returning `None`, `adapter.send` raising); never propagate | `entrypoints/telegram_bot.py` is a long-running process — one message's failure must not take down handling for every subsequent message (`langflow-message-relay` spec) |
| Give `WhatsAppAdapter` a working implementation, or run `tests/e2e/` in CI, "since we're here" | `WhatsAppAdapter` stays a `NotImplementedError` stub; `tests/e2e/` stays local/manual-only | Both are explicit Non-Goals — a working WhatsApp adapter pulls in 360dialog integration and template/opt-in accounting deliberately deferred; live-Telegram-in-CI adds secret management and flakiness risk for no current need |

## Test Case Specifications

### Unit Tests Required

| Test ID | Component | Input | Expected Output | Edge Cases |
|---|---|---|---|---|
| TC-001 | `derive_session_id` ([plan.md Task 3](plan.md#task-3-models-channelref-and-derive_session_id)) | `(Medium.Telegram, "123456789")` called twice | Identical string both times | `(Medium.Telegram, "X")` vs `(Medium.WhatsApp, "X")` (same digits, different medium) must not collide |
| TC-002 | `ChannelRef` ([plan.md Task 3](plan.md#task-3-models-channelref-and-derive_session_id)) | `ChannelRef(medium=Medium.WhatsApp, system_id="+1555...")` | A two-field object; no `id`/`validationStatus` attributes exist on the type at all | N/A — the type structurally cannot hold persistence fields, by design |
| TC-003 | `TelegramAdapter.receive` ([plan.md Task 5](plan.md#task-5-adapters-telegramadapter)) | aiogram `Message` with `reply_to_message=None` | `InboundMessage.reply_to_message_id is None` | A `reply_to_message` present sets the field to its string `message_id` |
| TC-004 | `WhatsAppAdapter` ([plan.md Task 6](plan.md#task-6-adapters-whatsappadapter-stub)) | any call to `.receive()`/`.send()` | Raises `NotImplementedError` | Static: `WhatsAppAdapter()` assigned to a `ChannelPort`-typed variable passes mypy |
| TC-005 | `LangflowClient.run` ([plan.md Task 7](plan.md#task-7-adapters-langflowclient)) | LangFlow returns HTTP 500 | Returns `None`, no exception raised | Response with unexpected JSON shape (missing `outputs` key) also returns `None` |
| TC-006 | `relay_inbound_message` ([plan.md Task 8](plan.md#task-8-services-relay_message)) | `langflow_client.run` returns `None` | `adapter.send` is never awaited | `adapter.send` itself raises → exception is caught and logged, not propagated |

### Integration Tests Required

| Test ID | Flow | Setup | Verification | Teardown |
|---|---|---|---|---|
| IT-001 | Gateway → LangFlow, feature-tier ([plan.md Task 12](plan.md#task-12-feature-tests-gherkin-langflow-connected)) | Synthetic `InboundMessage` via mocked `ChannelPort`, real `relay_inbound_message` orchestration | LangFlow client receives the correct `session_id`/`medium`/`systemID` (asserted on mock call args) | None — fully mocked, no real external state |
| IT-002 | Full round trip, e2e ([plan.md Task 13](plan.md#task-13-e2e-tests-localmanual-only-excluded-from-ci)) | Real Telegram test bot sends a message; local LangFlow stack running | Test bot receives a reply within the polling window | None — Telegram test bot holds no state to clean |
| IT-003 | Telegram-adapter isolation, e2e ([plan.md Task 13](plan.md#task-13-e2e-tests-localmanual-only-excluded-from-ci)) | Real Telegram test bot; LangFlow response stubbed | Send/receive contract verified independent of LangFlow's actual behavior | None |

## Error Handling Matrix

### External Service Errors

| Error Type | Detection | Response | Fallback | Logging | Alert |
|---|---|---|---|---|---|
| LangFlow Run API unreachable or 5xx | `httpx.HTTPError` in `LangflowClient.run` | `run()` returns `None` | `relay_inbound_message` logs and sends no reply (see User-Facing Errors below) | WARNING | None wired in this change — no alerting pipeline exists yet; tracked as a Risk below |
| LangFlow response has an unexpected shape | `KeyError`/`IndexError`/`TypeError` parsing `response.json()` in `LangflowClient.run` | `run()` returns `None` | Same as above | WARNING | Same as above |
| Telegram `sendMessage`/`sendPhoto` fails (e.g. bot blocked by the user) | Exception raised by aiogram inside `TelegramAdapter.send()` | Caught in `relay_inbound_message` (not in the adapter — see Anti-Patterns) | Message is dropped, not retried | `logger.exception` (ERROR + traceback) | None wired in this change |
| Telegram webhook `secret_token` mismatch | aiogram's `SimpleRequestHandler` validates the header internally | Request rejected with 401 before reaching the dispatcher | N/A — not a real inbound message | Whatever aiogram's webhook handler logs by default; not separately configured in this change | None |

### User-Facing Errors

| Error Type | User Message | Code | Recovery Action |
|---|---|---|---|
| LangFlow unavailable or errors | **None is sent** — the sender's message is silently unanswered | N/A (no HTTP-style code concept in a chat UI) | Sender can resend later; **this is a known, currently-accepted gap, not a resolved UX decision — see Risks below and Open Questions** |
| Telegram delivery fails (bot blocked, chat deleted, etc.) | None — nothing can be sent back to a channel that just rejected delivery | N/A | None available from the gateway's side |
| WhatsApp channel used | Unreachable in this change — `WhatsAppAdapter` has no live send/receive path | N/A | N/A — out of scope (Non-Goals) |

## Risks / Trade-offs

- [Risk] Single-active-request session binding will need rework once concurrent-request
  support lands (Phase 3 §6.1) → Mitigation: D4 documents the future shape as a design note
  now, so the gateway's `session_id` derivation and `ChannelPort` contract don't assume
  anything that would need to change (session_id stays a pure function of channel identity,
  not of request state).
- [Risk] Cross-channel identity merge (same person, Telegram + WhatsApp) has no mechanism —
  a future WhatsApp adapter will surface this gap in practice → Mitigation: explicitly
  out of scope here; flagged for its own design work before a real WhatsApp adapter ships.
- [Trade-off] One gateway container instead of per-channel containers trades fault isolation
  for simplicity → accepted because WhatsApp isn't live code in this change; revisit when it
  is.
- [Trade-off] Local webhook testing via ngrok adds a moving part (tunnel URL registration,
  ngrok account/session limits) to local dev → accepted per explicit user preference to
  exercise the real webhook code path, not just polling.
- [Risk] `WhatsAppAdapter` stub could silently drift out of sync with 360dialog's real payload
  shape since it's never exercised against a live endpoint → Mitigation: stub's structure
  should be reviewed against 360dialog's published webhook/API schema at design time, not
  just invented; flagged for the tasks breakdown.
- [Risk] The original reason `model/generated/pydantic/**` was excluded from
  `check-model-generated`'s staleness check (commit `7a4981e`) was not re-verified before
  relocating it (D9) → Mitigation: the new location keeps the same exclusion (no behavior
  change), so this isn't a new risk introduced by the move — but re-enabling the freshness
  check on the new path later requires first confirming `gen-pydantic`'s output is actually
  deterministic across runs, not assuming it now.
- [Risk] `Channel.id` (D9/D7) is Neo4j's graph node identity, assigned only at persistence —
  no code in this change mints or predicts it → Mitigation: `ChannelRef` deliberately never
  carries an `id`; the full `Channel` is constructed exclusively inside `resolve_channel_actor`
  where a real node backs it, so there is no code path where a fake/placeholder `id` could
  leak out as if it were real.
- [Risk] When LangFlow is unreachable or errors, the sender's message is silently unanswered
  — no fallback "we're having trouble" message is sent (Error Handling Matrix, User-Facing
  Errors) → Mitigation: none yet; this is a known, currently-accepted gap, not a resolved UX
  decision. Whether to add a fallback message is an open question (below), deliberately not
  decided here to avoid scope creep into LangFlow-side or gateway-side messaging policy.

## Migration Plan

Mostly net-new (a bounded context and an infra service); the one existing-system change is
relocating `make pydantic`'s output (D9) — `Makefile`, `AGENTS.md`, and the old
`model/generated/pydantic/hulubul_models.py` are modified/removed, but this only changes
*where* already-generated content lives, not what it contains or how it's produced; no
domain flows, schema, or deployed code depend on the old path today. Deployment order for a
fresh environment:
1. `make up` (existing stack: Neo4j, LangFlow, Postgres, mcp-neo4j) — unchanged.
2. New `channel-gateway` service builds and starts after `langflow` is healthy (compose
   `depends_on`).
3. `GATEWAY_MODE=polling` is the safe default for first bring-up (no tunnel/webhook
   registration required); switch to `webhook` once the `ngrok` service and Telegram webhook
   registration are verified working locally.
Rollback: `docker compose stop channel-gateway` — no shared state to unwind, since the
gateway holds no persistence layer of its own (Neo4j via `resolve_channel_actor` remains the
only store of record).

## Open Questions

- Exact replacement data shape for `OperationalConversationBinding` under concurrent requests
  (Phase 3 scope, not this change) — remains unspecified anywhere in the architecture docs.
- Which use case(s) in `architecture/use-cases/` the `tests/feature/` Gherkin scenarios should
  trace back to — needs to be resolved when writing the actual `.feature` files (tasks phase),
  not here.
- Whether `WhatsAppAdapter`'s stub payload shape needs a real 360dialog API-doc review before
  being written, or can stay a best-effort placeholder until the real adapter is built.
- Whether the gateway should send a fallback user-facing message when LangFlow is unreachable
  (Error Handling Matrix, User-Facing Errors; Risks above) — currently the sender gets
  silence, which is an accepted gap, not a decision.

## References

### Implementation
| Topic | Document | Section |
|---|---|---|
| Full micro-task implementation plan | [plan.md](plan.md) | Tasks 0–14 |
| Checkbox task breakdown | [tasks.md](tasks.md) | Groups 0–10 |
| Raw brainstorm decision log (Q1–Q8) | [brainstorm.md](brainstorm.md) | Decision chain |

### Specs
| Capability | Document | Anchor |
|---|---|---|
| `ChannelPort`, `TelegramAdapter`, `WhatsAppAdapter` | [specs/channel-gateway-adapter/spec.md](specs/channel-gateway-adapter/spec.md) | `#added-requirements` |
| Session derivation, LangFlow relay | [specs/langflow-message-relay/spec.md](specs/langflow-message-relay/spec.md) | `#added-requirements` |
| Deployment, config, test tiers | [specs/gateway-deployment-setup/spec.md](specs/gateway-deployment-setup/spec.md) | `#added-requirements` |
| Domain model import path | [specs/domain-model-reachability/spec.md](specs/domain-model-reachability/spec.md) | `#added-requirements` |

### Architecture (repo-level, outside this change)
| Topic | Document | Section |
|---|---|---|
| Channel-abstracted messaging decision | [../../../architecture/decisions/README.md](../../../architecture/decisions/README.md) | `#adr-003--channel-abstracted-messaging-telegram-dev-whatsapp-prod-l1` |
| Per-provider adapter decision | [../../../architecture/decisions/README.md](../../../architecture/decisions/README.md) | `#adr-008--channel-gateway-with-per-provider-adapters-l2` |
| Generated domain models registration | [../../../architecture/decisions/README.md](../../../architecture/decisions/README.md) | `#adr-019--generated-domain-models-land-in-an-importable-package-l2` (added by Task 0, Step 8) |
| Phase 1 flow-level Main Router (PREFETCH step, routing rules table) | [../../../architecture/agentic-system-blueprint-phase-1.md](../../../architecture/agentic-system-blueprint-phase-1.md) | `#4-lf-00-main-router` |
| Target-architecture Router Agent spec (`resolve_channel_actor`, `get_request_routing_context`) | [../../../architecture/agentic-system-blueprint.md](../../../architecture/agentic-system-blueprint.md) | `#81-router-agent` |
| Phase 3 field-pilot scope | [../../../architecture/incremental-system-development-strategy.md](../../../architecture/incremental-system-development-strategy.md) | `#6-phase-3---field-pilot` |

All anchors above were verified against the actual heading text in each target file (not
guessed) — GitHub's slugifier lowercases, strips punctuation other than existing hyphens/
underscores, and joins words with single hyphens; `en`/`em`-dashes in headings (e.g. `—`)
become double hyphens once the surrounding spaces are joined.
