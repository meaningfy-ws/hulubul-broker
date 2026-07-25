import os
from dataclasses import dataclass

import httpx
from aiogram import Bot, Dispatcher
from aiogram.types import Message

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
            import httpx as _httpx
            from aiogram.webhook.aiohttp_server import (
                SimpleRequestHandler,
                setup_application,
            )
            from aiohttp import web

            async with _httpx.AsyncClient() as ngrok_client:
                tunnels_resp = await ngrok_client.get(
                    f"{os.environ.get('NGROK_API_URL', 'http://ngrok:4040')}/api/tunnels"
                )
                public_url = tunnels_resp.json()["tunnels"][0]["public_url"]

            secret = os.environ.get("TELEGRAM_WEBHOOK_SECRET") or None
            await bot.set_webhook(
                url=f"{public_url}/webhook", secret_token=secret, drop_pending_updates=True
            )

            app = web.Application()
            SimpleRequestHandler(dispatcher=dispatcher, bot=bot, secret_token=secret).register(
                app, path="/webhook"
            )
            setup_application(app, dispatcher, bot=bot)
            runner = web.AppRunner(app)
            await runner.setup()
            site = web.TCPSite(runner, host="0.0.0.0", port=8080)
            await site.start()
            await asyncio.Event().wait()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
