"""Routing lookup validation and context adaptation."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field, model_validator

from .base import RequestId, SessionId, StrictModel, VersionedContract
from .enums import (
    POST_INTAKE_STATUSES,
    BindingState,
    ErrorCode,
    RequestStatus,
    RouterOutcome,
    RouterTarget,
    RoutingReason,
    RoutingStage,
)
from .envelope import MainFlowInput
from .errors import ERROR_POLICY, OperationalError

__all__ = [
    "RouterInput",
    "RouterResult",
    "RoutingContext",
    "RoutingLookupRecord",
    "adapt_routing_lookup",
]


class RoutingLookupRecord(StrictModel):
    """Internal routing lookup record from Neo4j query."""

    binding_count: int
    active_relationship_count: int
    active_target_count: int
    requests: list[dict[str, Any]] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_cardinality(self) -> "RoutingLookupRecord":
        """Validate cardinality consistency."""
        # Check valid cardinalities: 0/0/0 or 1/1/1
        if self.binding_count == 0:
            # No binding case
            if (
                self.active_relationship_count != 0
                or self.active_target_count != 0
                or len(self.requests) != 0
            ):
                raise ValueError(
                    "Cardinality inconsistent: 0 bindings but non-zero "
                    "relationships/targets/requests"
                )
        elif self.binding_count == 1:
            # One binding case
            if (
                self.active_relationship_count != 1
                or self.active_target_count != 1
                or len(self.requests) != 1
            ):
                raise ValueError(
                    "Cardinality inconsistent: 1 binding requires 1 relationship, "
                    "1 target, 1 request"
                )
        else:
            # Invalid: >1 bindings
            raise ValueError("Cardinality inconsistent: duplicate bindings")

        return self


class RoutingContext(VersionedContract):
    """Result of routing lookup adaptation."""

    session_id: SessionId
    binding_state: BindingState
    binding_count: int
    active_relationship_count: int
    active_target_count: int
    request_id: RequestId | None = None
    request_status: RequestStatus | None = None
    closed_at: datetime | None = None
    routing_stage: RoutingStage
    error: OperationalError | None = None


class RouterResult(VersionedContract):
    """Router decision result."""

    outcome: RouterOutcome
    target: RouterTarget
    reason: RoutingReason
    request_id: RequestId | None = None
    safe_message: str
    error: OperationalError | None = None


def adapt_routing_lookup(
    record: RoutingLookupRecord,
    *,
    schema_version: str,
    correlation_id: UUID,
    session_id: SessionId,
) -> RoutingContext:
    """Adapt raw Neo4j routing lookup to typed RoutingContext.

    Implements exact precedence from plan lines 371-401:
    1. Validate cardinality (binding/relationship/target/request counts match)
    2. Check closed timestamp: if not null, routing_stage is CLOSED regardless of status
    3. If absent binding (count 0): require 0 relationships, 0 targets, no request
    4. If one bound (1/1/1): consume one request row, adapt raw status to enum
    5. Adapt status:
       - Null/absent binding → no request, no status
       - new, needsClarification, complete (typed) → preserve
       - All 8 post-intake statuses (typed) → preserve as unsupported but not failure
       - Null raw status → typed None with no error
       - Unknown raw status string → typed None with UNSUPPORTED_REQUEST_STATUS error
       - Closed not-null → RoutingStage.CLOSED, error None, status None

    Unknown raw status values are never copied into error/message/log/trace.
    """

    # Step 1: Validate cardinality (done by RoutingLookupRecord validator)

    # Step 2: Check closed timestamp - it takes precedence over status
    binding_state = BindingState.ABSENT
    request_id = None
    request_status = None
    closed_at = None
    routing_stage = None
    error = None

    if record.binding_count == 0:
        # Step 3: No binding
        binding_state = BindingState.ABSENT
        routing_stage = RoutingStage.INTAKE  # Default for absent binding
        request_id = None
        request_status = None
    else:
        # Step 4: One bound request
        binding_state = BindingState.BOUND
        request_row = record.requests[0]
        request_id = RequestId(request_row["request_id"])

        # Parse timestamps
        if request_row.get("closed") is not None:
            closed_at = datetime.fromisoformat(request_row["closed"].rstrip("Z"))

        # Step 2: Closed takes precedence
        if closed_at is not None:
            routing_stage = RoutingStage.CLOSED
            request_status = None
            error = None
        else:
            # Step 5: Adapt status
            raw_status = request_row.get("request_status_raw")

            if raw_status is None:
                # Null raw status on open request
                request_status = None
                error = None
                routing_stage = RoutingStage.INTAKE
            else:
                # Try to match to RequestStatus enum
                try:
                    request_status = RequestStatus(raw_status)

                    # Check if it's a post-intake status
                    if request_status in POST_INTAKE_STATUSES:
                        routing_stage = RoutingStage.UNSUPPORTED
                        error = None
                    elif request_status in (RequestStatus.NEW, RequestStatus.NEEDS_CLARIFICATION):
                        routing_stage = RoutingStage.INTAKE
                        error = None
                    elif request_status == RequestStatus.COMPLETE:
                        routing_stage = RoutingStage.COMPLETE
                        error = None
                    else:
                        # Shouldn't reach here, but safety fallback
                        routing_stage = RoutingStage.INTAKE
                        error = None
                except ValueError:
                    # Unknown raw status - NEVER copy raw text into error
                    request_status = None
                    policy = ERROR_POLICY[ErrorCode.UNSUPPORTED_REQUEST_STATUS]
                    error = OperationalError(
                        schema_version="1.0.0",
                        code=ErrorCode.UNSUPPORTED_REQUEST_STATUS,
                        correlation_id=correlation_id,
                        category=policy.category,
                        message=policy.safe_message,
                        retryable=policy.retryable,
                    )
                    routing_stage = RoutingStage.FAILURE

    return RoutingContext(
        schema_version=schema_version,
        correlation_id=correlation_id,
        session_id=session_id,
        binding_state=binding_state,
        binding_count=record.binding_count,
        active_relationship_count=record.active_relationship_count,
        active_target_count=record.active_target_count,
        request_id=request_id,
        request_status=request_status,
        closed_at=closed_at,
        routing_stage=routing_stage,
        error=error,
    )


class RouterInput(VersionedContract):
    """Input wrapper for routing operations.

    Combines MainFlowInput envelope with routing context lookup result.
    Enforces matching schema_version, correlation_id, and session_id across
    wrapper and nested objects.
    """

    envelope: MainFlowInput
    routing_context: RoutingContext

    @model_validator(mode="after")
    def validate_envelope_context_consistency(self) -> "RouterInput":
        """Validate schema_version and correlation_id consistency."""
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
        return self
