"""Deterministic completeness policy for parcel-request intake.

Per plan Task 10 (original task ID 3.1), a request is complete once Sender
identity, Receiver identity (name OR stable ID), pickup location, drop-off
location, and parcel declared content are all present; preferred period is
always optional. The deterministic missing-field priority is Receiver
identity, pickup location, drop-off location, then parcel declared content.
A supplied invalid field takes priority over the fixed order so it is
corrected immediately.

Pure domain logic: no I/O, no framework dependencies.
"""

from __future__ import annotations

from hulubul.core.models.operational.enums import IntakeField
from hulubul.core.models.operational.intake import CompleteIntakeFacts, IntakeFacts

__all__ = [
    "REQUIRED_INTAKE_FIELDS",
    "missing_required_fields",
    "select_clarification_field",
    "validate_complete_facts",
]

REQUIRED_INTAKE_FIELDS: tuple[IntakeField, ...] = (
    IntakeField.RECEIVER_IDENTITY,
    IntakeField.PICKUP_LOCATION,
    IntakeField.DROP_OFF_LOCATION,
    IntakeField.PARCEL_DECLARED_CONTENT,
)
"""Fixed clarification order; preferred_period is never required."""


def _is_field_present(facts: IntakeFacts, field: IntakeField) -> bool:
    """Report whether a single required field is satisfied by sparse facts."""
    if field is IntakeField.RECEIVER_IDENTITY:
        return facts.receiver_name is not None or facts.receiver_stable_id is not None
    return getattr(facts, field.value) is not None


def missing_required_fields(facts: IntakeFacts) -> tuple[IntakeField, ...]:
    """Return every unmet required field, in the fixed clarification order."""
    return tuple(field for field in REQUIRED_INTAKE_FIELDS if not _is_field_present(facts, field))


def select_clarification_field(
    missing_fields: tuple[IntakeField, ...],
    *,
    invalid_field: IntakeField | None = None,
) -> IntakeField | None:
    """Select at most one field to ask about next.

    An invalid field supplied in the current interaction always takes
    priority so it can be corrected immediately; otherwise the first missing
    field in the fixed order is selected. Returns None when nothing is
    missing and no invalid field was supplied.
    """
    if invalid_field is not None:
        return invalid_field
    return missing_fields[0] if missing_fields else None


def validate_complete_facts(facts: IntakeFacts) -> CompleteIntakeFacts:
    """Validate sparse facts against the complete-facts contract.

    Callers must only invoke this once ``missing_required_fields`` reports an
    empty tuple; it re-validates via ``CompleteIntakeFacts`` so any structural
    violation (e.g. a receiver with neither name nor stable ID) still raises.
    """
    return CompleteIntakeFacts(**facts.model_dump())
