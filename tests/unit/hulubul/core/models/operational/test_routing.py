"""Tests for routing lookup validation and adaptation."""

from typing import Any
from uuid import uuid4

import pytest
from pydantic import ValidationError

from hulubul.core.models.operational.base import RequestId, SessionId
from hulubul.core.models.operational.enums import (
    BindingState,
    ErrorCode,
    RequestStatus,
    RouterOutcome,
    RouterTarget,
    RoutingReason,
    RoutingStage,
)
from hulubul.core.models.operational.routing import (
    RouterResult,
    RoutingLookupRecord,
    adapt_routing_lookup,
)


# Test fixtures
def valid_routing_metadata() -> dict[str, Any]:
    """Return valid metadata for adapt_routing_lookup."""
    return {
        "schema_version": "1.0.0",
        "correlation_id": uuid4(),
        "session_id": SessionId("test-session-123"),
    }


def no_binding_record() -> dict[str, Any]:
    """0/0/0 cardinality - no binding."""
    return {
        "binding_count": 0,
        "active_relationship_count": 0,
        "active_target_count": 0,
        "requests": [],
    }


def one_bound_record(
    request_id: str | None = None,
    request_status_raw: str | None = None,
    closed_at: str | None = None,
) -> dict[str, Any]:
    """1/1/1 cardinality - one bound request."""
    if request_id is None:
        request_id = str(uuid4())
    return {
        "binding_count": 1,
        "active_relationship_count": 1,
        "active_target_count": 1,
        "requests": [
            {
                "request_id": request_id,
                "request_status_raw": request_status_raw,
                "updated": "2025-01-23T10:00:00Z",
                "closed": closed_at,
            }
        ],
    }


class TestRoutingLookupRecordValidation:
    """Test RoutingLookupRecord cardinality validation."""

    def test_no_binding_accepts_zero_cardinality(self) -> None:
        """0/0/0 is valid."""
        record = RoutingLookupRecord(**no_binding_record())
        assert record.binding_count == 0
        assert record.active_relationship_count == 0
        assert record.active_target_count == 0

    def test_one_binding_one_relationship_one_target_valid(self) -> None:
        """1/1/1 is valid."""
        record = RoutingLookupRecord(**one_bound_record())
        assert record.binding_count == 1
        assert record.active_relationship_count == 1
        assert record.active_target_count == 1

    def test_duplicate_binding_fails(self) -> None:
        """2/x/x fails with GRAPH_CONTEXT_INCONSISTENT."""
        data = no_binding_record()
        data["binding_count"] = 2
        with pytest.raises(ValidationError) as exc_info:
            RoutingLookupRecord(**data)
        # Validation error should capture the contradiction
        assert "cardinality" in str(exc_info.value).lower()

    def test_mismatched_cardinality_binding_relationship_fails(self) -> None:
        """1/0/1 fails with GRAPH_CONTEXT_INCONSISTENT."""
        data = no_binding_record()
        data["binding_count"] = 1
        data["active_target_count"] = 1
        with pytest.raises(ValidationError):
            RoutingLookupRecord(**data)

    def test_mismatched_cardinality_binding_target_fails(self) -> None:
        """1/1/0 fails with GRAPH_CONTEXT_INCONSISTENT."""
        data = no_binding_record()
        data["binding_count"] = 1
        data["active_relationship_count"] = 1
        with pytest.raises(ValidationError):
            RoutingLookupRecord(**data)

    def test_requests_mismatch_target_count_fails(self) -> None:
        """requests list length != active_target_count fails."""
        data = one_bound_record()
        data["active_target_count"] = 2  # But only 1 request
        with pytest.raises(ValidationError):
            RoutingLookupRecord(**data)


class TestAdaptRoutingLookup:
    """Test adapt_routing_lookup conversion logic."""

    def test_no_binding_returns_absent_state(self) -> None:
        """No binding -> BindingState.ABSENT, no request."""
        metadata = valid_routing_metadata()
        context = adapt_routing_lookup(
            RoutingLookupRecord(**no_binding_record()),
            **metadata,
        )
        assert context.binding_state == BindingState.ABSENT
        assert context.request_id is None
        assert context.request_status is None

    def test_recognized_status_adapts_to_enum_identity(self) -> None:
        """Every RequestStatus value -> same enum identity."""
        metadata = valid_routing_metadata()
        for status in RequestStatus:
            record = RoutingLookupRecord(**one_bound_record(request_status_raw=status.value))
            context = adapt_routing_lookup(record, **metadata)
            assert context.request_status == status

    def test_null_status_on_open_request_becomes_none(self) -> None:
        """requestStatusRaw=None, closed=None -> request_status=None, no error."""
        metadata = valid_routing_metadata()
        record = RoutingLookupRecord(**one_bound_record(request_status_raw=None, closed_at=None))
        context = adapt_routing_lookup(record, **metadata)
        assert context.request_status is None
        assert context.error is None

    def test_unknown_status_on_open_request_fails_closed(self) -> None:
        """Unknown requestStatusRaw, closed=None -> UNSUPPORTED_REQUEST_STATUS error."""
        metadata = valid_routing_metadata()
        record = RoutingLookupRecord(
            **one_bound_record(request_status_raw="unknownStatus", closed_at=None)
        )
        context = adapt_routing_lookup(record, **metadata)
        assert context.error is not None
        assert context.error.code == ErrorCode.UNSUPPORTED_REQUEST_STATUS
        assert context.request_status is None

    def test_closed_timestamp_precedence_over_status(self) -> None:
        """closed!=None -> RoutingStage.CLOSED, regardless of status."""
        metadata = valid_routing_metadata()

        # closed with recognized status
        record = RoutingLookupRecord(
            **one_bound_record(request_status_raw="complete", closed_at="2025-01-23T11:00:00Z")
        )
        context = adapt_routing_lookup(record, **metadata)
        assert context.routing_stage == RoutingStage.CLOSED
        assert context.closed_at is not None

        # closed with unknown status - closed takes precedence
        record = RoutingLookupRecord(
            **one_bound_record(request_status_raw="unknownStatus", closed_at="2025-01-23T11:00:00Z")
        )
        context = adapt_routing_lookup(record, **metadata)
        assert context.routing_stage == RoutingStage.CLOSED

        # closed with null status - closed takes precedence
        record = RoutingLookupRecord(
            **one_bound_record(request_status_raw=None, closed_at="2025-01-23T11:00:00Z")
        )
        context = adapt_routing_lookup(record, **metadata)
        assert context.routing_stage == RoutingStage.CLOSED

    def test_post_intake_status_produces_unsupported_stage(self) -> None:
        """Post-intake statuses (optionsProposed, etc.) -> UNSUPPORTED, no error."""
        metadata = valid_routing_metadata()
        post_intake_statuses = [
            RequestStatus.OPTIONS_PROPOSED,
            RequestStatus.WAITING_RESPONSE,
            RequestStatus.ACCEPTED,
            RequestStatus.REJECTED,
            RequestStatus.PICK_UP_PLANNED,
            RequestStatus.PICKED_UP,
            RequestStatus.DELIVERED,
            RequestStatus.CANCELLED,
        ]
        for status in post_intake_statuses:
            record = RoutingLookupRecord(**one_bound_record(request_status_raw=status.value))
            context = adapt_routing_lookup(record, **metadata)
            assert context.routing_stage == RoutingStage.UNSUPPORTED
            assert context.error is None
            assert context.request_status == status

    def test_new_status_produces_intake_stage(self) -> None:
        """new -> RoutingStage.INTAKE."""
        metadata = valid_routing_metadata()
        record = RoutingLookupRecord(**one_bound_record(request_status_raw="new"))
        context = adapt_routing_lookup(record, **metadata)
        assert context.routing_stage == RoutingStage.INTAKE
        assert context.request_status == RequestStatus.NEW

    def test_needsclarification_produces_intake_stage(self) -> None:
        """needsClarification -> RoutingStage.INTAKE."""
        metadata = valid_routing_metadata()
        record = RoutingLookupRecord(**one_bound_record(request_status_raw="needsClarification"))
        context = adapt_routing_lookup(record, **metadata)
        assert context.routing_stage == RoutingStage.INTAKE

    def test_complete_produces_complete_stage(self) -> None:
        """complete -> RoutingStage.COMPLETE."""
        metadata = valid_routing_metadata()
        record = RoutingLookupRecord(**one_bound_record(request_status_raw="complete"))
        context = adapt_routing_lookup(record, **metadata)
        assert context.routing_stage == RoutingStage.COMPLETE

    def test_unknown_raw_status_text_never_copied_to_error(self) -> None:
        """Unknown raw status -> error has safe message, never contains raw text."""
        metadata = valid_routing_metadata()
        record = RoutingLookupRecord(**one_bound_record(request_status_raw="mysterystatus12345"))
        context = adapt_routing_lookup(record, **metadata)
        assert context.error is not None
        # Ensure raw text never appears in error code or structure
        error_str = repr(context.error)
        assert "mysterystatus12345" not in error_str
        assert context.error.code == ErrorCode.UNSUPPORTED_REQUEST_STATUS


class TestRouterResult:
    """Test RouterResult invariants."""

    def test_routed_result_has_request_id(self) -> None:
        """RouterOutcome.ROUTED requires request_id."""
        result = RouterResult(
            correlation_id=uuid4(),
            outcome=RouterOutcome.ROUTED,
            target=RouterTarget.INTAKE,
            reason=RoutingReason.NO_BINDING,
            request_id=RequestId(str(uuid4())),
            safe_message="Processing your request",
            error=None,
        )
        assert result.request_id is not None

    def test_failure_result_targets_none(self) -> None:
        """RouterOutcome.FAILURE targets RouterTarget.NONE."""
        result = RouterResult(
            correlation_id=uuid4(),
            outcome=RouterOutcome.FAILURE,
            target=RouterTarget.NONE,
            reason=RoutingReason.INVALID_CONTEXT,
            request_id=None,
            safe_message="Could not process",
            error=None,
        )
        assert result.target == RouterTarget.NONE

    def test_informational_result_targets_none(self) -> None:
        """RouterOutcome.INFORMATIONAL targets RouterTarget.NONE."""
        result = RouterResult(
            correlation_id=uuid4(),
            outcome=RouterOutcome.INFORMATIONAL,
            target=RouterTarget.NONE,
            reason=RoutingReason.UNSUPPORTED_STATUS,
            request_id=RequestId(str(uuid4())),
            safe_message="This request cannot be handled",
            error=None,
        )
        assert result.target == RouterTarget.NONE

    def test_frozen_immutable(self) -> None:
        """RouterResult is frozen/immutable."""
        result = RouterResult(
            correlation_id=uuid4(),
            outcome=RouterOutcome.ROUTED,
            target=RouterTarget.INTAKE,
            reason=RoutingReason.NO_BINDING,
            request_id=RequestId(str(uuid4())),
            safe_message="Test",
            error=None,
        )
        with pytest.raises(ValidationError):
            result.outcome = RouterOutcome.FAILURE
