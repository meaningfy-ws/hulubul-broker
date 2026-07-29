"""Tests for GraphIdentifiersGenerator: deterministic graph identifier generation component."""

import json

import pytest
from lfx.schema.message import Message

from hulubul.core.models.operational.intake import GraphIdentifiers
from hulubul.request_intake.entrypoints.langflow.components.hulubul.graph_identifiers_generator import (
    HulubulGraphIdentifiersGenerator,
)


def _text(message: Message) -> str:
    """Narrow Message.text (str | AsyncIterator | Iterator | None) to str for mypy."""
    assert isinstance(message.text, str)
    return message.text


@pytest.fixture
def generator() -> HulubulGraphIdentifiersGenerator:
    """Create a HulubulGraphIdentifiersGenerator."""
    return HulubulGraphIdentifiersGenerator()


class TestDeterministicGeneration:
    """Test deterministic graph identifier generation for create operations."""

    def test_generates_identifiers_for_complete_intake(
        self, generator: HulubulGraphIdentifiersGenerator
    ) -> None:
        """Generate full set of identifiers when all facts present."""
        generator.actor_id = "urn:uuid:sender-12345678"
        generator.receiver_stable_id = "receiver@example.com"
        generator.receiver_name = "Jane Doe"
        generator.parcel_declared_content = "Books"
        generator.pickup_location = "123 Main St"
        generator.drop_off_location = "456 Oak Ave"

        output = generator.build_output()

        assert isinstance(output, Message)
        identifiers = GraphIdentifiers.model_validate_json(_text(output))

        # Verify all fields are present
        assert identifiers.request_id
        assert identifiers.request_id.startswith("req-")
        assert identifiers.sender_id
        assert identifiers.sender_id.startswith("s-")
        assert identifiers.sender_agent_id
        assert identifiers.sender_agent_id.startswith("ag-")
        assert identifiers.receiver_id
        assert identifiers.receiver_id.startswith("r-")
        assert identifiers.receiver_agent_id
        assert identifiers.receiver_agent_id.startswith("ag-")
        assert identifiers.receiver_agent_identifier == "receiver@example.com"
        assert identifiers.parcel_id
        assert identifiers.parcel_id.startswith("p-")
        assert identifiers.pickup_place_id
        assert identifiers.pickup_place_id.startswith("pl-")
        assert identifiers.pickup_place_identifier
        assert identifiers.pickup_place_identifier.startswith("urn:uuid:")
        assert identifiers.drop_off_place_id
        assert identifiers.drop_off_place_id.startswith("pl-")
        assert identifiers.drop_off_place_identifier
        assert identifiers.drop_off_place_identifier.startswith("urn:uuid:")

    def test_generates_identifiers_for_name_only_receiver(
        self, generator: HulubulGraphIdentifiersGenerator
    ) -> None:
        """Name-only receiver gets request-scoped URN instead of enduring agent ID."""
        generator.actor_id = "urn:uuid:sender-12345678"
        generator.receiver_name = "Jane Doe"
        generator.receiver_stable_id = None  # Name-only
        generator.pickup_location = "123 Main St"
        generator.drop_off_location = "456 Oak Ave"

        output = generator.build_output()

        identifiers = GraphIdentifiers.model_validate_json(_text(output))

        # Receiver should have role ID and request-scoped URN, but NO enduring agent ID
        assert identifiers.receiver_id
        assert identifiers.receiver_id.startswith("r-")
        assert identifiers.receiver_agent_id is None
        assert identifiers.receiver_agent_identifier
        assert identifiers.receiver_agent_identifier.startswith("urn:hulubul:phase1:receiver:")

    def test_generates_identifiers_minimal_facts(
        self, generator: HulubulGraphIdentifiersGenerator
    ) -> None:
        """Generate only request/sender IDs when minimal facts present."""
        generator.actor_id = "urn:uuid:sender-12345678"
        # No receiver, parcel, or place info

        output = generator.build_output()

        identifiers = GraphIdentifiers.model_validate_json(_text(output))

        # Always present
        assert identifiers.request_id
        assert identifiers.request_id.startswith("req-")
        assert identifiers.sender_id
        assert identifiers.sender_id.startswith("s-")
        assert identifiers.sender_agent_id
        assert identifiers.sender_agent_id.startswith("ag-")

        # Should be None when not included
        assert identifiers.receiver_id is None
        assert identifiers.receiver_agent_id is None
        assert identifiers.receiver_agent_identifier is None
        assert identifiers.parcel_id is None
        assert identifiers.pickup_place_id is None
        assert identifiers.pickup_place_identifier is None
        assert identifiers.drop_off_place_id is None
        assert identifiers.drop_off_place_identifier is None

    def test_sender_agent_id_is_stable(self, generator: HulubulGraphIdentifiersGenerator) -> None:
        """Sender agent ID is stable across calls (UUID5 from actor_id)."""
        generator.actor_id = "urn:uuid:sender-12345678"

        output1 = generator.build_output()
        identifiers1 = GraphIdentifiers.model_validate_json(_text(output1))

        output2 = generator.build_output()
        identifiers2 = GraphIdentifiers.model_validate_json(_text(output2))

        # Sender agent ID must be the same (deterministic)
        assert identifiers1.sender_agent_id == identifiers2.sender_agent_id

    def test_request_id_is_unique_per_call(
        self, generator: HulubulGraphIdentifiersGenerator
    ) -> None:
        """Request ID is unique per call (UUID4 from session)."""
        generator.actor_id = "urn:uuid:sender-12345678"

        output1 = generator.build_output()
        identifiers1 = GraphIdentifiers.model_validate_json(_text(output1))

        output2 = generator.build_output()
        identifiers2 = GraphIdentifiers.model_validate_json(_text(output2))

        # Request ID must differ (non-deterministic)
        assert identifiers1.request_id != identifiers2.request_id

    def test_receiver_agent_id_stable_with_same_stable_id(
        self, generator: HulubulGraphIdentifiersGenerator
    ) -> None:
        """Receiver agent ID is stable for same receiver_stable_id."""
        generator.actor_id = "urn:uuid:sender-12345678"
        generator.receiver_stable_id = "receiver@example.com"
        generator.receiver_name = "Jane Doe"

        output1 = generator.build_output()
        identifiers1 = GraphIdentifiers.model_validate_json(_text(output1))

        output2 = generator.build_output()
        identifiers2 = GraphIdentifiers.model_validate_json(_text(output2))

        # Receiver agent ID must match (deterministic from stable_id)
        assert identifiers1.receiver_agent_id == identifiers2.receiver_agent_id


class TestRealEdgeValueCoercion:
    """Test handling of different input shapes from LangFlow edges."""

    def test_accepts_string_values(self, generator: HulubulGraphIdentifiersGenerator) -> None:
        """Accepts string values for actor_id and other text fields."""
        generator.actor_id = "urn:uuid:sender-12345678"
        generator.receiver_stable_id = "receiver@example.com"
        generator.receiver_name = "Jane Doe"
        generator.pickup_location = "123 Main St"
        generator.drop_off_location = "456 Oak Ave"

        output = generator.build_output()

        identifiers = GraphIdentifiers.model_validate_json(_text(output))
        assert identifiers.request_id
        assert identifiers.receiver_agent_identifier == "receiver@example.com"

    def test_handles_none_stable_id(self, generator: HulubulGraphIdentifiersGenerator) -> None:
        """Handles None/empty receiver_stable_id correctly."""
        generator.actor_id = "urn:uuid:sender-12345678"
        generator.receiver_name = "Jane Doe"
        generator.receiver_stable_id = None

        output = generator.build_output()

        identifiers = GraphIdentifiers.model_validate_json(_text(output))
        assert identifiers.receiver_agent_id is None
        assert identifiers.receiver_agent_identifier
        assert identifiers.receiver_agent_identifier.startswith("urn:hulubul:phase1:receiver:")

    def test_output_is_json_serializable(self, generator: HulubulGraphIdentifiersGenerator) -> None:
        """Output text is valid JSON."""
        generator.actor_id = "urn:uuid:sender-12345678"
        generator.receiver_name = "Jane Doe"

        output = generator.build_output()

        parsed = json.loads(_text(output))
        assert isinstance(parsed, dict)
        assert "request_id" in parsed
        assert "sender_agent_id" in parsed


class TestPurity:
    """Test that generation is pure/deterministic (no I/O, no model calls)."""

    def test_no_side_effects(self, generator: HulubulGraphIdentifiersGenerator) -> None:
        """Multiple calls produce independent results with no shared state."""
        generator.actor_id = "urn:uuid:sender-12345678"

        result1 = generator.build_output()
        result2 = generator.build_output()

        id1 = GraphIdentifiers.model_validate_json(_text(result1))
        id2 = GraphIdentifiers.model_validate_json(_text(result2))

        # Request IDs differ but sender agent IDs match
        assert id1.request_id != id2.request_id
        assert id1.sender_agent_id == id2.sender_agent_id
