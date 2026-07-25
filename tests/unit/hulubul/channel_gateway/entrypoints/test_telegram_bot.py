import pytest

from hulubul.channel_gateway.entrypoints.telegram_bot import GatewayConfig, load_config


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
