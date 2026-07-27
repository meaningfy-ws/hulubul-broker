"""Tests for HulubulDataAccessAgentComponent: LF-70-scoped retry middleware.

Verifies DEC-015 (design.md): retry a transient read or model call once,
never retry a dispatched write. The retry mechanism is LangChain's own
ModelRetryMiddleware/ToolRetryMiddleware, scoped so ToolRetryMiddleware only
ever applies to the two read-only MCP tools, never write_neo4j_cypher.
"""

from langchain.agents.middleware import ModelRetryMiddleware, ToolRetryMiddleware

from hulubul.request_intake.entrypoints.langflow.components.hulubul.data_access_agent import (
    HulubulDataAccessAgentComponent,
)


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
