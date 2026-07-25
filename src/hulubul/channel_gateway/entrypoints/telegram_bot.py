import os
from dataclasses import dataclass

from aiogram import Bot, Dispatcher
from aiogram.types import Message
import httpx

from hulubul.channel_gateway.adapters.langflow_client import LangflowClient
from hulubul.channel_gateway.adapters.telegram_adapter import TelegramAdapter
from hulubul.channel_gateway.services.relay_message import relay_inbound_message

_VALID_MODES = {"polling", "webhook"}


@dataclass(frozen=True)
class GatewayConfig:
    telegram_bot_token: str
    langflow_api_url: str
    langflow_flow_id: str
    mode: str


def load_config() -> GatewayConfig:
    mode = os.environ["GATEWAY_MODE"]
    if mode not in _VALID_MODES:
        raise ValueError(f"GATEWAY_MODE must be one of {_VALID_MODES}, got {mode!r}")
    return GatewayConfig(
        telegram_bot_token=os.environ["TELEGRAM_BOT_TOKEN"],
        langflow_api_url=os.environ["LANGFLOW_API_URL"],
        langflow_flow_id=os.environ["LANGFLOW_FLOW_ID"],
        mode=mode,
    )


async def main() -> None:
    config = load_config()
    bot = Bot(token=config.telegram_bot_token)
    dispatcher = Dispatcher()
    adapter = TelegramAdapter(bot=bot)

    async with httpx.AsyncClient() as http_client:
        langflow_client = LangflowClient(
            base_url=config.langflow_api_url,
            flow_id=config.langflow_flow_id,
            client=http_client,
        )

        @dispatcher.message()
        async def on_message(message: Message) -> None:
            await relay_inbound_message(adapter, langflow_client, message)

        if config.mode == "polling":
            await dispatcher.start_polling(bot)
        else:
            # Webhook mode: registration and the aiohttp server are wired in
            # Task 11 (local deployment), where the public URL (via ngrok
            # locally) is known at container startup.
            raise NotImplementedError(
                "Webhook server wiring is completed in the local-deployment task."
            )


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
