"""Operational error handling and policy."""
from dataclasses import dataclass
from typing import Any, NamedTuple, Tuple
from uuid import UUID
from pydantic import BaseModel, Field, field_validator, ValidationError

from .base import StrictModel, VersionedContract
from .enums import ErrorCode, ErrorCategory, ErrorEscalation

__all__ = [
    "OperationalError",
    "FieldViolation",
    "ErrorPolicy",
    "ERROR_POLICY",
    "validation_error_to_operational_error",
]


class FieldViolation(NamedTuple):
    """Field-level validation violation (rule ID and field path only, no value)."""

    field_path: str
    rule_id: str


@dataclass(frozen=True)
class ErrorPolicy:
    """Policy for an error code."""

    code: ErrorCode
    category: ErrorCategory
    retryable: bool
    safe_message: str
    log_level: str
    log_fields: tuple[str, ...]
    escalation: ErrorEscalation


ERROR_POLICY = {
    ErrorCode.INVALID_INPUT: ErrorPolicy(
        code=ErrorCode.INVALID_INPUT,
        category=ErrorCategory.INPUT,
        retryable=False,
        safe_message="I could not process this message safely.",
        log_level="WARNING",
        log_fields=("correlation_id", "session_id", "flow_id", "component_id", "error_code", "schema_version"),
        escalation=ErrorEscalation.NONE,
    ),
    ErrorCode.INVALID_CONTRACT: ErrorPolicy(
        code=ErrorCode.INVALID_CONTRACT,
        category=ErrorCategory.CONTRACT,
        retryable=False,
        safe_message="I could not produce a safe response.",
        log_level="ERROR",
        log_fields=("correlation_id", "operation_id", "session_id", "flow_id", "component_id", "error_code", "schema_version"),
        escalation=ErrorEscalation.HARD_GATE_FAILURE,
    ),
    ErrorCode.OPERATION_NOT_ALLOWED: ErrorPolicy(
        code=ErrorCode.OPERATION_NOT_ALLOWED,
        category=ErrorCategory.AUTHORIZATION,
        retryable=False,
        safe_message="This operation is not allowed.",
        log_level="WARNING",
        log_fields=("correlation_id", "operation_id", "session_id", "flow_id", "component_id", "error_code", "schema_version"),
        escalation=ErrorEscalation.HARD_GATE_FAILURE,
    ),
    ErrorCode.BINDING_REQUEST_MISMATCH: ErrorPolicy(
        code=ErrorCode.BINDING_REQUEST_MISMATCH,
        category=ErrorCategory.STATE,
        retryable=False,
        safe_message="I could not resume this request safely.",
        log_level="ERROR",
        log_fields=("correlation_id", "request_id", "session_id", "flow_id", "component_id", "error_code", "schema_version"),
        escalation=ErrorEscalation.HARD_GATE_FAILURE,
    ),
    ErrorCode.GRAPH_CONTEXT_INCONSISTENT: ErrorPolicy(
        code=ErrorCode.GRAPH_CONTEXT_INCONSISTENT,
        category=ErrorCategory.STATE,
        retryable=False,
        safe_message="I could not resume this request safely.",
        log_level="ERROR",
        log_fields=("correlation_id", "request_id", "session_id", "flow_id", "component_id", "error_code", "schema_version"),
        escalation=ErrorEscalation.HARD_GATE_FAILURE,
    ),
    ErrorCode.UNSUPPORTED_PHASE1_STATUS: ErrorPolicy(
        code=ErrorCode.UNSUPPORTED_PHASE1_STATUS,
        category=ErrorCategory.STATE,
        retryable=False,
        safe_message="This request cannot be handled by the current intake flow.",
        log_level="INFO",
        log_fields=("correlation_id", "request_id", "session_id", "flow_id", "component_id", "error_code", "schema_version"),
        escalation=ErrorEscalation.NONE,
    ),
    ErrorCode.UNSUPPORTED_REQUEST_STATUS: ErrorPolicy(
        code=ErrorCode.UNSUPPORTED_REQUEST_STATUS,
        category=ErrorCategory.STATE,
        retryable=False,
        safe_message="I could not resume this request safely.",
        log_level="ERROR",
        log_fields=("correlation_id", "request_id", "session_id", "flow_id", "component_id", "error_code", "schema_version"),
        escalation=ErrorEscalation.HARD_GATE_FAILURE,
    ),
    ErrorCode.INVALID_EXPECTED_STATUS: ErrorPolicy(
        code=ErrorCode.INVALID_EXPECTED_STATUS,
        category=ErrorCategory.CONCURRENCY,
        retryable=False,
        safe_message="The request changed before this update could be applied.",
        log_level="INFO",
        log_fields=("correlation_id", "operation_id", "request_id", "session_id", "flow_id", "component_id", "error_code", "schema_version"),
        escalation=ErrorEscalation.NONE,
    ),
    ErrorCode.INVALID_STATUS_TRANSITION: ErrorPolicy(
        code=ErrorCode.INVALID_STATUS_TRANSITION,
        category=ErrorCategory.STATE,
        retryable=False,
        safe_message="This request update is not allowed.",
        log_level="WARNING",
        log_fields=("correlation_id", "operation_id", "request_id", "session_id", "flow_id", "component_id", "error_code", "schema_version"),
        escalation=ErrorEscalation.HARD_GATE_FAILURE,
    ),
    ErrorCode.CONCURRENT_MODIFICATION: ErrorPolicy(
        code=ErrorCode.CONCURRENT_MODIFICATION,
        category=ErrorCategory.CONCURRENCY,
        retryable=False,
        safe_message="The request changed before this update could be applied.",
        log_level="INFO",
        log_fields=("correlation_id", "operation_id", "request_id", "session_id", "flow_id", "component_id", "error_code", "schema_version"),
        escalation=ErrorEscalation.NONE,
    ),
    ErrorCode.AFFECTED_RECORD_COUNT_MISMATCH: ErrorPolicy(
        code=ErrorCode.AFFECTED_RECORD_COUNT_MISMATCH,
        category=ErrorCategory.STATE,
        retryable=False,
        safe_message="I could not confirm the request update safely.",
        log_level="ERROR",
        log_fields=("correlation_id", "operation_id", "request_id", "session_id", "flow_id", "component_id", "error_code", "schema_version"),
        escalation=ErrorEscalation.HARD_GATE_FAILURE,
    ),
    ErrorCode.MODEL_TRANSIENT_FAILURE: ErrorPolicy(
        code=ErrorCode.MODEL_TRANSIENT_FAILURE,
        category=ErrorCategory.DEPENDENCY,
        retryable=True,
        safe_message="I could not process this request right now.",
        log_level="ERROR",
        log_fields=("correlation_id", "session_id", "flow_id", "component_id", "retry_attempt", "error_code", "schema_version"),
        escalation=ErrorEscalation.HARD_GATE_FAILURE,
    ),
    ErrorCode.MODEL_AUTHENTICATION_FAILURE: ErrorPolicy(
        code=ErrorCode.MODEL_AUTHENTICATION_FAILURE,
        category=ErrorCategory.DEPENDENCY,
        retryable=False,
        safe_message="I could not process this request right now.",
        log_level="ERROR",
        log_fields=("correlation_id", "session_id", "flow_id", "component_id", "error_code", "schema_version"),
        escalation=ErrorEscalation.HARD_GATE_FAILURE,
    ),
    ErrorCode.MALFORMED_AGENT_RESULT: ErrorPolicy(
        code=ErrorCode.MALFORMED_AGENT_RESULT,
        category=ErrorCategory.CONTRACT,
        retryable=False,
        safe_message="I could not produce a safe response.",
        log_level="ERROR",
        log_fields=("correlation_id", "operation_id", "session_id", "flow_id", "component_id", "retry_attempt", "error_code", "schema_version"),
        escalation=ErrorEscalation.HARD_GATE_FAILURE,
    ),
    ErrorCode.MCP_READ_TRANSIENT_FAILURE: ErrorPolicy(
        code=ErrorCode.MCP_READ_TRANSIENT_FAILURE,
        category=ErrorCategory.DEPENDENCY,
        retryable=True,
        safe_message="I could not load this request right now.",
        log_level="ERROR",
        log_fields=("correlation_id", "operation_id", "request_id", "session_id", "flow_id", "component_id", "retry_attempt", "error_code", "schema_version"),
        escalation=ErrorEscalation.HARD_GATE_FAILURE,
    ),
    ErrorCode.MCP_WRITE_AMBIGUOUS: ErrorPolicy(
        code=ErrorCode.MCP_WRITE_AMBIGUOUS,
        category=ErrorCategory.DEPENDENCY,
        retryable=False,
        safe_message="I could not confirm whether the request update was saved.",
        log_level="ERROR",
        log_fields=("correlation_id", "operation_id", "request_id", "session_id", "flow_id", "component_id", "error_code", "schema_version"),
        escalation=ErrorEscalation.MANUAL_AMBIGUOUS_WRITE_GRAPH_INSPECTION,
    ),
    ErrorCode.MCP_AUTHENTICATION_FAILURE: ErrorPolicy(
        code=ErrorCode.MCP_AUTHENTICATION_FAILURE,
        category=ErrorCategory.DEPENDENCY,
        retryable=False,
        safe_message="I could not access the request safely.",
        log_level="ERROR",
        log_fields=("correlation_id", "operation_id", "session_id", "flow_id", "component_id", "error_code", "schema_version"),
        escalation=ErrorEscalation.HARD_GATE_FAILURE,
    ),
    ErrorCode.MCP_OPERATION_FAILURE: ErrorPolicy(
        code=ErrorCode.MCP_OPERATION_FAILURE,
        category=ErrorCategory.DEPENDENCY,
        retryable=False,
        safe_message="I could not access the request safely.",
        log_level="ERROR",
        log_fields=("correlation_id", "operation_id", "request_id", "session_id", "flow_id", "component_id", "error_code", "schema_version"),
        escalation=ErrorEscalation.HARD_GATE_FAILURE,
    ),
    ErrorCode.DEPENDENCY_UNAVAILABLE: ErrorPolicy(
        code=ErrorCode.DEPENDENCY_UNAVAILABLE,
        category=ErrorCategory.DEPENDENCY,
        retryable=True,
        safe_message="I could not process this request right now.",
        log_level="ERROR",
        log_fields=("correlation_id", "session_id", "flow_id", "component_id", "retry_attempt", "error_code", "schema_version"),
        escalation=ErrorEscalation.HARD_GATE_FAILURE,
    ),
}


class OperationalError(VersionedContract):
    """Canonical operational error with enforced policy values."""

    code: ErrorCode = Field(description="Error code")
    category: ErrorCategory = Field(description="Error category (from policy)")
    message: str = Field(description="Safe user message (from policy)")
    retryable: bool = Field(description="Whether error is retryable (from policy)")
    violations: Tuple[FieldViolation, ...] = Field(
        default_factory=tuple,
        description="Validation violations (field and rule ID only, no values)",
    )

    @field_validator("category", mode="before")
    @classmethod
    def validate_category(cls, value: Any, info: Any) -> Any:
        """Enforce that category matches policy for this code."""
        code = info.data.get("code")
        if code is None or code not in ERROR_POLICY:
            return value
        policy = ERROR_POLICY[code]
        if value != policy.category:
            raise ValueError(
                f"category must be {policy.category.value} for {code.value}"
            )
        return value

    @field_validator("message", mode="before")
    @classmethod
    def validate_message(cls, value: Any, info: Any) -> Any:
        """Enforce that message matches policy for this code."""
        code = info.data.get("code")
        if code is None or code not in ERROR_POLICY:
            return value
        policy = ERROR_POLICY[code]
        if value != policy.safe_message:
            raise ValueError(
                f"message must be '{policy.safe_message}' for {code.value}"
            )
        return value

    @field_validator("retryable", mode="before")
    @classmethod
    def validate_retryable(cls, value: Any, info: Any) -> Any:
        """Enforce that retryable matches policy for this code."""
        code = info.data.get("code")
        if code is None or code not in ERROR_POLICY:
            return value
        policy = ERROR_POLICY[code]
        if value != policy.retryable:
            raise ValueError(
                f"retryable must be {policy.retryable} for {code.value}"
            )
        return value


def validation_error_to_operational_error(
    error: ValidationError, *, correlation_id: UUID
) -> OperationalError:
    """Convert Pydantic ValidationError to OperationalError.

    Records only normalized field locations and Pydantic rule IDs, never
    rejected values or fabricated identifiers.

    Args:
        error: Pydantic ValidationError to convert
        correlation_id: UUID for correlation

    Returns:
        OperationalError with INVALID_CONTRACT code and violations
    """
    violations: list[FieldViolation] = []

    for err in error.errors():
        # Extract field path
        field_path = ".".join(str(loc) for loc in err.get("loc", []))

        # Extract rule ID (type) from error
        rule_id = err.get("type", "validation_error")

        # Never include the violated value
        violation = FieldViolation(
            field_path=field_path,
            rule_id=rule_id,
        )
        violations.append(violation)

    policy = ERROR_POLICY[ErrorCode.INVALID_CONTRACT]

    return OperationalError(
        schema_version="1.0.0",
        correlation_id=correlation_id,
        code=ErrorCode.INVALID_CONTRACT,
        category=policy.category,
        message=policy.safe_message,
        retryable=policy.retryable,
        violations=tuple(violations),
    )
