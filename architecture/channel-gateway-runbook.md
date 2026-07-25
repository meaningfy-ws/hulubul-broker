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
[channel-gateway-blueprint.md's Non-Goals](channel-gateway-blueprint.md#non-goals)
("Live WhatsApp integration") and the WhatsApp-related entries under
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

### End-to-end tests (real Telegram test bot)

A full round-trip test against a real Telegram test bot (`test_telegram_roundtrip.py`), plus a
Telegram-adapter isolation test with LangFlow's response stubbed (`test_telegram_adapter_isolation.py`),
run locally only — never in CI (D8). Both tests require a **second, dedicated Telegram test bot**
distinct from your dev bot.

#### Creating a test bot (via @BotFather)

Follow the same steps as "Telegram bot setup" above (sections 1–7), but use different names to
keep your test bot separate:
- Display name: e.g. `Hulubul Test Bot` or similar
- Username: e.g. `hulubul_test_bot` (must end in `bot`)

You now have two bot tokens:
- `TELEGRAM_BOT_TOKEN`: your personal dev bot (in `infra/.env`)
- `TELEGRAM_TEST_BOT_TOKEN`: your test bot (use below)

#### Finding TELEGRAM_TEST_CHAT_ID

The test bot must know where to send and receive messages. You'll need its own chat ID:

1. In Telegram, start a **new 1:1 chat** with your test bot (the one you just created).
2. Send it any message, e.g. `hello`.
3. Open a terminal and run:
   ```bash
   curl "https://api.telegram.org/bot<TELEGRAM_TEST_BOT_TOKEN>/getUpdates" \
     | jq '.result[0].message.chat.id'
   ```
   Replace `<TELEGRAM_TEST_BOT_TOKEN>` with the token from the test bot's BotFather message.
4. Copy the numeric ID printed by `jq` — that is your `TELEGRAM_TEST_CHAT_ID`.

#### Running e2e tests locally

With the test bot token and chat ID in hand, run:

```bash
export TELEGRAM_TEST_BOT_TOKEN=<your test bot token>
export TELEGRAM_TEST_CHAT_ID=<the chat ID from above>
poetry run pytest tests/e2e/ -v -s
```

Or in one line without intermediate `export`:
```bash
TELEGRAM_TEST_BOT_TOKEN=<your test bot token> TELEGRAM_TEST_CHAT_ID=<your chat ID> \
  poetry run pytest tests/e2e/ -v -s
```

**Expected behavior:** Both tests pass if you have a real test bot token and the local
LangFlow stack is running (`docker compose up`). In development environments without a real
token, both tests skip automatically (marked with `pytest.mark.skipif`) — skipping is the
expected outcome, not a failure.

#### e2e: isolating the Telegram adapter

`test_telegram_adapter_isolation.py` tests only the TelegramAdapter's send/receive contract
without hitting the real LangFlow API. To run this in isolation:

1. Start a stub LangFlow server on `localhost:7860` that returns a fixed response (instructions
   for this stub server are outside this runbook's scope — for now, use a simple HTTP mock
   server that echoes back a `{"reply": "..."}` payload).
2. Ensure `LANGFLOW_API_URL` points to that stub in your `infra/.env` or shell environment.
3. Run the test as above:
   ```bash
   TELEGRAM_TEST_BOT_TOKEN=<token> TELEGRAM_TEST_CHAT_ID=<id> poetry run pytest tests/e2e/test_telegram_adapter_isolation.py -v -s
   ```

This test is marked `skipif` as well, so it will skip in CI and in any environment without a
real test bot token.

## References

- [channel-gateway-blueprint.md](channel-gateway-blueprint.md) — design and rationale behind
  every step above
- `openspec/changes/build-telegram-gateway/specs/gateway-deployment-setup/spec.md` — the
  acceptance scenarios this runbook satisfies
- `openspec/changes/build-telegram-gateway/plan.md` — Tasks 11–14, for the work still pending
