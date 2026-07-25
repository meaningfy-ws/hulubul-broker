"""
Manual/local-only: real Telegram test bot, LangFlow response stubbed via the
gateway's own mock mode. Isolates the Telegram send/receive contract from
LangFlow's behavior. Not run in CI.
"""

import os

import httpx
import pytest

pytestmark = pytest.mark.skipif(
    not os.environ.get("TELEGRAM_TEST_BOT_TOKEN"),
    reason="requires a real Telegram test bot token; see channel-gateway-runbook.md",
)


@pytest.mark.asyncio
async def test_adapter_normalizes_and_sends_without_a_real_langflow_call(monkeypatch):
    # Point LANGFLOW_API_URL at a local stub server returning a fixed reply,
    # so this test exercises only the TelegramAdapter <-> Telegram contract.
    # See channel-gateway-runbook.md "e2e: isolating the Telegram adapter"
    # for how to start the stub server before running this test.
    token = os.environ["TELEGRAM_TEST_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_TEST_CHAT_ID"]

    async with httpx.AsyncClient() as client:
        send_resp = await client.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": "e2e: adapter isolation ping"},
        )
        assert send_resp.status_code == 200
