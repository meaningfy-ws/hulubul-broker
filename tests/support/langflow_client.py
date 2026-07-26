"""Authenticated LangFlow API client with actor context support.

Provides a typed client for programmatic LangFlow API calls with:
- API key authentication
- Actor context request-variable headers
- Typed response objects
- Safe repr (no secret exposure)
"""

from dataclasses import dataclass
from typing import Any, Protocol

try:
    import httpx
except ImportError:
    httpx = None  # type: ignore


class ConversationLike(Protocol):
    """Structural contract for the conversation context passed to run_lf00."""

    actor_id: str | None
    display_name: str | None
    session_id: str | None


@dataclass
class FlowReply:
    """Typed response from LangFlow flow run.

    Attributes:
        status_code: HTTP status code from LangFlow API
        flow_id: Identifier of the flow that was run (optional)
        correlation_id: Request correlation ID (optional)
        result: Flow result data (optional)
        error: Error message (optional)
    """

    status_code: int
    flow_id: str | None = None
    correlation_id: str | None = None
    result: dict[str, Any] | None = None
    error: str | None = None

    def __repr__(self) -> str:
        """Safe repr: never expose API key or sensitive data."""
        parts = [f"status={self.status_code}"]
        if self.flow_id:
            parts.append(f"flow_id={self.flow_id}")
        if self.error:
            parts.append(f"error={self.error}")
        return f"FlowReply({', '.join(parts)})"


class LangFlowClient:
    """Authenticated LangFlow API client with actor context support.

    Attributes:
        base_url: Base URL of the LangFlow API (e.g., http://localhost:7860)
        _api_key: Private API key field (never exposed in repr)
    """

    def __init__(self, base_url: str, api_key: str | None = None) -> None:
        """Initialize LangFlow client.

        Args:
            base_url: Base URL of the LangFlow API
            api_key: Optional API key for authentication
        """
        self.base_url = base_url
        self._api_key = api_key

    def _get_headers(self, actor_id: str, display_name: str | None = None) -> dict[str, str]:
        """Build request headers with actor context and API key.

        Args:
            actor_id: Actor identifier (required)
            display_name: Optional human-readable actor display name

        Returns:
            Dictionary of request headers including actor context and auth
        """
        headers: dict[str, str] = {
            "X-LANGFLOW-GLOBAL-VAR-HULUBUL_PHASE1_ACTOR_ID": actor_id,
        }
        if display_name:
            headers["X-LANGFLOW-GLOBAL-VAR-HULUBUL_PHASE1_ACTOR_DISPLAY_NAME"] = display_name
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers

    def run_lf00(self, conversation: ConversationLike, message: str) -> FlowReply:
        """Run LF-00 (main router) flow with actor context.

        Args:
            conversation: Conversation object with actor_id (required)
                         and optional display_name and session_id
            message: User message to process

        Returns:
            FlowReply with status, flow_id, correlation_id, result, or error
        """
        if not conversation.actor_id:
            return FlowReply(status_code=400, error="Missing required actor_id")

        url = f"{self.base_url}/api/v1/run/lf-00"
        headers = self._get_headers(conversation.actor_id, conversation.display_name)
        payload = {
            "input": {
                "message": message,
                "session_id": conversation.session_id,
            }
        }

        try:
            if httpx is None:
                return FlowReply(
                    status_code=500,
                    error="httpx not installed; run: poetry install --with integration",
                )

            with httpx.Client() as client:
                response = client.post(url, json=payload, headers=headers, timeout=30.0)

                if response.status_code == 403:
                    return FlowReply(
                        status_code=403,
                        error="Unauthorized (missing or invalid API key)",
                    )

                if response.status_code == 200:
                    result = response.json()
                    return FlowReply(
                        status_code=200,
                        flow_id="lf-00",
                        correlation_id=result.get("correlation_id"),
                        result=result,
                    )

                return FlowReply(
                    status_code=response.status_code,
                    error=f"LangFlow error: {response.text[:200]}",
                )
        except Exception as e:
            error_str = str(e)
            return FlowReply(status_code=500, error=f"Connection error: {error_str[:200]}")

    def run_without_key(self, flow_id: str, input_data: dict[str, Any]) -> FlowReply:
        """Unauthenticated request (for testing 403 rejection).

        Args:
            flow_id: Flow identifier (e.g., "lf-00")
            input_data: Input data payload

        Returns:
            FlowReply with HTTP status code
        """
        url = f"{self.base_url}/api/v1/run/{flow_id}"

        try:
            if httpx is None:
                return FlowReply(
                    status_code=500,
                    error="httpx not installed; run: poetry install --with integration",
                )

            with httpx.Client() as client:
                response = client.post(url, json=input_data, timeout=30.0)
                return FlowReply(status_code=response.status_code)
        except Exception as e:
            return FlowReply(status_code=500, error=f"Connection error: {str(e)[:200]}")

    def run_with_wrong_key(self, flow_id: str, input_data: dict[str, Any]) -> FlowReply:
        """Request with wrong API key (for testing 403 rejection).

        Args:
            flow_id: Flow identifier (e.g., "lf-00")
            input_data: Input data payload

        Returns:
            FlowReply with HTTP status code
        """
        url = f"{self.base_url}/api/v1/run/{flow_id}"
        headers = {"Authorization": "Bearer wrong-key-12345"}

        try:
            if httpx is None:
                return FlowReply(
                    status_code=500,
                    error="httpx not installed; run: poetry install --with integration",
                )

            with httpx.Client() as client:
                response = client.post(url, json=input_data, headers=headers, timeout=30.0)
                return FlowReply(status_code=response.status_code)
        except Exception as e:
            return FlowReply(status_code=500, error=f"Connection error: {str(e)[:200]}")
