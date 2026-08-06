import logging

from hulubul.channel_gateway.adapters.channel_port import ChannelPort
from hulubul.channel_gateway.adapters.langflow_client import LangflowClient
from hulubul.channel_gateway.models.channel import derive_session_id
from hulubul.channel_gateway.models.message import TextMessage

logger = logging.getLogger(__name__)


async def relay_inbound_message(
    adapter: ChannelPort, langflow_client: LangflowClient, raw_update: object
) -> None:
    inbound = adapter.receive(raw_update)
    session_id = derive_session_id(inbound.channel)

    reply_text = await langflow_client.run(
        session_id=session_id,
        channel=inbound.channel,
        text=inbound.text,
    )

    if reply_text is None:
        logger.warning(
            "No reply from LangFlow for session_id=%s; not sending a response.", session_id
        )
        return

    try:
        await adapter.send(inbound.channel.system_id, TextMessage(text=reply_text))
    except Exception:
        logger.exception(
            "Failed to send reply for session_id=%s; message is dropped, not retried.",
            session_id,
        )
