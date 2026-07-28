"""Tests for data operation boundary components: validation, authorization, serialization."""

import json
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
from hulubul.request_intake.entrypoints.langflow.components.hulubul.data_operation_request_boundary import (
    DataOperationRequestBoundaryComponent,
)
from hulubul.request_intake.entrypoints.langflow.components.hulubul.data_operation_result_boundary import (
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
        # Should use request's correlation_id, as a JSON-native str (not UUID)
        assert data["correlation_id"] == str(FIXED_CORRELATION_ID)
        assert isinstance(data["correlation_id"], str)
        json.dumps(data)  # must not raise

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
        # Should have correlation_id (from request if not in result), JSON-native
        assert "correlation_id" in data
        assert isinstance(data["correlation_id"], str)
        json.dumps(data)  # must not raise


class TestRequestInputValueCoercion:
    """input_value is MessageTextInput (not HandleInput): it must accept a Message
    (edge-connected), a plain JSON string (literal value/tweak), or a dict-like
    Data/JSON object, and coerce all three into a dict for validate_request_value.

    MessageTextInput was chosen over HandleInput specifically because HandleInput
    fields never read their own literal `value` in LangFlow -- confirmed by
    directly baking a value into a pushed flow and observing it stay None at
    build time -- which made this component's public entry point unreachable via
    the plain Run Flow API (and would equally break LF-10's future Tool Mode
    invocation of this flow, which sets tool arguments the same way).
    """

    def test_message_input_is_parsed(
        self, request_boundary: DataOperationRequestBoundaryComponent
    ) -> None:
        request_boundary.input_value = Message(text=json.dumps(lf00_get_routing_context_request()))
        result = request_boundary.build_output()
        assert isinstance(result, Message)

    def test_json_string_input_is_parsed(
        self, request_boundary: DataOperationRequestBoundaryComponent
    ) -> None:
        request_boundary.input_value = json.dumps(lf00_get_routing_context_request())
        result = request_boundary.build_output()
        assert isinstance(result, Message)

    def test_dict_like_input_is_still_accepted(
        self, request_boundary: DataOperationRequestBoundaryComponent
    ) -> None:
        from lfx.schema.data import Data

        request_boundary.input_value = Data(data=lf00_get_routing_context_request())
        result = request_boundary.build_output()
        assert isinstance(result, Message)

    def test_empty_string_input_is_invalid_contract(
        self, request_boundary: DataOperationRequestBoundaryComponent
    ) -> None:
        request_boundary.input_value = ""
        result = request_boundary.build_output()
        assert isinstance(result, Message)
        text = result.text
        assert isinstance(text, str)
        payload = json.loads(text)
        assert payload["code"] == ErrorCode.INVALID_CONTRACT.value

    def test_non_json_literal_input_is_invalid_contract(
        self, request_boundary: DataOperationRequestBoundaryComponent
    ) -> None:
        """A malformed literal (not valid JSON) must not crash the component build.

        Confirmed live: a plain-text `input_value` raised an unhandled
        JSONDecodeError ("Expecting value: line 1 column 1 (char 0)") that
        took down the whole flow with a 500, instead of being rejected as a
        normal INVALID_CONTRACT response.
        """
        request_boundary.input_value = "not-json-at-all"
        result = request_boundary.build_output()
        assert isinstance(result, Message)
        text = result.text
        assert isinstance(text, str)
        payload = json.loads(text)
        assert payload["code"] == ErrorCode.INVALID_CONTRACT.value


class TestResultRawValueCoercion:
    """The Agent's final text is LLM-generated and not guaranteed to be valid
    JSON (e.g. it may explain a failure in prose instead of emitting the
    DataOperationResult contract). The result boundary must reject that as
    INVALID_CONTRACT rather than crash the component build with an unhandled
    JSONDecodeError -- confirmed live: a confused Agent run produced a prose
    Message ("The error message `INVALID_CONTRACT`...") and json.loads() on
    that text raised, taking down the whole flow with a 500.
    """

    def test_non_json_agent_text_is_invalid_contract(
        self, result_boundary: DataOperationResultBoundaryComponent
    ) -> None:
        result_boundary.raw_value = Message(text="I could not produce a safe response.")
        result_boundary.request_dict = Message(text=json.dumps(lf10_create_request()))
        result = result_boundary.build_output()

        assert isinstance(result, JSON)
        assert result.data["code"] == ErrorCode.INVALID_CONTRACT.value

    def test_empty_agent_text_is_invalid_contract(
        self, result_boundary: DataOperationResultBoundaryComponent
    ) -> None:
        result_boundary.raw_value = Message(text="")
        result_boundary.request_dict = Message(text=json.dumps(lf10_create_request()))
        result = result_boundary.build_output()

        assert isinstance(result, JSON)
        assert result.data["code"] == ErrorCode.INVALID_CONTRACT.value


class TestRepairFailedMarker:
    """DEC-016: `_repair_failed` (set by HulubulDataAccessAgentComponent's
    tool-less repair pass) distinguishes "the Agent already tried once to
    reformat this and still couldn't" (MALFORMED_AGENT_RESULT) from "never
    attempted" (INVALID_CONTRACT) -- both still shape-invalid, only the
    error code differs.
    """

    def test_marked_still_invalid_result_is_malformed_agent_result(
        self, result_boundary: DataOperationResultBoundaryComponent
    ) -> None:
        result_boundary.raw_value = Message(
            text=json.dumps({"_repair_failed": True, "_raw_operation": "createDeliveryRequest"})
        )
        result_boundary.request_dict = Message(text=json.dumps(lf10_create_request()))
        result = result_boundary.build_output()

        assert isinstance(result, JSON)
        assert result.data["code"] == ErrorCode.MALFORMED_AGENT_RESULT.value

    def test_unmarked_invalid_result_is_still_invalid_contract(
        self, result_boundary: DataOperationResultBoundaryComponent
    ) -> None:
        """No `_repair_failed` marker (e.g. getRequestRoutingContext's shape,
        which never goes through result-shape repair) -- unchanged behavior."""
        result_boundary.raw_value = Message(text=json.dumps({"foo": "bar"}))
        result_boundary.request_dict = Message(text=json.dumps(lf10_create_request()))
        result = result_boundary.build_output()

        assert isinstance(result, JSON)
        assert result.data["code"] == ErrorCode.INVALID_CONTRACT.value

    def test_repair_failed_marker_ignored_when_result_is_actually_valid(
        self, result_boundary: DataOperationResultBoundaryComponent
    ) -> None:
        """A stray `_repair_failed` key on an otherwise-valid result is just
        an unexpected field -- DataOperationResult's extra='forbid' rejects
        it as INVALID_CONTRACT, same as any other malformed shape; it must
        not be misread as a successful result."""
        payload = {
            "operation": DataOperation.CREATE_DELIVERY_REQUEST.value,
            "outcome": DataOperationOutcome.CONFIRMED.value,
            "success": True,
            "write_dispatched": True,
            "count": 1,
            "_repair_failed": True,
        }
        result_boundary.raw_value = Message(text=json.dumps(payload))
        result_boundary.request_dict = Message(text=json.dumps(lf10_create_request()))
        result = result_boundary.build_output()

        assert isinstance(result, JSON)
        assert result.data["code"] == ErrorCode.MALFORMED_AGENT_RESULT.value


class TestRequestOperationEnrichment:
    """build_output()'s rejection path enriches the OperationalError JSON with
    `_raw_operation` -- the client-supplied operation string -- so a
    downstream Agent can recognize and short-circuit an already-rejected
    request (see HulubulDataAccessAgentComponent._short_circuit_rejection)
    without ever calling the LLM/MCP tools for it. Additive only:
    validate_request_value's own return contract is untouched.
    """

    def test_operation_not_allowed_carries_raw_operation(
        self, request_boundary: DataOperationRequestBoundaryComponent
    ) -> None:
        raw_value = lf10_create_request()
        raw_value["operation"] = DataOperation.GET_REQUEST_ROUTING_CONTEXT.value
        del raw_value["identifiers"]
        del raw_value["facts"]
        request_boundary.input_value = json.dumps(raw_value)
        result = request_boundary.build_output()
        assert isinstance(result, Message)
        payload = json.loads(str(result.text))
        assert payload["code"] == ErrorCode.OPERATION_NOT_ALLOWED.value
        assert payload["_raw_operation"] == DataOperation.GET_REQUEST_ROUTING_CONTEXT.value

    def test_invalid_contract_carries_raw_operation_when_present(
        self, request_boundary: DataOperationRequestBoundaryComponent
    ) -> None:
        payload_in = malformed_with_raw_query()
        request_boundary.input_value = json.dumps(payload_in)
        result = request_boundary.build_output()
        assert isinstance(result, Message)
        payload = json.loads(str(result.text))
        assert payload["code"] == ErrorCode.INVALID_CONTRACT.value
        assert payload["_raw_operation"] == payload_in.get("operation")


class TestRejectionBypassTrust:
    """A self-contained, non-CONFIRMED DataOperationResult -- built
    deterministically by the Agent's reject-short-circuit path, not claimed by
    an LLM -- is trusted directly when `request_dict` isn't a valid
    DataOperationRequest (expected: it's the original rejection's own
    OperationalError, since the request never reached the Agent to produce a
    fresh one). CONFIRMED outcomes always still require a resolvable original
    request, so they fall through to INVALID_CONTRACT unchanged.
    """

    def test_bypassed_rejection_is_trusted(
        self, result_boundary: DataOperationResultBoundaryComponent
    ) -> None:
        rejection_error = Message(
            text=json.dumps(
                {
                    "schema_version": "1.0.0",
                    "correlation_id": str(FIXED_CORRELATION_ID),
                    "code": "OPERATION_NOT_ALLOWED",
                    "category": "authorization",
                    "message": "This operation is not allowed.",
                    "retryable": False,
                    "violations": [],
                    "_raw_operation": "getRequestRoutingContext",
                }
            )
        )
        bypass_result = {
            "operation": DataOperation.GET_REQUEST_ROUTING_CONTEXT.value,
            "outcome": DataOperationOutcome.REJECTED.value,
            "success": False,
            "write_dispatched": False,
            "error_code": "OPERATION_NOT_ALLOWED",
        }
        result_boundary.raw_value = Message(text=json.dumps(bypass_result))
        result_boundary.request_dict = rejection_error
        result = result_boundary.build_output()

        assert isinstance(result, JSON)
        assert result.data["outcome"] == DataOperationOutcome.REJECTED.value
        assert result.data["error_code"] == "OPERATION_NOT_ALLOWED"

    def test_bypassed_confirmed_outcome_is_not_trusted(
        self, result_boundary: DataOperationResultBoundaryComponent
    ) -> None:
        """A CONFIRMED outcome with no resolvable original request is rejected,
        not trusted -- unlike REJECTED/AMBIGUOUS, a claimed success always needs
        the original request for affected-count/operation-match cross-checks."""
        rejection_error = Message(
            text=json.dumps(
                {
                    "schema_version": "1.0.0",
                    "correlation_id": str(FIXED_CORRELATION_ID),
                    "code": "OPERATION_NOT_ALLOWED",
                    "category": "authorization",
                    "message": "This operation is not allowed.",
                    "retryable": False,
                    "violations": [],
                }
            )
        )
        suspicious_confirmed = {
            "operation": DataOperation.GET_REQUEST_ROUTING_CONTEXT.value,
            "outcome": DataOperationOutcome.CONFIRMED.value,
            "success": True,
            "write_dispatched": False,
        }
        result_boundary.raw_value = Message(text=json.dumps(suspicious_confirmed))
        result_boundary.request_dict = rejection_error
        result = result_boundary.build_output()

        assert isinstance(result, JSON)
        assert result.data["code"] == ErrorCode.INVALID_CONTRACT.value
