# Channel Gateway Runbook

Operational how-to for the Telegram/WhatsApp channel gateway: standing up a Telegram bot,
bringing the gateway up locally, and running its test suites. For the design behind these
steps — why the gateway is shaped this way — see the companion
[channel-gateway-blueprint.md](channel-gateway-blueprint.md).

Telegram bot setup, local Docker deployment (both polling and webhook modes), and all three
test tiers (unit, feature, e2e) are implemented and documented below. The one remaining gap is
WhatsApp, which is out of scope for this change — see its own section further down.

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
7. **Generate a webhook secret token (needed for webhook mode).** Telegram's webhook mode sends
   a shared secret back on every request (`X-Telegram-Bot-Api-Secret-Token` header) so the
   gateway can reject requests that didn't actually come from Telegram. This is **mandatory**:
   `load_config()` in `hulubul/channel_gateway/entrypoints/telegram_bot.py` raises
   `ValueError: TELEGRAM_WEBHOOK_SECRET is required when GATEWAY_MODE=webhook: ...` and the
   process refuses to start without it. Generate a random value now, following the same
   random-string convention BotFather itself uses for tokens:
   ```
   openssl rand -hex 32
   ```
   Store it in `infra/.env` as `TELEGRAM_WEBHOOK_SECRET=<the value you generated>`. Polling mode
   (below) doesn't need this — only set it once you're bringing up webhook mode.

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
   `hulubul/channel_gateway/entrypoints/telegram_bot.py`).
3. Message your bot on Telegram. In polling mode the gateway calls Telegram to fetch updates
   itself, so no public URL or tunnel is required.

### Webhook mode (via the `ngrok` tunnel)

Webhook mode needs a public URL Telegram can reach, so it uses `ngrok` (D6) to tunnel to the
gateway's local port. The `ngrok` service lives behind Compose's `webhook` profile so it never
starts during normal polling-mode bring-up.

1. In `infra/.env`, set:
   ```
   GATEWAY_MODE=webhook
   TELEGRAM_WEBHOOK_SECRET=<the value you generated in step 7 above>
   NGROK_AUTHTOKEN=<your ngrok auth token, from https://dashboard.ngrok.com/get-started/your-authtoken>
   ```
   `TELEGRAM_BOT_TOKEN` and `LANGFLOW_FLOW_ID` should already be set from earlier steps.
2. Bring up the gateway and the tunnel together:
   ```
   GATEWAY_MODE=webhook docker compose --profile webhook up -d --build channel-gateway ngrok
   ```
   (`docker-compose.yaml`'s `ngrok` service only starts under `--profile webhook`; `--build`
   picks up `infra/docker/channel-gateway/Dockerfile` if it hasn't been built yet.)
3. On startup, `run_webhook()` in `entrypoints/telegram_bot.py` reads the tunnel's public URL
   from ngrok's local API (`http://ngrok:4040/api/tunnels` inside the Compose network — see
   `NGROK_API_URL` in `docker-compose.yaml`) and registers it as the bot's webhook, with
   `TELEGRAM_WEBHOOK_SECRET` as the shared secret Telegram echoes back on every request.
4. Message your bot on Telegram. Telegram now delivers updates by POSTing to the tunnel's
   public URL instead of the gateway polling for them.
5. To inspect the tunnel (public URL, recent requests), open `http://localhost:4040` — ngrok's
   own local dashboard, exposed via the `4040:4040` port mapping in `docker-compose.yaml`.

To go back to polling mode, set `GATEWAY_MODE=polling` and bring the stack up without the
`webhook` profile (`docker compose up -d --build channel-gateway`) — `ngrok` won't start.

## WhatsApp configuration

**Not yet implemented.** There is no live WhatsApp configuration to document here.
`WhatsAppAdapter` (`hulubul/channel_gateway/adapters/whatsapp_adapter.py`) is a stub that
matches the `ChannelPort` interface shape but raises `NotImplementedError` on every call — no
360dialog account, template, or opt-in setup exists for this gateway. This is a deliberate
scope boundary, not an oversight: see
[channel-gateway-blueprint.md's Non-Goals](channel-gateway-blueprint.md#non-goals)
("Live WhatsApp integration") and the WhatsApp-related entries under
[Known limitations](channel-gateway-blueprint.md#known-limitations). Come back to this section
once a real WhatsApp adapter is scoped and built.

## Running the test suites locally

The gateway's tests are organized into three tiers (D8): unit, feature, and e2e.

### Unit tests (runs in CI)

Models and adapters tested against mocks, no real Telegram or LangFlow involved:

```
poetry run pytest tests/unit/hulubul/channel_gateway -v
```

### Feature tests (Gherkin, mocked LangFlow; runs in CI)

`tests/feature/telegram_message_relay.feature` and its step-definitions under
`tests/feature/steps/` (`test_telegram_message_relay.py`) exercise the relay path with synthetic
(non-Telegram) inbound payloads against a mocked `LangflowClient`. Run them with:

```
poetry run pytest tests/feature -v
```

or via the Makefile target, which also excludes `tests/e2e` (defense in depth) and writes a
JUnit report:

```
make test-feature
```

This runs in CI alongside the unit suite (`make ci-static`, per D8).

### End-to-end tests (real Telegram test bot)

A full round-trip test against a real Telegram test bot (`test_telegram_roundtrip.py`), plus a
Telegram-adapter isolation test that exercises `TelegramAdapter` against the real Telegram API
independent of LangFlow (`test_telegram_adapter_isolation.py`), run locally only — never in CI
(D8). Both tests require a **second, dedicated Telegram test bot** distinct from your dev bot.

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

**Expected behavior — round-trip test:** `test_telegram_roundtrip.py` sends a message to the
test chat with a unique marker embedded in the text (e.g. `e2e: I need to send a parcel
[3fa8...]`, a fresh UUID each run), then polls `getUpdates` for a reply. Success means a new
update appears whose `update_id` is strictly greater than the highest `update_id` seen right
before the send — this is what rules out the test false-passing on a stale message already
sitting in the chat (e.g. the `hello` you sent while looking up `TELEGRAM_TEST_CHAT_ID` above)
without the gateway having run at all. The test requires the local LangFlow stack and a running
`channel-gateway` (polling mode, pointed at the test bot token) to actually produce a reply. In
development environments without a real token, it skips automatically (`pytest.mark.skipif`) —
skipping is the expected outcome, not a failure.

**Expected behavior — adapter isolation test:** `test_telegram_adapter_isolation.py` constructs
a real `TelegramAdapter` around a real `aiogram.Bot(token=...)` and calls the adapter's own
`send()` method directly — no LangFlow client, flow, or API call is involved anywhere in this
test. Success means `send()` completes without raising, i.e. the real Telegram API accepted the
request the adapter built. This tests the adapter's send contract in isolation from LangFlow,
but does not exercise `TelegramAdapter.receive()` (covered by unit tests) or verify anything
about LangFlow's behavior when stubbed — a stub-LangFlow harness would be a further
improvement. Run it directly:
```bash
TELEGRAM_TEST_BOT_TOKEN=<token> TELEGRAM_TEST_CHAT_ID=<id> poetry run pytest tests/e2e/test_telegram_adapter_isolation.py -v -s
```
It's marked `skipif` as well, so it skips in CI and in any environment without a real test bot
token.

## References

- [channel-gateway-blueprint.md](channel-gateway-blueprint.md) — design and rationale behind
  every step above
- `openspec/changes/build-telegram-gateway/specs/gateway-deployment-setup/spec.md` — the
  acceptance scenarios this runbook satisfies
- `openspec/changes/build-telegram-gateway/plan.md` — Tasks 11–14, the local-deployment and
  test-suite work this runbook documents
