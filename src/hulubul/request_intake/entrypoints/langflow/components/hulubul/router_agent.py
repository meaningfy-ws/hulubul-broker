"""LF-00 Router Agent: scoped Agent for intake routing.

Per the spec (plan.md task 44), the Router Agent:
1. Takes deterministic RouterInput from the contract boundary (never model-substitutable)
2. Has LF-10 as its only tool (Tool Mode, single RunFlow component exposed as a tool)
3. Never retries writes (LF-10 handle retries/idempotency there)
4. Emits RouterResult with exact discriminator

DEC-019: "Give LF-00 or LF-10 raw MCP tools" is explicitly forbidden.
The Router calls LF-10 through a typed RunFlow tool only, never MCP directly.
"""

from lfx.components.models_and_agents.agent import AgentComponent
from lfx.schema.message import Message

__all__ = ["HulubulRouterAgent"]


class HulubulRouterAgent(AgentComponent):
    """LF-00 Router Agent: routes intake requests and reports non-intake outcomes."""

    display_name = "Router Agent"
    description = (
        "LF-00's router: decides intake vs. informational vs. fail-closed based on "
        "RoutingContext. Calls LF-10 as a tool for intake routes, otherwise returns "
        "structured result for complete/closed/unsupported/unknown contexts."
    )
    icon = "bot"
    name = "HulubulRouterAgent"

    # LF-00's Router does not need custom middleware behavior:
    # - It calls LF-10 (another flow) as a tool, not MCP directly
    # - LF-10 handles its own retries
    # - No local writes to protect from replay
    # Stock AgentComponent middleware is sufficient.

    async def message_response(self) -> Message:
        """Return the Agent's response message."""
        return await super().message_response()
