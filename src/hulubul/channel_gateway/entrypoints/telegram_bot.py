import asyncio
import os
from dataclasses import dataclass

import httpx
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

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
    webhook_secret: str | None = None


def load_config() -> GatewayConfig:
    mode = os.environ["GATEWAY_MODE"]
    if mode not in _VALID_MODES:
        raise ValueError(f"GATEWAY_MODE must be one of {_VALID_MODES}, got {mode!r}")

    webhook_secret = os.environ.get("TELEGRAM_WEBHOOK_SECRET") or None
    if mode == "webhook" and not webhook_secret:
        raise ValueError(
            "TELEGRAM_WEBHOOK_SECRET is required when GATEWAY_MODE=webhook: without it, "
            "Telegram's webhook signature validation (X-Telegram-Bot-Api-Secret-Token) is "
            "disabled and the public endpoint would accept forged updates from anyone who "
            "reaches it."
        )

    return GatewayConfig(
        telegram_bot_token=os.environ["TELEGRAM_BOT_TOKEN"],
        langflow_api_url=os.environ["LANGFLOW_API_URL"],
        langflow_flow_id=os.environ["LANGFLOW_FLOW_ID"],
        mode=mode,
        webhook_secret=webhook_secret,
    )


async def run_webhook(config: GatewayConfig, bot: Bot, dispatcher: Dispatcher) -> None:
    """Register the Telegram webhook against the local ngrok tunnel and serve it.

    Runs forever (the caller only returns once the process is killed) — extracted out
    of main() so it's mockable/testable without needing a real event loop that never
    returns.
    """
    ngrok_api_url = os.environ.get("NGROK_API_URL", "http://ngrok:4040")
    async with httpx.AsyncClient() as ngrok_client:
        try:
            tunnels_resp = await ngrok_client.get(f"{ngrok_api_url}/api/tunnels")
            tunnels_resp.raise_for_status()
            tunnels = tunnels_resp.json()["tunnels"]
            if not tunnels:
                raise RuntimeError(
                    f"ngrok reported no active tunnels at {ngrok_api_url}/api/tunnels — it "
                    "may still be starting up. Wait for it to finish establishing a tunnel "
                    "and retry."
                )
            public_url = tunnels[0]["public_url"]
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            raise RuntimeError(
                f"Could not read the ngrok tunnel list from {ngrok_api_url}/api/tunnels: "
                f"{exc}. Is the 'ngrok' container up (docker compose --profile webhook up) "
                "and has it finished establishing a tunnel?"
            ) from exc

    await bot.set_webhook(
        url=f"{public_url}/webhook",
        secret_token=config.webhook_secret,
        drop_pending_updates=True,
    )

    app = web.Application()
    SimpleRequestHandler(
        dispatcher=dispatcher, bot=bot, secret_token=config.webhook_secret
    ).register(app, path="/webhook")
    setup_application(app, dispatcher, bot=bot)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=8080)
    await site.start()
    await asyncio.Event().wait()


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

        @dispatcher.message(F.text)
        async def on_message(message: Message) -> None:
            await relay_inbound_message(adapter, langflow_client, message)

        if config.mode == "polling":
            await dispatcher.start_polling(bot)
        else:
            await run_webhook(config, bot, dispatcher)


if __name__ == "__main__":
    asyncio.run(main())
