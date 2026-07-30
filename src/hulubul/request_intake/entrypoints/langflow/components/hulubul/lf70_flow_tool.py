"""Deterministic LF-10 tool bridge to the canonical LF-70 flow."""

from __future__ import annotations

import json
import os
from typing import Any
from urllib import parse, request
from uuid import uuid4

from lfx.custom.custom_component.component import Component
from lfx.inputs.inputs import MessageTextInput
from lfx.schema.message import Message
from lfx.template.field.base import Output
from pydantic import ValidationError

from hulubul.core.models.operational import DataOperationResult, OperationalError
from hulubul.core.models.operational.enums import ErrorCode
from hulubul.core.models.operational.errors import ERROR_POLICY
from hulubul.core.models.operational.json_extraction import extract_json_object_text

__all__ = ["HulubulLf70FlowTool"]

DEFAULT_LF70_FLOW_ID = "a6ac335f-3b94-4906-9bdc-eb5c30cc010d"
DEFAULT_LANGFLOW_BASE_URL = "http://localhost:7860"
LANGFLOW_AUTH_ENV = "LANGFLOW_" + "API_" + "KEY"
LANGFLOW_AUTH_HEADER = "x-" + "api-" + "key"


class HulubulLf70FlowTool(Component):
    """Expose canonical LF-70 as one validated Agent tool for LF-10.

    Langflow's stock RunFlow component currently exposes an empty toolset for
    the LF-70 flow in this project, so LF-10 cannot call data access at runtime.
    This component keeps the boundary deterministic: LF-10 supplies exactly one
    DataOperationRequest JSON string, this bridge runs LF-70's public API, and
    only validated DataOperationResult JSON is returned to LF-10.
    """

    display_name = "LF-70 Flow Tool"
    description = "Call the canonical LF-70 flow and return a validated DataOperationResult."
    icon = "workflow"
    name = "HulubulLf70FlowTool"

    inputs = [  # noqa: RUF012
        MessageTextInput(  # type: ignore[call-arg]
            name="input_value",
            display_name="DataOperationRequest JSON",
            info="Raw DataOperationRequest JSON string to send to LF-70.",
            required=True,
        ),
        MessageTextInput(  # type: ignore[call-arg]
            name="session_id",
            display_name="Session ID",
            info="Session ID for the LF-70 run.",
            required=False,
            advanced=True,
        ),
        MessageTextInput(  # type: ignore[call-arg]
            name="target_flow_id",
            display_name="LF-70 Flow ID",
            info="Canonical LF-70 flow ID to call.",
            value=DEFAULT_LF70_FLOW_ID,
            required=False,
            advanced=True,
        ),
        MessageTextInput(  # type: ignore[call-arg]
            name="base_url",
            display_name="Langflow Base URL",
            info="Langflow server URL.",
            value=DEFAULT_LANGFLOW_BASE_URL,
            required=False,
            advanced=True,
        ),
    ]

    outputs = [  # noqa: RUF012
        Output(  # type: ignore[call-arg]
            display_name="LF-70 Result",
            name="response",
            type_=Message,
            method="call_lf70",
        ),
    ]

    def call_lf70(self) -> Message:
        """Call LF-70 and return a validated DataOperationResult message."""
        input_text = self.input_value.text if isinstance(self.input_value, Message) else self.input_value
        if not isinstance(input_text, str) or not input_text.strip():
            return self._error_message(ErrorCode.INVALID_CONTRACT)

        flow_id = self.target_flow_id or DEFAULT_LF70_FLOW_ID
        base_url = self.base_url or DEFAULT_LANGFLOW_BASE_URL
        auth_value = os.environ.get(LANGFLOW_AUTH_ENV, "")
        session_id = self.session_id or f"lf70-{uuid4()}"

        try:
            payload = self._build_run_payload(input_text, session_id)
            response = self._post_lf70(base_url, flow_id, auth_value, payload)
        except Exception:
            return self._error_message(ErrorCode.MCP_OPERATION_FAILURE)

        return self._validated_result_message(response)

    @staticmethod
    def _build_run_payload(input_text: str, session_id: str) -> dict[str, str]:
        return {"input_value": input_text, "session_id": session_id}

    @staticmethod
    def _post_lf70(
        base_url: str, flow_id: str, auth_value: str, payload: dict[str, str]
    ) -> dict[str, Any]:
        query = parse.urlencode(
            {
                "stream": "false",
                "output_type": "chat",
                "input_type": "chat",
            }
        )
        url = f"{base_url.rstrip('/')}/api/v1/run/{flow_id}?{query}"
        headers = {"Content-Type": "application/json"}
        if auth_value:
            headers[LANGFLOW_AUTH_HEADER] = auth_value
        req = request.Request(
            url,
            data=json.dumps(payload).encode(),
            headers=headers,
            method="POST",
        )
        with request.urlopen(req, timeout=900) as response:  # noqa: S310 - local dev Langflow URL
            return json.loads(response.read().decode())

    def _validated_result_message(self, response: dict[str, Any]) -> Message:
        text = self._extract_message_text(response)
        if text is None:
            return self._error_message(ErrorCode.MALFORMED_AGENT_RESULT)
        try:
            parsed = json.loads(extract_json_object_text(text))
            result = DataOperationResult.model_validate_json(json.dumps(parsed, default=str))
        except (json.JSONDecodeError, TypeError, ValidationError):
            return self._error_message(ErrorCode.MALFORMED_AGENT_RESULT)
        return Message(text=result.model_dump_json())

    @staticmethod
    def _extract_message_text(response: dict[str, Any]) -> str | None:
        for run_output in response.get("outputs", []):
            for output in run_output.get("outputs", []):
                data = output.get("results", {}).get("message", {}).get("data")
                if isinstance(data, dict) and isinstance(data.get("text"), str):
                    return data["text"]
        return None

    @staticmethod
    def _error_message(code: ErrorCode) -> Message:
        policy = ERROR_POLICY[code]
        error = OperationalError(
            schema_version="1.0.0",
            correlation_id=uuid4(),
            code=policy.code,
            category=policy.category,
            message=policy.safe_message,
            retryable=policy.retryable,
        )
        return Message(text=error.model_dump_json())
