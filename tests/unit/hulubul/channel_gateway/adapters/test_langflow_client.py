import json

import httpx
import pytest

from hulubul.channel_gateway.adapters.langflow_client import LangflowClient
from hulubul.channel_gateway.models.channel import ChannelRef
from hulubul.core.models.domain.hulubul_models import Medium

_TELEGRAM_123 = ChannelRef(medium=Medium.Telegram, system_id="123")


@pytest.mark.asyncio
async def test_run_posts_session_id_and_channel_identity_and_returns_reply_text() -> None:
    captured_request: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured_request["json"] = httpx.Request.read(request) and request.content
        captured_request["url"] = str(request.url)
        return httpx.Response(
            200,
            json={
                "outputs": [{"outputs": [{"results": {"message": {"data": {"text": "Got it!"}}}}]}]
            },
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        client = LangflowClient(
            base_url="http://langflow:7860", flow_id="abc123", client=http_client
        )
        reply = await client.run(session_id="Telegram:123", channel=_TELEGRAM_123, text="hello")

    assert reply == "Got it!"
    assert captured_request["url"] == "http://langflow:7860/api/v1/run/abc123"

    raw_body = captured_request["json"]
    assert isinstance(raw_body, bytes)
    sent_payload = json.loads(raw_body)
    assert sent_payload["session_id"] == "Telegram:123"
    assert sent_payload["tweaks"]["channel_identity"] == {
        "medium": "Telegram",
        "system_id": "123",
    }


@pytest.mark.asyncio
async def test_run_returns_none_on_http_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "boom"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        client = LangflowClient(
            base_url="http://langflow:7860", flow_id="abc123", client=http_client
        )
        reply = await client.run(session_id="Telegram:123", channel=_TELEGRAM_123, text="hello")

    assert reply is None


@pytest.mark.asyncio
async def test_run_returns_none_on_unexpected_response_shape() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"unexpected": "shape"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        client = LangflowClient(
            base_url="http://langflow:7860", flow_id="abc123", client=http_client
        )
        reply = await client.run(session_id="Telegram:123", channel=_TELEGRAM_123, text="hello")

    assert reply is None


@pytest.mark.asyncio
async def test_run_returns_none_on_malformed_json_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"not json")

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        client = LangflowClient(
            base_url="http://langflow:7860", flow_id="abc123", client=http_client
        )
        reply = await client.run(session_id="Telegram:123", channel=_TELEGRAM_123, text="hello")

    assert reply is None
