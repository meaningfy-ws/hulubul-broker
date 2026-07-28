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
    extract_json_object_text,
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
                decoded = json.loads(extract_json_object_text(text))
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
            # Result contract validation failed. `_repair_failed` (set by
            # HulubulDataAccessAgentComponent's tool-less repair pass, DEC-016)
            # distinguishes "the Agent already tried once to reformat this and
            # still couldn't" (MALFORMED_AGENT_RESULT) from "never attempted"
            # (INVALID_CONTRACT, e.g. getRequestRoutingContext's own shape,
            # which never goes through result-shape repair).
            code = (
                ErrorCode.MALFORMED_AGENT_RESULT
                if raw_value.get("_repair_failed")
                else ErrorCode.INVALID_CONTRACT
            )
            return self._make_error_response(
                code=code,
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
