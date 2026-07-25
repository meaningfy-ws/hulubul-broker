## 0. Domain model reachability (prerequisite)

- [x] 0.1 Relocate `make pydantic`'s output from `model/generated/pydantic/hulubul_models.py`
      to `src/hulubul/core/models/domain/hulubul_models.py`, so generated domain models
      (`Channel`, `Medium`, etc.) are importable from `hulubul.core.models.domain` instead of
      unreachable from `src/hulubul/` entirely, per `domain-model-reachability` spec.
- [x] 0.2 Update the `check-model-generated` Makefile target's exclusion paths for the new
      location, preserving the current (unverified-reason) exclusion of pydantic output from
      the staleness check.
- [x] 0.3 Update `AGENTS.md`'s generated-artifacts convention note to cover the new location.
- [x] 0.4 Remove the old `model/generated/pydantic/` output.
- [x] 0.5 Add `ADR-019` to `architecture/decisions/README.md` (table row + full entry)
      documenting this decision — it's a system-wide change (every future bounded context
      benefits), not gateway-specific, so it belongs in the ADR registry alongside
      ADR-005/ADR-015/ADR-016, not only in this change's own design.md.

## 1. Architecture documentation

- [x] 1.1 Write `architecture/channel-gateway-blueprint.md` using the `meaningfy-core:technical-writing`
      skill: `ChannelPort` interface, module layout, session_id derivation, deployment
      topology — elaborating ADR-003/ADR-008 per design.md D1–D9 (see plan.md Task 10 Step 1
      for the exact section-by-section source mapping).
- [x] 1.2 Write `architecture/channel-gateway-runbook.md` using the `meaningfy-core:technical-writing`
      skill: Telegram bot setup via @BotFather, webhook secret token, privacy mode, local
      Compose + ngrok instructions, WhatsApp configuration placeholder, per
      `gateway-deployment-setup` spec (see plan.md Task 10 Step 2 for the exact
      section-by-section source mapping).
- [x] 1.3 Cross-link both new docs from `architecture/README.md` and note the Phase 3
      "prepare later" scope this change pulls forward, per design.md Context.

## 2. Project scaffolding

- [x] 2.1 Add a new optional Poetry dependency group `gateway` (aiogram 3.x) to
      `pyproject.toml`, following the existing `test`/`quality`/`integration`/`langflow`
      group pattern; run `poetry lock`.
- [x] 2.2 Create the `src/hulubul/channel_gateway/` package skeleton
      (`models/`, `adapters/`, `services/`, `entrypoints/`, each with `__init__.py`).
- [x] 2.3 Add the new bounded context to `.importlinter` contracts so `models/` cannot import
      `adapters/`/`services/`/`entrypoints/`, and `adapters/` cannot import `services/`/
      `entrypoints/`, per the cosmic-python dependency direction (design.md D7).

## 3. Models layer (pure domain, no I/O)

- [x] 3.1 Implement `models/message.py`: `InboundMessage`, `TextMessage`, `MediaMessage`
      value objects, reusing `Medium` from `hulubul.core.models.domain.hulubul_models` (task
      0.1) rather than redefining it, per `channel-gateway-adapter` spec.
- [x] 3.2 Implement `models/channel.py`: `ChannelRef` value object (medium + systemID only —
      an identity/reference distinct from the full LinkML-generated `Channel` entity, per
      design.md D7) and `derive_session_id(medium, systemID) -> str`, per
      `langflow-message-relay` spec "Deterministic session_id derivation".
- [x] 3.3 Unit tests for both modules in `tests/unit/hulubul/channel_gateway/models/`,
      including the same-channel-same-session_id and different-channels-never-collide
      scenarios from the spec.

## 4. Adapters layer

- [x] 4.1 Implement `adapters/channel_port.py`: the `ChannelPort` ABC (`receive()`, `send()`),
      per `channel-gateway-adapter` spec "ChannelPort interface".
- [x] 4.2 Implement `adapters/telegram_adapter.py`: `TelegramAdapter(ChannelPort)` using
      aiogram, supporting both polling and webhook modes per `GATEWAY_MODE`, normalizing
      inbound updates into `InboundMessage` and sending `TextMessage` via `sendMessage`.
- [x] 4.3 Implement `adapters/whatsapp_adapter.py`: `WhatsAppAdapter(ChannelPort)` stub,
      method bodies raising `NotImplementedError`, shaped against 360dialog's published
      payload structure per design.md's open question on stub fidelity.
- [x] 4.4 Implement `adapters/langflow_client.py`: `LangflowClient` wrapping LangFlow's Run
      API (`session_id`, `medium`, `systemID`, message text), per `langflow-message-relay`
      spec "LangFlow Run API client isolates the HTTP integration".
- [x] 4.5 Unit tests for all four adapters in
      `tests/unit/hulubul/channel_gateway/adapters/`, mocking aiogram and HTTP calls —
      including the mypy structural-typing scenario for `WhatsAppAdapter` against
      `ChannelPort`.

## 5. Services layer

- [x] 5.1 Implement `services/relay_message.py`: orchestrates
      `adapter.receive() → derive_session_id() → langflow_client.run() → adapter.send()`,
      replying to the same channel/identity the inbound message arrived on, per
      `langflow-message-relay` spec "Reply relay back to the originating channel".
- [x] 5.2 Add error handling so a LangFlow call failure OR a channel-send failure (e.g.
      Telegram API rejects the reply) is logged, not raised, per `langflow-message-relay`
      spec "A LangFlow error does not crash the gateway process" — both failure points must
      be caught, not just the LangFlow one.
- [x] 5.3 Unit tests in `tests/unit/hulubul/channel_gateway/services/`, with `ChannelPort` and
      `LangflowClient` mocked.

## 6. Entrypoint

- [x] 6.1 Implement `entrypoints/telegram_bot.py`: process entrypoint wiring aiogram's
      Dispatcher to `services/relay_message.py`, reading `GATEWAY_MODE` and other
      configuration from environment variables.
- [x] 6.2 Contract-level test(s) in `tests/unit/hulubul/channel_gateway/entrypoints/`
      verifying argument/config parsing and startup wiring, without starting a real bot
      connection.

## 7. Feature tests (Gherkin, LangFlow-connected)

- [x] 7.1 Identify or add the relevant use case(s) in `architecture/use-cases/` that the
      gateway's Gherkin scenarios should trace back to, per design.md's open question.
- [x] 7.2 Write `tests/features/telegram_message_relay.feature` (business-language scenarios:
      first message creates a draft request, a reply continues an existing conversation,
      etc.), using the `bdd-gherkin` skill conventions.
- [x] 7.3 Implement `tests/feature/` step-definitions wiring the `.feature` file to a real
      local LangFlow container and a synthetic `InboundMessage` (no real Telegram), per
      `gateway-deployment-setup` spec "Three-tier local test suite".

## 8. Local deployment

- [x] 8.1 Write `infra/channel-gateway/Dockerfile`.
- [x] 8.2 Add the `channel-gateway` service to `infra/docker-compose.yaml`
      (`TELEGRAM_BOT_TOKEN`, `LANGFLOW_API_URL`, `LANGFLOW_FLOW_ID`, `GATEWAY_MODE`,
      `depends_on: langflow` healthy), per `gateway-deployment-setup` spec.
- [x] 8.3 Add the `ngrok` service to `infra/docker-compose.yaml` and wire automatic webhook
      URL registration on gateway startup when `GATEWAY_MODE=webhook`.
- [x] 8.4 Update `infra/.env.example` with the new required variables.
- [x] 8.5 Update `AGENTS.md`'s Docker command table if a new `make` target is added for the
      gateway service.

## 9. e2e tests (local/manual only)

- [x] 9.1 Write `tests/e2e/test_telegram_roundtrip.py`: real Telegram test bot + real local
      LangFlow, full round trip, per `gateway-deployment-setup` spec "e2e suite is excluded
      from CI but documented".
- [x] 9.2 Write `tests/e2e/test_telegram_adapter_isolation.py`: real Telegram test bot, real
      local LangFlow, but with a stubbed LangFlow response, isolating the Telegram
      send/receive contract (the "Telegram connected, LangFlow disconnected" case from the
      original brainstorm matrix).
- [x] 9.3 Document how to run `tests/e2e/` locally with a test-bot token in the runbook.

## 10. CI and final verification

- [x] 10.1 Update CI configuration to run `tests/unit/` and the `tests/feature/`
      step-definitions, explicitly excluding `tests/e2e/`.
- [x] 10.2 Run `make check-architecture` (import-linter) and confirm no layering violations.
- [x] 10.3 Run the full unit + feature suite locally and confirm ≥80% coverage on the new
      `channel_gateway` package.
- [x] 10.4 Manually verify polling mode and webhook mode (via ngrok) both work against a real
      Telegram test bot and the local LangFlow stack, per the runbook.
- [x] 10.5 Dispatch a separate code-review pass (`meaningfy-building:meaningfy-code-review` /
      `meaningfy-building:code-reviewer` / `/code-review`) against the full diff, per
      `AGENTS.md`'s "Implementation subagent routing" — the implementer must not review its
      own work. Check spec conformance against all four `specs/*/spec.md` files, not just
      lint/type/test passes.
