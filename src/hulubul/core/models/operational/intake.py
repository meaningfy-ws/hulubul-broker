"""Intake facts and result contracts for operational phase.

Per plan 2.3 (Locked Fact And Result Contracts), these models enforce the
distinction between sparse facts (for 'new' and 'needsClarification' states)
and complete facts (for 'complete' state and persisted snapshots).

Sparse facts allow up to 8 fields with nullable human-text inputs (1-4000 chars).
Complete facts require four core fields and no missing markers.
Results carry outcomes, clarification needs, and user-safe messaging.
"""
from __future__ import annotations

from typing import Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from hulubul.core.models.operational.base import (
    ActorUrn,
    HumanSuppliedText,
    NonBlankText,
)
from hulubul.core.models.operational.enums import IntakeOutcome


# ============================================================================
# Sparse Intake Facts (new, needsClarification states)
# ============================================================================


class IntakeFacts(BaseModel):
    """Sparse intake facts for new and needsClarification parcel requests.

    Allows up to 8 fields with nullable human-text inputs (1-4000 chars each).
    Receiver identity satisfied by either name OR stable_id (both allowed).
    No missing/clarification/error fields; those belong in IntakeResult.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_default=True,
        validate_assignment=True,
    )

    sender_actor_id: ActorUrn = Field(
        ...,
        description="URN-style actor identifier of the sender (chain identity).",
    )

    sender_display_name: Optional[NonBlankText] = Field(
        default=None,
        description="Human-readable display name for the sender.",
    )

    receiver_name: Optional[HumanSuppliedText] = Field(
        default=None,
        description="Human-supplied name of the receiver (1-4000 chars).",
    )

    receiver_stable_id: Optional[NonBlankText] = Field(
        default=None,
        description="Stable business identifier for the receiver.",
    )

    pickup_location: Optional[HumanSuppliedText] = Field(
        default=None,
        description="Human-supplied pickup location (1-4000 chars).",
    )

    drop_off_location: Optional[HumanSuppliedText] = Field(
        default=None,
        description="Human-supplied drop-off location (1-4000 chars).",
    )

    parcel_declared_content: Optional[HumanSuppliedText] = Field(
        default=None,
        description="Sender's declared description of contents (1-4000 chars).",
    )

    preferred_period: Optional[HumanSuppliedText] = Field(
        default=None,
        description="Requester's preferred timeframe (orientative, free text, 1-4000 chars).",
    )


# ============================================================================
# Intake Fact Updates (Partial Updates)
# ============================================================================


class IntakeFactUpdates(BaseModel):
    """Partial fact updates; rejects empty updates (at least one field required)."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_default=True,
    )

    sender_actor_id: Optional[ActorUrn] = None
    sender_display_name: Optional[NonBlankText] = None
    receiver_name: Optional[HumanSuppliedText] = None
    receiver_stable_id: Optional[NonBlankText] = None
    pickup_location: Optional[HumanSuppliedText] = None
    drop_off_location: Optional[HumanSuppliedText] = None
    parcel_declared_content: Optional[HumanSuppliedText] = None
    preferred_period: Optional[HumanSuppliedText] = None

    @model_validator(mode="after")
    def reject_empty_updates(self) -> IntakeFactUpdates:
        """Reject updates with all fields None."""
        if not any(
            getattr(self, field, None) is not None
            for field in self.__class__.model_fields
        ):
            raise ValueError("At least one field must be provided for update")
        return self


# ============================================================================
# Complete Intake Facts (complete state)
# ============================================================================


class CompleteIntakeFacts(BaseModel):
    """Complete intake facts for 'complete' status requests.

    Enforces that four core fields are present and non-None:
    - sender_actor_id (required, always)
    - receiver_name OR receiver_stable_id (at least one required)
    - pickup_location (required)
    - drop_off_location (required)

    Optional fields (can be None if not captured):
    - sender_display_name
    - parcel_declared_content
    - preferred_period
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_default=True,
        validate_assignment=True,
    )

    sender_actor_id: ActorUrn = Field(
        ...,
        description="URN-style actor identifier of the sender (required).",
    )

    sender_display_name: Optional[NonBlankText] = Field(
        default=None,
        description="Human-readable display name for the sender.",
    )

    receiver_name: Optional[HumanSuppliedText] = Field(
        default=None,
        description="Human-supplied name of the receiver (1-4000 chars).",
    )

    receiver_stable_id: Optional[NonBlankText] = Field(
        default=None,
        description="Stable business identifier for the receiver.",
    )

    pickup_location: HumanSuppliedText = Field(
        ...,
        description="Human-supplied pickup location (required, 1-4000 chars).",
    )

    drop_off_location: HumanSuppliedText = Field(
        ...,
        description="Human-supplied drop-off location (required, 1-4000 chars).",
    )

    parcel_declared_content: Optional[HumanSuppliedText] = Field(
        default=None,
        description="Sender's declared description of contents (1-4000 chars).",
    )

    preferred_period: Optional[HumanSuppliedText] = Field(
        default=None,
        description="Requester's preferred timeframe (orientative, free text, 1-4000 chars).",
    )

    @model_validator(mode="after")
    def receiver_name_or_stable_id_required(self) -> CompleteIntakeFacts:
        """Validate that at least one receiver identifier is present."""
        if not self.receiver_name and not self.receiver_stable_id:
            raise ValueError(
                "At least one of receiver_name or receiver_stable_id must be provided"
            )
        return self


# ============================================================================
# Intake Result
# ============================================================================


class GraphIdentifiers(BaseModel):
    """Graph node identifiers for linking entities."""

    model_config = ConfigDict(validate_default=True)

    request_id: str = Field(
        ...,
        description="Graph node ID for the delivery request.",
    )

    sender_id: Optional[str] = Field(
        default=None,
        description="Graph node ID for the sender (optional).",
    )

    receiver_id: Optional[str] = Field(
        default=None,
        description="Graph node ID for the receiver (optional).",
    )


class IntakeResult(BaseModel):
    """Result of an intake operation.

    Carries outcome, request state, facts, missing/clarification fields,
    user-safe messaging, and errors. Missing and clarification are mutually
    exclusive with error; clarification_field is only present when outcome
    is 'clarification_needed'.
    """

    model_config = ConfigDict(
        validate_default=True,
        validate_assignment=True,
    )

    outcome: IntakeOutcome = Field(
        ...,
        description="Outcome classification: clarificationRequired, requestComplete, or failure.",
    )

    request_id: Optional[str] = Field(
        default=None,
        description="Graph node ID for created/updated request (clarificationRequired/requestComplete only).",
    )

    status: Optional[str] = Field(
        default=None,
        description="Request status when outcome is clarificationRequired or requestComplete.",
    )

    facts: Optional[IntakeFacts] = Field(
        default=None,
        description="Sparse facts captured (clarificationRequired/requestComplete only).",
    )

    missing_fields: Tuple[str, ...] = Field(
        default_factory=tuple,
        description="Immutable tuple of field names not yet provided.",
    )

    clarification_field: Optional[str] = Field(
        default=None,
        description="Single field name requiring clarification (clarificationRequired outcome only).",
    )

    safe_user_message: Optional[str] = Field(
        default=None,
        description="User-safe message (not exposing internals).",
    )

    error: Optional[str] = Field(
        default=None,
        description="Error message (failure outcome only).",
    )

    @field_validator("missing_fields", mode="before")
    @classmethod
    def ensure_tuple(cls, v):
        """Convert missing_fields to immutable tuple."""
        if isinstance(v, (list, tuple)):
            return tuple(v)
        return v

    @model_validator(mode="after")
    def validate_outcome_invariants(self) -> IntakeResult:
        """Validate that outcome state is consistent with field presence."""
        outcome = self.outcome

        # Validate failure outcome
        if outcome == IntakeOutcome.FAILURE:
            if not self.error:
                raise ValueError(
                    "failure outcome must include error message"
                )
            if self.request_id or self.facts:
                raise ValueError(
                    "failure outcome must not include request_id or facts"
                )

        # Validate requestComplete outcome
        elif outcome == IntakeOutcome.REQUEST_COMPLETE:
            if self.error:
                raise ValueError(
                    "requestComplete outcome must not include error"
                )
            if not self.request_id:
                raise ValueError(
                    "requestComplete outcome must include request_id"
                )

        # Validate clarificationRequired outcome
        elif outcome == IntakeOutcome.CLARIFICATION_REQUIRED:
            if self.error:
                raise ValueError(
                    "clarificationRequired outcome must not include error"
                )
            if not self.clarification_field:
                raise ValueError(
                    "clarificationRequired outcome must include clarification_field"
                )

        return self
