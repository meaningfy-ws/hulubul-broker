"""Unit tests for the deterministic intake completeness policy.

Tests the fixed missing-field order, single-clarification-field selection
(including invalid-field priority), and complete-facts validation per plan
Task 10 (original task ID 3.1).
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from hulubul.core.models.operational.enums import IntakeField
from hulubul.core.models.operational.intake import CompleteIntakeFacts, IntakeFacts
from hulubul.request_intake.models.completeness import (
    REQUIRED_INTAKE_FIELDS,
    missing_required_fields,
    select_clarification_field,
    validate_complete_facts,
)


def sender_only_facts() -> IntakeFacts:
    """Sparse facts with only the always-present Sender identity."""
    return IntakeFacts(sender_actor_id="urn:actor:alice")


def complete_facts(*, preferred_period: str | None = None) -> IntakeFacts:
    """Sparse facts satisfying every required field (period optional)."""
    return IntakeFacts(
        sender_actor_id="urn:actor:alice",
        receiver_name="Bob",
        pickup_location="123 Main St",
        drop_off_location="456 Oak Ave",
        parcel_declared_content="Books",
        preferred_period=preferred_period,
    )


# ============================================================================
# REQUIRED_INTAKE_FIELDS
# ============================================================================


class TestRequiredIntakeFields:
    """The required-field tuple is fixed, ordered, and excludes preferred_period."""

    def test_fixed_order_is_receiver_pickup_dropoff_content(self) -> None:
        assert REQUIRED_INTAKE_FIELDS == (
            IntakeField.RECEIVER_IDENTITY,
            IntakeField.PICKUP_LOCATION,
            IntakeField.DROP_OFF_LOCATION,
            IntakeField.PARCEL_DECLARED_CONTENT,
        )

    def test_preferred_period_is_never_required(self) -> None:
        assert IntakeField.PREFERRED_PERIOD not in REQUIRED_INTAKE_FIELDS


# ============================================================================
# missing_required_fields
# ============================================================================


class TestMissingRequiredFields:
    """Missing-field detection respects the fixed order and receiver OR logic."""

    def test_zero_field_facts_report_every_required_field_in_order(self) -> None:
        assert missing_required_fields(sender_only_facts()) == (
            IntakeField.RECEIVER_IDENTITY,
            IntakeField.PICKUP_LOCATION,
            IntakeField.DROP_OFF_LOCATION,
            IntakeField.PARCEL_DECLARED_CONTENT,
        )

    def test_all_field_facts_report_no_missing_fields(self) -> None:
        assert missing_required_fields(complete_facts()) == ()

    def test_all_field_facts_without_preferred_period_report_no_missing_fields(self) -> None:
        assert missing_required_fields(complete_facts(preferred_period=None)) == ()

    def test_single_missing_field_is_reported_alone(self) -> None:
        facts = complete_facts()
        facts = facts.model_copy(update={"parcel_declared_content": None})
        assert missing_required_fields(facts) == (IntakeField.PARCEL_DECLARED_CONTENT,)

    @pytest.mark.parametrize(
        "receiver_field",
        ["receiver_name", "receiver_stable_id"],
    )
    def test_receiver_identity_satisfied_by_either_name_or_stable_id(self, receiver_field: str) -> None:
        facts = IntakeFacts(
            sender_actor_id="urn:actor:alice",
            pickup_location="123 Main St",
            drop_off_location="456 Oak Ave",
            parcel_declared_content="Books",
            **{receiver_field: "identifier-value"},
        )
        assert IntakeField.RECEIVER_IDENTITY not in missing_required_fields(facts)

    def test_receiver_identity_missing_when_neither_name_nor_stable_id_present(self) -> None:
        facts = complete_facts().model_copy(
            update={"receiver_name": None, "receiver_stable_id": None}
        )
        assert missing_required_fields(facts) == (IntakeField.RECEIVER_IDENTITY,)


# ============================================================================
# select_clarification_field
# ============================================================================


class TestSelectClarificationField:
    """At most one clarification field is selected, deterministically."""

    def test_no_missing_fields_selects_none(self) -> None:
        assert select_clarification_field(()) is None

    def test_first_missing_field_in_fixed_order_is_selected(self) -> None:
        missing = missing_required_fields(sender_only_facts())
        assert select_clarification_field(missing) is IntakeField.RECEIVER_IDENTITY

    def test_selection_follows_fixed_order_as_fields_are_resolved(self) -> None:
        assert (
            select_clarification_field(
                (
                    IntakeField.PICKUP_LOCATION,
                    IntakeField.DROP_OFF_LOCATION,
                    IntakeField.PARCEL_DECLARED_CONTENT,
                )
            )
            is IntakeField.PICKUP_LOCATION
        )
        assert (
            select_clarification_field(
                (IntakeField.DROP_OFF_LOCATION, IntakeField.PARCEL_DECLARED_CONTENT)
            )
            is IntakeField.DROP_OFF_LOCATION
        )
        assert (
            select_clarification_field((IntakeField.PARCEL_DECLARED_CONTENT,))
            is IntakeField.PARCEL_DECLARED_CONTENT
        )

    def test_invalid_field_takes_priority_over_fixed_order(self) -> None:
        missing = missing_required_fields(sender_only_facts())
        assert (
            select_clarification_field(missing, invalid_field=IntakeField.DROP_OFF_LOCATION)
            is IntakeField.DROP_OFF_LOCATION
        )

    def test_invalid_field_takes_priority_even_when_nothing_is_missing(self) -> None:
        assert (
            select_clarification_field((), invalid_field=IntakeField.PARCEL_DECLARED_CONTENT)
            is IntakeField.PARCEL_DECLARED_CONTENT
        )


# ============================================================================
# validate_complete_facts
# ============================================================================


class TestValidateCompleteFacts:
    """Complete validation only ever runs once the fixed missing tuple is empty."""

    def test_complete_facts_produce_a_complete_intake_facts_instance(self) -> None:
        result = validate_complete_facts(complete_facts())
        assert isinstance(result, CompleteIntakeFacts)
        assert result.pickup_location == "123 Main St"

    def test_incomplete_facts_raise_validation_error(self) -> None:
        with pytest.raises(ValidationError):
            validate_complete_facts(sender_only_facts())

    def test_incomplete_facts_missing_receiver_raise_validation_error(self) -> None:
        facts = complete_facts().model_copy(
            update={"receiver_name": None, "receiver_stable_id": None}
        )
        with pytest.raises(ValidationError):
            validate_complete_facts(facts)
