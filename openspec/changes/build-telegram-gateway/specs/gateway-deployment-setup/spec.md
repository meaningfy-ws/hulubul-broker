## ADDED Requirements

### Requirement: Local Docker Compose service for the gateway
The system SHALL provide a `channel-gateway` service in `infra/docker-compose.yaml`, built
from a dedicated `infra/channel-gateway/Dockerfile`, configured entirely through environment
variables (`TELEGRAM_BOT_TOKEN`, `LANGFLOW_API_URL`, `LANGFLOW_FLOW_ID`, `GATEWAY_MODE`), and
started after the `langflow` service has started (`langflow` has no healthcheck defined, so
Compose uses `service_started` rather than `service_healthy`).

#### Scenario: The gateway starts as part of the standard local stack
- **WHEN** a developer runs `make up`
- **THEN** the `channel-gateway` service builds and starts alongside `langflow`, `postgres`,
  `neo4j`, and `mcp-neo4j`, using secrets from `infra/.env` (never committed), consistent with
  the existing services in the compose file

### Requirement: Telegram bot configuration is documented end-to-end
The runbook SHALL document every manual step required to stand up a working Telegram bot for
local development: creating the bot via @BotFather, obtaining the bot token, setting the
webhook `secret_token` for request validation, and disabling bot privacy mode.

#### Scenario: A developer follows the runbook and gets a working bot
- **WHEN** a developer with no prior Telegram bot has follows
  `architecture/channel-gateway-runbook.md` from the top
- **THEN** they end up with a `TELEGRAM_BOT_TOKEN` populated in `infra/.env` and a bot that
  responds to messages once the `channel-gateway` service is running, without needing
  information from any other document

### Requirement: Local webhook-mode testing via an ngrok tunnel
The system SHALL provide an `ngrok` service in the local Compose stack so that
`GATEWAY_MODE=webhook` can be exercised end-to-end locally, registering the tunnel's public
HTTPS URL as the Telegram webhook automatically on gateway startup.

#### Scenario: Webhook mode works locally without a real public deployment
- **WHEN** `GATEWAY_MODE=webhook` and the `ngrok` service is running
- **THEN** the gateway registers the current ngrok URL as the Telegram webhook on startup, and
  an inbound Telegram message reaches the gateway through that tunnel

### Requirement: Three-tier local test suite
The system SHALL organize gateway tests into three suites — `tests/unit/` (mocked, always run),
`tests/features/*.feature` with `tests/feature/` step-definitions (mocked LangFlow client,
synthetic inbound, run in CI), and `tests/e2e/` (real Telegram test bot and real local
LangFlow, local/manual only, excluded from CI) — with the split documented in the runbook.

#### Scenario: Unit and feature suites run in CI
- **WHEN** the GitHub Actions CI pipeline runs
- **THEN** it executes `tests/unit/` and the `tests/feature/` step-definitions against
  `tests/features/*.feature`, and does not require a Telegram bot token as a secret

#### Scenario: e2e suite is excluded from CI but documented
- **WHEN** a developer wants to run the full round-trip test against a real Telegram bot
- **THEN** the runbook documents how to run `tests/e2e/` locally with a test-bot token, and
  the CI configuration does not invoke this suite
