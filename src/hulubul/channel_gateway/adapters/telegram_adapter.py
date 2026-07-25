from aiogram import Bot

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
        reply_to_message_id = None
        if getattr(raw_update, "reply_to_message", None) is not None:
            reply_to_message_id = str(raw_update.reply_to_message.message_id)
        return InboundMessage(
            medium=Medium.Telegram,
            system_id=str(raw_update.chat.id),
            text=raw_update.text,
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
