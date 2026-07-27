"""Data operation result boundary component: validation and serialization.

Split from the former data_operation_boundary.py (which held both the request
and result boundary components) because LangFlow's directory-based custom
component loader registers exactly one component per file, named after the
file -- a second class in the same file is silently dropped from the sidebar
palette. See data_operation_request_boundary.py for the paired component.

Runs as the terminal node (last step before flow output). Failure
classification for retry decisioning is handled by a separate
FailureClassifierComponent that runs on the Agent's raw output BEFORE this
component -- retries themselves now happen inside the Agent's own execution
(ModelRetryMiddleware/ToolRetryMiddleware), not via a flow-level loop, so
this component's only job is validating the final result exactly once.
"""

import json
from typing import Any
from uuid import UUID

from lfx.custom.custom_component.component import Component
from lfx.inputs.inputs import HandleInput
from lfx.schema.data import JSON
from lfx.schema.message import Message
from lfx.template.field.base import Output
from pydantic import ValidationError

from hulubul.core.models.operational import (
    DataOperationOutcome,
    DataOperationResult,
    ErrorCode,
    OperationalError,
    validate_data_operation_request,
)
from hulubul.core.models.operational.errors import ERROR_POLICY
from hulubul.request_intake.services.data_operation_policy import validate_result_postconditions

__all__ = ["DataOperationResultBoundaryComponent"]


class DataOperationResultBoundaryComponent(Component):
    """Validate and serialize operation results.

    Verifies result postconditions:
    - Request/result operation match
    - Affected count matches expectations (write operations)
    - Timestamps and status consistency (as defined by operation type)
    - Correlation/operation ID coherence

    Returns JSON with typed result or error (INVALID_CONTRACT or other).
    """

    display_name = "Data Operation Result Boundary"
    description = "Validate and serialize DataOperationResult payloads (terminal node)."
    icon = "shield-check"
    name = "HulubulDataOperationResultBoundary"

    inputs = [  # noqa: RUF012
        HandleInput(  # type: ignore[call-arg]
            name="raw_value",
            display_name="Raw Result",
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
            display_name="Result", name="response", type_=JSON, method="build_output"
        ),
    ]

    @staticmethod
    def _extract_json_text(text: str) -> str:
        """Best-effort extraction of a JSON object from LLM output that may be
        wrapped in prose or markdown fences despite being instructed to emit
        only JSON. A no-op on already-clean JSON text.

        Confirmed live: the model sometimes "thinks out loud" with a fenced
        *draft* JSON block, then produces the real (unfenced) final answer
        afterwards ("Now producing the final JSON.\\n\\n{...}"). A naive
        first-match regex grabs the draft. This scans for every balanced
        top-level `{...}` block (brace-depth tracking, so nested nested
        objects and fence markers don't confuse it) and tries each from
        *last* to *first* -- the model's own "final answer comes last"
        pattern -- returning the first one that's valid JSON.
        """
        text = text.strip()
        candidates: list[str] = []
        depth = 0
        start: int | None = None
        for i, char in enumerate(text):
            if char == "{":
                if depth == 0:
                    start = i
                depth += 1
            elif char == "}" and depth > 0:
                depth -= 1
                if depth == 0 and start is not None:
                    candidates.append(text[start : i + 1])
        for candidate in reversed(candidates):
            try:
                json.loads(candidate)
            except json.JSONDecodeError:
                continue
            return candidate
        return text

    @classmethod
    def _as_dict(cls, value: Any) -> dict[str, Any]:
        """Coerce an incoming Message/Data/JSON edge value into a plain dict.

        The Agent's final text is LLM-generated and not guaranteed to be valid
        JSON (e.g. it may explain a failure in prose instead of emitting the
        DataOperationResult contract). Treat undecodable text as an empty dict
        rather than raising, so it is validated normally and rejected as
        INVALID_CONTRACT downstream instead of crashing the component build.
        """
        if isinstance(value, Message):
            text = value.text
            if not isinstance(text, str):
                return {}
            try:
                decoded = json.loads(cls._extract_json_text(text))
            except json.JSONDecodeError:
                return {}
            return decoded if isinstance(decoded, dict) else {}
        if hasattr(value, "data"):
            return dict(value.data)
        return dict(value) if value else {}

    def build_output(self) -> JSON:
        """LFX-facing output: validate self.raw_value against self.request_dict."""
        raw_value = self._as_dict(self.raw_value)
        request_dict = self._as_dict(self.request_dict)
        return self.validate_result_value(raw_value, request_dict)

    def validate_result_value(
        self, raw_value: dict[str, Any], request_dict: dict[str, Any]
    ) -> JSON:
        """Validate result, return typed output or error.

        Args:
            raw_value: Raw result dict from MCP operation
            request_dict: Original request dict

        Returns:
            JSON: Validated DataOperationResult or OperationalError with INVALID_CONTRACT
                  or other error code
        """
        # Extract correlation_id from request for error responses (string format)
        correlation_id_str = request_dict.get("correlation_id", "")

        # Deserialize request first
        try:
            request = validate_data_operation_request(request_dict)
        except ValidationError:
            # `request_dict` isn't a valid DataOperationRequest -- expected when
            # the request was rejected before ever reaching the Agent (e.g. by
            # DataOperationRequestBoundary's authorization/contract check), so
            # `request_dict` here is that rejection's own OperationalError, not
            # the original request. If `raw_value` is nonetheless a complete,
            # self-consistent, non-CONFIRMED DataOperationResult -- built
            # deterministically by the Agent's own reject-short-circuit path,
            # not claimed by an LLM -- trust it directly. Postcondition
            # cross-checks against the original request only matter when an
            # Agent is claiming a result, and CONFIRMED (success) outcomes
            # always require a resolvable original request for the
            # affected-count/operation-match checks, so both still fall
            # through to INVALID_CONTRACT below.
            try:
                bypass_result = DataOperationResult.model_validate(raw_value)
            except ValidationError:
                bypass_result = None
            if (
                bypass_result is not None
                and bypass_result.outcome != DataOperationOutcome.CONFIRMED
            ):
                return JSON(data=bypass_result.model_dump(mode="json"))
            return self._make_error_response(
                code=ErrorCode.INVALID_CONTRACT,
                correlation_id_str=correlation_id_str,
            )

        # Update correlation_id from valid request (it's a string in DataOperationRequest)
        correlation_id_str = request.correlation_id

        # First validate result contract
        try:
            result = DataOperationResult.model_validate(raw_value)
        except ValidationError:
            # Result contract validation failed
            return self._make_error_response(
                code=ErrorCode.INVALID_CONTRACT,
                correlation_id_str=correlation_id_str,
            )

        # Validate postconditions
        postcond_error = validate_result_postconditions(request, result)
        if postcond_error is not None:
            # Create new error with correct correlation_id (model is frozen)
            return self._make_error_response(
                code=postcond_error.code,
                correlation_id_str=correlation_id_str,
            )

        # Success: return typed JSON with result
        return JSON(data=result.model_dump(mode="json"))

    def _make_error_response(
        self,
        code: ErrorCode,
        correlation_id_str: str,
    ) -> JSON:
        """Create error response with correlation_id.

        Args:
            code: The ErrorCode
            correlation_id_str: The correlation_id string

        Returns:
            JSON: Serialized OperationalError
        """
        from uuid import uuid4

        # Try to parse correlation_id_str as UUID, otherwise generate new one
        try:
            correlation_id = UUID(correlation_id_str) if correlation_id_str else uuid4()
        except (ValueError, TypeError):
            correlation_id = uuid4()

        policy = ERROR_POLICY[code]
        error = OperationalError(
            schema_version="1.0.0",
            code=code,
            correlation_id=correlation_id,
            category=policy.category,
            message=policy.safe_message,
            retryable=policy.retryable,
        )

        return JSON(data=error.model_dump(mode="json"))
