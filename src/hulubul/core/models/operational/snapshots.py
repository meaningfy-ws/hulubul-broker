"""Delivery request snapshot and mutation confirmation contracts.

Per plan 2.3 (Locked Fact And Result Contracts), snapshots enforce:
- Sparse/complete fact contradictions based on request status
- Immutable created_at, authoritative updated_at, nullable closed_at
- Missing fields as locked tuple
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

from hulubul.core.models.operational.intake import (
    CompleteIntakeFacts,
    IntakeFacts,
)

# ============================================================================
# Delivery Request Snapshot
# ============================================================================


class DeliveryRequestSnapshot(BaseModel):
    """Immutable snapshot of a delivery request state.

    Enforces nested schema equality and sparse/complete contradictions:
    - For 'new' and 'needsClarification' states: sparse IntakeFacts allowed
    - For 'complete' state: CompleteIntakeFacts required, empty missing_fields
    - Timestamps: created_at immutable, updated_at authoritative, closed_at nullable
    """

    model_config = ConfigDict(
        validate_default=True,
        validate_assignment=True,
    )

    request_id: str = Field(
        ...,
        description="Graph node ID for this delivery request.",
    )

    created_at: datetime = Field(
        ...,
        description="When the request was created (immutable).",
    )

    updated_at: datetime = Field(
        ...,
        description="When the request was last modified (authoritative).",
    )

    closed_at: datetime | None = Field(
        default=None,
        description="When the request was closed/terminated (nullable).",
    )

    status: str | None = Field(
        default=None,
        description="Request lifecycle status (new, needsClarification, complete, etc.).",
    )

    facts: IntakeFacts | CompleteIntakeFacts = Field(
        ...,
        description="Sparse or complete intake facts depending on status.",
    )

    missing_fields: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Immutable tuple of field names not yet provided.",
    )

    @field_validator("missing_fields", mode="before")
    @classmethod
    def ensure_tuple(cls, v: Any) -> tuple[str, ...]:
        """Convert missing_fields to immutable tuple."""
        if isinstance(v, list | tuple):
            return tuple(v)
        return v

    @field_validator("facts", mode="after")
    @classmethod
    def validate_status_fact_consistency(cls, v: Any, info: ValidationInfo) -> Any:
        """Enforce nested schema equality between status and facts type.

        For 'complete' status: facts must be CompleteIntakeFacts, no missing fields.
        For 'new' and 'needsClarification': facts can be sparse IntakeFacts.
        """
        values = info.data
        status = values.get("status")
        missing_fields = values.get("missing_fields", ())

        if status == "complete":
            # Complete status requires CompleteIntakeFacts
            if not isinstance(v, CompleteIntakeFacts):
                raise ValueError(
                    "status='complete' requires CompleteIntakeFacts, not sparse IntakeFacts"
                )
            # Complete status must have empty missing_fields
            if missing_fields:
                raise ValueError("status='complete' must have empty missing_fields tuple")

        elif status in ("new", "needsClarification"):
            # These statuses allow sparse facts (may be any IntakeFacts variant)
            pass

        return v

    def __eq__(self, other: Any) -> bool:
        """Test equality based on all fields."""
        if not isinstance(other, DeliveryRequestSnapshot):
            return False
        return (
            self.request_id == other.request_id
            and self.created_at == other.created_at
            and self.updated_at == other.updated_at
            and self.closed_at == other.closed_at
            and self.status == other.status
            and self.facts == other.facts
            and self.missing_fields == other.missing_fields
        )

    def __hash__(self) -> int:
        """Hash based on request_id."""
        return hash(self.request_id)


# ============================================================================
# Mutation Confirmation
# ============================================================================


class MutationConfirmation(BaseModel):
    """Confirmation of a mutation operation with locked snapshot state.

    Carries the snapshot after mutation and the specific changes applied.
    """

    model_config = ConfigDict(
        validate_default=True,
        frozen=True,  # Locked/immutable
    )

    snapshot: DeliveryRequestSnapshot = Field(
        ...,
        description="The delivery request snapshot after mutation.",
    )

    changes: dict[str, Any] = Field(
        ...,
        description="Dictionary of fields that were changed and their new values.",
    )
