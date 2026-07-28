"""Tests for RoutingContextAdapterComponent.

Verifies the deterministic RoutingLookupRecord -> RoutingContext adaptation
(adapt_routing_lookup, independently unit-tested in
tests/unit/hulubul/core/models/operational/test_routing.py) is correctly
wired into a DataOperationResult for getRequestRoutingContext, and that every
other operation passes through unchanged. Root cause context: leaving this
classification to the Agent caused a live recursion-limit crash (no schema
grounding to work from, blind exploration burning all iterations) -- see
data_access_agent.py and design.md ("LF-70 does not instantiate RoutingContext
directly from a Neo4j row").
"""

import json
from typing import Any
from uuid import uuid4

from lfx.schema.message import Message

from hulubul.core.models.operational import DataOperation, DataOperationOutcome, ErrorCode
from hulubul.request_intake.entrypoints.langflow.components.hulubul.routing_context_adapter import (
    RoutingContextAdapterComponent,
)

FIXED_CORRELATION_ID = str(uuid4())


def _routing_request(**overrides: Any) -> dict[str, Any]:
    request = {
        "schema_version": "1.0.0",
        "correlation_id": FIXED_CORRELATION_ID,
        "operation": DataOperation.GET_REQUEST_ROUTING_CONTEXT.value,
        "operation_id": "op-001",
        "caller": "LF-00",
        "session_id": "p1-001",
        "actor_id": "urn:uuid:test-actor",
    }
    request.update(overrides)
    return request


def _adapter(raw_value: Any, request_dict: Any) -> RoutingContextAdapterComponent:
    adapter = RoutingContextAdapterComponent()
    adapter.raw_value = raw_value
    adapter.request_dict = request_dict
    return adapter


class TestPassthroughForOtherOperations:
    """Only getRequestRoutingContext is adapted; every other operation's raw
    Agent output flows through unchanged."""

    def test_read_delivery_request_passes_through(self) -> None:
        agent_output = {"operation": "readDeliveryRequest", "outcome": "confirmed", "success": True}
        request = _routing_request(
            operation=DataOperation.READ_DELIVERY_REQUEST.value, request_id="req-001"
        )
        adapter = _adapter(json.dumps(agent_output), json.dumps(request))
        result = adapter.build_output()
        assert json.loads(str(result.text)) == agent_output

    def test_passthrough_preserves_message_object_when_raw_value_is_a_message(self) -> None:
        agent_message = Message(text=json.dumps({"anything": "goes"}))
        request = _routing_request(
            operation=DataOperation.READ_DELIVERY_REQUEST.value, request_id="req-001"
        )
        adapter = _adapter(agent_message, json.dumps(request))
        result = adapter.build_output()
        assert result is agent_message


class TestRoutingContextAdaptation:
    def test_no_binding_becomes_confirmed_absent_context(self) -> None:
        raw_lookup = {
            "binding_count": 0,
            "active_relationship_count": 0,
            "active_target_count": 0,
            "requests": [],
        }
        adapter = _adapter(json.dumps(raw_lookup), json.dumps(_routing_request()))
        result = adapter.build_output()
        payload = json.loads(str(result.text))

        assert payload["operation"] == DataOperation.GET_REQUEST_ROUTING_CONTEXT.value
        assert payload["outcome"] == DataOperationOutcome.CONFIRMED.value
        assert payload["success"] is True
        assert payload["result"]["binding_state"] == "absent"
        assert payload["result"]["binding_count"] == 0
        assert payload["result"]["request_id"] is None

    def test_bound_new_request_becomes_confirmed_bound_context(self) -> None:
        raw_lookup = {
            "binding_count": 1,
            "active_relationship_count": 1,
            "active_target_count": 1,
            "requests": [{"request_id": "req-001", "request_status_raw": "new", "closed": None}],
        }
        adapter = _adapter(json.dumps(raw_lookup), json.dumps(_routing_request()))
        result = adapter.build_output()
        payload = json.loads(str(result.text))

        assert payload["outcome"] == DataOperationOutcome.CONFIRMED.value
        assert payload["result"]["binding_state"] == "bound"
        assert payload["result"]["request_id"] == "req-001"
        assert payload["result"]["request_status"] == "new"

    def test_closed_request_takes_precedence_over_status(self) -> None:
        raw_lookup = {
            "binding_count": 1,
            "active_relationship_count": 1,
            "active_target_count": 1,
            "requests": [
                {
                    "request_id": "req-001",
                    "request_status_raw": "new",
                    "closed": "2026-01-01T00:00:00+00:00",
                }
            ],
        }
        adapter = _adapter(json.dumps(raw_lookup), json.dumps(_routing_request()))
        result = adapter.build_output()
        payload = json.loads(str(result.text))

        assert payload["result"]["routing_stage"] == "closed"
        assert payload["result"]["request_status"] is None

    def test_unknown_raw_status_is_rejected_with_unsupported_request_status(self) -> None:
        raw_lookup = {
            "binding_count": 1,
            "active_relationship_count": 1,
            "active_target_count": 1,
            "requests": [
                {
                    "request_id": "req-001",
                    "request_status_raw": "totally-made-up-status",
                    "closed": None,
                }
            ],
        }
        adapter = _adapter(json.dumps(raw_lookup), json.dumps(_routing_request()))
        result = adapter.build_output()
        payload = json.loads(str(result.text))

        assert payload["outcome"] == DataOperationOutcome.REJECTED.value
        assert payload["success"] is False
        assert payload["error_code"] == ErrorCode.UNSUPPORTED_REQUEST_STATUS.value


class TestMarkdownWrappedAgentOutput:
    """Confirmed live: despite being instructed to emit only JSON, the model
    wrapped its answer in prose and a markdown code fence ("I have the query
    result... ```json\\n{...}\\n```"). Extraction must recover the JSON object
    from that wrapping rather than treating it as malformed."""

    def test_prose_and_markdown_fence_are_stripped(self) -> None:
        raw_lookup = {
            "binding_count": 0,
            "active_relationship_count": 0,
            "active_target_count": 0,
            "requests": [],
        }
        wrapped = (
            "I have the query result. Now let me construct the answer.\n\n"
            "```json\n" + json.dumps(raw_lookup) + "\n```"
        )
        adapter = _adapter(wrapped, json.dumps(_routing_request()))
        result = adapter.build_output()
        payload = json.loads(str(result.text))

        assert payload["outcome"] == DataOperationOutcome.CONFIRMED.value
        assert payload["result"]["binding_state"] == "absent"

    def test_final_unfenced_answer_after_a_fenced_draft_is_preferred(self) -> None:
        """Confirmed live: the model sometimes "thinks out loud" with a fenced
        *draft* JSON block, then produces the real (unfenced) final answer
        afterwards. A naive first-match extraction grabs the draft, which is
        typically a different (incomplete/wrong-shape) object -- exactly what
        caused a ~50% live failure rate on readDeliveryRequest before this fix."""
        final = {
            "binding_count": 0,
            "active_relationship_count": 0,
            "active_target_count": 0,
            "requests": [],
        }
        wrapped = (
            "Let me draft the shape first.\n\n"
            '```json\n{"not": "the real answer"}\n```\n\n'
            "Now producing the final JSON.\n\n" + json.dumps(final)
        )
        adapter = _adapter(wrapped, json.dumps(_routing_request()))
        result = adapter.build_output()
        payload = json.loads(str(result.text))

        assert payload["outcome"] == DataOperationOutcome.CONFIRMED.value
        assert payload["result"]["binding_state"] == "absent"


class TestMalformedAgentResult:
    """The Agent's raw Cypher-summary text is LLM-generated and not guaranteed
    to be a valid RoutingLookupRecord (wrong shape, inconsistent cardinality,
    or not even JSON)."""

    def test_non_json_raw_value_is_rejected(self) -> None:
        adapter = _adapter("not json at all", json.dumps(_routing_request()))
        result = adapter.build_output()
        payload = json.loads(str(result.text))
        assert payload["outcome"] == DataOperationOutcome.REJECTED.value
        assert payload["error_code"] == ErrorCode.MALFORMED_AGENT_RESULT.value

    def test_inconsistent_cardinality_is_rejected(self) -> None:
        # binding_count=0 but a non-empty requests list: invalid per
        # RoutingLookupRecord's own cardinality validator.
        raw_lookup = {
            "binding_count": 0,
            "active_relationship_count": 0,
            "active_target_count": 0,
            "requests": [{"request_id": "req-001", "request_status_raw": "new", "closed": None}],
        }
        adapter = _adapter(json.dumps(raw_lookup), json.dumps(_routing_request()))
        result = adapter.build_output()
        payload = json.loads(str(result.text))
        assert payload["outcome"] == DataOperationOutcome.REJECTED.value
        assert payload["error_code"] == ErrorCode.MALFORMED_AGENT_RESULT.value


class TestNonUuidCorrelationId:
    """DataOperationRequest.correlation_id is a plain str (any format); the
    downstream RoutingContext (VersionedContract) requires a real UUID. A
    non-UUID-formatted correlation_id -- a perfectly valid
    DataOperationRequest.correlation_id -- must not cause the operation to be
    rejected; confirmed live with a real caller-supplied value
    ("corr-no-binding-001")."""

    def test_non_uuid_correlation_id_still_succeeds(self) -> None:
        raw_lookup = {
            "binding_count": 0,
            "active_relationship_count": 0,
            "active_target_count": 0,
            "requests": [],
        }
        adapter = _adapter(
            json.dumps(raw_lookup),
            json.dumps(_routing_request(correlation_id="corr-no-binding-001")),
        )
        result = adapter.build_output()
        payload = json.loads(str(result.text))
        assert payload["outcome"] == DataOperationOutcome.CONFIRMED.value
        assert payload["result"]["binding_state"] == "absent"

    def test_same_non_uuid_correlation_id_maps_to_the_same_surrogate(self) -> None:
        """Deterministic: the same input string always yields the same
        derived UUID, preserving traceability."""
        raw_lookup = {
            "binding_count": 0,
            "active_relationship_count": 0,
            "active_target_count": 0,
            "requests": [],
        }
        request = json.dumps(_routing_request(correlation_id="corr-stable-001"))
        result_a = _adapter(json.dumps(raw_lookup), request).build_output()
        result_b = _adapter(json.dumps(raw_lookup), request).build_output()
        assert (
            json.loads(str(result_a.text))["result"]["correlation_id"]
            == json.loads(str(result_b.text))["result"]["correlation_id"]
        )
