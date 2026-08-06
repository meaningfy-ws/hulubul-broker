## Why

Hulubul has no real communication channel yet — Phase 1 injects trusted actor context via a
test harness. Phase 3 (Field Pilot) requires a real Telegram gateway before any field
testing can start, and the adapter/gateway boundary has already been explored and decided
across prior sessions (`architecture/task-2-frameworks-exploration.md`, ADR-003/ADR-008) but
never built. Building it now, ahead of Phase 1's completion, de-risks the Phase 3 cutover
without committing to WhatsApp or to redesigning concurrent-session binding yet.

## What Changes

**New: Telegram channel gateway**
- From: no real channel; trusted actor context injected by a test harness/API (Phase 1).
- To: a standalone gateway process (`src/hulubul/channel_gateway/`) that owns the Telegram
  Bot API connection via aiogram 3.x, derives a deterministic `session_id`, attaches the
  trusted `(medium, systemID)` channel identity, and calls LangFlow's Run API — the real
  version of the Phase 1 test-harness injection seam.
- Reason: unblocks Phase 3 Field Pilot without waiting on the rest of Phase 3's scope
  (reminder scheduling, Recovery Agent, concurrent-request binding redesign).
- Impact: non-breaking addition; no existing flows or code change.

**New: `ChannelPort` abstraction with a WhatsApp stub**
- From: no channel-agnostic interface exists in code (only documented as ADR-008's decision).
- To: one `ChannelPort` interface (`adapters/channel_port.py`) implemented by `TelegramAdapter`
  now and an unimplemented `WhatsAppAdapter` stub, proving the interface fits WhatsApp's
  shape without building live WhatsApp integration.
- Reason: keeps the adapter boundary honest to ADR-008 without over-building WhatsApp before
  it's needed.
- Impact: non-breaking; WhatsApp stub raises `NotImplementedError`, not callable in practice.

**New: LinkML-generated domain models become importable from `src/hulubul/`**
- From: `make pydantic` writes to `model/generated/pydantic/hulubul_models.py`, which is not
  part of the installed `hulubul` package — nothing under `src/hulubul/` can import `Channel`,
  `Medium`, etc. without a path hack.
- To: `make pydantic` writes to `src/hulubul/core/models/domain/hulubul_models.py` instead —
  still fully generated, never hand-edited, just reachable by a normal import.
- Reason: surfaced directly by building this gateway — its `ChannelRef`/`InboundMessage`
  models need to reuse the real `Medium` enum rather than redefine a second, smaller one (the
  first draft was missing `GSM`/`Viber`/`email`), which isn't possible until the generated
  models are importable.
- Impact: non-breaking; only the `pydantic` generation target's output location changes.
  OWL/SHACL/JSON Schema/diagrams/Cypher/neomodel outputs are untouched.

**New: local deployment and testing infrastructure**
- From: `infra/docker-compose.yaml` has no channel gateway service.
- To: a new `channel-gateway` compose service (own Dockerfile), an `ngrok` tunnel service for
  local webhook-mode testing, and three test suites (`tests/unit/`, `tests/feature/` +
  `tests/features/*.feature`, `tests/e2e/`) covering the dependency states from fully mocked
  through real-Telegram-and-real-LangFlow.
- Reason: the change was explicitly scoped to include local deployment, not just code.
- Impact: non-breaking; new optional Poetry dependency group (`gateway`, aiogram) alongside
  existing `test`/`quality`/`integration`/`langflow` groups.

**Explicitly out of scope**
- Redesigning `OperationalConversationBinding` for concurrent requests per channel (documented
  as a design note only, per the brainstorm's Q1 decision).
- Cross-channel identity merge (Telegram `chat_id` vs. WhatsApp phone number as `systemID`).
- Live WhatsApp integration (360dialog account/BSP onboarding).
- Running live-Telegram tests in CI (local/manual-only for now).

## Capabilities

### New Capabilities
- `domain-model-reachability`: relocating LinkML-generated Pydantic domain models into an
  importable package (`hulubul.core.models.domain`) so bounded contexts can reuse real domain
  types instead of redefining them.
- `channel-gateway-adapter`: the `ChannelPort` interface, `TelegramAdapter` (aiogram-backed,
  polling and webhook modes), and the `WhatsAppAdapter` stub — inbound message reception and
  outbound message sending for a channel.
- `langflow-message-relay`: deterministic `session_id` derivation, trusted channel-identity
  attachment, the LangFlow Run API client, and the orchestration that relays an inbound
  message to LangFlow and the reply back out.
- `gateway-deployment-setup`: the local Docker Compose service, Telegram bot configuration
  (via @BotFather, webhook secret token, privacy mode), the local ngrok tunnel for webhook
  testing, and the three-tier test suite (unit/feature/e2e).

### Modified Capabilities
(none — no existing specs in `openspec/specs/` yet)

## Impact

- New code: `src/hulubul/channel_gateway/` (models, adapters, services, entrypoints layers).
- Relocated (not changed in content): `make pydantic` output moves from
  `model/generated/pydantic/hulubul_models.py` to
  `src/hulubul/core/models/domain/hulubul_models.py`; `Makefile` and `AGENTS.md` updated
  accordingly.
- New architecture docs: `architecture/channel-gateway-blueprint.md` (design, elaborating
  ADR-003/ADR-008), `architecture/channel-gateway-runbook.md` (deployment/configuration/testing).
- New infra: `infra/channel-gateway/Dockerfile`, new services in `infra/docker-compose.yaml`
  (`channel-gateway`, `ngrok`).
- New dependency: aiogram 3.x, under a new optional Poetry group `gateway`.
- New tests: `tests/unit/hulubul/channel_gateway/`, `tests/unit/hulubul/core/models/` (domain
  reachability), `tests/feature/` (new top-level dir), `tests/features/*.feature` (new Gherkin
  files), `tests/e2e/` (new top-level dir, excluded from CI).
- No changes to existing Phase 1 flows, LF-00/LF-70, or the LinkML domain schema itself
  (`model/linkml/hulubul_channel.yaml` is unchanged — only where its generated Pydantic output
  is written changes).
