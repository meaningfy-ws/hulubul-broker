from typing import cast

from aiogram import Bot
from aiogram.types import Message

from hulubul.channel_gateway.adapters.channel_port import ChannelPort
from hulubul.channel_gateway.models.message import (
    InboundMessage,
    MediaMessage,
    TextMessage,
)
from hulubul.core.models.domain.hulubul_models import Medium


class TelegramAdapter(ChannelPort):
    def __init__(self, bot: Bot) -> None:
        self._bot = bot

    def receive(self, raw_update: object) -> InboundMessage:
        # ChannelPort.receive() takes `object` since each channel has its own
        # raw update shape; narrow to aiogram's actual type here.
        message = cast(Message, raw_update)
        reply_to_message_id = None
        if message.reply_to_message is not None:
            reply_to_message_id = str(message.reply_to_message.message_id)
        return InboundMessage(
            medium=Medium.Telegram,
            system_id=str(message.chat.id),
            text=message.text or "",
            reply_to_message_id=reply_to_message_id,
        )

    async def send(self, system_id: str, message: TextMessage | MediaMessage) -> None:
        chat_id = int(system_id)
        if isinstance(message, TextMessage):
            await self._bot.send_message(chat_id=chat_id, text=message.text)
        else:
            await self._bot.send_photo(
                chat_id=chat_id, photo=message.url, caption=message.caption
            )
