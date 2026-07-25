from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from hulubul.channel_gateway.entrypoints.telegram_bot import GatewayConfig, load_config, main


def test_load_config_reads_required_environment_variables(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:abc")
    monkeypatch.setenv("LANGFLOW_API_URL", "http://langflow:7860")
    monkeypatch.setenv("LANGFLOW_FLOW_ID", "flow-1")
    monkeypatch.setenv("GATEWAY_MODE", "polling")

    config = load_config()

    assert config == GatewayConfig(
        telegram_bot_token="123:abc",
        langflow_api_url="http://langflow:7860",
        langflow_flow_id="flow-1",
        mode="polling",
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
