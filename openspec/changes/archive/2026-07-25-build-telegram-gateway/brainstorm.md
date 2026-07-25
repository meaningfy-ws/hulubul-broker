<!--
Raw capture of superpowers:brainstorming output.
-->

## Background

Prior sessions (see project memory) explored Telegram/WhatsApp connector architecture ahead
of schedule — Phase 3 (Field Pilot) territory per `architecture/incremental-system-development-strategy.md`
§6, while the active OpenSpec change (`deliver-phase-1-request-intake-thread`) covers Phase 1.
Findings already established before this brainstorm:

- Two architectural shapes for a channel adapter exist: (A) LangFlow-native component wired
  to LangFlow's own webhook trigger, vs (B) an external gateway process. Shape B was already
  selected in `architecture/task-2-frameworks-exploration.md` (Telegram dev → aiogram 3.x
  Bot API; WhatsApp prod → 360dialog EU BSP; WAHA/unofficial WhatsApp APIs disqualified) via
  a `ChannelPort` interface, one implementation per channel.
- Two prior-art repos read and found not reusable: `fauzaanu/langflow-bot/bot.py` (proves
  shape B is ~90 lines of glue, but no session_id derivation, hardcoded flow tweaks, no error
  handling) and `Empreiteiro/langflow-factory/components/whatsapp_and_others` (all four
  components — Telegram/Slack/WhatsApp-Evolution/WhatsApp-Z-API — are outbound-only LangFlow
  Components, none handle inbound webhooks).
- Session/routing centralization already exists inside LangFlow (`LF-00 Main Router` +
  `LF-70 Data Access`, backed by Neo4j's `OperationalConversationBinding(sessionId,
  activeRequestId)`), not the gateway. The gateway's job is narrow: derive a session_id
  locally (no round-trip) and attach the trusted `(medium, systemID)` channel identity so
  `resolve_channel_actor` can resolve it — the gateway is the actual trust boundary (holds
  the authenticated bot token).
- `Channel.systemID` (`model/linkml/hulubul_channel.yaml`) is not a phone number for
  Telegram — it's `chat_id`. WhatsApp's systemID ≈ phone number. Phone number can't be the
  cross-channel identity-merge key.
- User-caught correction: `session_id = f(medium, systemID)` conflates session with channel.
  Holds for sequential reuse (binding frees when a request closes) but breaks for concurrent
  requests on one channel — `OperationalConversationBinding` is explicitly Phase-1-only per
  `incremental-system-development-strategy.md` §3.1, flagged for reconsideration when
  multiple active requests per conversation appear (Phase 3 §6.1 scope). Mechanism already
  named for resolving which concurrent request a message belongs to: `resolve_reply_reference`
  (deterministic, via the channel's native reply-to-message feature) falling back to
  `ask_request_disambiguation`. The actual Phase-3 replacement binding shape is not yet
  specified anywhere.
- ADR-008 ("Channel gateway with per-provider adapters") and ADR-003 ("Channel-abstracted
  messaging; Telegram dev, WhatsApp prod") already make the top-level architecture decision
  this change operationalizes — no new ADR needed, but a new detailed design doc under
  `architecture/` does.

## Decision chain (Q1–Q8)

**Q1 — Should this change also redesign `OperationalConversationBinding` for concurrent
requests, or stay out of it?**
Decided: **design-aware, but implement single-active-request only.** Build the gateway
against the current Phase 1 binding shape; document the future concurrent-request shape as
a design note so the gateway's session_id/interfaces don't paint us into a corner, but ship
only the single-active-request version now. Full concurrent-binding redesign is a separate,
later change.

**Q2 — Which Telegram library: aiogram 3.x or python-telegram-bot?**
Decided: **aiogram 3.x**, matching the earlier `task-2-frameworks-exploration.md` decision.
(python-telegram-bot was only used by the prior-art skeleton, not independently chosen.)

**Q3 — How much WhatsApp should actually get built now vs. just designed for?**
Decided: **interface + a stub/skeleton WhatsApp adapter.** `ChannelPort` interface defined
so a WhatsApp adapter can be added later without touching the gateway core or LangFlow
contract, plus an unimplemented `WhatsAppAdapter` class (raises `NotImplementedError` on
send/receive bodies) that proves the interface actually fits WhatsApp's shape (360dialog
payloads) without full send/receive logic. No live WhatsApp code, no 360dialog account
integration in this change.

**Q4 — Should tests hitting the real Telegram API run in CI, or stay local/manual-only?**
Decided: **local/manual-only for now.** No Telegram test-bot token as a CI secret; no
flakiness/rate-limit risk added to the GitHub Actions pipeline. Documented (how to run with
a test bot) but excluded from `make ci-static`.

**Q5 — Local dev connection mode: polling only, or also webhook via a local tunnel?**
Decided: **support both — webhook via a tunnel locally too.** Rather than deferring webhook
mode entirely to a future real deployment, add a tunnel service to the local compose stack
so the full webhook code path is exercisable locally, not just polling.

**Q6 — Container topology: one gateway container with multiple adapters, or one container
per channel?**
Decided: **one gateway container hosting all channel adapters**, sibling to `mcp-neo4j` in
`infra/docker-compose.yaml`. Single Dockerfile/service; Telegram (aiogram, polling or
webhook per `GATEWAY_MODE`) and the WhatsApp stub both live in one process. Simpler to
deploy; matches the single `ChannelPort` interface design. Revisit only if a real
scaling/blast-radius need emerges (WhatsApp isn't live code yet anyway).

**Q7 — Where should the new architecture documentation live?**
Decided: **split into two docs** — `architecture/channel-gateway-blueprint.md` (design:
`ChannelPort` interface, `TelegramAdapter`/aiogram, `WhatsAppAdapter` stub, deployment
topology, session_id derivation, elaborating ADR-003/ADR-008) and
`architecture/channel-gateway-runbook.md` (deployment/configuration/testing how-to: Telegram
bot setup via @BotFather, webhook secret token, local compose + tunnel, WhatsApp config as a
forward-looking placeholder).

**Q8 — Module layout and naming (raised after the first design pass; corrected using the
`cosmic-python` and `bdd-gherkin` Meaningfy skills, since the first pass mis-layered two
things):**

Corrections made against the cosmic-python canonical layer catalogue:
- The LangFlow Run API client is infrastructure — a "gateway/client" per the `adapters/`
  layer definition — not a `services/` orchestration; moved from `services/langflow_client.py`
  to `adapters/langflow_client.py`.
- `session_id` derivation (`f(medium, systemID)`) is pure domain logic, no I/O — belongs in
  `models/`, not `services/`.
- `ChannelPort` (the abstract interface) and the value objects flowing across it
  (`InboundMessage`, `TextMessage`, `MediaMessage`) split: the abstract port/interface itself
  lives in `adapters/` (matching the cosmic-python book's convention of defining abstractions
  like `AbstractRepository` inside the adapters layer that implements them), while the value
  objects are pure domain data — `models/message.py`.
- The process entrypoint was first named `aiogram_bot.py` (naming after the concrete SDK,
  echoing the cosmic-python book's `flask_app.py`/`redis_eventconsumer.py` convention of
  naming entrypoints after their technology). **User corrected this**: rename to
  `telegram_bot.py` — hide the aiogram/SDK dependency behind the stable channel concept
  (Telegram) rather than exposing a swappable implementation detail in the module name.

Final layout:
```
src/hulubul/channel_gateway/
  models/
    message.py          # InboundMessage/TextMessage/MediaMessage value objects (pure, no I/O)
    channel.py           # Channel value object + derive_session_id(medium, systemID) — pure function
  adapters/
    channel_port.py       # ChannelPort ABC — the interface adapters implement
    telegram_adapter.py   # TelegramAdapter(ChannelPort), aiogram-backed
    whatsapp_adapter.py   # WhatsAppAdapter(ChannelPort) stub
    langflow_client.py    # LangFlow Run API client
  services/
    relay_message.py      # orchestrates: adapter.receive() -> langflow_client.run() -> adapter.send()
  entrypoints/
    telegram_bot.py        # process entrypoint, wires aiogram Dispatcher -> services (polling or webhook via GATEWAY_MODE)
```

Testing reconciled to 3 named suites (unit / feature / e2e), collapsing the original
4-state dependency matrix (LangFlow connected/disconnected × Telegram connected/disconnected)
into this simpler taxonomy per user preference:

- **unit** (`tests/unit/`) — models + adapters with mocks, nothing real, runs in CI always.
- **feature** (`tests/features/*.feature` Gherkin, new `tests/feature/` step-definitions,
  pytest-bdd) — real local LangFlow container, synthetic inbound payloads (no real Telegram).
  This is the "LangFlow connected, Telegram disconnected" layer from the original 4-state
  matrix. Per the `bdd-gherkin` skill: `.feature` files trace back to a use case in
  `architecture/use-cases/` where a catalogue exists; runs in CI.
- **e2e** (new `tests/e2e/`, local/manual only, not CI) — real Telegram test bot + real local
  LangFlow, dev/staging-like full stack up. The "Telegram connected, LangFlow disconnected"
  isolation case (from the original 4-state matrix) becomes a scenario inside e2e (LangFlow
  response stubbed) rather than a separate top-level suite.

Deployment: `infra/channel-gateway/Dockerfile` + new compose service, env-configured
(`TELEGRAM_BOT_TOKEN`, `LANGFLOW_API_URL`, `LANGFLOW_FLOW_ID`, `GATEWAY_MODE=polling|webhook`).
Webhook mode adds an **ngrok** tunnel service to `docker-compose.yaml` (user preference, used
in a colleague's project previously) so the full webhook path is exercisable locally.

Telegram configuration to document in the runbook: creating a bot via @BotFather, obtaining
the token, setting Telegram's webhook `secret_token` for request validation, disabling bot
privacy mode. WhatsApp configuration documented as a forward-looking placeholder only.

## Outcome

Design approved by the user across the architecture overview, module layout, testing
matrix, and deployment sections (with the two corrections in Q8 applied). Proceeding to
`proposal.md` / `design.md` / `specs/` / `tasks.md` / `plan.md` artifacts for the
`build-telegram-gateway` OpenSpec change.
