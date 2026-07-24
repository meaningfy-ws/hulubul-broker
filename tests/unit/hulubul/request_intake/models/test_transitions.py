"""Unit tests for deterministic request status transitions.

Tests the fixed four-edge state machine (None->NEW, NEW->NEEDS_CLARIFICATION,
NEW->COMPLETE, NEEDS_CLARIFICATION->COMPLETE) and compare-and-set preconditions
(actual status/timestamp must match expected values before transition is allowed).
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from hulubul.core.models.operational.enums import ErrorCode, RequestStatus
from hulubul.request_intake.models.transitions import (
    ALLOWED_TRANSITIONS,
    TransitionDecision,
    evaluate_transition,
)

# Fixture: a fixed timestamp for CAS checks.
FIXED_TIMESTAMP = datetime(2026, 7, 23, 12, 0, 0, tzinfo=timezone.utc)
DIFFERENT_TIMESTAMP = datetime(2026, 7, 23, 13, 0, 0, tzinfo=timezone.utc)


# ============================================================================
# ALLOWED_TRANSITIONS
# ============================================================================


class TestAllowedTransitions:
    """The transition table is fixed, finite, and locked."""

    def test_allowed_transitions_exactly_four_edges(self) -> None:
        """ALLOWED_TRANSITIONS must contain exactly four allowed edges."""
        all_transitions = set()
        for source_status, targets in ALLOWED_TRANSITIONS.items():
            for target in targets:
                all_transitions.add((source_status, target))

        expected_edges = {
            (None, RequestStatus.NEW),
            (RequestStatus.NEW, RequestStatus.NEEDS_CLARIFICATION),
            (RequestStatus.NEW, RequestStatus.COMPLETE),
            (RequestStatus.NEEDS_CLARIFICATION, RequestStatus.COMPLETE),
        }

        assert all_transitions == expected_edges

    def test_allowed_transitions_is_immutable_frozenset(self) -> None:
        """Each ALLOWED_TRANSITIONS value must be a frozenset (immutable)."""
        for _, targets in ALLOWED_TRANSITIONS.items():
            assert isinstance(targets, frozenset)


# ============================================================================
# TransitionDecision
# ============================================================================


class TestTransitionDecision:
    """TransitionDecision must be immutable and enforce allowed/error_code contract."""

    def test_allowed_decision_has_no_error_code(self) -> None:
        """An allowed transition must have error_code=None."""
        decision = TransitionDecision(allowed=True, error_code=None)
        assert decision.allowed is True
        assert decision.error_code is None

    def test_rejected_decision_has_error_code(self) -> None:
        """A rejected transition must have a non-None error_code."""
        decision = TransitionDecision(allowed=False, error_code=ErrorCode.INVALID_STATUS_TRANSITION)
        assert decision.allowed is False
        assert decision.error_code is ErrorCode.INVALID_STATUS_TRANSITION

    def test_transition_decision_is_immutable(self) -> None:
        """TransitionDecision must be frozen (immutable)."""
        decision = TransitionDecision(allowed=True, error_code=None)
        with pytest.raises(AttributeError):
            decision.allowed = False  # type: ignore


# ============================================================================
# evaluate_transition - Positive Cases (Allowed Edges)
# ============================================================================


class TestEvaluateTransitionPositive:
    """Allowed edges must pass CAS checks and evaluate as allowed."""

    @pytest.mark.parametrize(
        "source_status,target_status",
        [
            (None, RequestStatus.NEW),
            (RequestStatus.NEW, RequestStatus.NEEDS_CLARIFICATION),
            (RequestStatus.NEW, RequestStatus.COMPLETE),
            (RequestStatus.NEEDS_CLARIFICATION, RequestStatus.COMPLETE),
        ],
    )
    def test_allowed_edges_when_cas_matches(
        self, source_status: RequestStatus | None, target_status: RequestStatus
    ) -> None:
        """Each of the four allowed edges must be allowed when CAS checks pass."""
        decision = evaluate_transition(
            actual_status=source_status,
            actual_updated_at=FIXED_TIMESTAMP,
            expected_status=source_status,
            expected_updated_at=FIXED_TIMESTAMP,
            target_status=target_status,
        )
        assert decision.allowed is True
        assert decision.error_code is None


# ============================================================================
# evaluate_transition - Precondition Failures (CAS Checks)
# ============================================================================


class TestEvaluateTransitionPreconditionFailures:
    """CAS preconditions must be checked before edge validation."""

    def test_stale_status_rejected_with_invalid_expected_status(self) -> None:
        """If actual_status != expected_status, return INVALID_EXPECTED_STATUS."""
        decision = evaluate_transition(
            actual_status=RequestStatus.NEW,
            actual_updated_at=FIXED_TIMESTAMP,
            expected_status=RequestStatus.NEEDS_CLARIFICATION,  # Stale expectation
            expected_updated_at=FIXED_TIMESTAMP,
            target_status=RequestStatus.COMPLETE,
        )
        assert decision.allowed is False
        assert decision.error_code is ErrorCode.INVALID_EXPECTED_STATUS

    def test_stale_timestamp_rejected_with_concurrent_modification(self) -> None:
        """If actual_updated_at != expected_updated_at, return CONCURRENT_MODIFICATION."""
        decision = evaluate_transition(
            actual_status=RequestStatus.NEW,
            actual_updated_at=DIFFERENT_TIMESTAMP,  # Different timestamp
            expected_status=RequestStatus.NEW,
            expected_updated_at=FIXED_TIMESTAMP,  # Expected a different one
            target_status=RequestStatus.COMPLETE,
        )
        assert decision.allowed is False
        assert decision.error_code is ErrorCode.CONCURRENT_MODIFICATION

    def test_invalid_status_takes_priority_over_timestamp(self) -> None:
        """Invalid status is checked before timestamp."""
        decision = evaluate_transition(
            actual_status=RequestStatus.COMPLETE,  # Wrong status
            actual_updated_at=DIFFERENT_TIMESTAMP,  # Also wrong timestamp
            expected_status=RequestStatus.NEW,
            expected_updated_at=FIXED_TIMESTAMP,
            target_status=RequestStatus.NEEDS_CLARIFICATION,
        )
        # Should return INVALID_EXPECTED_STATUS (status checked first)
        assert decision.allowed is False
        assert decision.error_code is ErrorCode.INVALID_EXPECTED_STATUS


# ============================================================================
# evaluate_transition - Edge Validation
# ============================================================================


class TestEvaluateTransitionEdgeValidation:
    """After CAS passes, edge must be in ALLOWED_TRANSITIONS."""

    def test_disallowed_edge_rejected_with_invalid_status_transition(self) -> None:
        """If edge is not in ALLOWED_TRANSITIONS, return INVALID_STATUS_TRANSITION."""
        decision = evaluate_transition(
            actual_status=RequestStatus.NEEDS_CLARIFICATION,
            actual_updated_at=FIXED_TIMESTAMP,
            expected_status=RequestStatus.NEEDS_CLARIFICATION,
            expected_updated_at=FIXED_TIMESTAMP,
            target_status=RequestStatus.WAITING_RESPONSE,  # Not an allowed edge
        )
        assert decision.allowed is False
        assert decision.error_code is ErrorCode.INVALID_STATUS_TRANSITION

    def test_backward_transition_rejected(self) -> None:
        """Transitioning backward (COMPLETE -> NEW) is not allowed."""
        decision = evaluate_transition(
            actual_status=RequestStatus.COMPLETE,
            actual_updated_at=FIXED_TIMESTAMP,
            expected_status=RequestStatus.COMPLETE,
            expected_updated_at=FIXED_TIMESTAMP,
            target_status=RequestStatus.NEW,
        )
        assert decision.allowed is False
        assert decision.error_code is ErrorCode.INVALID_STATUS_TRANSITION

    def test_skip_step_allowed(self) -> None:
        """Skipping a step (NEW -> COMPLETE via NEEDS_CLARIFICATION) is allowed."""
        decision = evaluate_transition(
            actual_status=RequestStatus.NEW,
            actual_updated_at=FIXED_TIMESTAMP,
            expected_status=RequestStatus.NEW,
            expected_updated_at=FIXED_TIMESTAMP,
            target_status=RequestStatus.COMPLETE,
        )
        assert decision.allowed is True

    def test_post_intake_status_transition_not_allowed(self) -> None:
        """Transitioning from intake to post-intake status is not allowed."""
        decision = evaluate_transition(
            actual_status=RequestStatus.COMPLETE,
            actual_updated_at=FIXED_TIMESTAMP,
            expected_status=RequestStatus.COMPLETE,
            expected_updated_at=FIXED_TIMESTAMP,
            target_status=RequestStatus.OPTIONS_PROPOSED,
        )
        assert decision.allowed is False
        assert decision.error_code is ErrorCode.INVALID_STATUS_TRANSITION


# ============================================================================
# evaluate_transition - Creation Edge (None -> NEW)
# ============================================================================


class TestEvaluateTransitionCreation:
    """Creation uses None as the source status (atomic)."""

    def test_creation_none_to_new_when_cas_matches(self) -> None:
        """Creation (None -> NEW) is allowed when CAS checks pass."""
        decision = evaluate_transition(
            actual_status=None,
            actual_updated_at=None,  # No timestamp for non-existent request
            expected_status=None,
            expected_updated_at=None,
            target_status=RequestStatus.NEW,
        )
        assert decision.allowed is True
        assert decision.error_code is None

    def test_creation_rejected_if_cas_fails(self) -> None:
        """Creation fails if CAS doesn't match (request already exists)."""
        decision = evaluate_transition(
            actual_status=RequestStatus.NEW,  # Request already exists
            actual_updated_at=FIXED_TIMESTAMP,
            expected_status=None,  # Expected non-existent
            expected_updated_at=None,
            target_status=RequestStatus.NEW,
        )
        assert decision.allowed is False
        assert decision.error_code is ErrorCode.INVALID_EXPECTED_STATUS
