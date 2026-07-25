from unittest.mock import AsyncMock, MagicMock

import pytest

from hulubul.core.models.domain.hulubul_models import Medium

from hulubul.channel_gateway.models.message import InboundMessage, TextMessage
from hulubul.channel_gateway.services.relay_message import relay_inbound_message


@pytest.mark.asyncio
async def test_relay_calls_langflow_with_derived_session_id_and_sends_reply_to_origin():
    adapter = MagicMock()
    adapter.receive.return_value = InboundMessage(
        medium=Medium.Telegram, system_id="123456789", text="I need to send a parcel"
    )
    adapter.send = AsyncMock()

    langflow_client = MagicMock()
    langflow_client.run = AsyncMock(return_value="Sure, where is it going?")

    await relay_inbound_message(adapter, langflow_client, raw_update=object())

    langflow_client.run.assert_awaited_once_with(
        session_id="Telegram:123456789",
        medium="Telegram",
        system_id="123456789",
        text="I need to send a parcel",
    )
    adapter.send.assert_awaited_once_with(
        "123456789", TextMessage(text="Sure, where is it going?")
    )


@pytest.mark.asyncio
async def test_relay_does_not_send_when_langflow_call_fails():
    adapter = MagicMock()
    adapter.receive.return_value = InboundMessage(
        medium=Medium.Telegram, system_id="123456789", text="hi"
    )
    adapter.send = AsyncMock()

    langflow_client = MagicMock()
    langflow_client.run = AsyncMock(return_value=None)

    await relay_inbound_message(adapter, langflow_client, raw_update=object())

    adapter.send.assert_not_awaited()


@pytest.mark.asyncio
async def test_relay_does_not_crash_the_process_when_send_fails():
    adapter = MagicMock()
    adapter.receive.return_value = InboundMessage(
        medium=Medium.Telegram, system_id="123456789", text="hi"
    )
    adapter.send = AsyncMock(side_effect=RuntimeError("Telegram API: bot was blocked by the user"))

    langflow_client = MagicMock()
    langflow_client.run = AsyncMock(return_value="Sure, where is it going?")

    # Must not raise — a delivery failure for one message must not take down
    # the long-running gateway process for every subsequent message.
    await relay_inbound_message(adapter, langflow_client, raw_update=object())
