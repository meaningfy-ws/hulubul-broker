from hulubul.channel_gateway.adapters.channel_port import ChannelPort
from hulubul.channel_gateway.models.message import (
    InboundMessage,
    MediaMessage,
    TextMessage,
)


class WhatsAppAdapter(ChannelPort):
    """Stub proving ChannelPort generalizes to WhatsApp/360dialog.

    Not wired to any live WhatsApp API. Implement receive()/send() only
    when a real 360dialog integration is scoped (see channel-gateway
    design.md non-goals).
    """

    def receive(self, raw_update: object) -> InboundMessage:
        raise NotImplementedError("WhatsApp adapter is a stub; not implemented yet.")

    async def send(self, system_id: str, message: TextMessage | MediaMessage) -> None:
        raise NotImplementedError("WhatsApp adapter is a stub; not implemented yet.")
