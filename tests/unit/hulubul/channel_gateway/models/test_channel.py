from hulubul.core.models.domain.hulubul_models import Medium

from hulubul.channel_gateway.models.channel import ChannelRef, derive_session_id


def test_same_channel_always_derives_the_same_session_id():
    first = derive_session_id(Medium.Telegram, "123456789")
    second = derive_session_id(Medium.Telegram, "123456789")
    assert first == second


def test_different_media_never_collide_even_with_same_system_id():
    telegram_session = derive_session_id(Medium.Telegram, "15551234567")
    whatsapp_session = derive_session_id(Medium.WhatsApp, "15551234567")
    assert telegram_session != whatsapp_session


def test_session_id_is_a_plain_deterministic_string():
    assert derive_session_id(Medium.Telegram, "42") == "Telegram:42"


def test_channel_ref_holds_medium_and_system_id():
    channel_ref = ChannelRef(medium=Medium.WhatsApp, system_id="+15551234567")
    assert channel_ref.medium is Medium.WhatsApp
    assert channel_ref.system_id == "+15551234567"
