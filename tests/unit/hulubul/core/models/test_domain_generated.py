from hulubul.core.models.domain.hulubul_models import Channel, ChannelValidationStatus, Medium


def test_medium_has_the_full_permissible_value_set():
    assert {m.value for m in Medium} == {"GSM", "WhatsApp", "Telegram", "Viber", "email"}


def test_channel_requires_id_system_id_medium_and_validation_status():
    channel = Channel(
        id="channel-123",
        systemID="987654321",
        hasMedium=Medium.Telegram,
        validationStatus=ChannelValidationStatus.valid,
    )
    assert channel.id == "channel-123"
    assert channel.alias is None  # optional fields still default to None
