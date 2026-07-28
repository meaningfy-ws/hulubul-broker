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

import json
from typing import Any

from langchain.agents.middleware import ModelRetryMiddleware, ToolRetryMiddleware
from lfx.components.models_and_agents.agent import AgentComponent
from lfx.log.logger import logger
from lfx.schema.message import Message
from pydantic import ValidationError

from hulubul.core.models.operational import (
    DataOperation,
    DataOperationOutcome,
    DataOperationResult,
    extract_json_object_text,
)

__all__ = ["HulubulDataAccessAgentComponent"]

# MCP toolkit tool names exposed only inside LF-70 (tests/integration/conftest.py's
# mcp_client fixture asserts this exact three-tool inventory). Only the two read
# tools are eligible for retry; write_neo4j_cypher is intentionally excluded.
_READ_ONLY_MCP_TOOL_NAMES = ("read_neo4j_cypher", "get_neo4j_schema")

# getRequestRoutingContext's raw output is a RoutingLookupRecord, not a
# DataOperationResult -- RoutingContextAdapterComponent (downstream) owns its
# extraction/validation. Result-shape repair below does not apply to it.
_NO_RESULT_REPAIR_OPERATIONS = frozenset({DataOperation.GET_REQUEST_ROUTING_CONTEXT})

# Design.md DEC-016: "Malformed model result -> tool-less repair with
# validation -> one repair; then MALFORMED_AGENT_RESULT". This prompt asks
# for a pure reformat of information already present in the malformed text --
# never fabricate new facts -- since the repair call has no tools and cannot
# independently verify anything against Neo4j.
_REPAIR_PROMPT_TEMPLATE = """\
The text below was supposed to be a single JSON object matching this schema, \
but failed validation. Reformat/extract the SAME information into valid \
JSON matching the schema exactly -- do not invent, guess, or add any fact \
that is not already present in the text below. Output ONLY the JSON object, \
nothing else.

If the text does not contain enough information to fill the schema \
truthfully, output exactly this JSON object instead: {{"_unrepairable": true}}

Schema:
{schema}

Text to reformat:
{malformed_text}
"""


class HulubulDataAccessAgentComponent(AgentComponent):
    """Agent scoped for LF-70: retries transient reads/model calls, never writes."""

    display_name = "Data Access Agent"
    description = (
        "LF-70's tool-using Agent: executes each data operation against Neo4j via "
        "MCP. Retries only transient reads/model calls, never a dispatched write "
        "(DEC-015); short-circuits already-rejected requests; makes one tool-less "
        "repair attempt on a malformed final result (DEC-016)."
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

    async def message_response(self) -> Message:
        rejection = self._short_circuit_rejection()
        if rejection is not None:
            return rejection

        result = await super().message_response()

        if self._operation_from_input() in _NO_RESULT_REPAIR_OPERATIONS:
            return result
        if self._is_valid_data_operation_result_shape(result):
            return result

        repaired = await self._repair_malformed_result(result)
        return repaired if repaired is not None else self._mark_repair_failed(result)

    def _short_circuit_rejection(self) -> Message | None:
        """Detect a pre-rejected DataOperationRequest and skip the LLM/MCP entirely.

        DataOperationRequestBoundaryComponent rejects contract-invalid or
        unauthorized requests before they ever reach this Agent, emitting an
        OperationalError enriched with `_raw_operation` (the client-supplied
        operation string, best-effort -- see data_operation_request_boundary.py).
        Building the final `DataOperationResult(rejected)` here, deterministically,
        from that known operation and error code means an already-rejected
        request never triggers a real model/tool call: cheaper, and avoids the
        confusion observed live in this same investigation -- the model
        treating a pre-formed error as an ill-formed task and asking the
        caller to rephrase, burning iterations on a request that was never
        going to reach it.

        Returns None (falls through to the normal Agent path) whenever the
        input isn't recognizably this shape, or `_raw_operation` can't be
        resolved to a known operation -- e.g. a contract-invalid payload with
        no parseable operation at all. That's today's existing (imperfect but
        non-crashing) behavior, unchanged.
        """
        value = self.input_value
        text = value.text if isinstance(value, Message) else value
        if not isinstance(text, str) or not text:
            return None
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            return None
        if not isinstance(payload, dict) or "code" not in payload or "operation" in payload:
            return None  # Not a rejection shape: a valid request has "operation", not "code"

        try:
            operation = DataOperation(payload.get("_raw_operation"))
        except ValueError:
            return None

        result = DataOperationResult(
            operation=operation,
            outcome=DataOperationOutcome.REJECTED,
            success=False,
            error_code=payload.get("code"),
        )
        return Message(text=result.model_dump_json())

    def _operation_from_input(self) -> DataOperation | None:
        """Best-effort: read this Agent's own request's `operation` field."""
        value = self.input_value
        text = value.text if isinstance(value, Message) else value
        if not isinstance(text, str) or not text:
            return None
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            return None
        if not isinstance(payload, dict):
            return None
        try:
            return DataOperation(payload.get("operation"))
        except ValueError:
            return None

    @staticmethod
    def _is_valid_data_operation_result_shape(result: Message) -> bool:
        """Cheap shape check: does the Agent's final text parse as a DataOperationResult?

        Postcondition correctness (affected count, timestamp equality,
        operation match) is deliberately NOT checked here -- a tool-less
        repair pass has no way to independently verify those against Neo4j,
        and DataOperationResultBoundaryComponent already re-validates them
        unconditionally downstream with its own specific error codes,
        regardless of whether repair ran. This only decides whether the text
        is even shaped like a DataOperationResult at all.
        """
        text = result.text if isinstance(result, Message) else result
        if not isinstance(text, str) or not text:
            return False
        try:
            parsed = json.loads(extract_json_object_text(text))
        except json.JSONDecodeError:
            return False
        if not isinstance(parsed, dict):
            return False
        try:
            DataOperationResult.model_validate(parsed)
        except ValidationError:
            return False
        return True

    async def _repair_malformed_result(self, result: Message) -> Message | None:
        """DEC-016 tool-less repair: one reformat attempt, no tools, no MCP.

        Calls the plain (non-tool-bound) chat model directly -- structurally
        incapable of dispatching another write, since it is never wrapped
        into the tool-calling agent runnable used by the normal Agent loop.
        Returns None if repair could not produce valid DataOperationResult
        JSON (caller falls back to `_mark_repair_failed`).
        """
        text = result.text if isinstance(result, Message) else result
        if not isinstance(text, str) or not text:
            return None

        try:
            llm_model, _chat_history, _tools = await self.get_agent_requirements()  # type: ignore[no-untyped-call]
        except (ValueError, TypeError) as exc:
            logger.warning(f"LF-70 repair: could not resolve a model for repair: {exc}")
            return None

        prompt = _REPAIR_PROMPT_TEMPLATE.format(
            schema=json.dumps(DataOperationResult.model_json_schema()),
            malformed_text=text,
        )

        try:
            response = await llm_model.ainvoke(prompt)
        except Exception as exc:  # provider-specific exception types vary
            logger.warning(f"LF-70 repair: model call failed: {type(exc).__name__}")
            return None

        response_text = response.content if hasattr(response, "content") else str(response)
        if not isinstance(response_text, str):
            return None

        try:
            parsed = json.loads(extract_json_object_text(response_text))
        except json.JSONDecodeError as exc:
            # exc carries only position/reason (e.g. "Expecting value: line 1
            # column 1"), never the malformed text itself -- safe to log
            # under DEC-016 ("no secret/raw prompt logging").
            logger.warning(f"LF-70 repair: repair attempt did not produce valid JSON: {exc}")
            return None
        if not isinstance(parsed, dict) or parsed.get("_unrepairable"):
            logger.warning("LF-70 repair: repair attempt reported unrepairable or wrong shape")
            return None

        try:
            repaired_result = DataOperationResult.model_validate(parsed)
        except ValidationError as exc:
            # include_input/include_url=False: .errors() otherwise embeds the
            # actual offending value per error, which could be repaired,
            # LLM-extracted content -- DEC-016 forbids logging that.
            safe_errors = exc.errors(include_input=False, include_url=False)
            logger.warning(
                f"LF-70 repair: repair attempt still failed schema validation: {safe_errors}"
            )
            return None

        return Message(text=repaired_result.model_dump_json())

    def _mark_repair_failed(self, result: Message) -> Message:
        """Tag a still-malformed result so the boundary reports MALFORMED_AGENT_RESULT.

        Mirrors the `_raw_operation` marker convention used by
        DataOperationRequestBoundaryComponent's rejection enrichment: a
        private key the downstream boundary recognizes, distinguishing
        "repair was attempted and still failed" from "no repair was ever
        attempted" (plain INVALID_CONTRACT). Never carries the raw/malformed
        text itself -- see DEC-016 ("no secret/raw prompt logging").
        """
        operation = self._operation_from_input()
        payload: dict[str, Any] = {"_repair_failed": True}
        if operation is not None:
            payload["_raw_operation"] = operation.value
        return Message(text=json.dumps(payload))
