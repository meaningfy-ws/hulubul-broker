from abc import ABC, abstractmethod

from hulubul.channel_gateway.models.message import (
    InboundMessage,
    MediaMessage,
    TextMessage,
)


class ChannelPort(ABC):
    @abstractmethod
    def receive(self, raw_update: object) -> InboundMessage:
        """Normalize a channel-specific raw update into an InboundMessage."""

    @abstractmethod
    async def send(self, system_id: str, message: TextMessage | MediaMessage) -> None:
        """Send an outbound message to the given channel-specific system_id."""
