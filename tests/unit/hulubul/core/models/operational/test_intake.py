"""Unit tests for intake facts and results contracts.

Tests sparse/complete fact contradictions, field boundaries,
and result outcome validation invariants per the plan (2.3).
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import pytest
from pydantic import ValidationError

from hulubul.core.models.operational.intake import (
    CompleteIntakeFacts,
    GraphIdentifiers,
    IntakeFacts,
    IntakeFactUpdates,
    IntakeResult,
)
from hulubul.core.models.operational.enums import IntakeOutcome


# ============================================================================
# SPARSE FACTS TESTS (new, needsClarification states)
# ============================================================================


class TestIntakeFactsSparseBoundaries:
    """Test that sparse IntakeFacts enforces 1-4000 boundary on human text."""

    @pytest.mark.parametrize(
        "field_name,empty_value",
        [
            ("receiver_name", ""),
            ("pickup_location", ""),
            ("drop_off_location", ""),
            ("parcel_declared_content", ""),
        ],
    )
    def test_human_text_rejects_empty_string(self, field_name, empty_value):
        """Human-supplied text fields must reject empty strings (1-char minimum)."""
        with pytest.raises(ValidationError, match="at least 1 character"):
            IntakeFacts(
                sender_actor_id="urn:actor:alice",
                **{field_name: empty_value}
            )

    @pytest.mark.parametrize(
        "field_name",
        [
            "receiver_name",
            "pickup_location",
            "drop_off_location",
            "parcel_declared_content",
        ],
    )
    def test_human_text_accepts_1_character(self, field_name):
        """Human-supplied text fields must accept 1 character."""
        facts = IntakeFacts(
            sender_actor_id="urn:actor:alice",
            **{field_name: "x"}
        )
        assert getattr(facts, field_name) == "x"

    @pytest.mark.parametrize(
        "field_name",
        [
            "receiver_name",
            "pickup_location",
            "drop_off_location",
            "parcel_declared_content",
        ],
    )
    def test_human_text_accepts_4000_characters(self, field_name):
        """Human-supplied text fields must accept 4000 characters."""
        facts = IntakeFacts(
            sender_actor_id="urn:actor:alice",
            **{field_name: "x" * 4000}
        )
        assert len(getattr(facts, field_name)) == 4000

    @pytest.mark.parametrize(
        "field_name",
        [
            "receiver_name",
            "pickup_location",
            "drop_off_location",
            "parcel_declared_content",
        ],
    )
    def test_human_text_rejects_4001_characters(self, field_name):
        """Human-supplied text fields must reject 4001+ characters."""
        with pytest.raises(ValidationError, match="at most 4000"):
            IntakeFacts(
                sender_actor_id="urn:actor:alice",
                **{field_name: "x" * 4001}
            )

    def test_preferred_period_is_always_optional(self):
        """preferred_period is text but always optional (no required case)."""
        facts = IntakeFacts(sender_actor_id="urn:actor:alice")
        assert facts.preferred_period is None

    def test_preferred_period_accepts_4000_characters(self):
        """preferred_period also subject to 1-4000 when present."""
        facts = IntakeFacts(
            sender_actor_id="urn:actor:alice",
            preferred_period="x" * 4000
        )
        assert len(facts.preferred_period) == 4000


class TestIntakeFactsReceiverIdentity:
    """Test receiver identity contract: both allowed, one required for complete state."""

    def test_receiver_name_only_allowed(self):
        """Sparse facts allow receiver_name without receiver_stable_id."""
        facts = IntakeFacts(
            sender_actor_id="urn:actor:alice",
            receiver_name="Bob Smith"
        )
        assert facts.receiver_name == "Bob Smith"
        assert facts.receiver_stable_id is None

    def test_receiver_stable_id_only_allowed(self):
        """Sparse facts allow receiver_stable_id without receiver_name."""
        facts = IntakeFacts(
            sender_actor_id="urn:actor:alice",
            receiver_stable_id="stable-bob-123"
        )
        assert facts.receiver_stable_id == "stable-bob-123"
        assert facts.receiver_name is None

    def test_both_receiver_fields_allowed_in_sparse_facts(self):
        """Sparse facts allow both receiver_name and receiver_stable_id."""
        facts = IntakeFacts(
            sender_actor_id="urn:actor:alice",
            receiver_name="Bob Smith",
            receiver_stable_id="stable-bob-123"
        )
        assert facts.receiver_name == "Bob Smith"
        assert facts.receiver_stable_id == "stable-bob-123"

    def test_sparse_facts_with_no_receiver_identity(self):
        """Sparse facts allow neither receiver field (for incomplete intake)."""
        facts = IntakeFacts(sender_actor_id="urn:actor:alice")
        assert facts.receiver_name is None
        assert facts.receiver_stable_id is None


class TestIntakeFactsSenderIdentity:
    """Test sender field contracts."""

    def test_sender_actor_id_required(self):
        """sender_actor_id is always required (from chain identity)."""
        with pytest.raises(ValidationError, match="sender_actor_id"):
            IntakeFacts()

    def test_sender_actor_id_as_urn(self):
        """sender_actor_id stored and returned as-is (URN pattern)."""
        facts = IntakeFacts(sender_actor_id="urn:actor:alice:12345")
        assert facts.sender_actor_id == "urn:actor:alice:12345"

    def test_sender_display_name_optional(self):
        """sender_display_name is optional (sparse intake allows omission)."""
        facts = IntakeFacts(sender_actor_id="urn:actor:alice")
        assert facts.sender_display_name is None


# ============================================================================
# INTAKE FACT UPDATES TESTS
# ============================================================================


class TestIntakeFactUpdates:
    """Test IntakeFactUpdates rejects empty updates."""

    def test_empty_updates_rejected(self):
        """IntakeFactUpdates must reject all-None update dict."""
        with pytest.raises(ValidationError, match="At least one field"):
            IntakeFactUpdates()

    def test_updates_with_at_least_one_field(self):
        """IntakeFactUpdates accepts partial field updates."""
        updates = IntakeFactUpdates(receiver_name="Bob Smith")
        assert updates.receiver_name == "Bob Smith"


# ============================================================================
# COMPLETE INTAKE FACTS TESTS (complete state)
# ============================================================================


class TestCompleteIntakeFacts:
    """Test that complete facts enforce all four required fields."""

    def test_complete_facts_requires_all_four_required_fields(self):
        """Complete facts require: sender_actor_id, receiver_name or receiver_stable_id, pickup_location, drop_off_location."""
        with pytest.raises(ValidationError):
            CompleteIntakeFacts(
                sender_actor_id="urn:actor:alice",
                pickup_location="123 Main St",
                # missing receiver identity and drop_off
            )

    def test_complete_facts_with_all_required_fields(self):
        """Complete facts accepts all four required fields."""
        facts = CompleteIntakeFacts(
            sender_actor_id="urn:actor:alice",
            receiver_name="Bob Smith",
            pickup_location="123 Main St",
            drop_off_location="456 Oak Ave"
        )
        assert facts.sender_actor_id == "urn:actor:alice"
        assert facts.receiver_name == "Bob Smith"
        assert facts.pickup_location == "123 Main St"
        assert facts.drop_off_location == "456 Oak Ave"

    def test_complete_facts_with_receiver_stable_id_instead_of_name(self):
        """Complete facts accept receiver_stable_id instead of receiver_name."""
        facts = CompleteIntakeFacts(
            sender_actor_id="urn:actor:alice",
            receiver_stable_id="stable-bob-123",
            pickup_location="123 Main St",
            drop_off_location="456 Oak Ave"
        )
        assert facts.receiver_stable_id == "stable-bob-123"


# ============================================================================
# INTAKE RESULT TESTS
# ============================================================================


class TestIntakeResultOutcome:
    """Test IntakeResult outcome and state invariants."""

    def test_intake_result_requestcomplete_outcome(self):
        """IntakeResult with requestComplete outcome carries request and status."""
        result = IntakeResult(
            outcome=IntakeOutcome.REQUEST_COMPLETE,
            request_id="req-123",
            status="new",
            facts=IntakeFacts(sender_actor_id="urn:actor:alice"),
            missing_fields=("receiver_name", "pickup_location"),
            safe_user_message="Please provide receiver details"
        )
        assert result.outcome == IntakeOutcome.REQUEST_COMPLETE
        assert result.request_id == "req-123"
        assert result.status == "new"

    def test_intake_result_clarification_outcome(self):
        """IntakeResult with clarificationRequired outcome specifies one clarification field."""
        result = IntakeResult(
            outcome=IntakeOutcome.CLARIFICATION_REQUIRED,
            request_id="req-123",
            status="needsClarification",
            facts=IntakeFacts(sender_actor_id="urn:actor:alice"),
            missing_fields=("receiver_name",),
            clarification_field="receiver_name",
            safe_user_message="Please confirm receiver name"
        )
        assert result.outcome == IntakeOutcome.CLARIFICATION_REQUIRED
        assert result.clarification_field == "receiver_name"

    def test_intake_result_failure_outcome(self):
        """IntakeResult with failure outcome carries error message."""
        result = IntakeResult(
            outcome=IntakeOutcome.FAILURE,
            error="Invalid sender_actor_id format"
        )
        assert result.outcome == IntakeOutcome.FAILURE
        assert result.error == "Invalid sender_actor_id format"


class TestIntakeResultMissingFields:
    """Test missing_fields tuple invariants in results."""

    def test_result_missing_fields_locked_tuple(self):
        """Result missing_fields is immutable tuple, never list."""
        result = IntakeResult(
            outcome=IntakeOutcome.REQUEST_COMPLETE,
            request_id="req-123",
            missing_fields=("receiver_name", "pickup_location"),
            facts=IntakeFacts(sender_actor_id="urn:actor:alice"),
        )
        assert isinstance(result.missing_fields, tuple)
        assert result.missing_fields == ("receiver_name", "pickup_location")
