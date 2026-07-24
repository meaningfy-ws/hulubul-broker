"""Unit tests for deterministic, safe result rendering.

Per plan Task 15 (original task ID 3.6): rendering converts validated
structured contracts (RouterResult, IntakeResult, OperationalError) into
safe, deterministic user-facing text. No model calls, no timestamps, no
randomness, and no leakage of raw MCP output, prompts, or credentials.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from hulubul.core.models.operational.base import RequestId
from hulubul.core.models.operational.enums import (
    ErrorCode,
    IntakeField,
    IntakeOutcome,
    RequestStatus,
    RouterOutcome,
    RouterTarget,
    RoutingReason,
)
from hulubul.core.models.operational.errors import ERROR_POLICY, OperationalError
from hulubul.core.models.operational.intake import IntakeFacts, IntakeResult
from hulubul.core.models.operational.routing import RouterResult
from hulubul.request_intake.services.rendering import (
    CLARIFICATION_QUESTIONS,
    STATUS_UPDATE_MESSAGES,
    render_clarification_message,
    render_complete_message,
    render_intake_result,
    render_operational_error,
    render_router_result,
    render_status_update,
)


def make_error(code: ErrorCode) -> OperationalError:
    """Build a valid OperationalError enforcing the centralized policy."""
    policy = ERROR_POLICY[code]
    return OperationalError(
        correlation_id=uuid4(),
        code=code,
        category=policy.category,
        message=policy.safe_message,
        retryable=policy.retryable,
    )


# ============================================================================
# CLARIFICATION_QUESTIONS
# ============================================================================


class TestClarificationQuestions:
    """The canonical clarification map is fixed, exhaustive, and immutable."""

    def test_covers_every_intake_field(self) -> None:
        assert set(CLARIFICATION_QUESTIONS.keys()) == set(IntakeField)

    def test_exact_canonical_wording(self) -> None:
        assert CLARIFICATION_QUESTIONS == {
            IntakeField.RECEIVER_IDENTITY: "Who should receive the parcel?",
            IntakeField.PICKUP_LOCATION: "Where should the parcel be picked up?",
            IntakeField.DROP_OFF_LOCATION: "Where should the parcel be delivered?",
            IntakeField.PARCEL_DECLARED_CONTENT: "What does the parcel contain?",
            IntakeField.PREFERRED_PERIOD: "What preferred delivery period should I record?",
        }

    def test_immutable_mapping(self) -> None:
        with pytest.raises(TypeError):
            CLARIFICATION_QUESTIONS[IntakeField.PICKUP_LOCATION] = "changed"  # type: ignore[index]


# ============================================================================
# render_clarification_message
# ============================================================================


class TestRenderClarificationMessage:
    """Exactly one canonical question is rendered per field, deterministically."""

    @pytest.mark.parametrize("field", list(IntakeField))
    def test_renders_exactly_one_question_per_field(self, field: IntakeField) -> None:
        text = render_clarification_message(field)
        assert text == CLARIFICATION_QUESTIONS[field]
        assert text.count("?") == 1

    def test_receiver_identity_exact_wording(self) -> None:
        assert render_clarification_message(IntakeField.RECEIVER_IDENTITY) == (
            "Who should receive the parcel?"
        )

    def test_deterministic_across_calls(self) -> None:
        first = render_clarification_message(IntakeField.DROP_OFF_LOCATION)
        second = render_clarification_message(IntakeField.DROP_OFF_LOCATION)
        assert first == second


# ============================================================================
# render_complete_message
# ============================================================================


class TestRenderCompleteMessage:
    """The completion message always includes the confirmed request ID."""

    def test_includes_request_id(self) -> None:
        text = render_complete_message("req-123")
        assert "req-123" in text

    def test_deterministic_across_calls(self) -> None:
        assert render_complete_message("req-abc") == render_complete_message("req-abc")

    def test_different_request_ids_render_different_text(self) -> None:
        assert render_complete_message("req-1") != render_complete_message("req-2")

    def test_never_mentions_a_missing_field(self) -> None:
        text = render_complete_message("req-123")
        for field in IntakeField:
            assert field.value not in text


# ============================================================================
# render_operational_error
# ============================================================================


class TestRenderOperationalError:
    """Error rendering always returns the centralized policy's safe message."""

    @pytest.mark.parametrize("code", list(ErrorCode))
    def test_matches_canonical_policy_message(self, code: ErrorCode) -> None:
        error = make_error(code)
        assert render_operational_error(error) == ERROR_POLICY[code].safe_message

    def test_never_leaks_raw_internal_text(self) -> None:
        error = make_error(ErrorCode.MCP_OPERATION_FAILURE)
        text = render_operational_error(error)
        assert "mcp" not in text.lower()
        assert "cypher" not in text.lower()


# ============================================================================
# render_intake_result
# ============================================================================


def clarification_result(field: IntakeField) -> IntakeResult:
    return IntakeResult(
        outcome=IntakeOutcome.CLARIFICATION_REQUIRED,
        request_id="req-123",
        status="needsClarification",
        facts=IntakeFacts(sender_actor_id="urn:actor:alice"),
        missing_fields=(field.value,),
        clarification_field=field.value,
    )


class TestRenderIntakeResult:
    """Rendering is keyed only by the validated outcome discriminator."""

    def test_clarification_renders_exactly_selected_question(self) -> None:
        result = clarification_result(IntakeField.RECEIVER_IDENTITY)
        text = render_intake_result(result)
        assert text == "Who should receive the parcel?"
        assert text.count("?") == 1

    @pytest.mark.parametrize("field", list(IntakeField))
    def test_clarification_matches_canonical_map_for_every_field(self, field: IntakeField) -> None:
        result = clarification_result(field)
        assert render_intake_result(result) == CLARIFICATION_QUESTIONS[field]

    def test_complete_includes_confirmed_request_id(self) -> None:
        result = IntakeResult(
            outcome=IntakeOutcome.REQUEST_COMPLETE,
            request_id="req-999",
            status="complete",
            facts=IntakeFacts(sender_actor_id="urn:actor:alice"),
        )
        text = render_intake_result(result)
        assert text == render_complete_message("req-999")
        assert "req-999" in text

    def test_failure_delegates_to_pre_validated_safe_error(self) -> None:
        result = IntakeResult(
            outcome=IntakeOutcome.FAILURE,
            error="I could not produce a safe response.",
        )
        assert render_intake_result(result) == "I could not produce a safe response."

    def test_deterministic_across_calls(self) -> None:
        result = clarification_result(IntakeField.PICKUP_LOCATION)
        assert render_intake_result(result) == render_intake_result(result)


# ============================================================================
# render_router_result
# ============================================================================


class TestRenderRouterResult:
    """A present error always wins; otherwise the validated safe message is used."""

    def test_error_present_delegates_to_canonical_safe_error(self) -> None:
        error = make_error(ErrorCode.UNSUPPORTED_REQUEST_STATUS)
        result = RouterResult(
            correlation_id=uuid4(),
            outcome=RouterOutcome.FAILURE,
            target=RouterTarget.NONE,
            reason=RoutingReason.LOOKUP_FAILED,
            request_id=None,
            safe_message="a caller-supplied message that must be ignored",
            error=error,
        )
        expected = ERROR_POLICY[ErrorCode.UNSUPPORTED_REQUEST_STATUS].safe_message
        assert render_router_result(result) == expected

    def test_no_error_returns_validated_safe_message(self) -> None:
        result = RouterResult(
            correlation_id=uuid4(),
            outcome=RouterOutcome.ROUTED,
            target=RouterTarget.INTAKE,
            reason=RoutingReason.NO_BINDING,
            request_id=RequestId(str(uuid4())),
            safe_message="Let's get your parcel request started.",
            error=None,
        )
        assert render_router_result(result) == "Let's get your parcel request started."

    def test_informational_outcome_returns_validated_safe_message(self) -> None:
        result = RouterResult(
            correlation_id=uuid4(),
            outcome=RouterOutcome.INFORMATIONAL,
            target=RouterTarget.NONE,
            reason=RoutingReason.INTAKE_COMPLETE,
            request_id=RequestId(str(uuid4())),
            safe_message="This request is already complete.",
            error=None,
        )
        assert render_router_result(result) == "This request is already complete."

    def test_deterministic_across_calls(self) -> None:
        result = RouterResult(
            correlation_id=uuid4(),
            outcome=RouterOutcome.ROUTED,
            target=RouterTarget.INTAKE,
            reason=RoutingReason.NO_BINDING,
            request_id=RequestId(str(uuid4())),
            safe_message="Test",
            error=None,
        )
        assert render_router_result(result) == render_router_result(result)


# ============================================================================
# render_status_update
# ============================================================================


class TestRenderStatusUpdate:
    """A canonical, friendly status message is rendered for every lifecycle status."""

    def test_covers_every_request_status(self) -> None:
        assert set(STATUS_UPDATE_MESSAGES.keys()) == set(RequestStatus)

    @pytest.mark.parametrize("status", list(RequestStatus))
    def test_renders_the_canonical_message_for_every_status(self, status: RequestStatus) -> None:
        assert render_status_update(status) == STATUS_UPDATE_MESSAGES[status]

    def test_new_status_exact_wording(self) -> None:
        assert render_status_update(RequestStatus.NEW) == ("Your parcel request has been started.")

    def test_needs_clarification_status_exact_wording(self) -> None:
        assert render_status_update(RequestStatus.NEEDS_CLARIFICATION) == (
            "We need a bit more information to continue your parcel request."
        )

    def test_complete_status_exact_wording(self) -> None:
        assert render_status_update(RequestStatus.COMPLETE) == ("Your parcel request is complete.")

    def test_deterministic_across_calls(self) -> None:
        assert render_status_update(RequestStatus.DELIVERED) == render_status_update(
            RequestStatus.DELIVERED
        )

    def test_immutable_mapping(self) -> None:
        with pytest.raises(TypeError):
            STATUS_UPDATE_MESSAGES[RequestStatus.NEW] = "changed"  # type: ignore[index]

    def test_every_message_is_human_prose_ending_in_a_period(self) -> None:
        for text in STATUS_UPDATE_MESSAGES.values():
            assert text.endswith(".")
            assert text[0].isupper()
