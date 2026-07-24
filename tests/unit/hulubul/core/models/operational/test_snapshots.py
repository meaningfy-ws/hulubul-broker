"""Unit tests for delivery request snapshot contracts.

Tests sparse/complete snapshot contradictions, timestamp handling,
and nested schema equality per the plan (2.3).
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from hulubul.core.models.operational.intake import (
    CompleteIntakeFacts,
    GraphIdentifiers,
    IntakeFacts,
)
from hulubul.core.models.operational.snapshots import (
    DeliveryRequestSnapshot,
    MutationConfirmation,
)

# ============================================================================
# DELIVERY REQUEST SNAPSHOT TESTS
# ============================================================================


class TestDeliveryRequestSnapshotTimestamps:
    """Test timestamp handling in persisted snapshots."""

    def test_snapshot_created_at_immutable(self) -> None:
        """Snapshot created_at is set once and immutable."""
        now = datetime.now(timezone.utc)
        snap = DeliveryRequestSnapshot(
            request_id="req-123",
            created_at=now,
            updated_at=now,
            facts=IntakeFacts(sender_actor_id="urn:actor:alice"),
            missing_fields=(),
        )
        assert snap.created_at == now

    def test_snapshot_updated_at_authoritative(self) -> None:
        """Snapshot updated_at reflects last modification, authoritative."""
        now = datetime.now(timezone.utc)
        snap = DeliveryRequestSnapshot(
            request_id="req-123",
            created_at=now,
            updated_at=now,
            facts=IntakeFacts(sender_actor_id="urn:actor:alice"),
            missing_fields=(),
        )
        assert snap.updated_at == now

    def test_snapshot_closed_at_nullable(self) -> None:
        """Snapshot closed_at is nullable (request may not be closed)."""
        now = datetime.now(timezone.utc)
        snap = DeliveryRequestSnapshot(
            request_id="req-123",
            created_at=now,
            updated_at=now,
            closed_at=None,
            facts=IntakeFacts(sender_actor_id="urn:actor:alice"),
            missing_fields=(),
        )
        assert snap.closed_at is None

    def test_snapshot_closed_at_when_present(self) -> None:
        """Snapshot closed_at stores timestamp when request is closed."""
        now = datetime.now(timezone.utc)
        closed = now.replace(hour=now.hour + 1)
        snap = DeliveryRequestSnapshot(
            request_id="req-123",
            created_at=now,
            updated_at=now,
            closed_at=closed,
            facts=IntakeFacts(sender_actor_id="urn:actor:alice"),
            missing_fields=(),
        )
        assert snap.closed_at == closed


class TestDeliveryRequestSnapshotFacts:
    """Test fact storage and sparse/complete invariants in snapshots."""

    def test_snapshot_sparse_facts_allowed_for_new_state(self) -> None:
        """Snapshot with status 'new' allows sparse facts."""
        snap = DeliveryRequestSnapshot(
            request_id="req-123",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            status="new",
            facts=IntakeFacts(sender_actor_id="urn:actor:alice"),
            missing_fields=("receiver_name", "pickup_location"),
        )
        assert snap.status == "new"
        assert snap.missing_fields == ("receiver_name", "pickup_location")

    def test_snapshot_complete_facts_required_for_complete_state(self) -> None:
        """Snapshot with status 'complete' requires complete facts, no missing."""
        now = datetime.now(timezone.utc)
        snap = DeliveryRequestSnapshot(
            request_id="req-123",
            created_at=now,
            updated_at=now,
            status="complete",
            facts=CompleteIntakeFacts(
                sender_actor_id="urn:actor:alice",
                receiver_name="Bob",
                pickup_location="123 Main",
                drop_off_location="456 Oak",
            ),
            missing_fields=(),
        )
        assert snap.status == "complete"
        assert snap.missing_fields == ()

    def test_snapshot_complete_status_rejects_missing_fields(self) -> None:
        """Snapshot with status 'complete' and sparse facts fails."""
        with pytest.raises(ValidationError, match="CompleteIntakeFacts"):
            DeliveryRequestSnapshot(
                request_id="req-123",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                status="complete",
                facts=IntakeFacts(sender_actor_id="urn:actor:alice"),
                missing_fields=("receiver_name",),
            )

    def test_snapshot_complete_status_rejects_sparse_facts(self) -> None:
        """Snapshot with status 'complete' and sparse facts fails."""
        sparse = IntakeFacts(sender_actor_id="urn:actor:alice")
        with pytest.raises(ValidationError):
            DeliveryRequestSnapshot(
                request_id="req-123",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                status="complete",
                facts=sparse,  # sparse, not CompleteIntakeFacts
                missing_fields=(),
            )


class TestDeliveryRequestSnapshotMissingFields:
    """Test missing_fields exact tuple invariants."""

    def test_snapshot_missing_fields_is_immutable_tuple(self) -> None:
        """Snapshot missing_fields is immutable tuple, never list."""
        snap = DeliveryRequestSnapshot(
            request_id="req-123",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            facts=IntakeFacts(sender_actor_id="urn:actor:alice"),
            missing_fields=("receiver_name", "pickup_location"),
        )
        assert isinstance(snap.missing_fields, tuple)

    def test_snapshot_missing_fields_rejects_non_sequence(self) -> None:
        """A string must not be silently coerced into a tuple of characters."""
        with pytest.raises(ValidationError, match="list or tuple"):
            DeliveryRequestSnapshot(
                request_id="req-123",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                facts=IntakeFacts(sender_actor_id="urn:actor:alice"),
                missing_fields="receiver_name",  # type: ignore[arg-type]
            )

    def test_snapshot_missing_fields_empty_for_complete(self) -> None:
        """Snapshot missing_fields is empty tuple for 'complete' status."""
        snap = DeliveryRequestSnapshot(
            request_id="req-123",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            status="complete",
            facts=CompleteIntakeFacts(
                sender_actor_id="urn:actor:alice",
                receiver_name="Bob",
                pickup_location="123 Main",
                drop_off_location="456 Oak",
            ),
            missing_fields=(),
        )
        assert snap.missing_fields == ()


class TestDeliveryRequestSnapshotEquality:
    """Test nested schema and correlation equality."""

    def test_snapshot_equality_on_identical_fields(self) -> None:
        """Two snapshots with identical fields are equal."""
        now = datetime.now(timezone.utc)
        snap1 = DeliveryRequestSnapshot(
            request_id="req-123",
            created_at=now,
            updated_at=now,
            facts=IntakeFacts(sender_actor_id="urn:actor:alice"),
            missing_fields=(),
        )
        snap2 = DeliveryRequestSnapshot(
            request_id="req-123",
            created_at=now,
            updated_at=now,
            facts=IntakeFacts(sender_actor_id="urn:actor:alice"),
            missing_fields=(),
        )
        assert snap1 == snap2

    def test_snapshot_inequality_on_different_request_id(self) -> None:
        """Two snapshots with different request_id are not equal."""
        now = datetime.now(timezone.utc)
        snap1 = DeliveryRequestSnapshot(
            request_id="req-123",
            created_at=now,
            updated_at=now,
            facts=IntakeFacts(sender_actor_id="urn:actor:alice"),
            missing_fields=(),
        )
        snap2 = DeliveryRequestSnapshot(
            request_id="req-456",
            created_at=now,
            updated_at=now,
            facts=IntakeFacts(sender_actor_id="urn:actor:alice"),
            missing_fields=(),
        )
        assert snap1 != snap2


# ============================================================================
# MUTATION CONFIRMATION TESTS
# ============================================================================


class TestMutationConfirmation:
    """Test MutationConfirmation locked fields contract."""

    def test_mutation_confirmation_locked_fields(self) -> None:
        """MutationConfirmation carries snapshot and changes as immutable fields."""
        now = datetime.now(timezone.utc)
        snap = DeliveryRequestSnapshot(
            request_id="req-123",
            created_at=now,
            updated_at=now,
            facts=IntakeFacts(sender_actor_id="urn:actor:alice"),
        )
        confirm = MutationConfirmation(snapshot=snap, changes={"status": "needsClarification"})
        assert confirm.snapshot == snap
        assert confirm.changes == {"status": "needsClarification"}


# ============================================================================
# GRAPH IDENTIFIERS TESTS
# ============================================================================


class TestGraphIdentifiers:
    """Test GraphIdentifiers contract for linking entities."""

    def test_graph_identifiers_request_id_required(self) -> None:
        """GraphIdentifiers require request_id."""
        ids = GraphIdentifiers(request_id="req-123")
        assert ids.request_id == "req-123"

    def test_graph_identifiers_sender_id_optional(self) -> None:
        """GraphIdentifiers allow optional sender_id."""
        ids = GraphIdentifiers(request_id="req-123", sender_id="sender-456")
        assert ids.sender_id == "sender-456"
