from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from hulubul.channel_gateway.entrypoints.telegram_bot import (
    GatewayConfig,
    GatewayMode,
    load_config,
    main,
    run_webhook,
)


def test_load_config_reads_required_environment_variables(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:abc")
    monkeypatch.setenv("LANGFLOW_API_URL", "http://langflow:7860")
    monkeypatch.setenv("LANGFLOW_FLOW_ID", "flow-1")
    monkeypatch.setenv("GATEWAY_MODE", "polling")
    monkeypatch.delenv("TELEGRAM_WEBHOOK_SECRET", raising=False)

    config = load_config()

    assert config == GatewayConfig(
        telegram_bot_token="123:abc",
        langflow_api_url="http://langflow:7860",
        langflow_flow_id="flow-1",
        mode=GatewayMode.polling,
    )


def test_load_config_raises_when_a_required_variable_is_missing(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.setenv("LANGFLOW_API_URL", "http://langflow:7860")
    monkeypatch.setenv("LANGFLOW_FLOW_ID", "flow-1")
    monkeypatch.setenv("GATEWAY_MODE", "polling")

    with pytest.raises(KeyError):
        load_config()


def test_load_config_rejects_an_unknown_gateway_mode(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:abc")
    monkeypatch.setenv("LANGFLOW_API_URL", "http://langflow:7860")
    monkeypatch.setenv("LANGFLOW_FLOW_ID", "flow-1")
    monkeypatch.setenv("GATEWAY_MODE", "carrier-pigeon")

    with pytest.raises(ValueError, match="GATEWAY_MODE"):
        load_config()


def test_load_config_requires_webhook_secret_in_webhook_mode(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:abc")
    monkeypatch.setenv("LANGFLOW_API_URL", "http://langflow:7860")
    monkeypatch.setenv("LANGFLOW_FLOW_ID", "flow-1")
    monkeypatch.setenv("GATEWAY_MODE", "webhook")
    monkeypatch.delenv("TELEGRAM_WEBHOOK_SECRET", raising=False)

    with pytest.raises(ValueError, match="TELEGRAM_WEBHOOK_SECRET"):
        load_config()


def test_load_config_accepts_webhook_mode_when_secret_is_set(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:abc")
    monkeypatch.setenv("LANGFLOW_API_URL", "http://langflow:7860")
    monkeypatch.setenv("LANGFLOW_FLOW_ID", "flow-1")
    monkeypatch.setenv("GATEWAY_MODE", "webhook")
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "s3cr3t")

    config = load_config()

    assert config == GatewayConfig(
        telegram_bot_token="123:abc",
        langflow_api_url="http://langflow:7860",
        langflow_flow_id="flow-1",
        mode=GatewayMode.webhook,
        webhook_secret="s3cr3t",
    )


def test_load_config_does_not_require_webhook_secret_in_polling_mode(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:abc")
    monkeypatch.setenv("LANGFLOW_API_URL", "http://langflow:7860")
    monkeypatch.setenv("LANGFLOW_FLOW_ID", "flow-1")
    monkeypatch.setenv("GATEWAY_MODE", "polling")
    monkeypatch.delenv("TELEGRAM_WEBHOOK_SECRET", raising=False)

    config = load_config()

    assert config.mode == "polling"
    assert config.webhook_secret is None


@pytest.mark.asyncio
async def test_main_wires_telegram_adapter_and_starts_polling(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:abc")
    monkeypatch.setenv("LANGFLOW_API_URL", "http://langflow:7860")
    monkeypatch.setenv("LANGFLOW_FLOW_ID", "flow-1")
    monkeypatch.setenv("GATEWAY_MODE", "polling")

    fake_bot = MagicMock()
    fake_dispatcher = MagicMock()
    fake_dispatcher.start_polling = AsyncMock()

    fake_http_client = AsyncMock()
    fake_http_client.__aenter__.return_value = fake_http_client
    fake_http_client.__aexit__.return_value = None

    with (
        patch(
            "hulubul.channel_gateway.entrypoints.telegram_bot.Bot", return_value=fake_bot
        ) as bot_cls,
        patch(
            "hulubul.channel_gateway.entrypoints.telegram_bot.Dispatcher",
            return_value=fake_dispatcher,
        ),
        patch(
            "hulubul.channel_gateway.entrypoints.telegram_bot.httpx.AsyncClient",
            return_value=fake_http_client,
        ),
    ):
        await main()

    bot_cls.assert_called_once_with(token="123:abc")
    fake_dispatcher.start_polling.assert_awaited_once_with(fake_bot)


def _webhook_config(webhook_secret="s3cr3t"):
    return GatewayConfig(
        telegram_bot_token="123:abc",
        langflow_api_url="http://langflow:7860",
        langflow_flow_id="flow-1",
        mode=GatewayMode.webhook,
        webhook_secret=webhook_secret,
    )


def _fake_ngrok_client(tunnels):
    fake_client = AsyncMock()
    fake_client.__aenter__.return_value = fake_client
    fake_client.__aexit__.return_value = None
    tunnels_response = MagicMock()
    tunnels_response.raise_for_status = MagicMock()
    tunnels_response.json.return_value = {"tunnels": tunnels}
    fake_client.get = AsyncMock(return_value=tunnels_response)
    return fake_client


@pytest.mark.asyncio
async def test_run_webhook_registers_bot_webhook_with_secret_token_and_ngrok_url(monkeypatch):
    config = _webhook_config()
    monkeypatch.setenv("NGROK_API_URL", "http://ngrok:4040")

    fake_bot = MagicMock()
    fake_bot.set_webhook = AsyncMock()
    fake_dispatcher = MagicMock()
    fake_dispatcher.resolve_used_update_types = MagicMock(return_value=["message"])
    fake_ngrok_client = _fake_ngrok_client([{"public_url": "https://abc123.ngrok.io"}])

    fake_runner = MagicMock()
    fake_runner.setup = AsyncMock()
    fake_runner.cleanup = AsyncMock()
    fake_site = MagicMock()
    fake_site.start = AsyncMock()
    fake_event = MagicMock()
    fake_event.wait = AsyncMock()

    with (
        patch(
            "hulubul.channel_gateway.entrypoints.telegram_bot.httpx.AsyncClient",
            return_value=fake_ngrok_client,
        ),
        patch("hulubul.channel_gateway.entrypoints.telegram_bot.web.Application"),
        patch(
            "hulubul.channel_gateway.entrypoints.telegram_bot.web.AppRunner",
            return_value=fake_runner,
        ),
        patch(
            "hulubul.channel_gateway.entrypoints.telegram_bot.web.TCPSite",
            return_value=fake_site,
        ),
        patch(
            "hulubul.channel_gateway.entrypoints.telegram_bot.SimpleRequestHandler"
        ) as handler_cls,
        patch("hulubul.channel_gateway.entrypoints.telegram_bot.setup_application"),
        patch(
            "hulubul.channel_gateway.entrypoints.telegram_bot.asyncio.Event",
            return_value=fake_event,
        ),
    ):
        await run_webhook(config, fake_bot, fake_dispatcher)

    fake_ngrok_client.get.assert_awaited_once_with("http://ngrok:4040/api/tunnels")
    fake_bot.set_webhook.assert_awaited_once_with(
        url="https://abc123.ngrok.io/webhook",
        secret_token="s3cr3t",
        allowed_updates=["message"],
        drop_pending_updates=True,
    )
    handler_cls.assert_called_once_with(
        dispatcher=fake_dispatcher, bot=fake_bot, secret_token="s3cr3t"
    )
    fake_site.start.assert_awaited_once()
    fake_event.wait.assert_awaited_once()
    fake_runner.cleanup.assert_awaited_once()


@pytest.mark.asyncio
async def test_run_webhook_raises_a_clear_error_when_ngrok_has_no_tunnels(monkeypatch):
    config = _webhook_config()
    monkeypatch.setenv("NGROK_API_URL", "http://ngrok:4040")

    fake_bot = MagicMock()
    fake_dispatcher = MagicMock()
    fake_ngrok_client = _fake_ngrok_client([])

    with (
        patch(
            "hulubul.channel_gateway.entrypoints.telegram_bot.httpx.AsyncClient",
            return_value=fake_ngrok_client,
        ),
        pytest.raises(RuntimeError, match="no active tunnels"),
    ):
        await run_webhook(config, fake_bot, fake_dispatcher)


@pytest.mark.asyncio
async def test_run_webhook_raises_a_clear_error_when_the_ngrok_request_fails(monkeypatch):
    import httpx

    config = _webhook_config()
    monkeypatch.setenv("NGROK_API_URL", "http://ngrok:4040")

    fake_bot = MagicMock()
    fake_dispatcher = MagicMock()
    fake_ngrok_client = AsyncMock()
    fake_ngrok_client.__aenter__.return_value = fake_ngrok_client
    fake_ngrok_client.__aexit__.return_value = None
    fake_ngrok_client.get = AsyncMock(side_effect=httpx.ConnectError("connection refused"))

    with (
        patch(
            "hulubul.channel_gateway.entrypoints.telegram_bot.httpx.AsyncClient",
            return_value=fake_ngrok_client,
        ),
        pytest.raises(RuntimeError, match="Could not read the ngrok tunnel list"),
    ):
        await run_webhook(config, fake_bot, fake_dispatcher)
