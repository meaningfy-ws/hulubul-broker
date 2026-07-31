"""Hulubul LFX custom components for Phase 1 request intake and data access.

Twelve thin adapters bridging LangFlow's Message/Data boundary to pure operational contracts
and policies (Cosmic Python DEC-007 proportional architecture):

1. ExecutionEnvelopeComponent (Task 16): Trusted actor context + message envelope
2. RouterInputBoundaryComponent (Task 17): Router contract assembly
3. IntakeInputBoundaryComponent (Task 17): Intake contract assembly
4. ContractResultBoundaryComponent (Task 17): Result validation and serialization
5. DataOperationRequestBoundaryComponent (Task 18): Data operation request
   validation and authorization
6. DataOperationResultBoundaryComponent (Task 18): Data operation result
   validation and serialization
7. RetryDecisionComponent (Task 19): Retry policy delegation
8. DeterministicRendererComponent (Task 19): Safe rendering delegation
9. HulubulGraphIdentifiersGenerator (Task 9.2): Deterministic graph identifier
   allocation (request_id, sender_id, receiver_id, parcel_id, place_ids) before
   the operation reaches LF-70, preventing the LLM from inventing IDs
10. HulubulDataAccessAgentComponent (Task 32): Agent with LF-70-scoped retry
    middleware (read-only tool retry + model-call retry; never retries writes);
    also short-circuits already-rejected requests before any LLM/MCP call, and
    runs a tool-less repair pass on a malformed final result (DEC-016)
11. RoutingContextAdapterComponent (Task 33): Deterministic
    RoutingLookupRecord -> RoutingContext classification for
    getRequestRoutingContext, replacing LLM-improvised business logic
12. HulubulLf70FlowTool: Deterministic LF-10 tool bridge to canonical LF-70
    when Langflow's stock RunFlow tool exposure returns an empty toolset

One component per file: LangFlow's directory-based custom component loader
registers exactly one component per file, named after the file -- a second
class in the same file is silently dropped from the sidebar palette. This is
why boundary components that were originally grouped in pairs/triples
(data_operation_boundary.py, contract_boundary.py) are now one file each.

NOTE: an earlier LF-70 topology (commit 8020a8a) used a flow-graph retry loop
-- a FailureClassifierComponent feeding a ConditionalRouter back into the
Agent. That topology was replaced (commit 29ada18) by retry logic living
entirely inside HulubulDataAccessAgentComponent's own execution
(ModelRetryMiddleware/ToolRetryMiddleware, plus the tool-less repair pass
above) -- see that component's module docstring for why. FailureClassifierComponent
was removed as dead code once nothing referenced it.
"""

from .contract_result_boundary import ContractResultBoundaryComponent
from .data_access_agent import HulubulDataAccessAgentComponent
from .data_operation_request_boundary import DataOperationRequestBoundaryComponent
from .data_operation_result_boundary import DataOperationResultBoundaryComponent
from .deterministic_renderer import DeterministicRendererComponent
from .execution_envelope import ExecutionEnvelopeComponent
from .graph_identifiers_generator import HulubulGraphIdentifiersGenerator
from .intake_input_boundary import IntakeInputBoundaryComponent
from .lf70_flow_tool import HulubulLf70FlowTool
from .retry_decision import RetryDecisionComponent
from .router_input_boundary import RouterInputBoundaryComponent
from .routing_context_adapter import RoutingContextAdapterComponent

__all__ = [
    "ContractResultBoundaryComponent",
    "DataOperationRequestBoundaryComponent",
    "DataOperationResultBoundaryComponent",
    "DeterministicRendererComponent",
    "ExecutionEnvelopeComponent",
    "HulubulDataAccessAgentComponent",
    "HulubulGraphIdentifiersGenerator",
    "HulubulLf70FlowTool",
    "IntakeInputBoundaryComponent",
    "RetryDecisionComponent",
    "RouterInputBoundaryComponent",
    "RoutingContextAdapterComponent",
]
