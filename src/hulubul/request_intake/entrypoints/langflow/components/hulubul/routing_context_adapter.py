"""Routing context adapter: deterministic RoutingLookupRecord -> RoutingContext.

Sits between the Data Access Agent and the Result Boundary. Per design.md
("LF-70 does not instantiate RoutingContext directly from a Neo4j row"), the
Agent's job for getRequestRoutingContext is only to run one fixed Cypher query
and return the raw binding/relationship/target cardinality counts plus request
rows -- it must not classify binding state, routing stage, or status itself.
adapt_routing_lookup() applies that closed-precedence classification
deterministically and is independently unit-tested; leaving it to the LLM was
the root cause of a live recursion-limit crash (the model had no schema
grounding to work from and burned all iterations on blind exploration).

For every other operation this component passes the Agent's raw output
through unchanged.
"""

import json
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

from lfx.custom.custom_component.component import Component
from lfx.inputs.inputs import HandleInput
from lfx.schema.message import Message
from lfx.template.field.base import Output
from pydantic import ValidationError

from hulubul.core.models.operational import (
    DataOperation,
    DataOperationOutcome,
    DataOperationResult,
    ErrorCode,
    extract_json_object_text,
)
from hulubul.core.models.operational.routing import RoutingLookupRecord, adapt_routing_lookup

__all__ = ["RoutingContextAdapterComponent"]


class RoutingContextAdapterComponent(Component):
    """Deterministically adapt raw routing-lookup rows for getRequestRoutingContext.

    Passes every other operation's raw_value through unchanged.
    """

    display_name = "Routing Context Adapter"
    description = (
        "Applies adapt_routing_lookup's closed-precedence classification to "
        "getRequestRoutingContext results; passes other operations through unchanged."
    )
    icon = "route"
    name = "HulubulRoutingContextAdapter"

    inputs = [  # noqa: RUF012
        HandleInput(  # type: ignore[call-arg]
            name="raw_value",
            display_name="Raw Agent Result",
            info="Raw result from the Agent's output (Message text, or Data/JSON).",
            input_types=["Message", "Data", "JSON"],
            required=True,
        ),
        HandleInput(  # type: ignore[call-arg]
            name="request_dict",
            display_name="Original Request",
            info="The original validated DataOperationRequest (Message text, or Data/JSON).",
            input_types=["Message", "Data", "JSON"],
            required=True,
        ),
    ]

    outputs = [  # noqa: RUF012
        Output(  # type: ignore[call-arg]
            display_name="Message", name="response", type_=Message, method="build_output"
        ),
    ]

    @classmethod
    def _as_dict(cls, value: Any) -> dict[str, Any]:
        """Coerce an incoming Message/str/Data/JSON edge value into a plain dict."""
        if isinstance(value, Message):
            value = value.text
        if isinstance(value, str):
            if not value:
                return {}
            try:
                decoded = json.loads(extract_json_object_text(value))
            except json.JSONDecodeError:
                return {}
            return decoded if isinstance(decoded, dict) else {}
        if hasattr(value, "data"):
            return dict(value.data)
        return dict(value) if value else {}

    def build_output(self) -> Message:
        request_dict = self._as_dict(self.request_dict)

        if request_dict.get("operation") != DataOperation.GET_REQUEST_ROUTING_CONTEXT.value:
            # Not our operation: forward the Agent's raw output unchanged.
            if isinstance(self.raw_value, Message):
                return self.raw_value
            return Message(text=json.dumps(self._as_dict(self.raw_value)))

        raw_value = self._as_dict(self.raw_value)
        schema_version = request_dict.get("schema_version", "1.0.0")
        correlation_id = self._coerce_correlation_id(request_dict.get("correlation_id", ""))

        try:
            record = RoutingLookupRecord.model_validate(raw_value)
        except ValidationError:
            return self._rejected(
                DataOperation.GET_REQUEST_ROUTING_CONTEXT, ErrorCode.MALFORMED_AGENT_RESULT
            )

        context = adapt_routing_lookup(
            record,
            schema_version=schema_version,
            correlation_id=correlation_id,
            session_id=request_dict.get("session_id", ""),
        )

        if context.error is not None:
            return self._rejected(DataOperation.GET_REQUEST_ROUTING_CONTEXT, context.error.code)

        result = DataOperationResult(
            operation=DataOperation.GET_REQUEST_ROUTING_CONTEXT,
            outcome=DataOperationOutcome.CONFIRMED,
            success=True,
            write_dispatched=False,
            result=context.model_dump(mode="json"),
        )
        return Message(text=result.model_dump_json())

    @staticmethod
    def _coerce_correlation_id(correlation_id_str: str) -> UUID:
        """Bridge DataOperationRequest.correlation_id (a plain str, any format)
        to RoutingContext's stricter VersionedContract.correlation_id (a real
        UUID). When the caller's value isn't UUID-formatted, derive a
        deterministic UUID5 surrogate (the same input string always maps to
        the same UUID) rather than rejecting an otherwise-legitimate
        operation over a traceability ID's format.

        Confirmed live: a plain "corr-no-binding-001" -- a perfectly valid
        DataOperationRequest.correlation_id -- caused every
        getRequestRoutingContext call to be rejected as MALFORMED_AGENT_RESULT,
        mislabeling a client-supplied value as a bad Agent result.
        """
        try:
            return UUID(correlation_id_str)
        except (ValueError, TypeError, AttributeError):
            return uuid5(NAMESPACE_URL, f"hulubul:correlation_id:{correlation_id_str}")

    @staticmethod
    def _rejected(operation: DataOperation, error_code: ErrorCode) -> Message:
        result = DataOperationResult(
            operation=operation,
            outcome=DataOperationOutcome.REJECTED,
            success=False,
            error_code=error_code.value,
        )
        return Message(text=result.model_dump_json())
