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
    def _as_dict(value: Any) -> dict[str, Any]:
        """Coerce an incoming Message/Data/JSON edge value into a plain dict."""
        if isinstance(value, Message):
            text = value.text
            return json.loads(text) if isinstance(text, str) else {}
        if hasattr(value, "data"):
            return dict(value.data)
        return dict(value)

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
            # Request should already be valid, but safety check
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
