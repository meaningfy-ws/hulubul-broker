from hulubul.channel_gateway.models.channel import ChannelRef
from hulubul.channel_gateway.models.langflow import (
    LangflowRunReply,
    LangflowRunRequest,
    LangflowTweaks,
)
from hulubul.core.models.domain.hulubul_models import Medium


def test_run_request_serializes_channel_identity_as_plain_json():
    request = LangflowRunRequest(
        input_value="hello",
        session_id="Telegram:123",
        tweaks=LangflowTweaks(channel_identity=ChannelRef(medium=Medium.Telegram, system_id="123")),
    )

    assert request.model_dump(mode="json") == {
        "input_value": "hello",
        "session_id": "Telegram:123",
        "tweaks": {"channel_identity": {"medium": "Telegram", "system_id": "123"}},
        "input_type": "chat",
        "output_type": "chat",
    }


def test_run_reply_extracts_text_from_the_nested_response_shape():
    payload = {"outputs": [{"outputs": [{"results": {"message": {"data": {"text": "Got it!"}}}}]}]}

    assert LangflowRunReply.model_validate(payload).text == "Got it!"
