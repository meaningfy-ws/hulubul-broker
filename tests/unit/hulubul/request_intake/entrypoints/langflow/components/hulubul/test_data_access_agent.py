"""Tests for HulubulDataAccessAgentComponent: LF-70-scoped retry middleware.

Verifies DEC-015 (design.md): retry a transient read or model call once,
never retry a dispatched write. The retry mechanism is LangChain's own
ModelRetryMiddleware/ToolRetryMiddleware, scoped so ToolRetryMiddleware only
ever applies to the two read-only MCP tools, never write_neo4j_cypher.
"""

import asyncio
import json
from typing import Any
from unittest.mock import AsyncMock, patch

from langchain.agents.middleware import ModelRetryMiddleware, ToolRetryMiddleware
from lfx.components.models_and_agents.agent import AgentComponent
from lfx.schema.message import Message

from hulubul.request_intake.entrypoints.langflow.components.hulubul.data_access_agent import (
    HulubulDataAccessAgentComponent,
)


def _request_text_with_operation(operation: str = "createDeliveryRequest") -> str:
    """A minimal JSON body carrying just an `operation` field.

    `_operation_from_input` only reads that one field -- it does not (and
    should not) fully validate the request contract, so this deliberately
    stays minimal rather than building a complete per-operation payload.
    """
    return json.dumps({"operation": operation})


_VALID_RESULT_TEXT = json.dumps(
    {
        "operation": "createDeliveryRequest",
        "outcome": "confirmed",
        "success": True,
        "write_dispatched": True,
        "count": 1,
    }
)


class _FakeLLM:
    """Stand-in for the plain (non-tool-bound) chat model `ainvoke` returns."""

    def __init__(self, response_text: str | None = None, raise_error: bool = False) -> None:
        self.response_text = response_text
        self.raise_error = raise_error
        self.calls: list[Any] = []

    async def ainvoke(self, prompt: Any, *args: Any, **kwargs: Any) -> Any:
        self.calls.append(prompt)
        if self.raise_error:
            raise RuntimeError("provider unavailable")
        return _FakeAIMessage(self.response_text or "")


class _FakeAIMessage:
    def __init__(self, content: str) -> None:
        self.content = content


def _agent_with_tools(tools: list[str] | None) -> HulubulDataAccessAgentComponent:
    agent = HulubulDataAccessAgentComponent()
    # ToolRetryMiddleware's `tools` filter only needs tool *names*; real
    # StructuredTool objects aren't needed to exercise _build_middleware's
    # scoping logic, so a plain string list is used here.
    agent.tools = tools  # type: ignore[assignment]
    return agent


class TestMiddlewareComposition:
    def test_model_retry_middleware_always_present(self) -> None:
        agent = _agent_with_tools(["read_neo4j_cypher"])
        middleware = agent._build_middleware(llm=object())
        assert any(isinstance(m, ModelRetryMiddleware) for m in middleware)

    def test_model_retry_middleware_present_even_with_no_tools(self) -> None:
        agent = _agent_with_tools(None)
        middleware = agent._build_middleware(llm=object())
        assert any(isinstance(m, ModelRetryMiddleware) for m in middleware)

    def test_tool_retry_middleware_absent_when_no_tools(self) -> None:
        agent = _agent_with_tools(None)
        middleware = agent._build_middleware(llm=object())
        assert not any(isinstance(m, ToolRetryMiddleware) for m in middleware)

    def test_exactly_one_tool_retry_middleware_when_tools_present(self) -> None:
        agent = _agent_with_tools(["read_neo4j_cypher", "write_neo4j_cypher"])
        middleware = agent._build_middleware(llm=object())
        tool_retries = [m for m in middleware if isinstance(m, ToolRetryMiddleware)]
        assert len(tool_retries) == 1


class TestWriteToolNeverRetried:
    """DEC-015: a dispatched write is never automatically retried."""

    def test_write_tool_excluded_from_retry_scope(self) -> None:
        agent = _agent_with_tools(["read_neo4j_cypher", "get_neo4j_schema", "write_neo4j_cypher"])
        middleware = agent._build_middleware(llm=object())
        tool_retry = next(m for m in middleware if isinstance(m, ToolRetryMiddleware))
        assert tool_retry._tool_filter is not None
        assert "write_neo4j_cypher" not in tool_retry._tool_filter

    def test_only_read_tools_are_retry_scoped(self) -> None:
        agent = _agent_with_tools(["read_neo4j_cypher", "get_neo4j_schema", "write_neo4j_cypher"])
        middleware = agent._build_middleware(llm=object())
        tool_retry = next(m for m in middleware if isinstance(m, ToolRetryMiddleware))
        assert tool_retry._tool_filter is not None
        assert set(tool_retry._tool_filter) == {"read_neo4j_cypher", "get_neo4j_schema"}


class TestStockBehaviorPreserved:
    """Overriding _build_middleware must not silently drop stock behavior."""

    def test_model_call_limit_middleware_still_built_from_max_iterations(self) -> None:
        agent = _agent_with_tools(["read_neo4j_cypher"])
        agent.max_iterations = 5
        middleware = agent._build_middleware(llm=object())
        names = [type(m).__name__ for m in middleware]
        assert "ModelCallLimitMiddleware" in names

    def test_display_name_and_name_are_distinct_from_stock_agent(self) -> None:
        agent = HulubulDataAccessAgentComponent()
        assert agent.display_name != "Agent"
        assert agent.name != "Agent"

    def test_inherits_stock_agent_inputs(self) -> None:
        agent = HulubulDataAccessAgentComponent()
        input_names = {i.name for i in agent.inputs}
        assert {"input_value", "model", "tools", "system_prompt"} <= input_names


class TestShortCircuitRejection:
    """Requests rejected by DataOperationRequestBoundary before ever reaching this
    Agent must resolve to a typed DataOperationResult(rejected) without ever
    invoking the LLM/MCP tools -- confirmed live: without this, the model
    treated the pre-formed error as an ill-formed task and asked the caller to
    rephrase, burning iterations on a request that was never going anywhere.
    """

    def test_rejection_with_known_operation_short_circuits(self) -> None:
        agent = HulubulDataAccessAgentComponent()
        agent.input_value = Message(
            text=json.dumps(
                {
                    "schema_version": "1.0.0",
                    "correlation_id": "c0ffee00-0000-0000-0000-000000000000",
                    "code": "OPERATION_NOT_ALLOWED",
                    "category": "authorization",
                    "message": "This operation is not allowed.",
                    "retryable": False,
                    "violations": [],
                    "_raw_operation": "getRequestRoutingContext",
                }
            )
        )
        result = agent._short_circuit_rejection()
        assert result is not None
        payload = json.loads(str(result.text))
        assert payload["outcome"] == "rejected"
        assert payload["success"] is False
        assert payload["error_code"] == "OPERATION_NOT_ALLOWED"
        assert payload["operation"] == "getRequestRoutingContext"

    def test_rejection_with_unknown_operation_falls_through(self) -> None:
        """No _raw_operation resolvable: let the normal Agent path run (unchanged,
        pre-existing behavior for a contract-invalid payload with no parseable
        operation at all)."""
        agent = HulubulDataAccessAgentComponent()
        agent.input_value = Message(
            text=json.dumps(
                {
                    "schema_version": "1.0.0",
                    "correlation_id": "c0ffee00-0000-0000-0000-000000000000",
                    "code": "INVALID_CONTRACT",
                    "category": "contract",
                    "message": "I could not produce a safe response.",
                    "retryable": False,
                    "violations": [],
                    "_raw_operation": None,
                }
            )
        )
        assert agent._short_circuit_rejection() is None

    def test_valid_request_is_not_short_circuited(self) -> None:
        agent = HulubulDataAccessAgentComponent()
        agent.input_value = Message(
            text=json.dumps(
                {
                    "schema_version": "1.0.0",
                    "correlation_id": "c0ffee00-0000-0000-0000-000000000000",
                    "operation": "getRequestRoutingContext",
                    "operation_id": "op-001",
                    "caller": "LF-00",
                    "session_id": "p1-001",
                    "actor_id": "urn:uuid:test-actor",
                }
            )
        )
        assert agent._short_circuit_rejection() is None

    def test_non_json_input_is_not_short_circuited(self) -> None:
        agent = HulubulDataAccessAgentComponent()
        agent.input_value = Message(text="not json at all")
        assert agent._short_circuit_rejection() is None

    def test_empty_input_is_not_short_circuited(self) -> None:
        agent = HulubulDataAccessAgentComponent()
        agent.input_value = Message(text="")
        assert agent._short_circuit_rejection() is None


class TestOperationFromInput:
    def test_reads_operation_from_valid_json(self) -> None:
        agent = HulubulDataAccessAgentComponent()
        agent.input_value = Message(text=_request_text_with_operation("updateDeliveryRequest"))
        operation = agent._operation_from_input()
        assert operation is not None
        assert operation.value == "updateDeliveryRequest"

    def test_returns_none_for_unknown_operation(self) -> None:
        agent = HulubulDataAccessAgentComponent()
        agent.input_value = Message(text=json.dumps({"operation": "notARealOperation"}))
        assert agent._operation_from_input() is None

    def test_returns_none_for_non_json(self) -> None:
        agent = HulubulDataAccessAgentComponent()
        agent.input_value = Message(text="not json")
        assert agent._operation_from_input() is None

    def test_returns_none_for_empty_input(self) -> None:
        agent = HulubulDataAccessAgentComponent()
        agent.input_value = Message(text="")
        assert agent._operation_from_input() is None


class TestResultShapeValidation:
    """DEC-016: deciding whether a result even NEEDS repair.

    Deliberately checks shape only (DataOperationResult.model_validate), not
    postconditions -- see the docstring on _is_valid_data_operation_result_shape
    for why postcondition checks are left entirely to the boundary.
    """

    def test_valid_result_passes(self) -> None:
        message = Message(text=_VALID_RESULT_TEXT)
        assert HulubulDataAccessAgentComponent._is_valid_data_operation_result_shape(message)

    def test_prose_wrapped_valid_json_passes(self) -> None:
        message = Message(text=f"Here is my answer:\n\n{_VALID_RESULT_TEXT}\n\nDone.")
        assert HulubulDataAccessAgentComponent._is_valid_data_operation_result_shape(message)

    def test_non_json_text_fails(self) -> None:
        message = Message(text="I could not complete this operation.")
        assert not HulubulDataAccessAgentComponent._is_valid_data_operation_result_shape(message)

    def test_wrong_shape_json_fails(self) -> None:
        message = Message(text=json.dumps({"foo": "bar"}))
        assert not HulubulDataAccessAgentComponent._is_valid_data_operation_result_shape(message)

    def test_empty_text_fails(self) -> None:
        message = Message(text="")
        assert not HulubulDataAccessAgentComponent._is_valid_data_operation_result_shape(message)

    def test_postcondition_violation_still_passes_shape_check(self) -> None:
        """A result with an impossible count (postcondition violation) is still
        shape-valid -- that's the boundary's job to catch, not repair's."""
        text = json.dumps(
            {
                "operation": "createDeliveryRequest",
                "outcome": "confirmed",
                "success": True,
                "write_dispatched": True,
                "count": 99,
            }
        )
        assert HulubulDataAccessAgentComponent._is_valid_data_operation_result_shape(
            Message(text=text)
        )


class TestMarkRepairFailed:
    def test_carries_raw_operation_when_resolvable(self) -> None:
        agent = HulubulDataAccessAgentComponent()
        agent.input_value = Message(text=_request_text_with_operation("setRequestStatus"))
        marked = agent._mark_repair_failed(Message(text="garbage"))
        payload = json.loads(str(marked.text))
        assert payload["_repair_failed"] is True
        assert payload["_raw_operation"] == "setRequestStatus"

    def test_omits_raw_operation_when_unresolvable(self) -> None:
        agent = HulubulDataAccessAgentComponent()
        agent.input_value = Message(text="not json")
        marked = agent._mark_repair_failed(Message(text="garbage"))
        payload = json.loads(str(marked.text))
        assert payload["_repair_failed"] is True
        assert "_raw_operation" not in payload

    def test_never_carries_the_raw_malformed_text(self) -> None:
        """DEC-016: 'no secret/raw prompt logging' -- the marker must not echo
        the original malformed content back out."""
        agent = HulubulDataAccessAgentComponent()
        agent.input_value = Message(text=_request_text_with_operation())
        marked = agent._mark_repair_failed(
            Message(text="some sensitive extracted PII that must not leak: 555-1234")
        )
        assert "555-1234" not in str(marked.text)


class TestRepairMalformedResult:
    """DEC-016 tool-less repair: one reformat attempt via the plain,
    non-tool-bound chat model already resolved for the Agent."""

    def _agent_with_fake_llm(self, fake_llm: _FakeLLM) -> HulubulDataAccessAgentComponent:
        agent = HulubulDataAccessAgentComponent()
        agent.get_agent_requirements = AsyncMock(return_value=(fake_llm, None, []))  # type: ignore[method-assign]
        return agent

    def test_successful_repair_returns_valid_message(self) -> None:
        fake_llm = _FakeLLM(response_text=_VALID_RESULT_TEXT)
        agent = self._agent_with_fake_llm(fake_llm)

        result = asyncio.run(agent._repair_malformed_result(Message(text="I think it worked?")))

        assert result is not None
        payload = json.loads(str(result.text))
        assert payload["outcome"] == "confirmed"
        assert payload["success"] is True
        # Exactly one call: the repair pass calls the plain model once, no loop.
        assert len(fake_llm.calls) == 1

    def test_repair_call_never_receives_a_tool_bound_model(self) -> None:
        """Structural guarantee, not just a prompt instruction: the object
        _repair_malformed_result calls has no tools attached at all."""
        fake_llm = _FakeLLM(response_text=_VALID_RESULT_TEXT)
        agent = self._agent_with_fake_llm(fake_llm)

        asyncio.run(agent._repair_malformed_result(Message(text="I think it worked?")))

        assert not hasattr(fake_llm, "tools") or not fake_llm.__dict__.get("tools")

    def test_unrepairable_sentinel_returns_none(self) -> None:
        fake_llm = _FakeLLM(response_text=json.dumps({"_unrepairable": True}))
        agent = self._agent_with_fake_llm(fake_llm)

        result = asyncio.run(agent._repair_malformed_result(Message(text="not enough info here")))

        assert result is None

    def test_still_invalid_json_returns_none(self) -> None:
        fake_llm = _FakeLLM(response_text="I tried but here is more prose, not JSON.")
        agent = self._agent_with_fake_llm(fake_llm)

        result = asyncio.run(agent._repair_malformed_result(Message(text="garbage")))

        assert result is None

    def test_still_wrong_shape_returns_none(self) -> None:
        fake_llm = _FakeLLM(response_text=json.dumps({"foo": "bar"}))
        agent = self._agent_with_fake_llm(fake_llm)

        result = asyncio.run(agent._repair_malformed_result(Message(text="garbage")))

        assert result is None

    def test_model_error_returns_none(self) -> None:
        fake_llm = _FakeLLM(raise_error=True)
        agent = self._agent_with_fake_llm(fake_llm)

        result = asyncio.run(agent._repair_malformed_result(Message(text="garbage")))

        assert result is None

    def test_empty_original_text_returns_none_without_calling_model(self) -> None:
        fake_llm = _FakeLLM(response_text=_VALID_RESULT_TEXT)
        agent = self._agent_with_fake_llm(fake_llm)

        result = asyncio.run(agent._repair_malformed_result(Message(text="")))

        assert result is None
        assert len(fake_llm.calls) == 0


class TestMessageResponseRepairDispatch:
    """End-to-end dispatch inside message_response(): valid results pass
    through untouched, routing-context is exempt, malformed results get one
    repair attempt, and a failed repair is marked for the boundary."""

    def _agent(self, input_operation: str) -> HulubulDataAccessAgentComponent:
        agent = HulubulDataAccessAgentComponent()
        agent.input_value = Message(text=_request_text_with_operation(input_operation))
        return agent

    def test_valid_result_passes_through_unchanged(self) -> None:
        agent = self._agent("createDeliveryRequest")
        with patch.object(
            AgentComponent,
            "message_response",
            new=AsyncMock(return_value=Message(text=_VALID_RESULT_TEXT)),
        ):
            result = asyncio.run(agent.message_response())
        assert str(result.text) == _VALID_RESULT_TEXT

    def test_routing_context_result_skips_repair_even_if_not_data_operation_result_shaped(
        self,
    ) -> None:
        """getRequestRoutingContext's raw shape is a RoutingLookupRecord, not a
        DataOperationResult -- must never be routed into repair."""
        routing_shape_text = json.dumps({"binding_count": 0, "requests": []})
        agent = self._agent("getRequestRoutingContext")
        with patch.object(
            AgentComponent,
            "message_response",
            new=AsyncMock(return_value=Message(text=routing_shape_text)),
        ):
            result = asyncio.run(agent.message_response())
        assert str(result.text) == routing_shape_text

    def test_malformed_result_gets_repaired_and_returns_valid_result(self) -> None:
        agent = self._agent("createDeliveryRequest")
        agent.get_agent_requirements = AsyncMock(  # type: ignore[method-assign]
            return_value=(_FakeLLM(response_text=_VALID_RESULT_TEXT), None, [])
        )
        with patch.object(
            AgentComponent,
            "message_response",
            new=AsyncMock(return_value=Message(text="not valid json at all")),
        ):
            result = asyncio.run(agent.message_response())
        payload = json.loads(str(result.text))
        assert payload["outcome"] == "confirmed"

    def test_malformed_result_still_unrepairable_is_marked_for_boundary(self) -> None:
        agent = self._agent("createDeliveryRequest")
        agent.get_agent_requirements = AsyncMock(  # type: ignore[method-assign]
            return_value=(_FakeLLM(response_text="still not JSON"), None, [])
        )
        with patch.object(
            AgentComponent,
            "message_response",
            new=AsyncMock(return_value=Message(text="not valid json at all")),
        ):
            result = asyncio.run(agent.message_response())
        payload = json.loads(str(result.text))
        assert payload["_repair_failed"] is True
        assert payload["_raw_operation"] == "createDeliveryRequest"
