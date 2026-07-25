from hulubul.channel_gateway.models.message import (
    InboundMessage,
    MediaMessage,
    TextMessage,
)
from hulubul.core.models.domain.hulubul_models import Medium


def test_inbound_message_is_immutable():
    msg = InboundMessage(medium=Medium.Telegram, system_id="123", text="hello")
    assert msg.medium is Medium.Telegram
    assert msg.system_id == "123"
    assert msg.text == "hello"
    assert msg.reply_to_message_id is None


def test_inbound_message_carries_reply_reference_when_present():
    msg = InboundMessage(
        medium=Medium.Telegram,
        system_id="123",
        text="yes",
        reply_to_message_id="987",
    )
    assert msg.reply_to_message_id == "987"


def test_text_message_holds_text():
    assert TextMessage(text="hi there").text == "hi there"


def test_media_message_caption_defaults_to_none():
    media = MediaMessage(url="https://example.com/photo.jpg")
    assert media.caption is None
