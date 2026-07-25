import inspect

from hulubul.channel_gateway.adapters.channel_port import ChannelPort


def test_channel_port_cannot_be_instantiated_directly():
    assert inspect.isabstract(ChannelPort)


def test_channel_port_declares_receive_and_send():
    assert "receive" in ChannelPort.__abstractmethods__
    assert "send" in ChannelPort.__abstractmethods__


def test_a_conforming_subclass_can_be_instantiated():
    class FakeAdapter(ChannelPort):
        def receive(self, raw_update: object):
            raise NotImplementedError

        async def send(self, system_id: str, message) -> None:
            raise NotImplementedError

    FakeAdapter()  # does not raise
