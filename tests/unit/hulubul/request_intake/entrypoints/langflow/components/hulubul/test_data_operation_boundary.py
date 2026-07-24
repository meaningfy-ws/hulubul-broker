"""Tests for data operation boundary components: validation, authorization, serialization."""

from datetime import datetime
from typing import Any
from uuid import uuid4

import pytest
from lfx.schema.data import JSON
from lfx.schema.message import Message

from hulubul.core.models.operational import (
    CallerFlow,
    DataOperation,
    DataOperationOutcome,
    ErrorCode,
    RequestStatus,
    validate_data_operation_request,
)
from hulubul.request_intake.entrypoints.langflow.components.hulubul.data_operation_boundary import (
    DataOperationRequestBoundaryComponent,
    DataOperationResultBoundaryComponent,
)

# ============================================================================
# Fixtures and Helpers
# ============================================================================

FIXED_CORRELATION_ID = uuid4()
FIXED_SESSION_ID = "p1-12345678-1234-4000-8000-000000000000"
FIXED_ACTOR_ID = "urn:uuid:test-actor-id"
FIXED_OPERATION_ID = "op-12345678-1234-4000-8000-000000000000"
FIXED_REQUEST_ID = "req-12345678-1234-4000-8000-000000000000"


def lf00_get_routing_context_request() -> dict[str, Any]:
    """Create a valid LF-00 GET_REQUEST_ROUTING_CONTEXT request."""
    return {
        "operation": DataOperation.GET_REQUEST_ROUTING_CONTEXT.value,
        "operation_id": FIXED_OPERATION_ID,
        "caller": CallerFlow.LF_00.value,
        "session_id": FIXED_SESSION_ID,
        "actor_id": FIXED_ACTOR_ID,
        "schema_version": "1.0.0",
        "correlation_id": str(FIXED_CORRELATION_ID),
    }


def lf00_create_request() -> dict[str, Any]:
    """Create a LF-00 CREATE_DELIVERY_REQUEST request (invalid for LF-00)."""
    return {
        "operation": DataOperation.CREATE_DELIVERY_REQUEST.value,
        "operation_id": FIXED_OPERATION_ID,
        "caller": CallerFlow.LF_00.value,
        "session_id": FIXED_SESSION_ID,
        "actor_id": FIXED_ACTOR_ID,
        "schema_version": "1.0.0",
        "correlation_id": str(FIXED_CORRELATION_ID),
        "identifiers": {"sender_id": "sender-123"},
        "facts": {"item_description": "test item"},
    }


def lf10_create_request() -> dict[str, Any]:
    """Create a valid LF-10 CREATE_DELIVERY_REQUEST request."""
    return {
        "operation": DataOperation.CREATE_DELIVERY_REQUEST.value,
        "operation_id": FIXED_OPERATION_ID,
        "caller": CallerFlow.LF_10.value,
        "session_id": FIXED_SESSION_ID,
        "actor_id": FIXED_ACTOR_ID,
        "schema_version": "1.0.0",
        "correlation_id": str(FIXED_CORRELATION_ID),
        "identifiers": {"sender_id": "sender-123"},
        "facts": {"item_description": "test item"},
    }


def lf70_create_request() -> dict[str, Any]:
    """Create a valid LF-70 CREATE_DELIVERY_REQUEST request."""
    return {
        "operation": DataOperation.CREATE_DELIVERY_REQUEST.value,
        "operation_id": FIXED_OPERATION_ID,
        "caller": CallerFlow.LF_70.value,
        "session_id": FIXED_SESSION_ID,
        "actor_id": FIXED_ACTOR_ID,
        "schema_version": "1.0.0",
        "correlation_id": str(FIXED_CORRELATION_ID),
        "identifiers": {"sender_id": "sender-123"},
        "facts": {"item_description": "test item"},
    }


def lf10_set_status_request() -> dict[str, Any]:
    """Create a valid LF-10 SET_REQUEST_STATUS request."""
    return {
        "operation": DataOperation.SET_REQUEST_STATUS.value,
        "operation_id": FIXED_OPERATION_ID,
        "caller": CallerFlow.LF_10.value,
        "session_id": FIXED_SESSION_ID,
        "actor_id": FIXED_ACTOR_ID,
        "schema_version": "1.0.0",
        "correlation_id": str(FIXED_CORRELATION_ID),
        "request_id": FIXED_REQUEST_ID,
        "expected_updated_at": datetime.now().isoformat(),
        "expected_status": RequestStatus.NEW.value,
        "target_status": RequestStatus.NEEDS_CLARIFICATION.value,
    }


def lf70_read_request() -> dict[str, Any]:
    """Create a valid LF-70 READ_DELIVERY_REQUEST request."""
    return {
        "operation": DataOperation.READ_DELIVERY_REQUEST.value,
        "operation_id": FIXED_OPERATION_ID,
        "caller": CallerFlow.LF_70.value,
        "session_id": FIXED_SESSION_ID,
        "actor_id": FIXED_ACTOR_ID,
        "schema_version": "1.0.0",
        "correlation_id": str(FIXED_CORRELATION_ID),
        "request_id": FIXED_REQUEST_ID,
    }


def malformed_with_raw_query() -> dict[str, Any]:
    """Create a malformed request with raw 'query' field (MCP-specific)."""
    req = lf00_get_routing_context_request()
    req["query"] = "RETURN 1"
    return req


def malformed_with_extra_fields() -> dict[str, Any]:
    """Create a malformed request with undeclared fields."""
    req = lf00_get_routing_context_request()
    req["undeclared_field"] = "should not be here"
    return req


def malformed_with_invalid_operation() -> dict[str, Any]:
    """Create a malformed request with unknown operation."""
    req = lf00_get_routing_context_request()
    req["operation"] = "INVALID_OPERATION_123"
    return req


def malformed_create_missing_identifiers() -> dict[str, Any]:
    """Create request missing required identifiers."""
    return {
        "operation": DataOperation.CREATE_DELIVERY_REQUEST.value,
        "operation_id": FIXED_OPERATION_ID,
        "caller": CallerFlow.LF_10.value,
        "session_id": FIXED_SESSION_ID,
        "actor_id": FIXED_ACTOR_ID,
        "schema_version": "1.0.0",
        "correlation_id": str(FIXED_CORRELATION_ID),
        "facts": {"item_description": "test item"},
        # Missing identifiers
    }


@pytest.fixture
def request_boundary() -> DataOperationRequestBoundaryComponent:
    """Create a DataOperationRequestBoundaryComponent."""
    return DataOperationRequestBoundaryComponent()


@pytest.fixture
def result_boundary() -> DataOperationResultBoundaryComponent:
    """Create a DataOperationResultBoundaryComponent."""
    return DataOperationResultBoundaryComponent()


# ============================================================================
# Test: Validation Before Authorization Precedence
# ============================================================================


class TestValidationBeforeAuthorization:
    """Test that validation failures are reported before authorization failures."""

    def test_malformed_is_invalid_contract_not_authorization(
        self, request_boundary: DataOperationRequestBoundaryComponent
    ) -> None:
        """Malformed request → INVALID_CONTRACT, not authorization error."""
        raw_value = malformed_with_raw_query()
        result = request_boundary.validate_request_value(raw_value)

        assert isinstance(result, JSON)
        data = result.data
        assert data["code"] == ErrorCode.INVALID_CONTRACT.value
        assert data["category"] == "contract"

    def test_unknown_operation_is_invalid_contract(
        self, request_boundary: DataOperationRequestBoundaryComponent
    ) -> None:
        """Unknown operation → INVALID_CONTRACT before capability check."""
        raw_value = malformed_with_invalid_operation()
        result = request_boundary.validate_request_value(raw_value)

        assert isinstance(result, JSON)
        data = result.data
        assert data["code"] == ErrorCode.INVALID_CONTRACT.value

    def test_extra_fields_is_invalid_contract(
        self, request_boundary: DataOperationRequestBoundaryComponent
    ) -> None:
        """Extra undeclared fields → INVALID_CONTRACT."""
        raw_value = malformed_with_extra_fields()
        result = request_boundary.validate_request_value(raw_value)

        assert isinstance(result, JSON)
        data = result.data
        assert data["code"] == ErrorCode.INVALID_CONTRACT.value

    def test_missing_required_fields_is_invalid_contract(
        self, request_boundary: DataOperationRequestBoundaryComponent
    ) -> None:
        """Missing required fields → INVALID_CONTRACT."""
        raw_value = malformed_create_missing_identifiers()
        result = request_boundary.validate_request_value(raw_value)

        assert isinstance(result, JSON)
        data = result.data
        assert data["code"] == ErrorCode.INVALID_CONTRACT.value


# ============================================================================
# Test: LF-00 Authorization (Only GET_REQUEST_ROUTING_CONTEXT)
# ============================================================================


class TestLF00Authorization:
    """Test LF-00 authorization: only GET_REQUEST_ROUTING_CONTEXT allowed."""

    def test_lf00_get_routing_context_allowed(
        self, request_boundary: DataOperationRequestBoundaryComponent
    ) -> None:
        """LF-00 GET_REQUEST_ROUTING_CONTEXT is allowed."""
        raw_value = lf00_get_routing_context_request()
        result = request_boundary.validate_request_value(raw_value)

        # Should succeed (not be an error)
        assert isinstance(result, Message)
        parsed = validate_data_operation_request(raw_value)
        assert parsed.operation == DataOperation.GET_REQUEST_ROUTING_CONTEXT

    def test_lf00_create_denied(
        self, request_boundary: DataOperationRequestBoundaryComponent
    ) -> None:
        """LF-00 CREATE_DELIVERY_REQUEST is denied."""
        raw_value = lf00_create_request()
        result = request_boundary.validate_request_value(raw_value)

        assert isinstance(result, JSON)
        data = result.data
        assert data["code"] == ErrorCode.OPERATION_NOT_ALLOWED.value

    def test_lf00_update_denied(
        self, request_boundary: DataOperationRequestBoundaryComponent
    ) -> None:
        """LF-00 UPDATE_DELIVERY_REQUEST is denied."""
        raw_value = lf00_get_routing_context_request()
        raw_value["operation"] = DataOperation.UPDATE_DELIVERY_REQUEST.value
        raw_value["request_id"] = FIXED_REQUEST_ID
        raw_value["expected_updated_at"] = datetime.now().isoformat()
        raw_value["expected_status"] = RequestStatus.NEW.value
        raw_value["updates"] = {"some_field": "value"}
        raw_value["identifiers"] = {}

        result = request_boundary.validate_request_value(raw_value)

        assert isinstance(result, JSON)
        data = result.data
        assert data["code"] == ErrorCode.OPERATION_NOT_ALLOWED.value

    def test_lf00_read_denied(
        self, request_boundary: DataOperationRequestBoundaryComponent
    ) -> None:
        """LF-00 READ_DELIVERY_REQUEST is denied."""
        raw_value = lf00_get_routing_context_request()
        raw_value["operation"] = DataOperation.READ_DELIVERY_REQUEST.value
        raw_value["request_id"] = FIXED_REQUEST_ID

        result = request_boundary.validate_request_value(raw_value)

        assert isinstance(result, JSON)
        data = result.data
        assert data["code"] == ErrorCode.OPERATION_NOT_ALLOWED.value

    def test_lf00_set_status_denied(
        self, request_boundary: DataOperationRequestBoundaryComponent
    ) -> None:
        """LF-00 SET_REQUEST_STATUS is denied."""
        raw_value = lf00_get_routing_context_request()
        raw_value["operation"] = DataOperation.SET_REQUEST_STATUS.value
        raw_value["request_id"] = FIXED_REQUEST_ID
        raw_value["expected_updated_at"] = datetime.now().isoformat()
        raw_value["expected_status"] = RequestStatus.NEW.value
        raw_value["target_status"] = RequestStatus.NEEDS_CLARIFICATION.value

        result = request_boundary.validate_request_value(raw_value)

        assert isinstance(result, JSON)
        data = result.data
        assert data["code"] == ErrorCode.OPERATION_NOT_ALLOWED.value


# ============================================================================
# Test: LF-10 Authorization (Four Operations)
# ============================================================================


class TestLF10Authorization:
    """Test LF-10 authorization: CREATE, READ, UPDATE, SET_REQUEST_STATUS allowed."""

    def test_lf10_create_allowed(
        self, request_boundary: DataOperationRequestBoundaryComponent
    ) -> None:
        """LF-10 CREATE_DELIVERY_REQUEST is allowed."""
        raw_value = lf10_create_request()
        result = request_boundary.validate_request_value(raw_value)

        assert isinstance(result, Message)
        parsed = validate_data_operation_request(raw_value)
        assert parsed.operation == DataOperation.CREATE_DELIVERY_REQUEST

    def test_lf10_read_allowed(
        self, request_boundary: DataOperationRequestBoundaryComponent
    ) -> None:
        """LF-10 READ_DELIVERY_REQUEST is allowed."""
        raw_value = lf10_create_request()
        raw_value["operation"] = DataOperation.READ_DELIVERY_REQUEST.value
        del raw_value["identifiers"]
        del raw_value["facts"]
        raw_value["request_id"] = FIXED_REQUEST_ID

        result = request_boundary.validate_request_value(raw_value)

        assert isinstance(result, Message)

    def test_lf10_update_allowed(
        self, request_boundary: DataOperationRequestBoundaryComponent
    ) -> None:
        """LF-10 UPDATE_DELIVERY_REQUEST is allowed."""
        raw_value = lf10_create_request()
        raw_value["operation"] = DataOperation.UPDATE_DELIVERY_REQUEST.value
        del raw_value["facts"]  # UPDATE doesn't have facts field
        raw_value["request_id"] = FIXED_REQUEST_ID
        raw_value["expected_updated_at"] = datetime.now().isoformat()
        raw_value["expected_status"] = RequestStatus.NEW.value
        raw_value["updates"] = {"item_description": "updated"}
        # identifiers is required for UPDATE (keep from create_request)

        result = request_boundary.validate_request_value(raw_value)

        assert isinstance(result, Message)

    def test_lf10_set_status_allowed(
        self, request_boundary: DataOperationRequestBoundaryComponent
    ) -> None:
        """LF-10 SET_REQUEST_STATUS is allowed."""
        raw_value = lf10_set_status_request()
        result = request_boundary.validate_request_value(raw_value)

        assert isinstance(result, Message)

    def test_lf10_get_routing_context_denied(
        self, request_boundary: DataOperationRequestBoundaryComponent
    ) -> None:
        """LF-10 GET_REQUEST_ROUTING_CONTEXT is denied."""
        raw_value = lf10_create_request()
        raw_value["operation"] = DataOperation.GET_REQUEST_ROUTING_CONTEXT.value
        del raw_value["identifiers"]
        del raw_value["facts"]

        result = request_boundary.validate_request_value(raw_value)

        assert isinstance(result, JSON)
        data = result.data
        assert data["code"] == ErrorCode.OPERATION_NOT_ALLOWED.value


# ============================================================================
# Test: LF-70 Authorization (All Five Operations)
# ============================================================================


class TestLF70Authorization:
    """Test LF-70 authorization: all five operations allowed."""

    def test_lf70_get_routing_context_allowed(
        self, request_boundary: DataOperationRequestBoundaryComponent
    ) -> None:
        """LF-70 GET_REQUEST_ROUTING_CONTEXT is allowed."""
        raw_value = lf70_create_request()
        raw_value["operation"] = DataOperation.GET_REQUEST_ROUTING_CONTEXT.value
        del raw_value["identifiers"]
        del raw_value["facts"]

        result = request_boundary.validate_request_value(raw_value)

        assert isinstance(result, Message)

    def test_lf70_create_allowed(
        self, request_boundary: DataOperationRequestBoundaryComponent
    ) -> None:
        """LF-70 CREATE_DELIVERY_REQUEST is allowed."""
        raw_value = lf70_create_request()
        result = request_boundary.validate_request_value(raw_value)

        assert isinstance(result, Message)

    def test_lf70_read_allowed(
        self, request_boundary: DataOperationRequestBoundaryComponent
    ) -> None:
        """LF-70 READ_DELIVERY_REQUEST is allowed."""
        raw_value = lf70_read_request()
        result = request_boundary.validate_request_value(raw_value)

        assert isinstance(result, Message)

    def test_lf70_update_allowed(
        self, request_boundary: DataOperationRequestBoundaryComponent
    ) -> None:
        """LF-70 UPDATE_DELIVERY_REQUEST is allowed."""
        raw_value = lf70_create_request()
        raw_value["operation"] = DataOperation.UPDATE_DELIVERY_REQUEST.value
        del raw_value["facts"]  # UPDATE doesn't have facts field
        raw_value["request_id"] = FIXED_REQUEST_ID
        raw_value["expected_updated_at"] = datetime.now().isoformat()
        raw_value["expected_status"] = RequestStatus.NEW.value
        raw_value["updates"] = {"item_description": "updated"}
        # identifiers is required for UPDATE (keep from create_request)

        result = request_boundary.validate_request_value(raw_value)

        assert isinstance(result, Message)

    def test_lf70_set_status_allowed(
        self, request_boundary: DataOperationRequestBoundaryComponent
    ) -> None:
        """LF-70 SET_REQUEST_STATUS is allowed."""
        raw_value = lf70_create_request()
        raw_value["operation"] = DataOperation.SET_REQUEST_STATUS.value
        del raw_value["identifiers"]
        del raw_value["facts"]
        raw_value["request_id"] = FIXED_REQUEST_ID
        raw_value["expected_updated_at"] = datetime.now().isoformat()
        raw_value["expected_status"] = RequestStatus.NEW.value
        raw_value["target_status"] = RequestStatus.COMPLETE.value

        result = request_boundary.validate_request_value(raw_value)

        assert isinstance(result, Message)


# ============================================================================
# Test: Preconditions Validation (Status Transitions)
# ============================================================================


class TestPreconditionsValidation:
    """Test precondition validation for state transitions."""

    def test_set_status_valid_transition(
        self, request_boundary: DataOperationRequestBoundaryComponent
    ) -> None:
        """Valid status transition passes preconditions."""
        raw_value = lf10_set_status_request()
        result = request_boundary.validate_request_value(raw_value)

        # Should succeed (not error)
        assert isinstance(result, Message)

    def test_set_status_invalid_transition(
        self, request_boundary: DataOperationRequestBoundaryComponent
    ) -> None:
        """Invalid status transition fails preconditions."""
        raw_value = lf10_set_status_request()
        # Use an invalid transition (COMPLETE -> NEW is not allowed)
        raw_value["expected_status"] = RequestStatus.COMPLETE.value
        raw_value["target_status"] = RequestStatus.NEW.value

        result = request_boundary.validate_request_value(raw_value)

        assert isinstance(result, JSON)
        data = result.data
        assert data["code"] == ErrorCode.INVALID_STATUS_TRANSITION.value

    def test_set_status_invalid_expected_timestamp_format(
        self, request_boundary: DataOperationRequestBoundaryComponent
    ) -> None:
        """Invalid timestamp format fails validation."""
        raw_value = lf10_set_status_request()
        raw_value["expected_updated_at"] = "not-a-valid-timestamp"

        result = request_boundary.validate_request_value(raw_value)

        assert isinstance(result, JSON)
        data = result.data
        assert data["code"] == ErrorCode.INVALID_CONTRACT.value

    def test_set_status_invalid_status_value(
        self, request_boundary: DataOperationRequestBoundaryComponent
    ) -> None:
        """Invalid status value fails validation."""
        raw_value = lf10_set_status_request()
        raw_value["expected_status"] = "INVALID_STATUS_123"

        result = request_boundary.validate_request_value(raw_value)

        assert isinstance(result, JSON)
        data = result.data
        assert data["code"] == ErrorCode.INVALID_CONTRACT.value


# ============================================================================
# Test: Result Postconditions Validation
# ============================================================================


class TestResultPostconditionsValidation:
    """Test result postcondition validation."""

    def test_confirmed_write_result_valid(
        self, result_boundary: DataOperationResultBoundaryComponent
    ) -> None:
        """Confirmed write result with dispatch=true and count=1 is valid."""
        request_dict = lf10_create_request()

        # Use the same datetime for both created_at and updated_at (required for confirmed create)
        # and convert to ISO format string (Pydantic will parse it)
        now = datetime.now().isoformat()
        result_dict = {
            "operation": DataOperation.CREATE_DELIVERY_REQUEST.value,
            "outcome": DataOperationOutcome.CONFIRMED.value,
            "success": True,
            "write_dispatched": True,
            "request_id": FIXED_REQUEST_ID,
            "status": RequestStatus.NEW.value,
            "count": 1,
            "created_at": now,
            "updated_at": now,
        }

        output = result_boundary.validate_result_value(result_dict, request_dict)

        assert isinstance(output, JSON)
        data = output.data
        # Should succeed (have outcome field, not error code)
        assert data.get("outcome") is not None or data.get("success") is not None

    def test_mismatched_operation_fails_postcondition(
        self, result_boundary: DataOperationResultBoundaryComponent
    ) -> None:
        """Mismatched operation between request and result fails."""
        request_dict = lf10_create_request()

        result_dict = {
            "operation": DataOperation.READ_DELIVERY_REQUEST.value,
            "outcome": DataOperationOutcome.CONFIRMED.value,
            "success": True,
            "write_dispatched": False,
            "request_id": FIXED_REQUEST_ID,
        }

        output = result_boundary.validate_result_value(result_dict, request_dict)

        assert isinstance(output, JSON)
        data = output.data
        assert data["code"] == ErrorCode.INVALID_CONTRACT.value

    def test_write_affected_count_mismatch_fails(
        self, result_boundary: DataOperationResultBoundaryComponent
    ) -> None:
        """Write with affected count != 1 fails postcondition."""
        request_dict = lf10_create_request()

        # Use the same datetime for both created_at and updated_at (required for confirmed create)
        now = datetime.now().isoformat()
        result_dict = {
            "operation": DataOperation.CREATE_DELIVERY_REQUEST.value,
            "outcome": DataOperationOutcome.CONFIRMED.value,
            "success": True,
            "write_dispatched": True,
            "request_id": FIXED_REQUEST_ID,
            "status": RequestStatus.NEW.value,
            "count": 2,  # Should be 1
            "created_at": now,
            "updated_at": now,
        }

        output = result_boundary.validate_result_value(result_dict, request_dict)

        assert isinstance(output, JSON)
        data = output.data
        assert data["code"] == ErrorCode.AFFECTED_RECORD_COUNT_MISMATCH.value


# ============================================================================
# Test: Output is Typed Message/JSON (No Raw Dict)
# ============================================================================


class TestNoRawDictOutput:
    """Test that output is always typed Message/JSON, never raw dict."""

    def test_valid_request_returns_message(
        self, request_boundary: DataOperationRequestBoundaryComponent
    ) -> None:
        """Valid request returns typed Message."""
        raw_value = lf10_create_request()
        result = request_boundary.validate_request_value(raw_value)

        assert isinstance(result, Message)
        assert not isinstance(result, dict)

    def test_invalid_request_returns_json(
        self, request_boundary: DataOperationRequestBoundaryComponent
    ) -> None:
        """Invalid request returns typed JSON with error."""
        raw_value = malformed_with_raw_query()
        result = request_boundary.validate_request_value(raw_value)

        assert isinstance(result, JSON)
        assert not isinstance(result, dict)

    def test_result_returns_json(
        self, result_boundary: DataOperationResultBoundaryComponent
    ) -> None:
        """Result validation returns typed JSON."""
        request_dict = lf10_create_request()

        result_dict = {
            "operation": DataOperation.CREATE_DELIVERY_REQUEST.value,
            "outcome": DataOperationOutcome.CONFIRMED.value,
            "success": True,
            "write_dispatched": True,
            "request_id": FIXED_REQUEST_ID,
            "count": 1,
        }

        output = result_boundary.validate_result_value(result_dict, request_dict)

        assert isinstance(output, JSON)
        assert not isinstance(output, dict)


# ============================================================================
# Test: Correlation ID Patching (Task 18 TODO)
# ============================================================================


class TestCorrelationIdPatching:
    """Test that boundary patches actual correlation_id into errors."""

    def test_error_has_request_correlation_id(
        self, request_boundary: DataOperationRequestBoundaryComponent
    ) -> None:
        """Error response includes request's correlation_id, not fabricated."""
        raw_value = lf00_create_request()
        result = request_boundary.validate_request_value(raw_value)

        assert isinstance(result, JSON)
        data = result.data
        # Should use request's correlation_id
        assert str(data["correlation_id"]) == str(FIXED_CORRELATION_ID)

    def test_error_has_result_correlation_id(
        self, result_boundary: DataOperationResultBoundaryComponent
    ) -> None:
        """Result error uses result's correlation_id if available."""
        request_dict = lf10_create_request()

        result_dict = {
            "operation": DataOperation.READ_DELIVERY_REQUEST.value,
            "outcome": DataOperationOutcome.CONFIRMED.value,
            "success": True,
            "write_dispatched": False,
            "request_id": FIXED_REQUEST_ID,
        }

        output = result_boundary.validate_result_value(result_dict, request_dict)

        assert isinstance(output, JSON)
        data = output.data
        # Should have correlation_id (from request if not in result)
        assert "correlation_id" in data
