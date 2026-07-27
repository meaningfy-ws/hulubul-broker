"""Authenticated LangFlow API client with actor context support.

Provides a typed client for programmatic LangFlow API calls with:
- API key authentication
- Actor context request-variable headers
- Typed response objects
- Safe repr (no secret exposure)
"""

import json
import uuid
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
            # LangFlow's api_key_security dependency reads the literal header
            # name "x-api-key" (see langflow.services.auth.utils.api_key_header),
            # not a Bearer Authorization header -- confirmed live: every call
            # through this client 403'd regardless of payload shape until this
            # was fixed.
            headers["x-api-key"] = self._api_key
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
        headers = {"x-api-key": "wrong-key-12345"}

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

    def run_flow_with_actor(
        self, flow_uuid: str, input_data: dict[str, Any], actor_id: str = "test-actor"
    ) -> FlowReply:
        """Call a flow by stable UUID with actor context headers.

        Used for calling LF-70 and other data operation flows that require
        typed actor context via request-variable headers.

        Args:
            flow_uuid: Stable flow UUID (e.g., "94f6774d-ebc7-5bf1-8486-886f91886a5f")
            input_data: Input data payload (e.g., DataOperationRequest)
            actor_id: Actor identifier for context (default: "test-actor")

        Returns:
            FlowReply with status, flow_id, correlation_id, result, or error
        """
        url = f"{self.base_url}/api/v1/run/{flow_uuid}"
        headers = self._get_headers(actor_id)

        # LangFlow's SimplifiedAPIRequest wants the payload serialized under
        # `input_value` (a JSON string), not posted as the raw top-level body --
        # a flat body silently validates as an empty request (input_value=None),
        # which is dropped before it ever reaches the flow's entry component.
        # `input_type`/`output_type` must be "any": LF-70 has no ChatInput/
        # ChatOutput component, and "chat" (the API default) filters out every
        # vertex whose declared type isn't literally "ChatInput". A distinct
        # `session_id` per call keeps chat memory (if any) from bleeding
        # between test invocations that hit the same flow_id.
        session_id = str(input_data.get("correlation_id") or uuid.uuid4())
        body = {
            "input_value": json.dumps(input_data),
            "input_type": "any",
            "output_type": "any",
            "session_id": session_id,
        }

        try:
            if httpx is None:
                return FlowReply(
                    status_code=500,
                    error="httpx not installed; run: poetry install --with integration",
                )

            with httpx.Client() as client:
                response = client.post(url, json=body, headers=headers, timeout=60.0)

                if response.status_code == 403:
                    return FlowReply(
                        status_code=403,
                        error="Unauthorized (missing or invalid API key)",
                    )

                if response.status_code == 200:
                    result = response.json()
                    return FlowReply(
                        status_code=200,
                        flow_id=flow_uuid,
                        result=self._extract_result_message(result),
                    )

                return FlowReply(
                    status_code=response.status_code,
                    error=f"LangFlow error: {response.text[:200]}",
                )
        except Exception as e:
            error_str = str(e)
            return FlowReply(status_code=500, error=f"Connection error: {error_str[:200]}")

    @staticmethod
    def _extract_result_message(response: dict[str, Any]) -> dict[str, Any] | None:
        """Pull the terminal component's `DataOperationResult`/error dict out of
        the Run API's nested response envelope (`outputs[0].outputs[0].outputs.response.message`).
        """
        try:
            outputs = response["outputs"][0]["outputs"]
        except (KeyError, IndexError, TypeError):
            return None
        for output in outputs:
            message = output.get("outputs", {}).get("response", {}).get("message")
            if isinstance(message, dict):
                return message
        return None
