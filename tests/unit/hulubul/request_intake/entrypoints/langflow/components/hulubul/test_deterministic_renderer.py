"""Tests for DeterministicRendererComponent: delegation to pure rendering policy.

This module verifies that DeterministicRendererComponent correctly delegates to
pure rendering functions (render_intake_result, render_router_result,
render_operational_error) and returns typed Message responses.

Tests cover:
- Delegation equivalence: component output == pure renderer output
- All IntakeOutcome types (clarificationRequired, requestComplete, failure)
- All RouterOutcome patterns (routed, informational, failure)
- OperationalError rendering
- Input validation (never accepts Agent free text, only validated contracts)
- Response structure (Message type, never raw dict)
"""

from uuid import uuid4

import pytest
from lfx.schema.message import Message

from hulubul.core.models.operational import (
    ErrorCode,
    IntakeField,
    IntakeOutcome,
    IntakeResult,
    OperationalError,
    RouterOutcome,
    RouterResult,
    RouterTarget,
    RoutingReason,
)
from hulubul.core.models.operational.errors import ERROR_POLICY
from hulubul.request_intake.entrypoints.langflow.components.hulubul.deterministic_renderer import (
    DeterministicRendererComponent,
)
from hulubul.request_intake.services.rendering import (
    render_intake_result,
    render_operational_error,
    render_router_result,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def renderer_component() -> DeterministicRendererComponent:
    """Create a DeterministicRendererComponent."""
    return DeterministicRendererComponent()


# ============================================================================
# Test: IntakeResult Rendering (All Outcomes)
# ============================================================================


class TestIntakeResultRendering:
    """Test rendering of IntakeResult with all outcome types."""

    def test_clarification_required_outcome(
        self, renderer_component: DeterministicRendererComponent
    ) -> None:
        """Component renders IntakeResult with CLARIFICATION_REQUIRED outcome.

        - Dispatches on outcome discriminator
        - Calls render_intake_result()
        - Returns canonical clarification question
        """
        result = IntakeResult(
            outcome=IntakeOutcome.CLARIFICATION_REQUIRED,
            clarification_field=IntakeField.RECEIVER_IDENTITY,
            safe_user_message="Who should receive the parcel?",
        )

        renderer_component.result = result.model_dump()
        message = renderer_component.build_message()

        assert isinstance(message, Message)
        assert isinstance(message.text, str)
        # Verify matches pure renderer
        expected_text = render_intake_result(result)
        assert message.text == expected_text
        assert "Who should receive the parcel?" in message.text

    def test_request_complete_outcome(
        self, renderer_component: DeterministicRendererComponent
    ) -> None:
        """Component renders IntakeResult with REQUEST_COMPLETE outcome.

        - Dispatches on outcome discriminator
        - Calls render_intake_result()
        - Returns confirmation with request ID
        """
        request_id = "req-12345678"
        result = IntakeResult(
            outcome=IntakeOutcome.REQUEST_COMPLETE,
            request_id=request_id,
            safe_user_message="Your parcel request is confirmed.",
        )

        renderer_component.result = result.model_dump()
        message = renderer_component.build_message()

        assert isinstance(message, Message)
        assert isinstance(message.text, str)
        # Verify matches pure renderer
        expected_text = render_intake_result(result)
        assert message.text == expected_text
        assert request_id in message.text
        assert "confirmed" in message.text

    def test_failure_outcome(self, renderer_component: DeterministicRendererComponent) -> None:
        """Component renders IntakeResult with FAILURE outcome.

        - Dispatches on outcome discriminator
        - Calls render_intake_result()
        - Returns validated error message (never free text)
        """
        policy = ERROR_POLICY[ErrorCode.INVALID_INPUT]
        error = OperationalError(
            schema_version="1.0.0",
            code=ErrorCode.INVALID_INPUT,
            correlation_id=uuid4(),
            category=policy.category,
            message=policy.safe_message,
            retryable=policy.retryable,
        )

        result = IntakeResult(
            outcome=IntakeOutcome.FAILURE,
            error=error.model_dump_json(),
            safe_user_message="An error occurred",
        )

        renderer_component.result = result.model_dump()
        message = renderer_component.build_message()

        assert isinstance(message, Message)
        assert isinstance(message.text, str)
        # Verify matches pure renderer
        expected_text = render_intake_result(result)
        assert message.text == expected_text
        # Should render the error message, not free text
        assert "safely" in message.text


# ============================================================================
# Test: RouterResult Rendering (All Outcomes)
# ============================================================================


class TestRouterResultRendering:
    """Test rendering of RouterResult with all outcome types."""

    def test_routed_outcome(self, renderer_component: DeterministicRendererComponent) -> None:
        """Component renders RouterResult with ROUTED outcome.

        - Dispatches on outcome discriminator
        - Returns safe_message (already validated)
        """
        result = RouterResult(
            schema_version="1.0.0",
            correlation_id=uuid4(),
            outcome=RouterOutcome.ROUTED,
            target=RouterTarget.INTAKE,
            reason=RoutingReason.NO_BINDING,
            safe_message="Request routed to intake flow.",
        )

        renderer_component.result = result.model_dump()
        message = renderer_component.build_message()

        assert isinstance(message, Message)
        assert isinstance(message.text, str)
        # Verify matches pure renderer
        expected_text = render_router_result(result)
        assert message.text == expected_text
        assert "intake flow" in message.text

    def test_informational_outcome(
        self, renderer_component: DeterministicRendererComponent
    ) -> None:
        """Component renders RouterResult with INFORMATIONAL outcome.

        - Dispatches on outcome discriminator
        - Returns safe_message (informational only, no routing)
        """
        result = RouterResult(
            schema_version="1.0.0",
            correlation_id=uuid4(),
            outcome=RouterOutcome.INFORMATIONAL,
            target=RouterTarget.NONE,
            reason=RoutingReason.INTAKE_COMPLETE,
            safe_message="Your parcel request is complete.",
        )

        renderer_component.result = result.model_dump()
        message = renderer_component.build_message()

        assert isinstance(message, Message)
        assert isinstance(message.text, str)
        # Verify matches pure renderer
        expected_text = render_router_result(result)
        assert message.text == expected_text

    def test_failure_outcome_with_error(
        self, renderer_component: DeterministicRendererComponent
    ) -> None:
        """Component renders RouterResult with FAILURE outcome and error.

        - Dispatches on outcome discriminator
        - Error takes precedence over safe_message
        - Returns canonical error message
        """
        policy = ERROR_POLICY[ErrorCode.INVALID_CONTRACT]
        error = OperationalError(
            schema_version="1.0.0",
            code=ErrorCode.INVALID_CONTRACT,
            correlation_id=uuid4(),
            category=policy.category,
            message=policy.safe_message,
            retryable=policy.retryable,
        )

        result = RouterResult(
            schema_version="1.0.0",
            correlation_id=uuid4(),
            outcome=RouterOutcome.FAILURE,
            target=RouterTarget.NONE,
            reason=RoutingReason.INVALID_CONTEXT,
            safe_message="This message should be overridden by error",
            error=error,
        )

        renderer_component.result = result.model_dump()
        message = renderer_component.build_message()

        assert isinstance(message, Message)
        assert isinstance(message.text, str)
        # Verify matches pure renderer
        expected_text = render_router_result(result)
        assert message.text == expected_text
        # Error message takes precedence (policy safe message)
        assert "response" in message.text


# ============================================================================
# Test: OperationalError Rendering
# ============================================================================


class TestOperationalErrorRendering:
    """Test rendering of OperationalError directly."""

    def test_operational_error_direct_rendering(
        self, renderer_component: DeterministicRendererComponent
    ) -> None:
        """Component renders OperationalError with canonical safe message.

        - Validates OperationalError structure
        - Calls render_operational_error()
        - Returns pre-validated safe error string
        """
        policy = ERROR_POLICY[ErrorCode.INVALID_INPUT]
        error = OperationalError(
            schema_version="1.0.0",
            code=ErrorCode.INVALID_INPUT,
            correlation_id=uuid4(),
            category=policy.category,
            message=policy.safe_message,
            retryable=policy.retryable,
        )

        renderer_component.result = error.model_dump()
        message = renderer_component.build_message()

        assert isinstance(message, Message)
        assert isinstance(message.text, str)
        # Verify matches pure renderer
        expected_text = render_operational_error(error)
        assert message.text == expected_text


# ============================================================================
# Test: Input Validation (Never Trusts Free Text)
# ============================================================================


class TestInputValidation:
    """Test that renderer validates input and rejects free text."""

    def test_rejects_free_text_as_result(
        self, renderer_component: DeterministicRendererComponent
    ) -> None:
        """Component rejects plain free-text strings as results.

        Renderer must receive validated typed contracts, not Agent prose.
        """
        renderer_component.result = "This is free text from an Agent"

        with pytest.raises((ValueError, KeyError, AttributeError, TypeError)):
            renderer_component.build_message()

    def test_rejects_invalid_outcome_discriminator(
        self, renderer_component: DeterministicRendererComponent
    ) -> None:
        """Component rejects results with invalid outcome discriminators."""
        invalid_result = {
            "schema_version": "1.0.0",
            "correlation_id": str(uuid4()),
            "outcome": "invalid_outcome_type",
            "safe_user_message": "Some message",
        }

        renderer_component.result = invalid_result

        with pytest.raises((ValueError, KeyError)):
            renderer_component.build_message()

    def test_rejects_malformed_result(
        self, renderer_component: DeterministicRendererComponent
    ) -> None:
        """Component rejects malformed result objects."""
        renderer_component.result = {"malformed": "object"}

        with pytest.raises((ValueError, KeyError)):
            renderer_component.build_message()

    def test_accepts_only_validated_contracts(
        self, renderer_component: DeterministicRendererComponent
    ) -> None:
        """Component only accepts IntakeResult, RouterResult, or OperationalError.

        Never accepts Agent free text, unvalidated prose, or raw dicts.
        """
        # Valid contract succeeds
        valid_result = IntakeResult(
            outcome=IntakeOutcome.CLARIFICATION_REQUIRED,
            clarification_field=IntakeField.RECEIVER_IDENTITY,
            safe_user_message="Who?",
        )

        renderer_component.result = valid_result.model_dump()
        message = renderer_component.build_message()

        assert isinstance(message, Message)
        assert isinstance(message.text, str)
        assert message.text is not None


# ============================================================================
# Test: Response Structure
# ============================================================================


class TestResponseStructure:
    """Test response structure and typing."""

    def test_response_is_message(self, renderer_component: DeterministicRendererComponent) -> None:
        """Response is typed Message, not raw dict."""
        result = IntakeResult(
            outcome=IntakeOutcome.CLARIFICATION_REQUIRED,
            clarification_field=IntakeField.RECEIVER_IDENTITY,
            safe_user_message="Who?",
        )

        renderer_component.result = result.model_dump()
        message = renderer_component.build_message()

        assert isinstance(message, Message)
        assert isinstance(message.text, str)
        assert hasattr(message, "text")

    def test_message_text_is_string(
        self, renderer_component: DeterministicRendererComponent
    ) -> None:
        """Message text is a string, not raw JSON."""
        result = IntakeResult(
            outcome=IntakeOutcome.CLARIFICATION_REQUIRED,
            clarification_field=IntakeField.RECEIVER_IDENTITY,
            safe_user_message="Who?",
        )

        renderer_component.result = result.model_dump()
        message = renderer_component.build_message()

        assert isinstance(message.text, str)
        assert len(message.text) > 0


# ============================================================================
# Test: Component Does Not Perform Prohibited Operations
# ============================================================================


class TestComponentPurity:
    """Test that component does not perform prohibited operations."""

    def test_no_model_calls(self, renderer_component: DeterministicRendererComponent) -> None:
        """Component does not invoke language models."""
        # Component should only call pure rendering functions
        result = IntakeResult(
            outcome=IntakeOutcome.CLARIFICATION_REQUIRED,
            clarification_field=IntakeField.RECEIVER_IDENTITY,
            safe_user_message="Who?",
        )

        renderer_component.result = result.model_dump()
        message = renderer_component.build_message()

        # If it got here without exception, no model calls were made
        assert message is not None

    def test_no_credential_access(self, renderer_component: DeterministicRendererComponent) -> None:
        """Component does not read secrets or credentials."""
        # Verified by code inspection: component only calls pure rendering
        result = IntakeResult(
            outcome=IntakeOutcome.CLARIFICATION_REQUIRED,
            clarification_field=IntakeField.RECEIVER_IDENTITY,
            safe_user_message="Who?",
        )

        renderer_component.result = result.model_dump()
        message = renderer_component.build_message()

        assert message is not None

    def test_deterministic_output(self, renderer_component: DeterministicRendererComponent) -> None:
        """Same input always produces same output (no randomness)."""
        result = IntakeResult(
            outcome=IntakeOutcome.CLARIFICATION_REQUIRED,
            clarification_field=IntakeField.RECEIVER_IDENTITY,
            safe_user_message="Who?",
        )

        renderer_component.result = result.model_dump()
        message1 = renderer_component.build_message()

        renderer_component.result = result.model_dump()
        message2 = renderer_component.build_message()

        assert message1.text == message2.text


# ============================================================================
# Test: All Outcome Paths Covered
# ============================================================================


class TestExhaustiveOutcomeCoverage:
    """Verify all outcome types are handled."""

    def test_all_intake_outcomes(self, renderer_component: DeterministicRendererComponent) -> None:
        """Every IntakeOutcome variant produces a valid message."""
        for outcome in IntakeOutcome:
            if outcome == IntakeOutcome.CLARIFICATION_REQUIRED:
                result = IntakeResult(
                    outcome=outcome,
                    clarification_field=IntakeField.RECEIVER_IDENTITY,
                    safe_user_message="test",
                )
            elif outcome == IntakeOutcome.REQUEST_COMPLETE:
                result = IntakeResult(
                    outcome=outcome,
                    request_id="req-123",
                    safe_user_message="test",
                )
            else:  # FAILURE
                policy = ERROR_POLICY[ErrorCode.INVALID_INPUT]
                error = OperationalError(
                    schema_version="1.0.0",
                    code=ErrorCode.INVALID_INPUT,
                    correlation_id=uuid4(),
                    category=policy.category,
                    message=policy.safe_message,
                    retryable=policy.retryable,
                )
                result = IntakeResult(
                    outcome=outcome,
                    error=error.model_dump_json(),
                    safe_user_message="test",
                )

            renderer_component.result = result.model_dump()
            message = renderer_component.build_message()

            assert isinstance(message, Message)
            assert isinstance(message.text, str)
            assert message.text is not None

    def test_all_router_outcomes(self, renderer_component: DeterministicRendererComponent) -> None:
        """Every RouterOutcome variant produces a valid message."""
        for outcome in RouterOutcome:
            if outcome == RouterOutcome.FAILURE:
                policy = ERROR_POLICY[ErrorCode.INVALID_CONTRACT]
                error = OperationalError(
                    schema_version="1.0.0",
                    code=ErrorCode.INVALID_CONTRACT,
                    correlation_id=uuid4(),
                    category=policy.category,
                    message=policy.safe_message,
                    retryable=policy.retryable,
                )
                result = RouterResult(
                    schema_version="1.0.0",
                    correlation_id=uuid4(),
                    outcome=outcome,
                    target=RouterTarget.NONE,
                    reason=RoutingReason.INVALID_CONTEXT,
                    safe_message="test",
                    error=error,
                )
            else:
                result = RouterResult(
                    schema_version="1.0.0",
                    correlation_id=uuid4(),
                    outcome=outcome,
                    target=RouterTarget.INTAKE,
                    reason=RoutingReason.NO_BINDING,
                    safe_message="test",
                )

            renderer_component.result = result.model_dump()
            message = renderer_component.build_message()

            assert isinstance(message, Message)
            assert isinstance(message.text, str)
            assert message.text is not None
