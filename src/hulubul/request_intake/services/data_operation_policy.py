"""Caller capability and data operation policy.

Task 13 defines which data operations are allowed for each caller flow (LF-00,
LF-10, LF-70), with pre/postcondition validation tied to request status via
the fixed transition table from Task 11.

Pure domain logic: no I/O, no framework dependencies.
"""
from __future__ import annotations

from hulubul.core.models.operational.enums import CallerFlow, DataOperation, ErrorCode

__all__ = [
    "ALLOWED_OPERATIONS",
    "authorize_operation",
    "validate_operation_preconditions",
    "validate_result_postconditions",
]


ALLOWED_OPERATIONS: dict[CallerFlow, frozenset[DataOperation]] = {
    CallerFlow.LF_00: frozenset([
        DataOperation.GET_REQUEST_ROUTING_CONTEXT,
    ]),
    CallerFlow.LF_10: frozenset([
        DataOperation.CREATE_DELIVERY_REQUEST,
        DataOperation.READ_DELIVERY_REQUEST,
        DataOperation.UPDATE_DELIVERY_REQUEST,
        DataOperation.SET_REQUEST_STATUS,
    ]),
    CallerFlow.LF_70: frozenset([
        DataOperation.CREATE_DELIVERY_REQUEST,
        DataOperation.READ_DELIVERY_REQUEST,
        DataOperation.UPDATE_DELIVERY_REQUEST,
        DataOperation.SET_REQUEST_STATUS,
    ]),
}
"""Caller capability matrix: which operations each flow (LF-00, LF-10, LF-70) may invoke."""


def authorize_operation(
    caller: CallerFlow, operation: DataOperation
) -> ErrorCode | None:
    """Check if caller is authorized for the operation.

    Returns None if authorized; ErrorCode.OPERATION_NOT_ALLOWED if not.
    Callers (entrypoints) are responsible for converting error codes to OperationalError.

    Args:
        caller: The calling flow (LF-00, LF-10, or LF-70)
        operation: The requested operation

    Returns:
        None if authorized, or error code indicating authorization failure
    """
    if caller not in ALLOWED_OPERATIONS:
        # Unknown caller flow (should not happen with typed CallerFlow enum)
        return ErrorCode.OPERATION_NOT_ALLOWED

    if operation not in ALLOWED_OPERATIONS[caller]:
        return ErrorCode.OPERATION_NOT_ALLOWED

    return None


def validate_operation_preconditions(
    request: object,
) -> ErrorCode | None:
    """Validate preconditions for the operation (e.g., CAS, status transitions).

    This is a placeholder; full implementation depends on Task 11 (ALLOWED_TRANSITIONS)
    and request-specific logic.

    Args:
        request: The operation request

    Returns:
        None if preconditions pass, or error code if they fail
    """
    # Placeholder: future work will add status transition validation via Task 11.
    return None


def validate_result_postconditions(
    request: object, result: object
) -> ErrorCode | None:
    """Validate postconditions for the result (e.g., consistency, count matching).

    Verifies that the result is consistent with the request (IDs match, operation
    matches, etc.) and that invariants are upheld (e.g., confirmed writes must have
    dispatch=true and count=1).

    Args:
        request: The original operation request
        result: The operation result returned from Neo4j/MCP

    Returns:
        None if postconditions pass, or error code if they fail
    """
    # Placeholder: full implementation compares request/result and validates invariants.
    return None
