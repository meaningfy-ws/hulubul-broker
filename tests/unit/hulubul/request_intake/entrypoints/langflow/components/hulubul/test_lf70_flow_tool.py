"""Tests for the deterministic LF-70 flow tool bridge."""

import json

import pytest
from lfx.schema.message import Message

from hulubul.core.models.operational.enums import DataOperation, DataOperationOutcome
from hulubul.request_intake.entrypoints.langflow.components.hulubul.lf70_flow_tool import (
    HulubulLf70FlowTool,
)


def _lf70_run_response(text: str) -> dict:
    return {
        "outputs": [
            {
                "outputs": [
                    {
                        "results": {
                            "message": {
                                "data": {
                                    "text": text,
                                }
                            }
                        }
                    }
                ]
            }
        ]
    }


def _confirmed_result(request_id: str = "req-test-001") -> str:
    return json.dumps(
        {
            "operation": "createDeliveryRequest",
            "outcome": "confirmed",
            "success": True,
            "write_dispatched": True,
            "request_id": request_id,
            "status": "new",
            "count": 1,
            "result": {"request_id": request_id},
            "created_at": "2026-07-30T05:02:01.891Z",
            "updated_at": "2026-07-30T05:02:01.891Z",
            "error_code": None,
        }
    )


def test_extracts_and_validates_data_operation_result() -> None:
    """The bridge returns only validated DataOperationResult JSON text."""
    component = HulubulLf70FlowTool()

    result = component._validated_result_message(_lf70_run_response(_confirmed_result()))

    assert isinstance(result, Message)
    parsed = json.loads(result.text)
    assert parsed["operation"] == DataOperation.CREATE_DELIVERY_REQUEST.value
    assert parsed["outcome"] == DataOperationOutcome.CONFIRMED.value
    assert parsed["request_id"] == "req-test-001"


def test_rejects_non_result_echo() -> None:
    """A request echo from LF-70 is not accepted as a successful result."""
    component = HulubulLf70FlowTool()
    echo = json.dumps(
        {
            "operation": "createDeliveryRequest",
            "identifiers": {"request_id": "req-echo"},
            "facts": {"receiver_name": "Echo"},
        }
    )

    result = component._validated_result_message(_lf70_run_response(echo))

    assert json.loads(result.text)["code"] == "MALFORMED_AGENT_RESULT"


def test_builds_langflow_run_payload_with_raw_input_json() -> None:
    """LF-70 receives the exact DataOperationRequest JSON as input_value."""
    payload_text = '{"operation":"createDeliveryRequest"}'

    payload = HulubulLf70FlowTool._build_run_payload(payload_text, "session-1")

    assert payload == {"input_value": payload_text, "session_id": "session-1"}


def test_call_lf70_uses_validated_response(monkeypatch: pytest.MonkeyPatch) -> None:
    """The public component method returns the validated LF-70 response."""
    component = HulubulLf70FlowTool()
    component.input_value = '{"operation":"createDeliveryRequest"}'
    component.session_id = "session-1"
    component.target_flow_id = "flow-1"
    component.base_url = "http://langflow.local"

    def fake_post(base_url: str, flow_id: str, auth_value: str, payload: dict) -> dict:
        assert base_url == "http://langflow.local"
        assert flow_id == "flow-1"
        assert payload["input_value"] == component.input_value
        return _lf70_run_response(_confirmed_result("req-from-post"))

    monkeypatch.setattr(component, "_post_lf70", fake_post)

    result = component.call_lf70()

    assert json.loads(result.text)["request_id"] == "req-from-post"
