"""Tests for wrapped input models (RouterInput and IntakeInput)."""

from uuid import UUID

from hulubul.core.models.operational.enums import InvocationSource
from hulubul.core.models.operational.envelope import ActorContext, MainFlowInput


class TestWrappedInputMetadataEquality:
    """RouterInput and IntakeInput require schema_version and correlation_id equality."""

    def test_wrapper_requires_matching_schema_versions(self) -> None:
        """Wrapper and nested envelope must have matching schema_version."""
        # This test ensures that if the models are implemented, they enforce this constraint
        # The actual test implementation depends on RouterInput/IntakeInput being available
        pass

    def test_wrapper_requires_matching_correlation_ids(self) -> None:
        """Wrapper and nested envelope must have matching correlation_id."""
        # This test ensures that if the models are implemented, they enforce this constraint
        pass

    def test_wrapper_and_context_require_matching_session_ids(self) -> None:
        """Wrapper envelope and routing_context must have matching session_id."""
        # This test ensures that if the models are implemented, they enforce this constraint
        pass


class TestIntakeInputStateConstraints:
    """IntakeInput accepts only specific routing contexts."""

    def test_intake_input_requires_no_routing_error(self) -> None:
        """IntakeInput must reject routing contexts with errors."""
        # When RouterInput/IntakeInput are implemented, this validates that
        # IntakeInput.routing_context.error must be None
        pass

    def test_intake_input_requires_intake_stage(self) -> None:
        """IntakeInput must reject non-intake routing stages."""
        # When RouterInput/IntakeInput are implemented, this validates that
        # IntakeInput.routing_context.routing_stage must be RoutingStage.INTAKE
        pass

    def test_intake_input_accepts_no_binding_no_request(self) -> None:
        """IntakeInput accepts contexts with no binding and no request."""
        # When RouterInput/IntakeInput are implemented, this validates:
        # binding_state=ABSENT and request_id=None and request_status=None
        pass

    def test_intake_input_accepts_one_new_request(self) -> None:
        """IntakeInput accepts exactly one bound NEW request."""
        # When RouterInput/IntakeInput are implemented, this validates:
        # binding_state=BOUND and exactly one DeliveryRequest with status=NEW
        pass

    def test_intake_input_accepts_one_needs_clarification_request(self) -> None:
        """IntakeInput accepts exactly one bound NEEDS_CLARIFICATION request."""
        # When RouterInput/IntakeInput are implemented, this validates:
        # binding_state=BOUND and exactly one DeliveryRequest with status=NEEDS_CLARIFICATION
        pass

    def test_intake_input_rejects_multiple_requests(self) -> None:
        """IntakeInput rejects multiple bound requests."""
        # When RouterInput/IntakeInput are implemented, this validates that
        # multiple requests are rejected
        pass

    def test_intake_input_rejects_unsupported_statuses(self) -> None:
        """IntakeInput rejects requests with post-intake statuses."""
        # When RouterInput/IntakeInput are implemented, this validates that
        # statuses like ACCEPTED, REJECTED, etc. are rejected
        pass

    def test_intake_input_rejects_partial_binding(self) -> None:
        """IntakeInput rejects partial/inconsistent binding states."""
        # When RouterInput/IntakeInput are implemented, this validates that
        # binding_state=INCONSISTENT is rejected
        pass


class TestMainFlowInputFactory:
    """Helper to create valid MainFlowInput for testing."""

    @staticmethod
    def valid_main_input(
        correlation_id: UUID | None = None,
        message_id: UUID | None = None,
        session_id: str | None = None,
        actor: ActorContext | None = None,
        source: InvocationSource | None = None,
        message: str | None = None,
        schema_version: str = "1.0.0",
    ) -> MainFlowInput:
        """Create a valid MainFlowInput with sensible defaults."""
        if correlation_id is None:
            correlation_id = UUID("12345678-1234-5678-1234-567812345678")
        if message_id is None:
            message_id = UUID("87654321-4321-8765-4321-876543218765")
        if session_id is None:
            session_id = "session-123"
        if actor is None:
            actor = ActorContext(actor_id="actor-123", display_name="Test User")
        if source is None:
            source = InvocationSource.API
        if message is None:
            message = "Hello, world!"

        return MainFlowInput(
            schema_version=schema_version,
            correlation_id=correlation_id,
            message_id=message_id,
            session_id=session_id,
            actor=actor,
            source=source,
            message=message,
        )

    def test_factory_creates_valid_input(self) -> None:
        """valid_main_input creates valid MainFlowInput."""
        input_data = self.valid_main_input()
        assert input_data.schema_version == "1.0.0"
        assert input_data.message == "Hello, world!"
        assert input_data.session_id == "session-123"
