from dataclasses import dataclass

from hulubul.channel_gateway.models.channel import ChannelRef


@dataclass(frozen=True)
class InboundMessage:
    channel: ChannelRef
    text: str
    reply_to_message_id: str | None = None


@dataclass(frozen=True)
class TextMessage:
    text: str


@dataclass(frozen=True)
class MediaMessage:
    url: str
    caption: str | None = None
