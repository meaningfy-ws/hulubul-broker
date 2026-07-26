"""Tests for ExecutionEnvelopeComponent: trust boundary isolation and session normalization."""

from unittest.mock import patch
from uuid import UUID

import pytest
from lfx.schema.message import Message

from hulubul.core.models.operational import (
    ActorRole,
    IdentityAssurance,
    InvocationSource,
    MainFlowInput,
)
from hulubul.request_intake.entrypoints.langflow.components.hulubul import (
    ExecutionEnvelopeComponent,
)

# Constants for testing
SESSION = "p1-12345678-1234-4000-8000-000000000000"
BARE_UUID = "12345678-1234-4000-8000-000000000000"
TRUSTED_ACTOR_ID = "urn:uuid:87654321-4321-4000-8000-000000000000"
TRUSTED_DISPLAY_NAME = "Test Sender"


@pytest.fixture
def component() -> ExecutionEnvelopeComponent:
    """Create an ExecutionEnvelopeComponent instance."""
    return ExecutionEnvelopeComponent()


class TestActorIdResolution:
    """Test actor ID resolution from trusted sources."""

    def test_actor_id_from_api_header_required(self, component: ExecutionEnvelopeComponent) -> None:
        """Actor ID from API header X-LANGFLOW-GLOBAL-VAR-HULUBUL_PHASE1_ACTOR_ID is required."""
        component.message = Message(text="Hello", session_id=SESSION)

        with patch.object(component, "_get_api_actor_id", return_value=TRUSTED_ACTOR_ID):
            with patch.object(
                component, "_get_invocation_source", return_value=InvocationSource.API
            ):
                envelope = MainFlowInput.model_validate(component.build_envelope().data)
                assert envelope.actor.actor_id == TRUSTED_ACTOR_ID

    def test_actor_id_from_playground_env_required(
        self, component: ExecutionEnvelopeComponent
    ) -> None:
        """Actor ID from env var HULUBUL_PHASE1_PLAYGROUND_ACTOR_ID is required."""
        component.message = Message(text="Hello", session_id=SESSION)

        with patch.object(component, "_get_playground_actor_id", return_value=TRUSTED_ACTOR_ID):
            with patch.object(
                component, "_get_invocation_source", return_value=InvocationSource.PLAYGROUND
            ):
                envelope = MainFlowInput.model_validate(component.build_envelope().data)
                assert envelope.actor.actor_id == TRUSTED_ACTOR_ID

    def test_api_actor_id_missing_raises_error(self, component: ExecutionEnvelopeComponent) -> None:
        """Missing API actor ID raises INVALID_INPUT error."""
        component.message = Message(text="Hello", session_id=SESSION)

        with patch.object(component, "_get_api_actor_id", return_value=None):
            with patch.object(
                component, "_get_invocation_source", return_value=InvocationSource.API
            ):
                with pytest.raises(ValueError, match="INVALID_INPUT|required"):
                    component.build_envelope()

    def test_playground_actor_id_missing_raises_error(
        self, component: ExecutionEnvelopeComponent
    ) -> None:
        """Missing Playground actor ID raises INVALID_INPUT error."""
        component.message = Message(text="Hello", session_id=SESSION)

        with patch.object(component, "_get_playground_actor_id", return_value=None):
            with patch.object(
                component, "_get_invocation_source", return_value=InvocationSource.PLAYGROUND
            ):
                with pytest.raises(ValueError, match="INVALID_INPUT|required"):
                    component.build_envelope()


class TestDisplayNameResolution:
    """Test optional display name resolution."""

    def test_display_name_from_api_header_optional(
        self, component: ExecutionEnvelopeComponent
    ) -> None:
        """Display name from API header is optional."""
        component.message = Message(text="Hello", session_id=SESSION)

        with patch.object(component, "_get_api_actor_id", return_value=TRUSTED_ACTOR_ID):
            with patch.object(
                component, "_get_api_display_name", return_value=TRUSTED_DISPLAY_NAME
            ):
                with patch.object(
                    component, "_get_invocation_source", return_value=InvocationSource.API
                ):
                    envelope = MainFlowInput.model_validate(component.build_envelope().data)
                    assert envelope.actor.display_name == TRUSTED_DISPLAY_NAME

    def test_display_name_from_playground_env_optional(
        self, component: ExecutionEnvelopeComponent
    ) -> None:
        """Display name from Playground env var is optional."""
        component.message = Message(text="Hello", session_id=SESSION)

        with patch.object(component, "_get_playground_actor_id", return_value=TRUSTED_ACTOR_ID):
            with patch.object(
                component, "_get_playground_display_name", return_value=TRUSTED_DISPLAY_NAME
            ):
                with patch.object(
                    component, "_get_invocation_source", return_value=InvocationSource.PLAYGROUND
                ):
                    envelope = MainFlowInput.model_validate(component.build_envelope().data)
                    assert envelope.actor.display_name == TRUSTED_DISPLAY_NAME

    def test_missing_api_display_name_uses_default(
        self, component: ExecutionEnvelopeComponent
    ) -> None:
        """Missing API display name uses a default value."""
        component.message = Message(text="Hello", session_id=SESSION)

        with patch.object(component, "_get_api_actor_id", return_value=TRUSTED_ACTOR_ID):
            with patch.object(component, "_get_api_display_name", return_value=None):
                with patch.object(
                    component, "_get_invocation_source", return_value=InvocationSource.API
                ):
                    envelope = MainFlowInput.model_validate(component.build_envelope().data)
                    # Should have some display name (not empty)
                    assert len(envelope.actor.display_name) > 0

    def test_missing_playground_display_name_uses_default(
        self, component: ExecutionEnvelopeComponent
    ) -> None:
        """Missing Playground display name uses a default value."""
        component.message = Message(text="Hello", session_id=SESSION)

        with patch.object(component, "_get_playground_actor_id", return_value=TRUSTED_ACTOR_ID):
            with patch.object(component, "_get_playground_display_name", return_value=None):
                with patch.object(
                    component, "_get_invocation_source", return_value=InvocationSource.PLAYGROUND
                ):
                    envelope = MainFlowInput.model_validate(component.build_envelope().data)
                    # Should have some display name (not empty)
                    assert len(envelope.actor.display_name) > 0


class TestSessionNormalization:
    """Test session ID normalization: bare UUID or p1-<uuid> both normalize to lowercase p1-<uuid>."""

    def test_bare_uuid_normalizes_to_canonical_form(
        self, component: ExecutionEnvelopeComponent
    ) -> None:
        """Bare UUID normalizes to canonical p1-<lowercase-uuid> form."""
        component.message = Message(text="Hello", session_id=BARE_UUID)

        with patch.object(component, "_get_api_actor_id", return_value=TRUSTED_ACTOR_ID):
            with patch.object(
                component, "_get_invocation_source", return_value=InvocationSource.API
            ):
                envelope = MainFlowInput.model_validate(component.build_envelope().data)
                assert envelope.session_id == f"p1-{BARE_UUID.lower()}"

    def test_canonical_uuid_normalizes_to_lowercase(
        self, component: ExecutionEnvelopeComponent
    ) -> None:
        """Canonical p1-<UUID> normalizes to lowercase p1-<uuid>."""
        uppercase_session = SESSION.upper()
        component.message = Message(text="Hello", session_id=uppercase_session)

        with patch.object(component, "_get_api_actor_id", return_value=TRUSTED_ACTOR_ID):
            with patch.object(
                component, "_get_invocation_source", return_value=InvocationSource.API
            ):
                envelope = MainFlowInput.model_validate(component.build_envelope().data)
                assert envelope.session_id == SESSION.lower()

    def test_bare_uuid_uppercase_normalizes_correctly(
        self, component: ExecutionEnvelopeComponent
    ) -> None:
        """Bare UUID in uppercase normalizes correctly."""
        component.message = Message(text="Hello", session_id=BARE_UUID.upper())

        with patch.object(component, "_get_api_actor_id", return_value=TRUSTED_ACTOR_ID):
            with patch.object(
                component, "_get_invocation_source", return_value=InvocationSource.API
            ):
                envelope = MainFlowInput.model_validate(component.build_envelope().data)
                assert envelope.session_id == f"p1-{BARE_UUID.lower()}"


class TestSessionValidation:
    """Test session validation: matching, rejecting empty, rejecting malformed."""

    def test_empty_session_rejected(self, component: ExecutionEnvelopeComponent) -> None:
        """Empty session is rejected."""
        component.message = Message(text="Hello", session_id="")

        with patch.object(component, "_get_api_actor_id", return_value=TRUSTED_ACTOR_ID):
            with patch.object(
                component, "_get_invocation_source", return_value=InvocationSource.API
            ):
                with pytest.raises(ValueError, match="INVALID_INPUT|session"):
                    component.build_envelope()

    def test_malformed_uuid_rejected(self, component: ExecutionEnvelopeComponent) -> None:
        """Malformed UUID is rejected."""
        component.message = Message(text="Hello", session_id="not-a-uuid")

        with patch.object(component, "_get_api_actor_id", return_value=TRUSTED_ACTOR_ID):
            with patch.object(
                component, "_get_invocation_source", return_value=InvocationSource.API
            ):
                with pytest.raises(ValueError, match="INVALID_INPUT|session"):
                    component.build_envelope()

    def test_mismatched_message_and_graph_session_rejected(
        self, component: ExecutionEnvelopeComponent
    ) -> None:
        """Mismatched Message.session_id and graph session_id are rejected."""
        component.message = Message(text="Hello", session_id=SESSION)

        with patch.object(component, "_get_api_actor_id", return_value=TRUSTED_ACTOR_ID):
            with patch.object(
                component, "_get_invocation_source", return_value=InvocationSource.API
            ):
                with patch.object(
                    component, "_get_graph_session_id", return_value="p1-different-uuid"
                ):
                    with pytest.raises(ValueError, match="INVALID_INPUT|session"):
                        component.build_envelope()

    def test_graph_session_id_does_not_fall_back_to_message_session(
        self, component: ExecutionEnvelopeComponent
    ) -> None:
        """_get_graph_session_id() must not fall back to Message.session_id.

        Falling back would make the message-vs-graph mismatch check compare the
        message's session against itself, silently defeating the check.
        """
        component.message = Message(text="Hello", session_id=SESSION)

        assert component._get_graph_session_id() is None

    def test_flow_id_fallback_rejected(self, component: ExecutionEnvelopeComponent) -> None:
        """LangFlow's flow-ID fallback (when session omitted) is rejected."""
        # When session_id is omitted from Message, LFX might use flow_id as fallback
        # This test confirms we reject such fallback scenarios
        component.message = Message(text="Hello", session_id=None)

        with patch.object(component, "_get_api_actor_id", return_value=TRUSTED_ACTOR_ID):
            with patch.object(
                component, "_get_invocation_source", return_value=InvocationSource.API
            ):
                with pytest.raises(ValueError, match="INVALID_INPUT|session"):
                    component.build_envelope()


class TestConstantRoleAssuranceSource:
    """Test that role, assurance, and source are hard-coded constants."""

    def test_role_always_sender(self, component: ExecutionEnvelopeComponent) -> None:
        """Actor role is always SENDER (constant)."""
        component.message = Message(text="Hello", session_id=SESSION)

        with patch.object(component, "_get_api_actor_id", return_value=TRUSTED_ACTOR_ID):
            with patch.object(
                component, "_get_invocation_source", return_value=InvocationSource.API
            ):
                envelope = MainFlowInput.model_validate(component.build_envelope().data)
                assert envelope.actor.actor_role == ActorRole.SENDER

    def test_assurance_always_simulated(self, component: ExecutionEnvelopeComponent) -> None:
        """Identity assurance is always SIMULATED (constant)."""
        component.message = Message(text="Hello", session_id=SESSION)

        with patch.object(component, "_get_api_actor_id", return_value=TRUSTED_ACTOR_ID):
            with patch.object(
                component, "_get_invocation_source", return_value=InvocationSource.API
            ):
                envelope = MainFlowInput.model_validate(component.build_envelope().data)
                assert envelope.actor.identity_assurance == IdentityAssurance.SIMULATED

    def test_source_api_for_api_invocation(self, component: ExecutionEnvelopeComponent) -> None:
        """Source is API for API invocations."""
        component.message = Message(text="Hello", session_id=SESSION)

        with patch.object(component, "_get_api_actor_id", return_value=TRUSTED_ACTOR_ID):
            with patch.object(
                component, "_get_invocation_source", return_value=InvocationSource.API
            ):
                envelope = MainFlowInput.model_validate(component.build_envelope().data)
                assert envelope.source == InvocationSource.API

    def test_source_playground_for_playground_invocation(
        self, component: ExecutionEnvelopeComponent
    ) -> None:
        """Source is PLAYGROUND for Playground invocations."""
        component.message = Message(text="Hello", session_id=SESSION)

        with patch.object(component, "_get_playground_actor_id", return_value=TRUSTED_ACTOR_ID):
            with patch.object(
                component, "_get_invocation_source", return_value=InvocationSource.PLAYGROUND
            ):
                envelope = MainFlowInput.model_validate(component.build_envelope().data)
                assert envelope.source == InvocationSource.PLAYGROUND


class TestGeneratedIds:
    """Test that message_id and correlation_id are unique UUIDs per call."""

    def test_message_id_is_unique_uuid(self, component: ExecutionEnvelopeComponent) -> None:
        """message_id is a unique UUID."""
        component.message = Message(text="Hello", session_id=SESSION)

        with patch.object(component, "_get_api_actor_id", return_value=TRUSTED_ACTOR_ID):
            with patch.object(
                component, "_get_invocation_source", return_value=InvocationSource.API
            ):
                envelope = MainFlowInput.model_validate(component.build_envelope().data)
                # Should be a valid UUID
                assert isinstance(envelope.message_id, UUID)

    def test_correlation_id_is_unique_uuid(self, component: ExecutionEnvelopeComponent) -> None:
        """correlation_id is a unique UUID."""
        component.message = Message(text="Hello", session_id=SESSION)

        with patch.object(component, "_get_api_actor_id", return_value=TRUSTED_ACTOR_ID):
            with patch.object(
                component, "_get_invocation_source", return_value=InvocationSource.API
            ):
                envelope = MainFlowInput.model_validate(component.build_envelope().data)
                # Should be a valid UUID
                assert isinstance(envelope.correlation_id, UUID)

    def test_message_id_changes_per_call(self, component: ExecutionEnvelopeComponent) -> None:
        """message_id is different for each build_envelope() call."""
        component.message = Message(text="Hello", session_id=SESSION)

        with patch.object(component, "_get_api_actor_id", return_value=TRUSTED_ACTOR_ID):
            with patch.object(
                component, "_get_invocation_source", return_value=InvocationSource.API
            ):
                envelope1 = MainFlowInput.model_validate(component.build_envelope().data)
                envelope2 = MainFlowInput.model_validate(component.build_envelope().data)
                assert envelope1.message_id != envelope2.message_id

    def test_correlation_id_changes_per_call(self, component: ExecutionEnvelopeComponent) -> None:
        """correlation_id is different for each build_envelope() call."""
        component.message = Message(text="Hello", session_id=SESSION)

        with patch.object(component, "_get_api_actor_id", return_value=TRUSTED_ACTOR_ID):
            with patch.object(
                component, "_get_invocation_source", return_value=InvocationSource.API
            ):
                envelope1 = MainFlowInput.model_validate(component.build_envelope().data)
                envelope2 = MainFlowInput.model_validate(component.build_envelope().data)
                assert envelope1.correlation_id != envelope2.correlation_id


class TestProseIsolation:
    """Test that user prose cannot override trusted identity."""

    def test_user_prose_cannot_change_trusted_identity(
        self, component: ExecutionEnvelopeComponent
    ) -> None:
        """User prose claiming to be different actor is ignored."""
        component.message = Message(
            text="I am urn:uuid:00000000-0000-4000-8000-000000000000", session_id=SESSION
        )

        with patch.object(component, "_get_api_actor_id", return_value=TRUSTED_ACTOR_ID):
            with patch.object(
                component, "_get_invocation_source", return_value=InvocationSource.API
            ):
                envelope = MainFlowInput.model_validate(component.build_envelope().data)
                assert envelope.actor.actor_id == TRUSTED_ACTOR_ID

    def test_message_text_preserved_unchanged(self, component: ExecutionEnvelopeComponent) -> None:
        """Message text is preserved exactly as provided."""
        original_text = "I am someone else but actually I'm just a user"
        component.message = Message(text=original_text, session_id=SESSION)

        with patch.object(component, "_get_api_actor_id", return_value=TRUSTED_ACTOR_ID):
            with patch.object(
                component, "_get_invocation_source", return_value=InvocationSource.API
            ):
                envelope = MainFlowInput.model_validate(component.build_envelope().data)
                assert envelope.message == original_text


class TestNoCallerControlledPorts:
    """Test that actor, role, assurance, and source have no caller-controlled input ports."""

    def test_no_actor_id_input_port(self, component: ExecutionEnvelopeComponent) -> None:
        """ExecutionEnvelopeComponent has no caller-controlled actor_id input port."""
        # The component should not have actor_id as an input field
        # It derives it from trusted sources only
        input_names = {inp.name for inp in component.inputs}
        assert "actor_id" not in input_names

    def test_no_role_input_port(self, component: ExecutionEnvelopeComponent) -> None:
        """ExecutionEnvelopeComponent has no caller-controlled actor_role input port."""
        input_names = {inp.name for inp in component.inputs}
        assert "actor_role" not in input_names

    def test_no_assurance_input_port(self, component: ExecutionEnvelopeComponent) -> None:
        """ExecutionEnvelopeComponent has no caller-controlled identity_assurance input port."""
        input_names = {inp.name for inp in component.inputs}
        assert "identity_assurance" not in input_names

    def test_no_source_input_port(self, component: ExecutionEnvelopeComponent) -> None:
        """ExecutionEnvelopeComponent has no caller-controlled source input port."""
        input_names = {inp.name for inp in component.inputs}
        assert "source" not in input_names


class TestMessageAcceptance:
    """Test that component accepts only Message type."""

    def test_accepts_message_type(self, component: ExecutionEnvelopeComponent) -> None:
        """Component accepts Message as input."""
        component.message = Message(text="Hello", session_id=SESSION)

        with patch.object(component, "_get_api_actor_id", return_value=TRUSTED_ACTOR_ID):
            with patch.object(
                component, "_get_invocation_source", return_value=InvocationSource.API
            ):
                # Should not raise
                envelope = component.build_envelope()
                assert envelope is not None

    def test_rejects_string_input(self, component: ExecutionEnvelopeComponent) -> None:
        """Component rejects plain string input (no free prose as input)."""
        # The component should have message as Message type, not str
        component.message = "Not a Message object"  # type: ignore[assignment]

        with patch.object(component, "_get_api_actor_id", return_value=TRUSTED_ACTOR_ID):
            with patch.object(
                component, "_get_invocation_source", return_value=InvocationSource.API
            ):
                # Should raise a validation/type error
                with pytest.raises((TypeError, ValueError, AttributeError)):
                    component.build_envelope()


class TestOutputSchema:
    """Test that output conforms to MainFlowInput schema."""

    def test_output_is_valid_main_flow_input(self, component: ExecutionEnvelopeComponent) -> None:
        """Output can be validated as MainFlowInput."""
        component.message = Message(text="Hello", session_id=SESSION)

        with patch.object(component, "_get_api_actor_id", return_value=TRUSTED_ACTOR_ID):
            with patch.object(
                component, "_get_invocation_source", return_value=InvocationSource.API
            ):
                envelope_data = component.build_envelope().data
                # Should parse without errors
                envelope = MainFlowInput.model_validate(envelope_data)
                assert envelope is not None

    def test_output_has_all_required_fields(self, component: ExecutionEnvelopeComponent) -> None:
        """Output has all required MainFlowInput fields."""
        component.message = Message(text="Hello", session_id=SESSION)

        with patch.object(component, "_get_api_actor_id", return_value=TRUSTED_ACTOR_ID):
            with patch.object(
                component, "_get_invocation_source", return_value=InvocationSource.API
            ):
                envelope = MainFlowInput.model_validate(component.build_envelope().data)
                assert hasattr(envelope, "message_id")
                assert hasattr(envelope, "session_id")
                assert hasattr(envelope, "actor")
                assert hasattr(envelope, "source")
                assert hasattr(envelope, "message")
                assert hasattr(envelope, "correlation_id")
