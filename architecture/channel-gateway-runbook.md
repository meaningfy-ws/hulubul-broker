# Channel Gateway Runbook

Operational how-to for the Telegram/WhatsApp channel gateway: standing up a Telegram bot,
bringing the gateway up locally, and running its test suites. For the design behind these
steps — why the gateway is shaped this way — see the companion
[channel-gateway-blueprint.md](channel-gateway-blueprint.md).

Some steps below belong to work that hasn't landed yet (local Docker deployment, feature and
e2e tests). Those sections say so explicitly and point at the task that will fill them in,
rather than guessing at commands that don't exist yet.

## Telegram bot setup (via @BotFather)

Follow this section top to bottom with no prior Telegram bot experience. By the end you'll have
a bot token ready to drop into `infra/.env`.

1. **Open Telegram** (desktop, mobile, or web — [web.telegram.org](https://web.telegram.org)
   works fine) and sign in with your own account.
2. **Find BotFather.** Use Telegram's search to look up `@BotFather` — it's Telegram's own bot
   for creating and managing bots, marked with a blue verification checkmark. Open a chat with
   it and press **Start** (or send `/start`).
3. **Create a new bot.** Send:
   ```
   /newbot
   ```
   BotFather will ask two questions in sequence:
   - A **display name** — any text, e.g. `Hulubul Dev Bot`. This is what shows in chat headers.
   - A **username** — must be unique across Telegram and end in `bot`, e.g.
     `hulubul_dev_bot`. BotFather tells you immediately if it's taken; retry with a different
     one until it accepts.
4. **Copy the token.** BotFather replies with a message containing an API token that looks like
   `123456789:AAExampleTokenDoNotUseThisOneAbCdEfGhIjK`. Copy the whole string — this is your
   bot's credential, treat it like a password.
5. **Store the token locally.** In your working copy of this repo, make sure `infra/.env`
   exists (copy `infra/.env.example` if you don't have one yet), and add:
   ```
   TELEGRAM_BOT_TOKEN=<the token you copied>
   ```
   `infra/.env` is git-ignored — never commit a real bot token.
6. **Disable privacy mode.** By default, Telegram only forwards `/command`-style messages to a
   bot in group chats, not ordinary text — the gateway needs to see every message. Message
   BotFather again:
   ```
   /setprivacy
   ```
   Select your bot from the list, then choose **Disable**. (For 1:1 chats with the bot this
   step doesn't change anything — it matters once the bot is added to a group — but disabling it
   now avoids a confusing gap later.)
7. **Generate a webhook secret token (for later).** Telegram's webhook mode can send a shared
   secret back on every request (`X-Telegram-Bot-Api-Secret-Token` header) so the gateway can
   reject requests that didn't actually come from Telegram. Generate a random value now so it's
   ready when you need it:
   ```
   openssl rand -hex 32
   ```
   Keep this value somewhere safe for now. Wiring it into the gateway's webhook configuration
   is part of the local Compose webhook setup below, which is still pending (Task 11) — there is
   no environment variable for it yet.

At this point you have a working bot identity and a token, but no gateway running yet — that's
the next section.

## Local Compose bring-up

### Polling mode (works today)

Polling mode needs no inbound port and no tunnel, so it's the default for first bring-up (per
`design.md`'s Migration Plan):

1. Bring up the existing stack (Neo4j, LangFlow, Postgres, `mcp-neo4j`):
   ```
   make up
   ```
2. Set `GATEWAY_MODE=polling` alongside `TELEGRAM_BOT_TOKEN` (from the previous section),
   `LANGFLOW_API_URL`, and `LANGFLOW_FLOW_ID` in `infra/.env` — these are the environment
   variables `entrypoints/telegram_bot.py` reads at startup (`load_config()` in
   `src/hulubul/channel_gateway/entrypoints/telegram_bot.py`).
3. Message your bot on Telegram. In polling mode the gateway calls Telegram to fetch updates
   itself, so no public URL or tunnel is required.

> **TODO — webhook mode and the `ngrok` profile.** `GATEWAY_MODE=webhook` and the local `ngrok`
> tunnel service (D6) are not wired up yet: there is no `infra/channel-gateway/Dockerfile`, no
> `channel-gateway` entry in `infra/docker-compose.yaml`, and today's webhook code path
> (`entrypoints/telegram_bot.py`) deliberately raises `NotImplementedError` when
> `GATEWAY_MODE=webhook` is set, with a comment pointing at "the local-deployment task." That
> work is **Task 11** of this change's implementation plan (Dockerfile, Compose service, and
> webhook registration through the `ngrok` tunnel). Once Task 11 lands, this section will be
> updated with Task 11's exact commands — the `ngrok` Compose profile invocation and how the
> tunnel's public URL gets registered as the Telegram webhook on gateway startup. Until then,
> use polling mode above; do not attempt to hand-assemble webhook wiring from this runbook.

## WhatsApp configuration

**Not yet implemented.** There is no live WhatsApp configuration to document here.
`WhatsAppAdapter` (`src/hulubul/channel_gateway/adapters/whatsapp_adapter.py`) is a stub that
matches the `ChannelPort` interface shape but raises `NotImplementedError` on every call — no
360dialog account, template, or opt-in setup exists for this gateway. This is a deliberate
scope boundary, not an oversight: see
[channel-gateway-blueprint.md's Non-Goals](channel-gateway-blueprint.md) (`design.md`'s
`## Goals / Non-Goals`, "Live WhatsApp integration") and the WhatsApp-related entries under
[Known limitations](channel-gateway-blueprint.md#known-limitations). Come back to this section
once a real WhatsApp adapter is scoped and built.

## Running the test suites locally

The gateway's tests are organized into three tiers (D8) — only the first exists today.

### Unit tests (implemented, runs in CI)

Models and adapters tested against mocks, no real Telegram or LangFlow involved:

```
poetry run pytest tests/unit/hulubul/channel_gateway -v
```

### Feature tests (Gherkin, LangFlow-connected) — not yet implemented

`tests/features/*.feature` scenarios and their `tests/feature/` step-definitions, run against a
real local LangFlow container with synthetic (non-Telegram) inbound payloads, are **Task 12** of
this change's implementation plan and haven't landed yet. Once Task 12 lands, this section will
document the exact `.feature` file(s) and the command to run them (expected to run in CI
alongside the unit suite, per D8).

### End-to-end tests (real Telegram test bot) — not yet implemented

A full round-trip test against a real Telegram test bot, plus a Telegram-adapter isolation test
with LangFlow's response stubbed, are **Task 13** of this change's implementation plan and
haven't landed yet — `tests/e2e/` doesn't exist in this repo yet. The plan for this suite
(`plan.md` Task 13) calls for a dedicated Telegram test bot (created the same way as in
"Telegram bot setup" above, but kept separate from your personal dev bot) and two environment
variables, `TELEGRAM_TEST_BOT_TOKEN` and `TELEGRAM_TEST_CHAT_ID`, feeding a
`pytest tests/e2e/` invocation. Treat those names as the plan, not yet a working command — this
section will be filled in with the actual invocation once Task 13 lands. This suite is local/
manual-only by design (D8): it is deliberately excluded from CI to avoid adding a Telegram
bot-token secret to the pipeline.

## References

- [channel-gateway-blueprint.md](channel-gateway-blueprint.md) — design and rationale behind
  every step above
- `openspec/changes/build-telegram-gateway/specs/gateway-deployment-setup/spec.md` — the
  acceptance scenarios this runbook satisfies
- `openspec/changes/build-telegram-gateway/plan.md` — Tasks 11–14, for the work still pending
