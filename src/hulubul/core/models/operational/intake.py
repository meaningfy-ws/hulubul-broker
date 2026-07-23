"""Intake facts and result contracts for operational phase.

Per plan 2.3 (Locked Fact And Result Contracts), these models enforce the
distinction between sparse facts (for 'new' and 'needsClarification' states)
and complete facts (for 'complete' state and persisted snapshots).

Sparse facts allow up to 8 fields with nullable human-text inputs (1-4000 chars).
Complete facts require four core fields and no missing markers.
Results carry outcomes, clarification needs, and user-safe messaging.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from hulubul.core.models.operational.base import (
    ActorUrn,
    HumanSuppliedText,
    NonBlankText,
    VersionedContract,
)
from hulubul.core.models.operational.enums import (
    POST_INTAKE_STATUSES,
    BindingState,
    IntakeOutcome,
    RoutingStage,
)
from hulubul.core.models.operational.envelope import MainFlowInput
from hulubul.core.models.operational.routing import RoutingContext

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

    sender_display_name: NonBlankText | None = Field(
        default=None,
        description="Human-readable display name for the sender.",
    )

    receiver_name: HumanSuppliedText | None = Field(
        default=None,
        description="Human-supplied name of the receiver (1-4000 chars).",
    )

    receiver_stable_id: NonBlankText | None = Field(
        default=None,
        description="Stable business identifier for the receiver.",
    )

    pickup_location: HumanSuppliedText | None = Field(
        default=None,
        description="Human-supplied pickup location (1-4000 chars).",
    )

    drop_off_location: HumanSuppliedText | None = Field(
        default=None,
        description="Human-supplied drop-off location (1-4000 chars).",
    )

    parcel_declared_content: HumanSuppliedText | None = Field(
        default=None,
        description="Sender's declared description of contents (1-4000 chars).",
    )

    preferred_period: HumanSuppliedText | None = Field(
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

    sender_actor_id: ActorUrn | None = None
    sender_display_name: NonBlankText | None = None
    receiver_name: HumanSuppliedText | None = None
    receiver_stable_id: NonBlankText | None = None
    pickup_location: HumanSuppliedText | None = None
    drop_off_location: HumanSuppliedText | None = None
    parcel_declared_content: HumanSuppliedText | None = None
    preferred_period: HumanSuppliedText | None = None

    @model_validator(mode="after")
    def reject_empty_updates(self) -> IntakeFactUpdates:
        """Reject updates with all fields None."""
        if not any(getattr(self, field, None) is not None for field in self.__class__.model_fields):
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

    sender_display_name: NonBlankText | None = Field(
        default=None,
        description="Human-readable display name for the sender.",
    )

    receiver_name: HumanSuppliedText | None = Field(
        default=None,
        description="Human-supplied name of the receiver (1-4000 chars).",
    )

    receiver_stable_id: NonBlankText | None = Field(
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

    parcel_declared_content: HumanSuppliedText | None = Field(
        default=None,
        description="Sender's declared description of contents (1-4000 chars).",
    )

    preferred_period: HumanSuppliedText | None = Field(
        default=None,
        description="Requester's preferred timeframe (orientative, free text, 1-4000 chars).",
    )

    @model_validator(mode="after")
    def receiver_name_or_stable_id_required(self) -> CompleteIntakeFacts:
        """Validate that at least one receiver identifier is present."""
        if not self.receiver_name and not self.receiver_stable_id:
            raise ValueError("At least one of receiver_name or receiver_stable_id must be provided")
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

    sender_id: str | None = Field(
        default=None,
        description="Graph node ID for the sender (optional).",
    )

    receiver_id: str | None = Field(
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

    request_id: str | None = Field(
        default=None,
        description=(
            "Graph node ID for created/updated request "
            "(clarificationRequired/requestComplete only)."
        ),
    )

    status: str | None = Field(
        default=None,
        description="Request status when outcome is clarificationRequired or requestComplete.",
    )

    facts: IntakeFacts | None = Field(
        default=None,
        description="Sparse facts captured (clarificationRequired/requestComplete only).",
    )

    missing_fields: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Immutable tuple of field names not yet provided.",
    )

    clarification_field: str | None = Field(
        default=None,
        description=(
            "Single field name requiring clarification "
            "(clarificationRequired outcome only)."
        ),
    )

    safe_user_message: str | None = Field(
        default=None,
        description="User-safe message (not exposing internals).",
    )

    error: str | None = Field(
        default=None,
        description="Error message (failure outcome only).",
    )

    @field_validator("missing_fields", mode="before")
    @classmethod
    def ensure_tuple(cls, v):
        """Convert missing_fields to immutable tuple."""
        if isinstance(v, list | tuple):
            return tuple(v)
        return v

    @model_validator(mode="after")
    def validate_outcome_invariants(self) -> IntakeResult:
        """Validate that outcome state is consistent with field presence."""
        outcome = self.outcome

        # Validate failure outcome
        if outcome == IntakeOutcome.FAILURE:
            if not self.error:
                raise ValueError("failure outcome must include error message")
            if self.request_id or self.facts:
                raise ValueError("failure outcome must not include request_id or facts")

        # Validate requestComplete outcome
        elif outcome == IntakeOutcome.REQUEST_COMPLETE:
            if self.error:
                raise ValueError("requestComplete outcome must not include error")
            if not self.request_id:
                raise ValueError("requestComplete outcome must include request_id")

        # Validate clarificationRequired outcome
        elif outcome == IntakeOutcome.CLARIFICATION_REQUIRED:
            if self.error:
                raise ValueError("clarificationRequired outcome must not include error")
            if not self.clarification_field:
                raise ValueError("clarificationRequired outcome must include clarification_field")

        return self


# ============================================================================
# Wrapped Input (intake)
# ============================================================================


class IntakeInput(VersionedContract):
    """Input wrapper for intake operations.

    Combines MainFlowInput envelope with a routing context that has undergone
    validation constraints specific to intake (INTAKE stage, no errors, appropriate bindings).
    """

    envelope: MainFlowInput
    routing_context: RoutingContext

    @model_validator(mode="after")
    def validate_intake_constraints(self) -> IntakeInput:
        """Validate intake-specific routing context constraints."""
        # Validate schema_version and correlation_id consistency
        if self.schema_version != self.envelope.schema_version:
            raise ValueError(
                f"schema_version mismatch: wrapper={self.schema_version} "
                f"envelope={self.envelope.schema_version}"
            )
        if self.correlation_id != self.envelope.correlation_id:
            raise ValueError(
                f"correlation_id mismatch: wrapper={self.correlation_id} "
                f"envelope={self.envelope.correlation_id}"
            )
        if self.envelope.session_id != self.routing_context.session_id:
            raise ValueError(
                f"session_id mismatch: envelope={self.envelope.session_id} "
                f"routing_context={self.routing_context.session_id}"
            )

        # IntakeInput requires INTAKE routing stage
        if self.routing_context.routing_stage != RoutingStage.INTAKE:
            raise ValueError(
                f"IntakeInput requires INTAKE routing_stage, "
                f"got {self.routing_context.routing_stage}"
            )

        # IntakeInput must not have routing errors
        if self.routing_context.error is not None:
            raise ValueError("IntakeInput must not have routing errors")

        # Validate binding state constraints
        if self.routing_context.binding_state == BindingState.ABSENT:
            # No binding is OK (first message, new request will be created)
            if self.routing_context.request_id or self.routing_context.request_status:
                raise ValueError("ABSENT binding must not have request_id or request_status")
        elif self.routing_context.binding_state == BindingState.BOUND:
            # One bound request must be in intake stages (NEW or NEEDS_CLARIFICATION)
            if not self.routing_context.request_id:
                raise ValueError("BOUND binding must have request_id")
            if not self.routing_context.request_status:
                raise ValueError("BOUND binding must have request_status")
            if self.routing_context.request_status in POST_INTAKE_STATUSES:
                raise ValueError(
                    f"IntakeInput rejects post-intake status {self.routing_context.request_status}"
                )
        else:
            # INCONSISTENT binding is rejected
            raise ValueError(
                f"IntakeInput rejects {self.routing_context.binding_state} binding state"
            )

        return self
