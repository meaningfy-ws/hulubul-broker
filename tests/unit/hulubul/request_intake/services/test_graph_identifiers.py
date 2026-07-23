"""Tests for graph identifier generation service (Task 12).

Comprehensive test coverage:
- Old functions (backward compat): session, request, delivery IDs
- New functions: enduring_agent_id, new_graph_identifiers
- Sparse allocation (only allocate for present entities)
- Allocation order enforcement
- Prefix correctness (req-, ag-, s-, r-, p-, pl-, urn:)
- Determinism (same inputs → same output)
- Receiver fallback (name-only → request-scoped URN)
"""

import re
from uuid import UUID

import pytest

from hulubul.core.models.operational.intake import GraphIdentifiers
from hulubul.request_intake.services.graph_identifiers import (
    enduring_agent_id,
    generate_delivery_id,
    generate_request_id,
    generate_session_id,
    new_graph_identifiers,
)

# Valid UUID v4 or v5 string pattern (36 chars: 8-4-4-4-12 hex digits + hyphens)
UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE
)


class TestGenerateSessionId:
    """Test random session ID generation (UUID4) — backward compat."""

    def test_returns_string(self) -> None:
        """Session ID is returned as a string."""
        session_id = generate_session_id()
        assert isinstance(session_id, str)

    def test_valid_uuid_format(self) -> None:
        """Session ID is a valid UUID string format."""
        session_id = generate_session_id()
        assert UUID_PATTERN.match(session_id), f"Invalid UUID format: {session_id}"
        UUID(session_id)

    def test_uniqueness_on_multiple_calls(self) -> None:
        """Multiple calls to generate_session_id produce unique UUIDs."""
        ids = {generate_session_id() for _ in range(10)}
        assert len(ids) == 10, "Session IDs must be unique across calls"

    def test_multiple_calls_produce_different_results(self) -> None:
        """Specifically test that two consecutive calls differ."""
        id1 = generate_session_id()
        id2 = generate_session_id()
        assert id1 != id2, "Session IDs must be different on each call"


class TestGenerateRequestId:
    """Test deterministic request ID generation (UUID5) — backward compat."""

    def test_returns_string(self) -> None:
        """Request ID is returned as a string."""
        request_id = generate_request_id("intent_value", "receiver_123")
        assert isinstance(request_id, str)

    def test_valid_uuid_format(self) -> None:
        """Request ID is a valid UUID string format."""
        request_id = generate_request_id("intent_value", "receiver_123")
        assert UUID_PATTERN.match(request_id), f"Invalid UUID format: {request_id}"
        UUID(request_id)

    def test_deterministic_same_inputs(self) -> None:
        """Identical inputs produce identical request IDs."""
        id1 = generate_request_id("intent_value", "receiver_123")
        id2 = generate_request_id("intent_value", "receiver_123")
        assert id1 == id2, "Request ID must be deterministic (same inputs → same output)"

    def test_deterministic_stability_multiple_calls(self) -> None:
        """Request ID is stable across many calls with same inputs."""
        ids = [generate_request_id("test_intent", "receiver_456") for _ in range(5)]
        assert all(id == ids[0] for id in ids), "Request ID must be stable across calls"

    def test_different_inputs_produce_different_ids(self) -> None:
        """Different inputs produce different request IDs."""
        id1 = generate_request_id("intent_1", "receiver_A")
        id2 = generate_request_id("intent_2", "receiver_A")
        id3 = generate_request_id("intent_1", "receiver_B")
        assert id1 != id2, "Different parcel_intent should produce different IDs"
        assert id1 != id3, "Different receiver_id should produce different IDs"
        assert id2 != id3, "Different inputs should produce different IDs"

    def test_empty_string_inputs(self) -> None:
        """Empty strings are handled and produce valid UUIDs."""
        request_id = generate_request_id("", "")
        assert isinstance(request_id, str)
        assert UUID_PATTERN.match(request_id)
        UUID(request_id)

    def test_special_characters_in_inputs(self) -> None:
        """Special characters in inputs are handled safely."""
        request_id = generate_request_id("intent@#$%^&*()", "receiver_!<>?/\\")
        assert isinstance(request_id, str)
        assert UUID_PATTERN.match(request_id)
        UUID(request_id)

    def test_long_input_strings(self) -> None:
        """Very long input strings are handled."""
        long_intent = "x" * 10000
        long_receiver = "y" * 10000
        request_id = generate_request_id(long_intent, long_receiver)
        assert isinstance(request_id, str)
        assert UUID_PATTERN.match(request_id)
        UUID(request_id)


class TestGenerateDeliveryId:
    """Test deterministic delivery ID generation (UUID5)."""

    def test_returns_string(self) -> None:
        """Delivery ID is returned as a string."""
        delivery_id = generate_delivery_id("request_id_value", "transporter_123")
        assert isinstance(delivery_id, str)

    def test_valid_uuid_format(self) -> None:
        """Delivery ID is a valid UUID string format."""
        delivery_id = generate_delivery_id("request_id_value", "transporter_123")
        assert UUID_PATTERN.match(delivery_id), f"Invalid UUID format: {delivery_id}"
        UUID(delivery_id)

    def test_deterministic_same_inputs(self) -> None:
        """Identical inputs produce identical delivery IDs."""
        id1 = generate_delivery_id("request_xyz", "transporter_001")
        id2 = generate_delivery_id("request_xyz", "transporter_001")
        assert id1 == id2, "Delivery ID must be deterministic (same inputs → same output)"

    def test_deterministic_stability_multiple_calls(self) -> None:
        """Delivery ID is stable across many calls with same inputs."""
        ids = [generate_delivery_id("req_123", "trans_456") for _ in range(5)]
        assert all(id == ids[0] for id in ids), "Delivery ID must be stable across calls"

    def test_different_inputs_produce_different_ids(self) -> None:
        """Different inputs produce different delivery IDs."""
        id1 = generate_delivery_id("request_1", "transporter_A")
        id2 = generate_delivery_id("request_2", "transporter_A")
        id3 = generate_delivery_id("request_1", "transporter_B")
        assert id1 != id2, "Different request_id should produce different IDs"
        assert id1 != id3, "Different transporter_id should produce different IDs"
        assert id2 != id3, "Different inputs should produce different IDs"

    def test_empty_string_inputs(self) -> None:
        """Empty strings are handled and produce valid UUIDs."""
        delivery_id = generate_delivery_id("", "")
        assert isinstance(delivery_id, str)
        assert UUID_PATTERN.match(delivery_id)
        UUID(delivery_id)

    def test_special_characters_in_inputs(self) -> None:
        """Special characters in inputs are handled safely."""
        delivery_id = generate_delivery_id("request@#$%^&*()", "transporter_!<>?/\\")
        assert isinstance(delivery_id, str)
        assert UUID_PATTERN.match(delivery_id)
        UUID(delivery_id)

    def test_long_input_strings(self) -> None:
        """Very long input strings are handled."""
        long_request = "r" * 10000
        long_transporter = "t" * 10000
        delivery_id = generate_delivery_id(long_request, long_transporter)
        assert isinstance(delivery_id, str)
        assert UUID_PATTERN.match(delivery_id)
        UUID(delivery_id)


class TestIdConsistency:
    """Test consistency across different ID generation functions."""

    def test_session_ids_differ_from_request_ids(self) -> None:
        """Session IDs and request IDs are independent."""
        session_ids = {generate_session_id() for _ in range(3)}
        request_ids = {generate_request_id(f"intent_{i}", f"receiver_{i}") for i in range(3)}
        assert session_ids.isdisjoint(request_ids)

    def test_request_ids_differ_from_delivery_ids(self) -> None:
        """Request IDs and delivery IDs are independent."""
        id1 = generate_request_id("intent", "receiver")
        id2 = generate_delivery_id("request_base", "transporter")
        assert id1 != id2


class TestEnduringAgentId:
    """Test stable enduring Agent ID generation."""

    def test_returns_string(self) -> None:
        """Agent ID is returned as a string."""
        agent_id = enduring_agent_id("sender@example.com")
        assert isinstance(agent_id, str)

    def test_has_agent_prefix(self) -> None:
        """Agent ID has ag- prefix."""
        agent_id = enduring_agent_id("sender@example.com")
        assert agent_id.startswith("ag-"), f"Agent ID must start with 'ag-': {agent_id}"

    def test_contains_valid_uuid(self) -> None:
        """Agent ID contains valid UUID after ag- prefix."""
        agent_id = enduring_agent_id("sender@example.com")
        uuid_part = agent_id[3:]  # Remove "ag-" prefix
        assert UUID_PATTERN.match(uuid_part), f"Invalid UUID after prefix: {uuid_part}"
        UUID(uuid_part)

    def test_deterministic_same_identifier(self) -> None:
        """Same identifier produces same Agent ID (deterministic)."""
        id1 = enduring_agent_id("stable_sender_123")
        id2 = enduring_agent_id("stable_sender_123")
        assert id1 == id2, "Agent ID must be deterministic (same input → same output)"

    def test_different_identifiers_produce_different_ids(self) -> None:
        """Different identifiers produce different Agent IDs."""
        id1 = enduring_agent_id("sender_A")
        id2 = enduring_agent_id("sender_B")
        assert id1 != id2, "Different identifiers must produce different Agent IDs"

    def test_stability_across_multiple_calls(self) -> None:
        """Agent ID is stable across many calls with same identifier."""
        ids = [enduring_agent_id("persistent_identifier") for _ in range(5)]
        assert all(id == ids[0] for id in ids), "Agent ID must be stable across calls"


class TestNewGraphIdentifiers:
    """Test sparse allocation of graph node identifiers."""

    def test_returns_graph_identifiers_model(self) -> None:
        """new_graph_identifiers returns a GraphIdentifiers instance."""
        identifiers = new_graph_identifiers(
            actor_id="sender_123",
            receiver_stable_id=None,
        )
        assert isinstance(identifiers, GraphIdentifiers)

    def test_request_id_always_allocated(self) -> None:
        """Request ID is always allocated with req- prefix."""
        identifiers = new_graph_identifiers(
            actor_id="sender_123",
            receiver_stable_id=None,
        )
        assert identifiers.request_id is not None
        assert identifiers.request_id.startswith("req-")

    def test_sender_always_allocated(self) -> None:
        """Sender role ID and enduring agent ID are always allocated."""
        identifiers = new_graph_identifiers(
            actor_id="sender@example.com",
            receiver_stable_id=None,
        )
        assert identifiers.sender_id is not None
        assert identifiers.sender_id.startswith("s-")
        assert identifiers.sender_agent_id is not None
        assert identifiers.sender_agent_id.startswith("ag-")

    def test_sparse_allocation_receiver(self) -> None:
        """Receiver IDs only allocated when include_receiver=True."""
        # Without receiver
        ids_no_receiver = new_graph_identifiers(
            actor_id="sender_123",
            receiver_stable_id="receiver_456",
            include_receiver=False,
        )
        assert ids_no_receiver.receiver_id is None
        assert ids_no_receiver.receiver_agent_id is None
        assert ids_no_receiver.receiver_agent_identifier is None

        # With receiver
        ids_with_receiver = new_graph_identifiers(
            actor_id="sender_123",
            receiver_stable_id="receiver_456",
            include_receiver=True,
        )
        assert ids_with_receiver.receiver_id is not None
        assert ids_with_receiver.receiver_id.startswith("r-")
        assert ids_with_receiver.receiver_agent_id is not None
        assert ids_with_receiver.receiver_agent_id.startswith("ag-")

    def test_sparse_allocation_parcel(self) -> None:
        """Parcel ID only allocated when include_parcel=True."""
        # Without parcel
        ids_no_parcel = new_graph_identifiers(
            actor_id="sender_123",
            receiver_stable_id=None,
            include_parcel=False,
        )
        assert ids_no_parcel.parcel_id is None

        # With parcel
        ids_with_parcel = new_graph_identifiers(
            actor_id="sender_123",
            receiver_stable_id=None,
            include_parcel=True,
        )
        assert ids_with_parcel.parcel_id is not None
        assert ids_with_parcel.parcel_id.startswith("p-")

    def test_sparse_allocation_pickup_place(self) -> None:
        """Pickup place IDs only allocated when include_pickup=True."""
        # Without pickup
        ids_no_pickup = new_graph_identifiers(
            actor_id="sender_123",
            receiver_stable_id=None,
            include_pickup=False,
        )
        assert ids_no_pickup.pickup_place_id is None
        assert ids_no_pickup.pickup_place_identifier is None

        # With pickup
        ids_with_pickup = new_graph_identifiers(
            actor_id="sender_123",
            receiver_stable_id=None,
            include_pickup=True,
        )
        assert ids_with_pickup.pickup_place_id is not None
        assert ids_with_pickup.pickup_place_id.startswith("pl-")
        assert ids_with_pickup.pickup_place_identifier is not None
        assert ids_with_pickup.pickup_place_identifier.startswith("urn:uuid:")

    def test_sparse_allocation_drop_off_place(self) -> None:
        """Drop-off place IDs only allocated when include_drop_off=True."""
        # Without drop-off
        ids_no_drop = new_graph_identifiers(
            actor_id="sender_123",
            receiver_stable_id=None,
            include_drop_off=False,
        )
        assert ids_no_drop.drop_off_place_id is None
        assert ids_no_drop.drop_off_place_identifier is None

        # With drop-off
        ids_with_drop = new_graph_identifiers(
            actor_id="sender_123",
            receiver_stable_id=None,
            include_drop_off=True,
        )
        assert ids_with_drop.drop_off_place_id is not None
        assert ids_with_drop.drop_off_place_id.startswith("pl-")
        assert ids_with_drop.drop_off_place_identifier is not None
        assert ids_with_drop.drop_off_place_identifier.startswith("urn:uuid:")

    def test_receiver_fallback_name_only(self) -> None:
        """Name-only receiver (no stable_id) gets request-scoped URN."""
        identifiers = new_graph_identifiers(
            actor_id="sender_123",
            receiver_stable_id=None,
            include_receiver=True,
        )
        # Should have receiver role ID but no enduring agent ID
        assert identifiers.receiver_id is not None
        assert identifiers.receiver_id.startswith("r-")
        assert identifiers.receiver_agent_id is None
        # Fallback: receiver_agent_identifier should be request-scoped URN
        assert identifiers.receiver_agent_identifier is not None
        assert identifiers.receiver_agent_identifier.startswith("urn:hulubul:phase1:receiver:")

    def test_receiver_with_stable_id(self) -> None:
        """Receiver with stable_id gets enduring agent ID."""
        identifiers = new_graph_identifiers(
            actor_id="sender_123",
            receiver_stable_id="receiver@example.com",
            include_receiver=True,
        )
        assert identifiers.receiver_id is not None
        assert identifiers.receiver_agent_id is not None
        assert identifiers.receiver_agent_id.startswith("ag-")
        assert identifiers.receiver_agent_identifier == "receiver@example.com"

    def test_deterministic_with_injected_uuid_factory(self) -> None:
        """Allocation is deterministic when uuid_factory is controlled."""
        call_count = [0]

        def deterministic_uuid() -> str:
            call_count[0] += 1
            return f"uuid-{call_count[0]}"

        ids1 = new_graph_identifiers(
            actor_id="sender_123",
            receiver_stable_id=None,
            include_receiver=True,
            include_parcel=True,
            include_pickup=True,
            include_drop_off=True,
            uuid_factory=deterministic_uuid,
        )

        # Reset and generate again
        call_count[0] = 0
        ids2 = new_graph_identifiers(
            actor_id="sender_123",
            receiver_stable_id=None,
            include_receiver=True,
            include_parcel=True,
            include_pickup=True,
            include_drop_off=True,
            uuid_factory=deterministic_uuid,
        )

        # IDs should match (same allocation order, same uuid values)
        assert ids1.request_id == ids2.request_id
        assert ids1.sender_id == ids2.sender_id
        assert ids1.receiver_id == ids2.receiver_id
        assert ids1.parcel_id == ids2.parcel_id
        assert ids1.pickup_place_id == ids2.pickup_place_id
        assert ids1.drop_off_place_id == ids2.drop_off_place_id

    @pytest.mark.parametrize(
        "include_receiver,include_parcel,include_pickup,include_drop_off",
        [
            (False, False, False, False),  # Minimal: request + sender only
            (True, False, False, False),  # With receiver
            (False, True, False, False),  # With parcel
            (False, False, True, False),  # With pickup
            (False, False, False, True),  # With drop-off
            (True, True, True, True),  # Full: all entities
        ],
    )
    def test_sparse_combinations(
        self,
        include_receiver: bool,
        include_parcel: bool,
        include_pickup: bool,
        include_drop_off: bool,
    ) -> None:
        """Test various sparse allocation combinations."""
        identifiers = new_graph_identifiers(
            actor_id="sender_123",
            receiver_stable_id="receiver_456" if include_receiver else None,
            include_receiver=include_receiver,
            include_parcel=include_parcel,
            include_pickup=include_pickup,
            include_drop_off=include_drop_off,
        )

        # Always present
        assert identifiers.request_id is not None
        assert identifiers.sender_id is not None
        assert identifiers.sender_agent_id is not None

        # Conditionally present
        assert (identifiers.receiver_id is not None) == include_receiver
        assert (identifiers.parcel_id is not None) == include_parcel
        assert (identifiers.pickup_place_id is not None) == include_pickup
        assert (identifiers.drop_off_place_id is not None) == include_drop_off
