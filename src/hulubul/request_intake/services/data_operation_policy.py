"""Caller capability and data operation policy.

Task 13 defines which data operations are allowed for each caller flow (LF-00,
LF-10, LF-70), with pre/postcondition validation tied to request status via
the fixed transition table from Task 11.

Pure domain logic: no I/O, no framework dependencies.
"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from hulubul.core.models.operational import (
    ERROR_POLICY,
    CallerFlow,
    DataOperation,
    DataOperationRequest,
    DataOperationResult,
    ErrorCode,
    OperationalError,
    RequestStatus,
    SetRequestStatusRequest,
)
from hulubul.request_intake.models.transitions import ALLOWED_TRANSITIONS

__all__ = [
    "ALLOWED_OPERATIONS",
    "authorize_operation",
    "validate_operation_preconditions",
    "validate_result_postconditions",
]


ALLOWED_OPERATIONS: dict[CallerFlow, frozenset[DataOperation]] = {
    CallerFlow.LF_00: frozenset(
        [
            DataOperation.GET_REQUEST_ROUTING_CONTEXT,
        ]
    ),
    CallerFlow.LF_10: frozenset(
        [
            DataOperation.CREATE_DELIVERY_REQUEST,
            DataOperation.READ_DELIVERY_REQUEST,
            DataOperation.UPDATE_DELIVERY_REQUEST,
            DataOperation.SET_REQUEST_STATUS,
        ]
    ),
    CallerFlow.LF_70: frozenset(
        [
            DataOperation.GET_REQUEST_ROUTING_CONTEXT,
            DataOperation.CREATE_DELIVERY_REQUEST,
            DataOperation.READ_DELIVERY_REQUEST,
            DataOperation.UPDATE_DELIVERY_REQUEST,
            DataOperation.SET_REQUEST_STATUS,
        ]
    ),
}
"""Caller capability matrix: which operations each flow (LF-00, LF-10, LF-70) may invoke."""


def _operational_error(code: ErrorCode) -> OperationalError:
    """Build an OperationalError from an error code and policy.

    Args:
        code: The error code to wrap

    Returns:
        OperationalError with policy fields and a fabricated correlation_id

    Note:
        This fabricates correlation_id via uuid4(). Task 18's boundary component
        should patch in the actual request's correlation_id before emitting.
    """
    policy = ERROR_POLICY[code]
    # TODO(Task 18): correlation_id should come from the request, not fabricated here
    return OperationalError(
        schema_version="1.0.0",
        correlation_id=uuid4(),
        code=policy.code,
        category=policy.category,
        message=policy.safe_message,
        retryable=policy.retryable,
    )


def authorize_operation(caller: CallerFlow, operation: DataOperation) -> OperationalError | None:
    """Authorize an operation for a caller.

    Args:
        caller: The caller flow (LF-00, LF-10, or LF-70)
        operation: The operation to authorize

    Returns:
        OperationalError if not allowed, None if allowed
    """
    if operation not in ALLOWED_OPERATIONS[caller]:
        return _operational_error(ErrorCode.OPERATION_NOT_ALLOWED)
    return None


def validate_operation_preconditions(request: DataOperationRequest) -> OperationalError | None:
    """Validate operation preconditions before execution.

    For SetRequestStatus, validates that the transition is allowed using
    the transition policy from Task 11 (ALLOWED_TRANSITIONS).

    Args:
        request: The data operation request

    Returns:
        OperationalError if preconditions fail, None if valid
    """
    if isinstance(request, SetRequestStatusRequest):
        try:
            expected_status = RequestStatus(request.expected_status)
            target_status = RequestStatus(request.target_status)
        except ValueError:
            return _operational_error(ErrorCode.INVALID_CONTRACT)

        try:
            datetime.fromisoformat(request.expected_updated_at)
        except (ValueError, TypeError):
            return _operational_error(ErrorCode.INVALID_CONTRACT)

        if target_status not in ALLOWED_TRANSITIONS.get(expected_status, frozenset()):
            return _operational_error(ErrorCode.INVALID_STATUS_TRANSITION)

    return None


def validate_result_postconditions(
    request: DataOperationRequest, result: DataOperationResult
) -> OperationalError | None:
    """Validate result postconditions after operation execution.

    Args:
        request: The original operation request
        result: The operation result

    Returns:
        OperationalError if postconditions fail, None if valid
    """
    if result.operation != request.operation:
        return _operational_error(ErrorCode.INVALID_CONTRACT)

    is_write = request.operation in {
        DataOperation.CREATE_DELIVERY_REQUEST,
        DataOperation.UPDATE_DELIVERY_REQUEST,
        DataOperation.SET_REQUEST_STATUS,
    }

    if is_write and result.success and result.write_dispatched and result.count != 1:
        return _operational_error(ErrorCode.AFFECTED_RECORD_COUNT_MISMATCH)

    return None
