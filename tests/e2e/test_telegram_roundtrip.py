"""
Manual/local-only: requires a real Telegram test bot and the local LangFlow
stack running (`docker compose up`). Not run in CI.

Run with: poetry run pytest tests/e2e/test_telegram_roundtrip.py -v -s
Requires: TELEGRAM_TEST_BOT_TOKEN and TELEGRAM_TEST_CHAT_ID in the environment
(see architecture/channel-gateway-runbook.md "Running e2e tests locally").
"""

import os
import uuid

import httpx
import pytest

pytestmark = pytest.mark.skipif(
    not os.environ.get("TELEGRAM_TEST_BOT_TOKEN"),
    reason="requires a real Telegram test bot token; see channel-gateway-runbook.md",
)


@pytest.mark.asyncio
async def test_a_real_message_gets_a_real_reply() -> None:
    token = os.environ["TELEGRAM_TEST_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_TEST_CHAT_ID"]
    # Unique per run so the sent message (and any failure output) can be
    # traced back to this specific test invocation.
    marker = str(uuid.uuid4())

    async with httpx.AsyncClient() as client:
        # Record the highest update_id that already exists BEFORE sending.
        # `offset=-1` peeks the single most recent update without confirming it
        # (or anything before it), so this doesn't interfere with the
        # gateway's own getUpdates polling loop.
        #
        # Without this baseline, the loop below could false-pass on a STALE
        # message already sitting in the chat (e.g. the "hello" a developer
        # sent while looking up TELEGRAM_TEST_CHAT_ID per the runbook) even if
        # the gateway never actually ran and no reply was ever sent.
        baseline_resp = await client.get(
            f"https://api.telegram.org/bot{token}/getUpdates", params={"offset": -1}
        )
        baseline_updates = baseline_resp.json()["result"]
        baseline_update_id = baseline_updates[-1]["update_id"] if baseline_updates else 0

        send_resp = await client.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": f"e2e: I need to send a parcel [{marker}]"},
        )
        assert send_resp.status_code == 200

        # The running channel-gateway container (polling mode) picks this up
        # and relays it to the local LangFlow stack; poll for the bot's reply.
        import asyncio

        for _ in range(10):
            await asyncio.sleep(2)
            updates_resp = await client.get(
                f"https://api.telegram.org/bot{token}/getUpdates", params={"offset": -1}
            )
            updates = updates_resp.json()["result"]
            # Strictly greater than the baseline update_id: this is what makes
            # the update NEW relative to the send, ruling out a stale message.
            if (
                updates
                and updates[-1]["update_id"] > baseline_update_id
                and updates[-1]["message"]["chat"]["id"] == int(chat_id)
            ):
                assert updates[-1]["message"]["text"]
                return
        pytest.fail(
            f"No reply received from the gateway within the polling window (marker={marker})"
        )
