import pytest

from hulubul.channel_gateway.adapters.channel_port import ChannelPort
from hulubul.channel_gateway.adapters.whatsapp_adapter import WhatsAppAdapter
from hulubul.channel_gateway.models.message import TextMessage


def test_whatsapp_adapter_is_a_channel_port() -> None:
    adapter: ChannelPort = WhatsAppAdapter()
    assert isinstance(adapter, ChannelPort)


def test_receive_is_not_implemented() -> None:
    adapter = WhatsAppAdapter()
    with pytest.raises(NotImplementedError):
        adapter.receive(raw_update={"some": "360dialog payload"})


@pytest.mark.asyncio
async def test_send_is_not_implemented() -> None:
    adapter = WhatsAppAdapter()
    with pytest.raises(NotImplementedError):
        await adapter.send("+15551234567", TextMessage(text="hi"))
