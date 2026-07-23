"""Tests for operational envelope models (trusted metadata)."""

from uuid import UUID

import pytest
from pydantic import ValidationError

from hulubul.core.models.operational.enums import ActorRole, IdentityAssurance, InvocationSource
from hulubul.core.models.operational.envelope import (
    ActorContext,
    MainFlowInput,
)


class TestActorContext:
    """ActorContext represents trusted actor metadata."""

    def test_creates_with_required_fields(self) -> None:
        """ActorContext must accept actor_id and display_name."""
        actor = ActorContext(actor_id="actor-123", display_name="Test User")
        assert actor.actor_id == "actor-123"
        assert actor.display_name == "Test User"

    def test_actor_role_defaults_to_sender(self) -> None:
        """actor_role must default to SENDER."""
        actor = ActorContext(actor_id="actor-123", display_name="Test User")
        assert actor.actor_role == ActorRole.SENDER

    def test_identity_assurance_defaults_to_simulated(self) -> None:
        """identity_assurance must default to SIMULATED."""
        actor = ActorContext(actor_id="actor-123", display_name="Test User")
        assert actor.identity_assurance == IdentityAssurance.SIMULATED

    def test_accepts_explicit_actor_role(self) -> None:
        """ActorContext must accept explicit actor_role."""
        actor = ActorContext(
            actor_id="actor-123", display_name="Test User", actor_role=ActorRole.SENDER
        )
        assert actor.actor_role == ActorRole.SENDER

    def test_accepts_explicit_identity_assurance(self) -> None:
        """ActorContext must accept explicit identity_assurance."""
        actor = ActorContext(
            actor_id="actor-123",
            display_name="Test User",
            identity_assurance=IdentityAssurance.SIMULATED,
        )
        assert actor.identity_assurance == IdentityAssurance.SIMULATED

    def test_is_frozen(self) -> None:
        """ActorContext must be frozen."""
        actor = ActorContext(actor_id="actor-123", display_name="Test User")

        with pytest.raises((ValidationError, Exception)):
            actor.actor_id = "new-id"

    def test_rejects_extra_fields(self) -> None:
        """ActorContext must reject extra fields."""
        with pytest.raises(ValidationError):
            ActorContext(actor_id="actor-123", display_name="Test User", extra_field="value")

    def test_requires_actor_id(self) -> None:
        """actor_id is required."""
        with pytest.raises(ValidationError):
            ActorContext(display_name="Test User")

    def test_requires_display_name(self) -> None:
        """display_name is required."""
        with pytest.raises(ValidationError):
            ActorContext(actor_id="actor-123")


class TestMainFlowInput:
    """MainFlowInput is the trusted envelope separating metadata from prose."""

    def test_creates_with_all_required_fields(self) -> None:
        """MainFlowInput must accept all required fields."""
        test_uuid = UUID("12345678-1234-5678-1234-567812345678")
        message_id = UUID("87654321-4321-8765-4321-876543218765")
        session_id = "session-123"

        actor = ActorContext(actor_id="actor-123", display_name="Test User")

        input_data = MainFlowInput(
            correlation_id=test_uuid,
            message_id=message_id,
            session_id=session_id,
            actor=actor,
            source=InvocationSource.API,
            message="Hello, world!",
        )

        assert input_data.correlation_id == test_uuid
        assert input_data.message_id == message_id
        assert input_data.session_id == session_id
        assert input_data.actor == actor
        assert input_data.source == InvocationSource.API
        assert input_data.message == "Hello, world!"

    def test_schema_version_defaults_to_1_0_0(self) -> None:
        """schema_version must default to '1.0.0'."""
        test_uuid = UUID("12345678-1234-5678-1234-567812345678")
        message_id = UUID("87654321-4321-8765-4321-876543218765")

        actor = ActorContext(actor_id="actor-123", display_name="Test User")

        input_data = MainFlowInput(
            correlation_id=test_uuid,
            message_id=message_id,
            session_id="session-123",
            actor=actor,
            source=InvocationSource.API,
            message="Hello",
        )

        assert input_data.schema_version == "1.0.0"

    def test_message_must_be_human_supplied_text(self) -> None:
        """message must conform to HumanSuppliedText constraints (1-4000 chars)."""
        test_uuid = UUID("12345678-1234-5678-1234-567812345678")
        message_id = UUID("87654321-4321-8765-4321-876543218765")

        actor = ActorContext(actor_id="actor-123", display_name="Test User")

        # Empty message should fail
        with pytest.raises(ValidationError):
            MainFlowInput(
                correlation_id=test_uuid,
                message_id=message_id,
                session_id="session-123",
                actor=actor,
                source=InvocationSource.API,
                message="",
            )

    def test_message_whitespace_is_stripped(self) -> None:
        """message whitespace must be stripped."""
        test_uuid = UUID("12345678-1234-5678-1234-567812345678")
        message_id = UUID("87654321-4321-8765-4321-876543218765")

        actor = ActorContext(actor_id="actor-123", display_name="Test User")

        input_data = MainFlowInput(
            correlation_id=test_uuid,
            message_id=message_id,
            session_id="session-123",
            actor=actor,
            source=InvocationSource.API,
            message="  hello world  ",
        )

        assert input_data.message == "hello world"

    def test_is_frozen(self) -> None:
        """MainFlowInput must be frozen."""
        test_uuid = UUID("12345678-1234-5678-1234-567812345678")
        message_id = UUID("87654321-4321-8765-4321-876543218765")

        actor = ActorContext(actor_id="actor-123", display_name="Test User")

        input_data = MainFlowInput(
            correlation_id=test_uuid,
            message_id=message_id,
            session_id="session-123",
            actor=actor,
            source=InvocationSource.API,
            message="Hello",
        )

        with pytest.raises((ValidationError, Exception)):
            input_data.message = "changed"

    def test_rejects_extra_fields(self) -> None:
        """MainFlowInput must reject extra fields."""
        test_uuid = UUID("12345678-1234-5678-1234-567812345678")
        message_id = UUID("87654321-4321-8765-4321-876543218765")

        actor = ActorContext(actor_id="actor-123", display_name="Test User")

        with pytest.raises(ValidationError):
            MainFlowInput(
                correlation_id=test_uuid,
                message_id=message_id,
                session_id="session-123",
                actor=actor,
                source=InvocationSource.API,
                message="Hello",
                extra_field="value",
            )

    def test_requires_correlation_id(self) -> None:
        """correlation_id is required."""
        message_id = UUID("87654321-4321-8765-4321-876543218765")

        actor = ActorContext(actor_id="actor-123", display_name="Test User")

        with pytest.raises(ValidationError):
            MainFlowInput(
                message_id=message_id,
                session_id="session-123",
                actor=actor,
                source=InvocationSource.API,
                message="Hello",
            )

    def test_requires_message_id(self) -> None:
        """message_id is required."""
        test_uuid = UUID("12345678-1234-5678-1234-567812345678")

        actor = ActorContext(actor_id="actor-123", display_name="Test User")

        with pytest.raises(ValidationError):
            MainFlowInput(
                correlation_id=test_uuid,
                session_id="session-123",
                actor=actor,
                source=InvocationSource.API,
                message="Hello",
            )

    def test_requires_session_id(self) -> None:
        """session_id is required."""
        test_uuid = UUID("12345678-1234-5678-1234-567812345678")
        message_id = UUID("87654321-4321-8765-4321-876543218765")

        actor = ActorContext(actor_id="actor-123", display_name="Test User")

        with pytest.raises(ValidationError):
            MainFlowInput(
                correlation_id=test_uuid,
                message_id=message_id,
                actor=actor,
                source=InvocationSource.API,
                message="Hello",
            )

    def test_requires_actor(self) -> None:
        """actor is required."""
        test_uuid = UUID("12345678-1234-5678-1234-567812345678")
        message_id = UUID("87654321-4321-8765-4321-876543218765")

        with pytest.raises(ValidationError):
            MainFlowInput(
                correlation_id=test_uuid,
                message_id=message_id,
                session_id="session-123",
                source=InvocationSource.API,
                message="Hello",
            )

    def test_requires_source(self) -> None:
        """source is required."""
        test_uuid = UUID("12345678-1234-5678-1234-567812345678")
        message_id = UUID("87654321-4321-8765-4321-876543218765")

        actor = ActorContext(actor_id="actor-123", display_name="Test User")

        with pytest.raises(ValidationError):
            MainFlowInput(
                correlation_id=test_uuid,
                message_id=message_id,
                session_id="session-123",
                actor=actor,
                message="Hello",
            )

    def test_requires_message(self) -> None:
        """message is required."""
        test_uuid = UUID("12345678-1234-5678-1234-567812345678")
        message_id = UUID("87654321-4321-8765-4321-876543218765")

        actor = ActorContext(actor_id="actor-123", display_name="Test User")

        with pytest.raises(ValidationError):
            MainFlowInput(
                correlation_id=test_uuid,
                message_id=message_id,
                session_id="session-123",
                actor=actor,
                source=InvocationSource.API,
            )
