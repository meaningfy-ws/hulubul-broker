"""Unit tests for LangFlowClient.run_flow_with_actor's bounded retry.

Covers the retry-on-unparseable-result behavior added to work around
checkpoint8 runbook bug #17: the same well-formed request occasionally gets
an OperationalError back instead of a DataOperationResult, because the
model's final answer didn't extract cleanly. Retrying the whole flow call is
safe here (unlike DEC-015's prohibited write-retry) because Neo4j's
uniqueness constraint / compare-and-set makes a retry of an
already-succeeded write come back rejected, never a silent duplicate.
"""

from typing import Any
from unittest.mock import MagicMock, patch

from tests.support.langflow_client import LangFlowClient

_VALID_RESULT = {
    "operation": "createDeliveryRequest",
    "outcome": "confirmed",
    "success": True,
}
_UNPARSEABLE_RESULT = {
    "schema_version": "1.0.0",
    "code": "INVALID_CONTRACT",
    "category": "contract",
}


def _mock_response(status_code: int, body: dict[str, Any]) -> MagicMock:
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = {
        "outputs": [{"outputs": [{"outputs": {"response": {"message": body}}}]}]
    }
    response.text = str(body)
    return response


def _mock_client(*post_side_effects: MagicMock) -> MagicMock:
    client = MagicMock()
    client.__enter__.return_value = client
    client.__exit__.return_value = False
    client.post.side_effect = list(post_side_effects)
    return client


class TestRetryOnUnparseableResult:
    def test_retries_once_then_succeeds(self) -> None:
        first = _mock_response(200, _UNPARSEABLE_RESULT)
        second = _mock_response(200, _VALID_RESULT)
        client = _mock_client(first, second)

        with (
            patch("tests.support.langflow_client.httpx.Client", return_value=client),
            patch("tests.support.langflow_client.time.sleep") as mock_sleep,
        ):
            reply = LangFlowClient(base_url="http://x", api_key="k").run_flow_with_actor(
                "flow-1", {"correlation_id": "c1"}
            )

        assert reply.status_code == 200
        assert reply.result == _VALID_RESULT
        assert client.post.call_count == 2
        mock_sleep.assert_called_once_with(0.5)

    def test_no_retry_when_first_result_is_valid(self) -> None:
        client = _mock_client(_mock_response(200, _VALID_RESULT))

        with patch("tests.support.langflow_client.httpx.Client", return_value=client):
            reply = LangFlowClient(base_url="http://x", api_key="k").run_flow_with_actor(
                "flow-1", {"correlation_id": "c1"}
            )

        assert reply.status_code == 200
        assert reply.result == _VALID_RESULT
        assert client.post.call_count == 1

    def test_exhausts_attempts_and_returns_last_unparseable_result(self) -> None:
        client = _mock_client(
            _mock_response(200, _UNPARSEABLE_RESULT),
            _mock_response(200, _UNPARSEABLE_RESULT),
        )

        with (
            patch("tests.support.langflow_client.httpx.Client", return_value=client),
            patch("tests.support.langflow_client.time.sleep"),
        ):
            reply = LangFlowClient(base_url="http://x", api_key="k").run_flow_with_actor(
                "flow-1", {"correlation_id": "c1"}
            )

        assert reply.status_code == 200
        assert reply.result == _UNPARSEABLE_RESULT
        assert client.post.call_count == 2

    def test_max_attempts_1_disables_retry(self) -> None:
        client = _mock_client(_mock_response(200, _UNPARSEABLE_RESULT))

        with patch("tests.support.langflow_client.httpx.Client", return_value=client):
            reply = LangFlowClient(base_url="http://x", api_key="k").run_flow_with_actor(
                "flow-1", {"correlation_id": "c1"}, max_attempts=1
            )

        assert reply.status_code == 200
        assert reply.result == _UNPARSEABLE_RESULT
        assert client.post.call_count == 1

    def test_does_not_retry_on_403(self) -> None:
        forbidden = MagicMock()
        forbidden.status_code = 403
        client = _mock_client(forbidden)

        with patch("tests.support.langflow_client.httpx.Client", return_value=client):
            reply = LangFlowClient(base_url="http://x", api_key="k").run_flow_with_actor(
                "flow-1", {"correlation_id": "c1"}
            )

        assert reply.status_code == 403
        assert client.post.call_count == 1

    def test_retries_when_extraction_returns_none(self) -> None:
        """A malformed outputs envelope (extraction returns None) also retries once."""
        malformed = MagicMock()
        malformed.status_code = 200
        malformed.json.return_value = {"outputs": []}
        second = _mock_response(200, _VALID_RESULT)
        client = _mock_client(malformed, second)

        with (
            patch("tests.support.langflow_client.httpx.Client", return_value=client),
            patch("tests.support.langflow_client.time.sleep"),
        ):
            reply = LangFlowClient(base_url="http://x", api_key="k").run_flow_with_actor(
                "flow-1", {"correlation_id": "c1"}
            )

        assert reply.status_code == 200
        assert reply.result == _VALID_RESULT
        assert client.post.call_count == 2
