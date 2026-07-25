"""
Manual/local-only: requires a real Telegram test bot and the local LangFlow
stack running (`docker compose up`). Not run in CI.

Run with: poetry run pytest tests/e2e/test_telegram_roundtrip.py -v -s
Requires: TELEGRAM_TEST_BOT_TOKEN and TELEGRAM_TEST_CHAT_ID in the environment
(see architecture/channel-gateway-runbook.md "Running e2e tests locally").
"""

import os

import httpx
import pytest

pytestmark = pytest.mark.skipif(
    not os.environ.get("TELEGRAM_TEST_BOT_TOKEN"),
    reason="requires a real Telegram test bot token; see channel-gateway-runbook.md",
)


@pytest.mark.asyncio
async def test_a_real_message_gets_a_real_reply():
    token = os.environ["TELEGRAM_TEST_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_TEST_CHAT_ID"]

    async with httpx.AsyncClient() as client:
        send_resp = await client.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": "e2e: I need to send a parcel"},
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
            if updates and updates[-1]["message"]["chat"]["id"] == int(chat_id):
                assert updates[-1]["message"]["text"]
                return
        pytest.fail("No reply received from the gateway within the polling window")
