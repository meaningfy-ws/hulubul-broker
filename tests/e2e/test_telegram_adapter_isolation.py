"""
Manual/local-only: constructs a real `TelegramAdapter` around a real
`aiogram.Bot` and exercises the adapter's own `send()` method against the
real Telegram Bot API. Not run in CI.

"Isolating the Telegram adapter" here means testing `TelegramAdapter`'s own
send contract independently of LangFlow — no LangFlow client, flow, or API
call is constructed or reached anywhere in this file. It does NOT exercise
`TelegramAdapter.receive()` (that requires either a live inbound
webhook/poll or a hand-built `aiogram.types.Message` fixture, which is
covered by unit tests, not here), and it does not verify anything about
LangFlow's *behavior* under isolation (e.g. against a stub LangFlow
server) — only that no LangFlow call happens on this path. A stub-LangFlow
isolation harness would be a further improvement, not attempted here.
"""

import os

import pytest
from aiogram import Bot

from hulubul.channel_gateway.adapters.telegram_adapter import TelegramAdapter
from hulubul.channel_gateway.models.message import TextMessage

pytestmark = pytest.mark.skipif(
    not os.environ.get("TELEGRAM_TEST_BOT_TOKEN"),
    reason="requires a real Telegram test bot token; see channel-gateway-runbook.md",
)


@pytest.mark.asyncio
async def test_adapter_send_reaches_the_real_telegram_api() -> None:
    token = os.environ["TELEGRAM_TEST_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_TEST_CHAT_ID"]

    bot = Bot(token=token)
    try:
        adapter = TelegramAdapter(bot=bot)
        # No exception means the real Telegram API accepted the request built
        # by TelegramAdapter.send() itself — exercising the adapter's own
        # send contract, with no LangFlow client involved at all.
        await adapter.send(chat_id, TextMessage(text="e2e: adapter isolation ping"))
    finally:
        await bot.session.close()
