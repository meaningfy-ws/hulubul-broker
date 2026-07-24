"""Tests for data operation policy."""

from datetime import datetime, timezone

from hulubul.core.models.operational import (
    CallerFlow,
    CreateDeliveryRequestRequest,
    DataOperation,
    DataOperationOutcome,
    DataOperationResult,
    ErrorCode,
    RequestStatus,
    SetRequestStatusRequest,
)
from hulubul.request_intake.services.data_operation_policy import (
    ALLOWED_OPERATIONS,
    authorize_operation,
    validate_operation_preconditions,
    validate_result_postconditions,
)


# Task 13 Step 1: Capability matrix tests
def test_lf00_allowed_operations() -> None:
    """LF-00 can only GET_REQUEST_ROUTING_CONTEXT."""
    assert ALLOWED_OPERATIONS[CallerFlow.LF_00] == frozenset(
        {DataOperation.GET_REQUEST_ROUTING_CONTEXT}
    )


def test_lf10_allowed_operations() -> None:
    """LF-10 can create, read, update, and set status."""
    expected = frozenset(
        {
            DataOperation.CREATE_DELIVERY_REQUEST,
            DataOperation.READ_DELIVERY_REQUEST,
            DataOperation.UPDATE_DELIVERY_REQUEST,
            DataOperation.SET_REQUEST_STATUS,
        }
    )
    assert ALLOWED_OPERATIONS[CallerFlow.LF_10] == expected


def test_lf70_allowed_operations() -> None:
    """LF-70 can perform all five operations including routing context."""
    expected = frozenset(
        {
            DataOperation.GET_REQUEST_ROUTING_CONTEXT,
            DataOperation.CREATE_DELIVERY_REQUEST,
            DataOperation.READ_DELIVERY_REQUEST,
            DataOperation.UPDATE_DELIVERY_REQUEST,
            DataOperation.SET_REQUEST_STATUS,
        }
    )
    assert ALLOWED_OPERATIONS[CallerFlow.LF_70] == expected


def test_all_operation_values_are_immutable_frozensets() -> None:
    """Every ALLOWED_OPERATIONS value must be a frozenset (immutable)."""
    for _, ops in ALLOWED_OPERATIONS.items():
        assert isinstance(ops, frozenset)


# Task 13 Step 3: authorize_operation tests
def test_lf00_get_routing_context_allowed() -> None:
    """LF-00 is allowed to get routing context."""
    error = authorize_operation(CallerFlow.LF_00, DataOperation.GET_REQUEST_ROUTING_CONTEXT)
    assert error is None


def test_lf00_create_request_not_allowed() -> None:
    """LF-00 is not allowed to create requests."""
    error = authorize_operation(CallerFlow.LF_00, DataOperation.CREATE_DELIVERY_REQUEST)
    assert error is not None
    assert error.code == ErrorCode.OPERATION_NOT_ALLOWED


def test_lf10_create_allowed() -> None:
    """LF-10 is allowed to create."""
    error = authorize_operation(CallerFlow.LF_10, DataOperation.CREATE_DELIVERY_REQUEST)
    assert error is None


def test_lf10_get_routing_context_not_allowed() -> None:
    """LF-10 is not allowed to get routing context."""
    error = authorize_operation(CallerFlow.LF_10, DataOperation.GET_REQUEST_ROUTING_CONTEXT)
    assert error is not None
    assert error.code == ErrorCode.OPERATION_NOT_ALLOWED


def test_lf70_all_operations_allowed() -> None:
    """LF-70 is allowed all operations."""
    for operation in DataOperation:
        error = authorize_operation(CallerFlow.LF_70, operation)
        assert error is None, f"LF-70 should be allowed {operation}"


# Task 13 Step 3: validate_operation_preconditions tests
def test_create_request_requires_identifiers_and_facts() -> None:
    """Create request precondition validation."""
    request = CreateDeliveryRequestRequest(
        operation=DataOperation.CREATE_DELIVERY_REQUEST,
        operation_id="op-1",
        caller=CallerFlow.LF_10.value,
        session_id="sess-1",
        actor_id="actor-1",
        schema_version="1.0.0",
        correlation_id="corr-1",
        identifiers={"req_id": "req-1"},
        facts={"receiver": "Alice"},
    )
    error = validate_operation_preconditions(request)
    assert error is None


def test_set_status_with_valid_transition() -> None:
    """Status transition precondition validation."""
    now = datetime.now(timezone.utc).isoformat()
    request = SetRequestStatusRequest(
        operation=DataOperation.SET_REQUEST_STATUS,
        operation_id="op-1",
        caller=CallerFlow.LF_10.value,
        session_id="sess-1",
        actor_id="actor-1",
        schema_version="1.0.0",
        correlation_id="corr-1",
        request_id="req-1",
        expected_updated_at=now,
        expected_status=RequestStatus.NEW.value,
        target_status=RequestStatus.NEEDS_CLARIFICATION.value,
    )
    error = validate_operation_preconditions(request)
    assert error is None


def test_set_status_with_invalid_transition() -> None:
    """Invalid status transition rejected in preconditions."""
    now = datetime.now(timezone.utc).isoformat()
    request = SetRequestStatusRequest(
        operation=DataOperation.SET_REQUEST_STATUS,
        operation_id="op-1",
        caller=CallerFlow.LF_10.value,
        session_id="sess-1",
        actor_id="actor-1",
        schema_version="1.0.0",
        correlation_id="corr-1",
        request_id="req-1",
        expected_updated_at=now,
        expected_status=RequestStatus.NEEDS_CLARIFICATION.value,
        target_status=RequestStatus.WAITING_RESPONSE.value,
    )
    error = validate_operation_preconditions(request)
    assert error is not None
    assert error.code == ErrorCode.INVALID_STATUS_TRANSITION


# Task 13 Step 3: validate_result_postconditions tests
def test_confirmed_result_valid() -> None:
    """Confirmed result with success=True is valid."""
    request = CreateDeliveryRequestRequest(
        operation=DataOperation.CREATE_DELIVERY_REQUEST,
        operation_id="op-1",
        caller=CallerFlow.LF_10.value,
        session_id="sess-1",
        actor_id="actor-1",
        schema_version="1.0.0",
        correlation_id="corr-1",
        identifiers={},
        facts={},
    )
    now = datetime.now(timezone.utc)
    result = DataOperationResult(
        operation=DataOperation.CREATE_DELIVERY_REQUEST,
        outcome=DataOperationOutcome.CONFIRMED,
        success=True,
        write_dispatched=True,
        request_id="req-1",
        status=RequestStatus.NEW.value,
        count=1,
        created_at=now,
        updated_at=now,
    )
    error = validate_result_postconditions(request, result)
    assert error is None


def test_rejected_result_invalid() -> None:
    """Rejected result cannot claim success."""
    request = CreateDeliveryRequestRequest(
        operation=DataOperation.CREATE_DELIVERY_REQUEST,
        operation_id="op-1",
        caller=CallerFlow.LF_10.value,
        session_id="sess-1",
        actor_id="actor-1",
        schema_version="1.0.0",
        correlation_id="corr-1",
        identifiers={},
        facts={},
    )
    result = DataOperationResult(
        operation=DataOperation.CREATE_DELIVERY_REQUEST,
        outcome=DataOperationOutcome.REJECTED,
        success=False,
        write_dispatched=False,
        error_code=ErrorCode.OPERATION_NOT_ALLOWED.value,
    )
    error = validate_result_postconditions(request, result)
    assert error is None


def test_result_operation_mismatch() -> None:
    """Result operation must match request operation."""
    request = CreateDeliveryRequestRequest(
        operation=DataOperation.CREATE_DELIVERY_REQUEST,
        operation_id="op-1",
        caller=CallerFlow.LF_10.value,
        session_id="sess-1",
        actor_id="actor-1",
        schema_version="1.0.0",
        correlation_id="corr-1",
        identifiers={},
        facts={},
    )
    result = DataOperationResult(
        operation=DataOperation.READ_DELIVERY_REQUEST,  # Mismatch
        outcome=DataOperationOutcome.CONFIRMED,
        success=True,
        write_dispatched=False,  # Read operations have write_dispatched=False
        request_id="req-1",
    )
    error = validate_result_postconditions(request, result)
    assert error is not None
    assert error.code == ErrorCode.INVALID_CONTRACT


def test_affected_count_mismatch() -> None:
    """Write result must have exactly one affected request."""
    request = CreateDeliveryRequestRequest(
        operation=DataOperation.CREATE_DELIVERY_REQUEST,
        operation_id="op-1",
        caller=CallerFlow.LF_10.value,
        session_id="sess-1",
        actor_id="actor-1",
        schema_version="1.0.0",
        correlation_id="corr-1",
        identifiers={},
        facts={},
    )
    result = DataOperationResult(
        operation=DataOperation.CREATE_DELIVERY_REQUEST,
        outcome=DataOperationOutcome.CONFIRMED,
        success=True,
        write_dispatched=True,
        request_id="req-1",
        count=2,  # Wrong count
    )
    error = validate_result_postconditions(request, result)
    assert error is not None
    assert error.code == ErrorCode.AFFECTED_RECORD_COUNT_MISMATCH
