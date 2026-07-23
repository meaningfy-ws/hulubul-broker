"""Tests for graph identifier generation service.

Tests cover:
- Session ID generation (random UUID4, unique per call)
- Request ID generation (deterministic UUID5, same inputs -> same output)
- Delivery ID generation (deterministic UUID5, same inputs -> same output)
- All outputs are valid UUID strings
- Edge cases (empty strings, special characters)
"""

import re
from uuid import UUID

import pytest

from hulubul.request_intake.services.graph_identifiers import (
    generate_delivery_id,
    generate_request_id,
    generate_session_id,
)


# Valid UUID v4 or v5 string pattern (36 chars: 8-4-4-4-12 hex digits + hyphens)
UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE
)


class TestGenerateSessionId:
    """Test random session ID generation (UUID4)."""

    def test_returns_string(self):
        """Session ID is returned as a string."""
        session_id = generate_session_id()
        assert isinstance(session_id, str)

    def test_valid_uuid_format(self):
        """Session ID is a valid UUID string format."""
        session_id = generate_session_id()
        assert UUID_PATTERN.match(session_id), f"Invalid UUID format: {session_id}"
        # Verify it can be parsed as a UUID
        UUID(session_id)

    def test_uniqueness_on_multiple_calls(self):
        """Multiple calls to generate_session_id produce unique UUIDs."""
        ids = {generate_session_id() for _ in range(10)}
        assert len(ids) == 10, "Session IDs must be unique across calls"

    def test_multiple_calls_produce_different_results(self):
        """Specifically test that two consecutive calls differ."""
        id1 = generate_session_id()
        id2 = generate_session_id()
        assert id1 != id2, "Session IDs must be different on each call"


class TestGenerateRequestId:
    """Test deterministic request ID generation (UUID5)."""

    def test_returns_string(self):
        """Request ID is returned as a string."""
        request_id = generate_request_id("intent_value", "receiver_123")
        assert isinstance(request_id, str)

    def test_valid_uuid_format(self):
        """Request ID is a valid UUID string format."""
        request_id = generate_request_id("intent_value", "receiver_123")
        assert UUID_PATTERN.match(request_id), f"Invalid UUID format: {request_id}"
        # Verify it can be parsed as a UUID
        UUID(request_id)

    def test_deterministic_same_inputs(self):
        """Identical inputs produce identical request IDs."""
        id1 = generate_request_id("intent_value", "receiver_123")
        id2 = generate_request_id("intent_value", "receiver_123")
        assert id1 == id2, "Request ID must be deterministic (same inputs -> same output)"

    def test_deterministic_stability_multiple_calls(self):
        """Request ID is stable across many calls with same inputs."""
        ids = [
            generate_request_id("test_intent", "receiver_456")
            for _ in range(5)
        ]
        assert all(id == ids[0] for id in ids), "Request ID must be stable across calls"

    def test_different_inputs_produce_different_ids(self):
        """Different inputs produce different request IDs."""
        id1 = generate_request_id("intent_1", "receiver_A")
        id2 = generate_request_id("intent_2", "receiver_A")
        id3 = generate_request_id("intent_1", "receiver_B")
        assert id1 != id2, "Different parcel_intent should produce different IDs"
        assert id1 != id3, "Different receiver_id should produce different IDs"
        assert id2 != id3, "Different inputs should produce different IDs"

    def test_empty_string_inputs(self):
        """Empty strings are handled and produce valid UUIDs."""
        request_id = generate_request_id("", "")
        assert isinstance(request_id, str)
        assert UUID_PATTERN.match(request_id)
        UUID(request_id)

    def test_special_characters_in_inputs(self):
        """Special characters in inputs are handled safely."""
        request_id = generate_request_id(
            "intent@#$%^&*()", "receiver_!<>?/\\"
        )
        assert isinstance(request_id, str)
        assert UUID_PATTERN.match(request_id)
        UUID(request_id)

    def test_long_input_strings(self):
        """Very long input strings are handled."""
        long_intent = "x" * 10000
        long_receiver = "y" * 10000
        request_id = generate_request_id(long_intent, long_receiver)
        assert isinstance(request_id, str)
        assert UUID_PATTERN.match(request_id)
        UUID(request_id)


class TestGenerateDeliveryId:
    """Test deterministic delivery ID generation (UUID5)."""

    def test_returns_string(self):
        """Delivery ID is returned as a string."""
        delivery_id = generate_delivery_id("request_id_value", "transporter_123")
        assert isinstance(delivery_id, str)

    def test_valid_uuid_format(self):
        """Delivery ID is a valid UUID string format."""
        delivery_id = generate_delivery_id("request_id_value", "transporter_123")
        assert UUID_PATTERN.match(delivery_id), f"Invalid UUID format: {delivery_id}"
        # Verify it can be parsed as a UUID
        UUID(delivery_id)

    def test_deterministic_same_inputs(self):
        """Identical inputs produce identical delivery IDs."""
        id1 = generate_delivery_id("request_xyz", "transporter_001")
        id2 = generate_delivery_id("request_xyz", "transporter_001")
        assert id1 == id2, "Delivery ID must be deterministic (same inputs -> same output)"

    def test_deterministic_stability_multiple_calls(self):
        """Delivery ID is stable across many calls with same inputs."""
        ids = [
            generate_delivery_id("req_123", "trans_456")
            for _ in range(5)
        ]
        assert all(id == ids[0] for id in ids), "Delivery ID must be stable across calls"

    def test_different_inputs_produce_different_ids(self):
        """Different inputs produce different delivery IDs."""
        id1 = generate_delivery_id("request_1", "transporter_A")
        id2 = generate_delivery_id("request_2", "transporter_A")
        id3 = generate_delivery_id("request_1", "transporter_B")
        assert id1 != id2, "Different request_id should produce different IDs"
        assert id1 != id3, "Different transporter_id should produce different IDs"
        assert id2 != id3, "Different inputs should produce different IDs"

    def test_empty_string_inputs(self):
        """Empty strings are handled and produce valid UUIDs."""
        delivery_id = generate_delivery_id("", "")
        assert isinstance(delivery_id, str)
        assert UUID_PATTERN.match(delivery_id)
        UUID(delivery_id)

    def test_special_characters_in_inputs(self):
        """Special characters in inputs are handled safely."""
        delivery_id = generate_delivery_id(
            "request@#$%^&*()", "transporter_!<>?/\\"
        )
        assert isinstance(delivery_id, str)
        assert UUID_PATTERN.match(delivery_id)
        UUID(delivery_id)

    def test_long_input_strings(self):
        """Very long input strings are handled."""
        long_request = "r" * 10000
        long_transporter = "t" * 10000
        delivery_id = generate_delivery_id(long_request, long_transporter)
        assert isinstance(delivery_id, str)
        assert UUID_PATTERN.match(delivery_id)
        UUID(delivery_id)


class TestIdConsistency:
    """Test consistency across different ID generation functions."""

    def test_session_ids_differ_from_request_ids(self):
        """Session IDs and request IDs are independent."""
        # Generate multiple session and request IDs
        session_ids = {generate_session_id() for _ in range(3)}
        request_ids = {generate_request_id(f"intent_{i}", f"receiver_{i}") for i in range(3)}
        # No overlap between session and request ID sets
        assert session_ids.isdisjoint(request_ids)

    def test_request_ids_differ_from_delivery_ids(self):
        """Request IDs and delivery IDs are independent."""
        # Use the same base string to generate both
        request_id = generate_request_id("base", "input")
        delivery_id = generate_delivery_id("base", "input")
        # Different semantics should produce different UUIDs
        assert request_id != delivery_id
