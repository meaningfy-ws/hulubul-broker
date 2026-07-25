import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from hulubul.core.models.domain.hulubul_models import Medium

from hulubul.channel_gateway.models.message import InboundMessage, TextMessage
from hulubul.channel_gateway.services.relay_message import relay_inbound_message

scenarios("../features/telegram_message_relay.feature")


@pytest.fixture
def context():
    return {}


@given(parsers.parse('a Telegram chat with system_id "{system_id}" that has never messaged Hulubul before'))
@given(parsers.parse('a Telegram chat with system_id "{system_id}"'))
def a_telegram_chat(context, system_id):
    context["system_id"] = system_id
    context["adapter"] = MagicMock()
    context["adapter"].send = AsyncMock()
    context["langflow_client"] = MagicMock()
    context["langflow_client"].run = AsyncMock(return_value="")


@given(parsers.parse('LangFlow will reply with "{reply_text}"'))
def langflow_will_reply(context, reply_text):
    context["langflow_client"].run = AsyncMock(return_value=reply_text)


@when(parsers.parse('the sender sends the message "{message_text}"'))
def sender_sends_message(context, message_text):
    context["adapter"].receive.return_value = InboundMessage(
        medium=Medium.Telegram, system_id=context["system_id"], text=message_text
    )
    # pytest-bdd 8.1.0 calls step functions synchronously (the generated scenario
    # test item is a plain `def`, not `async def`), so pytest-asyncio's auto mode
    # never instruments this step and `await`/`@pytest.mark.asyncio` here would
    # leave the coroutine un-awaited. Drive it to completion explicitly instead.
    asyncio.run(
        relay_inbound_message(context["adapter"], context["langflow_client"], raw_update=object())
    )


@then(parsers.parse('LangFlow receives session_id "{expected_session_id}"'))
def langflow_receives_session_id(context, expected_session_id):
    _, kwargs = context["langflow_client"].run.await_args
    assert kwargs["session_id"] == expected_session_id


@then(parsers.parse('LangFlow receives the channel identity medium "{medium}" and system_id "{system_id}"'))
def langflow_receives_channel_identity(context, medium, system_id):
    _, kwargs = context["langflow_client"].run.await_args
    assert kwargs["medium"] == medium
    assert kwargs["system_id"] == system_id


@then(parsers.parse('the sender receives the message "{reply_text}"'))
def sender_receives_message(context, reply_text):
    context["adapter"].send.assert_awaited_once_with(
        context["system_id"], TextMessage(text=reply_text)
    )
