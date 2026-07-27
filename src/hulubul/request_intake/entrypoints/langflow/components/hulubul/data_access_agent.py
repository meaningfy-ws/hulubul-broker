"""LF-70 Data Access Agent: the stock Agent, scoped to a safe retry policy.

Per DEC-015 (design.md), LF-70 must retry a transient MCP read or model call
once, but must NEVER retry a dispatched write -- Phase 1 has no idempotency
key, so replaying a write whose outcome is ambiguous could silently create a
duplicate mutation (see brainstorm.md Q12 and the "No write idempotency
limits safe retry behavior" trade-off in design.md's risk list).

LangChain's `create_agent` already ships exactly the retry primitives this
needs (`ModelRetryMiddleware`, `ToolRetryMiddleware` -- both used internally
by LangFlow's own stock components, e.g. HuggingFace/embeddings retries), so
this is not a flow-graph loop: the retry happens inside a single Agent
invocation, transparent to the flow. But the stock `AgentComponent`'s
`handle_parsing_errors` checkbox only ever constructs an UNSCOPED
`ToolRetryMiddleware(max_retries=2)` -- applied to every tool, which would
also retry `write_neo4j_cypher`. This subclass overrides only the middleware
assembly step to scope tool retry to the two read-only MCP tools, and adds
model-call retry (which the stock component doesn't wire in at all).

NOTE for whoever builds LF-10/LF-00 (checkpoint 9): this `tools=[...]`
name-based scoping only works because LF-70 is the sole flow with a raw MCP
toolkit exposing separately-named read/write tools. LF-10/LF-00's agents call
*other flows* (LF-70, LF-10) through a single "Run Flow" tool each -- there is
no separate read-tool-name vs write-tool-name to filter by there. If those
flows want the same protection, `retry_on` needs a callable that inspects the
tool-call *arguments* (was this a read-type or write-type DataOperationRequest?),
not a plain `tools=[...]` name filter. See also the note in plan.md near the
LF-10 agent/tool-wiring section.
"""

from typing import Any

from langchain.agents.middleware import ModelRetryMiddleware, ToolRetryMiddleware
from lfx.components.models_and_agents.agent import AgentComponent

__all__ = ["HulubulDataAccessAgentComponent"]

# MCP toolkit tool names exposed only inside LF-70 (tests/integration/conftest.py's
# mcp_client fixture asserts this exact three-tool inventory). Only the two read
# tools are eligible for retry; write_neo4j_cypher is intentionally excluded.
_READ_ONLY_MCP_TOOL_NAMES = ("read_neo4j_cypher", "get_neo4j_schema")


class HulubulDataAccessAgentComponent(AgentComponent):
    """Agent scoped for LF-70: retries transient reads/model calls, never writes."""

    display_name = "Data Access Agent"
    description = (
        "LF-70's Data Access Agent: retries a transient read or model call once "
        "(DEC-015), never retries a dispatched write."
    )
    icon = "bot"
    name = "HulubulDataAccessAgent"

    def _build_middleware(self, llm: Any) -> list[Any]:
        # Signature matches the installed lfx==1.10.2 AgentComponent._build_middleware
        # exactly (verified via inspect.signature locally) -- GitHub's main branch
        # has since added an `allow_interrupts` kwarg not present in this pinned
        # release; do not add it here without re-verifying against the pinned version.
        middleware = super()._build_middleware(llm)

        # Drop the stock unscoped ToolRetryMiddleware (would also retry writes).
        middleware = [m for m in middleware if not isinstance(m, ToolRetryMiddleware)]

        if self.tools:
            middleware.append(ToolRetryMiddleware(tools=list(_READ_ONLY_MCP_TOOL_NAMES)))
        middleware.append(ModelRetryMiddleware())

        return middleware
