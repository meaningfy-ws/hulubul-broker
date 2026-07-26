import asyncio
import logging
import os
import signal
from dataclasses import dataclass
from enum import Enum

import httpx
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

from hulubul.channel_gateway.adapters.langflow_client import LangflowClient
from hulubul.channel_gateway.adapters.telegram_adapter import TelegramAdapter
from hulubul.channel_gateway.services.relay_message import relay_inbound_message

logger = logging.getLogger(__name__)


class GatewayMode(str, Enum):
    polling = "polling"
    webhook = "webhook"


@dataclass(frozen=True)
class GatewayConfig:
    telegram_bot_token: str
    langflow_api_url: str
    langflow_flow_id: str
    mode: GatewayMode
    webhook_secret: str | None = None


def load_config() -> GatewayConfig:
    mode_value = os.environ["GATEWAY_MODE"]
    try:
        mode = GatewayMode(mode_value)
    except ValueError as exc:
        valid = [m.value for m in GatewayMode]
        raise ValueError(f"GATEWAY_MODE must be one of {valid}, got {mode_value!r}") from exc

    webhook_secret = os.environ.get("TELEGRAM_WEBHOOK_SECRET") or None
    if mode == GatewayMode.webhook and not webhook_secret:
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

    Runs until SIGTERM/SIGINT — extracted out of main() so it's mockable/testable
    without needing a real event loop. `SimpleRequestHandler` defaults to handling
    updates as background tasks, so a signal-driven shutdown that runs `runner.cleanup()`
    is what stops in-flight requests from being lost silently on redeploy.
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
        allowed_updates=dispatcher.resolve_used_update_types(),
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

    shutdown_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, shutdown_event.set)

    try:
        await shutdown_event.wait()
    finally:
        await runner.cleanup()


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

        @dispatcher.message()
        async def on_non_text_message(message: Message) -> None:
            logger.info(
                "Ignoring non-text message in chat %s (no text content to relay).",
                message.chat.id,
            )

        if config.mode == GatewayMode.polling:
            await dispatcher.start_polling(bot)
        else:
            await run_webhook(config, bot, dispatcher)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    asyncio.run(main())
