"""Data operation boundary components: validation, authorization, serialization.

This module provides two LFX components for handling data operation contracts:

1. DataOperationRequestBoundaryComponent: Validates and authorizes operation requests
   - Enforces validation-before-authorization precedence
   - Contracts validated first (unknown operations, raw cypher, undeclared fields)
   - Then capability policy (caller can invoke operation)
   - Then preconditions (state transition validity)
   - Patches request correlation_id into errors (not fabricated)

2. DataOperationResultBoundaryComponent: Validates and serializes operation results
   - Verifies postconditions (request/result operation match, count correctness)
   - Patches result's correlation_id into errors if available
   - Returns typed JSON output (never raw dict)

Both components enforce:
- Validation-before-authorization (contract is prerequisite for capability check)
- Only fully-valid operations can be denied for capability
- Error redaction (no user values exposed)
- Type translation to INVALID_CONTRACT on contract failures
- Output as typed Message/JSON, never raw dict
"""

from typing import Any
from uuid import UUID

from lfx.custom.custom_component.component import Component
from lfx.schema.data import JSON
from lfx.schema.message import Message
from pydantic import ValidationError

from hulubul.core.models.operational import (
    CallerFlow,
    DataOperationResult,
    ErrorCode,
    OperationalError,
    validate_data_operation_request,
)
from hulubul.core.models.operational.errors import ERROR_POLICY
from hulubul.request_intake.services.data_operation_policy import (
    authorize_operation,
    validate_operation_preconditions,
    validate_result_postconditions,
)

__all__ = [
    "DataOperationRequestBoundaryComponent",
    "DataOperationResultBoundaryComponent",
]


class DataOperationRequestBoundaryComponent(Component):
    """Validate and authorize data operation requests.

    Enforces validation-before-authorization precedence:
    1. Validate contract (rejects raw query/Cypher, undeclared fields, mismatched payload)
    2. Authorize operation (caller capability check)
    3. Validate preconditions (expected state, transition validity)

    Returns Message (valid request) or JSON (error with INVALID_CONTRACT or OPERATION_NOT_ALLOWED).
    """

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

        return JSON(data=error.model_dump())


class DataOperationResultBoundaryComponent(Component):
    """Validate and serialize operation results.

    Verifies result postconditions:
    - Request/result operation match
    - Affected count matches expectations (write operations)
    - Timestamps and status consistency (as defined by operation type)
    - Correlation/operation ID coherence

    Returns JSON with typed result or error (INVALID_CONTRACT or other).
    """

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

        return JSON(data=error.model_dump())
