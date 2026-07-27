"""Data operation request boundary component: validation and authorization.

Split from the former data_operation_boundary.py (which held both the request
and result boundary components) because LangFlow's directory-based custom
component loader registers exactly one component per file, named after the
file -- a second class in the same file is silently dropped from the sidebar
palette. See data_operation_result_boundary.py for the paired component.
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
    CallerFlow,
    ErrorCode,
    OperationalError,
    validate_data_operation_request,
)
from hulubul.core.models.operational.errors import ERROR_POLICY
from hulubul.request_intake.services.data_operation_policy import (
    authorize_operation,
    validate_operation_preconditions,
)

__all__ = ["DataOperationRequestBoundaryComponent"]


class DataOperationRequestBoundaryComponent(Component):
    """Validate and authorize data operation requests.

    Enforces validation-before-authorization precedence:
    1. Validate contract (rejects raw query/Cypher, undeclared fields, mismatched payload)
    2. Authorize operation (caller capability check)
    3. Validate preconditions (expected state, transition validity)

    Returns Message (valid request) or JSON (error with INVALID_CONTRACT or OPERATION_NOT_ALLOWED).
    """

    display_name = "Data Operation Request Boundary"
    description = "Validate and authorize DataOperationRequest payloads"
    icon = "shield-check"
    name = "HulubulDataOperationRequestBoundary"

    inputs = [  # noqa: RUF012
        HandleInput(  # type: ignore[call-arg]
            name="input_value",
            display_name="Data Operation Request",
            info="Typed DataOperationRequest to validate and authorize",
            input_types=["Data", "JSON"],
            required=True,
        ),
    ]

    outputs = [  # noqa: RUF012
        Output(  # type: ignore[call-arg]
            display_name="Message", name="response", type_=Message, method="build_output"
        ),
    ]

    def build_output(self) -> Message:
        """LFX-facing output: validate self.input_value.

        Always returns Message (even for errors, wrapping the JSON error as
        message text) so LFX registers a single declared output type. A
        `Message | JSON` return annotation here previously made LFX register
        `output_types=["JSON", "Message"]`, which the frontend's connection
        check treats as a strict subset requirement against the (Message-only)
        target -- silently rejecting every edge into this output.
        """
        raw_value = self.input_value
        if hasattr(raw_value, "data"):
            raw_value = raw_value.data
        result = self.validate_request_value(raw_value)
        if isinstance(result, Message):
            return result
        return Message(text=json.dumps(result.data))

    def validate_request_value(self, raw_value: dict[str, Any]) -> Message | JSON:
        """Validate and authorize request, return typed output or error.

        Args:
            raw_value: Raw request dict

        Returns:
            Message: If valid and authorized (serialized DataOperationRequest as JSON text)
            JSON: If contract validation fails (INVALID_CONTRACT) or authorization fails
                  (OPERATION_NOT_ALLOWED)
        """
        # Extract correlation_id (string from request) for error responses
        correlation_id_str = raw_value.get("correlation_id", "")

        # Step 1: Validate contract (ValidationError → INVALID_CONTRACT)
        try:
            request = validate_data_operation_request(raw_value)
        except ValidationError:
            # Contract validation failed: wrong operation, undeclared fields, etc.
            return self._make_error_response(
                code=ErrorCode.INVALID_CONTRACT,
                correlation_id_str=correlation_id_str,
            )

        # Update correlation_id from valid request (it's a string in DataOperationRequest)
        correlation_id_str = request.correlation_id

        # Step 2: Authorize operation (capability check)
        try:
            caller = CallerFlow(request.caller)
        except ValueError:
            return self._make_error_response(
                code=ErrorCode.INVALID_CONTRACT,
                correlation_id_str=correlation_id_str,
            )

        auth_error = authorize_operation(caller, request.operation)
        if auth_error is not None:
            # Create new error with correct correlation_id (model is frozen)
            return self._make_error_response(
                code=auth_error.code,
                correlation_id_str=correlation_id_str,
            )

        # Step 3: Validate preconditions (state transitions, timestamps, etc.)
        precond_error = validate_operation_preconditions(request)
        if precond_error is not None:
            # Create new error with correct correlation_id (model is frozen)
            return self._make_error_response(
                code=precond_error.code,
                correlation_id_str=correlation_id_str,
            )

        # Success: return typed Message with validated request
        return Message(text=request.model_dump_json())

    def _make_error_response(
        self,
        code: ErrorCode,
        correlation_id_str: str,
    ) -> JSON:
        """Create error response with request's correlation_id.

        Args:
            code: The ErrorCode
            correlation_id_str: The request's correlation_id string

        Returns:
            JSON: Serialized OperationalError with correct correlation_id
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
