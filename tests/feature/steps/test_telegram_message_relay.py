import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from hulubul.channel_gateway.models.channel import ChannelRef
from hulubul.channel_gateway.models.message import InboundMessage, MediaMessage, TextMessage
from hulubul.channel_gateway.services.relay_message import relay_inbound_message
from hulubul.core.models.domain.hulubul_models import Medium

scenarios("../telegram_message_relay.feature")

# A pytest-bdd scenario's context is a free-form bag shared across step
# functions (adapter/client mocks, ids, replies-by-id); typing it any more
# strictly than `dict[str, Any]` would fight the pattern rather than help it.
Context = dict[str, Any]


@pytest.fixture
def context() -> Context:
    return {}


@given(
    parsers.parse(
        'a Telegram chat with system_id "{system_id}" that has never messaged Hulubul before'
    )
)
@given(parsers.parse('a Telegram chat with system_id "{system_id:w}"'))
def a_telegram_chat(context: Context, system_id: str) -> None:
    context["system_id"] = system_id
    context["adapter"] = MagicMock()
    context["adapter"].send = AsyncMock()
    context["langflow_client"] = MagicMock()
    context["langflow_client"].run = AsyncMock(return_value="")


@given(parsers.parse('LangFlow will reply with "{reply_text}"'))
def langflow_will_reply(context: Context, reply_text: str) -> None:
    context["langflow_client"].run = AsyncMock(return_value=reply_text)


@given("LangFlow is unreachable")
def langflow_is_unreachable(context: Context) -> None:
    context["langflow_client"].run = AsyncMock(return_value=None)


@given(
    parsers.parse(
        'a Telegram chat with system_id "{first_id}" and a Telegram chat with system_id '
        '"{second_id}"'
    )
)
def two_telegram_chats(context: Context, first_id: str, second_id: str) -> None:
    context["adapter"] = MagicMock()
    context["adapter"].send = AsyncMock()
    context["replies_by_system_id"] = {}

    async def run_side_effect(*, session_id: str, channel: ChannelRef, text: str) -> str | None:
        replies: dict[str, str] = context["replies_by_system_id"]
        return replies.get(channel.system_id)

    context["langflow_client"] = MagicMock()
    context["langflow_client"].run = AsyncMock(side_effect=run_side_effect)


@given(parsers.parse('LangFlow will reply "{reply_text}" to system_id "{system_id}"'))
def langflow_will_reply_to_system_id(context: Context, reply_text: str, system_id: str) -> None:
    context["replies_by_system_id"][system_id] = reply_text


@given(
    parsers.parse(
        'sending to system_id "{blocked_system_id}" fails because the Sender blocked the bot'
    )
)
def sending_fails_for_system_id(context: Context, blocked_system_id: str) -> None:
    async def send_side_effect(system_id: str, message: TextMessage | MediaMessage) -> None:
        if system_id == blocked_system_id:
            raise RuntimeError("Forbidden: bot was blocked by the user")

    context["adapter"].send = AsyncMock(side_effect=send_side_effect)


@when(parsers.parse('the sender on system_id "{system_id}" sends the message "{message_text}"'))
def sender_on_system_id_sends_message(context: Context, system_id: str, message_text: str) -> None:
    context["adapter"].receive.return_value = InboundMessage(
        channel=ChannelRef(medium=Medium.Telegram, system_id=system_id), text=message_text
    )
    asyncio.run(
        relay_inbound_message(context["adapter"], context["langflow_client"], raw_update=object())
    )


@when(parsers.parse('the sender sends the message "{message_text}"'))
def sender_sends_message(context: Context, message_text: str) -> None:
    context["adapter"].receive.return_value = InboundMessage(
        channel=ChannelRef(medium=Medium.Telegram, system_id=context["system_id"]),
        text=message_text,
    )
    # pytest-bdd 8.1.0 calls step functions synchronously (the generated scenario
    # test item is a plain `def`, not `async def`), so pytest-asyncio's auto mode
    # never instruments this step and `await`/`@pytest.mark.asyncio` here would
    # leave the coroutine un-awaited. Drive it to completion explicitly instead.
    asyncio.run(
        relay_inbound_message(context["adapter"], context["langflow_client"], raw_update=object())
    )


@then(parsers.parse('LangFlow receives session_id "{expected_session_id}"'))
def langflow_receives_session_id(context: Context, expected_session_id: str) -> None:
    _, kwargs = context["langflow_client"].run.await_args
    assert kwargs["session_id"] == expected_session_id


@then(
    parsers.parse(
        'LangFlow receives the channel identity medium "{medium}" and system_id "{system_id}"'
    )
)
def langflow_receives_channel_identity(context: Context, medium: str, system_id: str) -> None:
    _, kwargs = context["langflow_client"].run.await_args
    assert kwargs["channel"].medium == medium
    assert kwargs["channel"].system_id == system_id


@then(parsers.parse('the sender receives the message "{reply_text}"'))
def sender_receives_message(context: Context, reply_text: str) -> None:
    context["adapter"].send.assert_awaited_once_with(
        context["system_id"], TextMessage(text=reply_text)
    )


@then("the sender receives no message")
def sender_receives_no_message(context: Context) -> None:
    context["adapter"].send.assert_not_awaited()


@then(parsers.parse('the sender on system_id "{system_id}" receives the message "{reply_text}"'))
def sender_on_system_id_receives_message(context: Context, system_id: str, reply_text: str) -> None:
    context["adapter"].send.assert_any_await(system_id, TextMessage(text=reply_text))
