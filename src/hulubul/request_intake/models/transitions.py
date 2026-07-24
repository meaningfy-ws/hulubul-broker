"""Deterministic request status transitions and compare-and-set policy.

Task 11 defines exactly four allowed state-machine edges (None->NEW,
NEW->NEEDS_CLARIFICATION, NEW->COMPLETE, NEEDS_CLARIFICATION->COMPLETE).
The evaluate_transition function enforces compare-and-set preconditions
(actual status/timestamp must match expected) before checking edge validity.

Pure domain logic: no I/O, no framework dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from hulubul.core.models.operational.enums import ErrorCode, RequestStatus

__all__ = [
    "ALLOWED_TRANSITIONS",
    "TransitionDecision",
    "evaluate_transition",
]


ALLOWED_TRANSITIONS: dict[RequestStatus | None, frozenset[RequestStatus]] = {
    None: frozenset([RequestStatus.NEW]),
    RequestStatus.NEW: frozenset(
        [
            RequestStatus.NEEDS_CLARIFICATION,
            RequestStatus.COMPLETE,
        ]
    ),
    RequestStatus.NEEDS_CLARIFICATION: frozenset(
        [
            RequestStatus.COMPLETE,
        ]
    ),
}
"""Fixed state-machine table: exactly four allowed edges."""


@dataclass(frozen=True)
class TransitionDecision:
    """Immutable decision on whether a state transition is allowed.

    - allowed=True means transition is authorized; error_code must be None.
    - allowed=False means transition is rejected; error_code identifies why.
    """

    allowed: bool
    error_code: ErrorCode | None = None


def evaluate_transition(
    *,
    actual_status: RequestStatus | None,
    actual_updated_at: datetime | None,
    expected_status: RequestStatus | None,
    expected_updated_at: datetime | None,
    target_status: RequestStatus,
) -> TransitionDecision:
    """Evaluate whether a status transition is allowed via compare-and-set.

    Preconditions (checked first):
    1. actual_status must equal expected_status (snapshot consistency check)
    2. actual_updated_at must equal expected_updated_at (no concurrent modification)

    If preconditions pass, check whether the edge (actual_status → target_status)
    is in the fixed ALLOWED_TRANSITIONS table.

    Args:
        actual_status: Current status (or None for non-existent request)
        actual_updated_at: Current timestamp (or None for non-existent request)
        expected_status: Caller's expected status (snapshot)
        expected_updated_at: Caller's expected timestamp (snapshot)
        target_status: Desired target status

    Returns:
        TransitionDecision with allowed=True (no error) or
        allowed=False with one of:
        - INVALID_EXPECTED_STATUS: actual_status != expected_status
        - CONCURRENT_MODIFICATION: actual_updated_at != expected_updated_at
        - INVALID_STATUS_TRANSITION: edge not in ALLOWED_TRANSITIONS
    """
    # Precondition 1: status must match expectation (CAS check).
    if actual_status != expected_status:
        return TransitionDecision(False, ErrorCode.INVALID_EXPECTED_STATUS)

    # Precondition 2: timestamp must match expectation (CAS check).
    if actual_updated_at != expected_updated_at:
        return TransitionDecision(False, ErrorCode.CONCURRENT_MODIFICATION)

    # Edge validation: check if transition is allowed.
    if actual_status not in ALLOWED_TRANSITIONS:
        return TransitionDecision(False, ErrorCode.INVALID_STATUS_TRANSITION)

    if target_status not in ALLOWED_TRANSITIONS[actual_status]:
        return TransitionDecision(False, ErrorCode.INVALID_STATUS_TRANSITION)

    # All checks passed.
    return TransitionDecision(True, None)
