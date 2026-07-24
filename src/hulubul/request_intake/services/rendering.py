"""Deterministic, safe result rendering for request-intake outcomes.

Per plan Task 15 (original task ID 3.6), rendering converts validated
structured contracts (``RouterResult``, ``IntakeResult``,
``OperationalError``) into safe, deterministic user-facing text. Every
function here is pure: no model calls, no I/O, no timestamps, no randomness,
and no dynamic content beyond the validated structured input. Rendering
never inspects raw MCP output, prompts, or credentials, and it never trusts
a caller-supplied free-text field over a canonical, enum-keyed message.

Per DEC-014 (design.md), this is the single rendering authority: results are
converted to text exactly once, from validated typed fields, so structured
and chat output can never diverge.
"""

from __future__ import annotations

from types import MappingProxyType

from hulubul.core.models.operational.enums import (
    IntakeField,
    IntakeOutcome,
    RequestStatus,
)
from hulubul.core.models.operational.errors import OperationalError
from hulubul.core.models.operational.intake import IntakeResult
from hulubul.core.models.operational.routing import RouterResult

__all__ = [
    "CLARIFICATION_QUESTIONS",
    "STATUS_UPDATE_MESSAGES",
    "render_clarification_message",
    "render_complete_message",
    "render_intake_result",
    "render_operational_error",
    "render_router_result",
    "render_status_update",
]

CLARIFICATION_QUESTIONS: MappingProxyType[IntakeField, str] = MappingProxyType(
    {
        IntakeField.RECEIVER_IDENTITY: "Who should receive the parcel?",
        IntakeField.PICKUP_LOCATION: "Where should the parcel be picked up?",
        IntakeField.DROP_OFF_LOCATION: "Where should the parcel be delivered?",
        IntakeField.PARCEL_DECLARED_CONTENT: "What does the parcel contain?",
        IntakeField.PREFERRED_PERIOD: "What preferred delivery period should I record?",
    }
)
"""Canonical, exhaustive clarification question for every intake field.

Exactly one field is ever rendered per interaction (see
``request_intake.models.completeness.select_clarification_field``); this map
is the single source of truth for that field's question text.
"""


STATUS_UPDATE_MESSAGES: MappingProxyType[RequestStatus, str] = MappingProxyType(
    {
        RequestStatus.NEW: "Your parcel request has been started.",
        RequestStatus.NEEDS_CLARIFICATION: (
            "We need a bit more information to continue your parcel request."
        ),
        RequestStatus.COMPLETE: "Your parcel request is complete.",
        RequestStatus.OPTIONS_PROPOSED: (
            "Delivery options have been proposed for your parcel request."
        ),
        RequestStatus.WAITING_RESPONSE: (
            "We're waiting for your response on the delivery options."
        ),
        RequestStatus.ACCEPTED: "Your delivery option has been accepted.",
        RequestStatus.REJECTED: "Your parcel request was rejected.",
        RequestStatus.PICK_UP_PLANNED: "Pickup has been planned for your parcel.",
        RequestStatus.PICKED_UP: "Your parcel has been picked up.",
        RequestStatus.DELIVERED: "Your parcel has been delivered.",
        RequestStatus.CANCELLED: "Your parcel request has been cancelled.",
    }
)
"""Canonical, exhaustive friendly message for every request lifecycle status."""


def render_clarification_message(missing_field: IntakeField) -> str:
    """Render the one canonical question asking for a single intake field."""
    return CLARIFICATION_QUESTIONS[missing_field]


def render_complete_message(request_id: str) -> str:
    """Render the confirmation message for a request that reached ``complete``."""
    return f"Your parcel request is confirmed. Reference: {request_id}."


def render_status_update(status: RequestStatus) -> str:
    """Render the canonical friendly message for a request lifecycle status."""
    return STATUS_UPDATE_MESSAGES[status]


def render_operational_error(error: OperationalError) -> str:
    """Render the canonical safe message for a controlled operational error.

    ``OperationalError.message`` is itself enforced (by field validator) to
    equal the centralized ``ERROR_POLICY`` entry for ``error.code``, so this
    is the single, policy-backed safe string; no free text is ever accepted.
    """
    return error.message


def render_intake_result(result: IntakeResult) -> str:
    """Render the deterministic safe message for an intake result.

    Dispatches only on the validated ``outcome`` discriminator: a
    clarification request renders its one canonical question, a completed
    request renders the confirmation with its request ID, and a failure
    renders the pre-validated safe error string already carried by the
    result. ``safe_user_message`` is never trusted as free text.
    """
    if result.outcome is IntakeOutcome.CLARIFICATION_REQUIRED:
        if result.clarification_field is None:
            raise ValueError("clarificationRequired outcome must include clarification_field")
        return render_clarification_message(IntakeField(result.clarification_field))
    if result.outcome is IntakeOutcome.REQUEST_COMPLETE:
        if result.request_id is None:
            raise ValueError("requestComplete outcome must include request_id")
        return render_complete_message(result.request_id)
    if result.error is None:
        raise ValueError("failure outcome must include error")
    return result.error


def render_router_result(result: RouterResult) -> str:
    """Render the deterministic safe message for a router decision.

    A present error always wins and is rendered from the canonical error
    policy, overriding any caller-supplied ``safe_message``. Otherwise the
    already-validated ``safe_message`` carried by the result (routed or
    informational) is returned unchanged.
    """
    if result.error is not None:
        return render_operational_error(result.error)
    return result.safe_message
