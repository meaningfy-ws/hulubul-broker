from unittest.mock import AsyncMock, MagicMock

import pytest

from hulubul.channel_gateway.adapters.telegram_adapter import TelegramAdapter
from hulubul.channel_gateway.models.message import MediaMessage, TextMessage
from hulubul.core.models.domain.hulubul_models import Medium


def _fake_aiogram_message(text: str, chat_id: int, reply_to_message_id: int | None = None):
    message = MagicMock()
    message.text = text
    message.chat.id = chat_id
    message.reply_to_message = None
    if reply_to_message_id is not None:
        message.reply_to_message = MagicMock()
        message.reply_to_message.message_id = reply_to_message_id
    return message


def test_receive_normalizes_a_plain_text_update():
    adapter = TelegramAdapter(bot=MagicMock())
    raw = _fake_aiogram_message(text="hello", chat_id=123456789)

    inbound = adapter.receive(raw)

    assert inbound.medium is Medium.Telegram
    assert inbound.system_id == "123456789"
    assert inbound.text == "hello"
    assert inbound.reply_to_message_id is None


def test_receive_captures_reply_to_message_id_when_present():
    adapter = TelegramAdapter(bot=MagicMock())
    raw = _fake_aiogram_message(text="yes", chat_id=123456789, reply_to_message_id=555)

    inbound = adapter.receive(raw)

    assert inbound.reply_to_message_id == "555"


@pytest.mark.asyncio
async def test_send_text_message_calls_bot_send_message():
    bot = MagicMock()
    bot.send_message = AsyncMock()
    adapter = TelegramAdapter(bot=bot)

    await adapter.send("123456789", TextMessage(text="reply"))

    bot.send_message.assert_awaited_once_with(chat_id=123456789, text="reply")


@pytest.mark.asyncio
async def test_send_media_message_calls_bot_send_photo():
    bot = MagicMock()
    bot.send_photo = AsyncMock()
    adapter = TelegramAdapter(bot=bot)

    await adapter.send(
        "123456789", MediaMessage(url="https://example.com/a.jpg", caption="a parcel photo")
    )

    bot.send_photo.assert_awaited_once_with(
        chat_id=123456789, photo="https://example.com/a.jpg", caption="a parcel photo"
    )
