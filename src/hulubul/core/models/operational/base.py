"""Strict base models and constrained types for operational contracts."""
from typing import Annotated, Any, Mapping, TypeVar
from enum import Enum
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

__all__ = [
    "StrictModel",
    "VersionedContract",
    "HumanSuppliedText",
    "NonBlankText",
    "SessionId",
    "ActorUrn",
    "RequestId",
    "ContractKind",
    "validate_json_mapping",
]

ModelT = TypeVar("ModelT", bound=BaseModel)


class StrictModel(BaseModel):
    """Base model with strict validation, frozen, and whitespace stripping."""

    model_config = ConfigDict(
        extra="forbid",
        strict=True,
        str_strip_whitespace=True,
        frozen=True,
    )


class VersionedContract(StrictModel):
    """Contract with schema version and correlation ID."""

    schema_version: str = "1.0.0"
    correlation_id: UUID


# Constrained types
HumanSuppliedText = Annotated[
    str,
    StringConstraints(min_length=1, max_length=4000),
]
"""1-4000 characters after stripping whitespace."""

NonBlankText = Annotated[
    str,
    StringConstraints(min_length=1),
]
"""1+ characters, not whitespace-only."""

SessionId = Annotated[str, Field(min_length=1)]
"""Session identifier."""

ActorUrn = Annotated[str, Field(min_length=1)]
"""Actor URN (Uniform Resource Name)."""

RequestId = Annotated[str, Field(min_length=1)]
"""Request UUID identifier."""


class ContractKind(str, Enum):
    """Exact 11-value contract kind enumeration."""

    MAIN_FLOW_INPUT = "main-flow-input"
    ROUTER_INPUT = "router-input"
    INTAKE_INPUT = "intake-input"
    ROUTING_CONTEXT = "routing-context"
    ROUTER_RESULT = "router-result"
    INTAKE_FACTS = "intake-facts"
    INTAKE_RESULT = "intake-result"
    DATA_OPERATION_REQUEST = "data-operation-request"
    DATA_OPERATION_RESULT = "data-operation-result"
    DELIVERY_REQUEST_SNAPSHOT = "delivery-request-snapshot"
    OPERATIONAL_ERROR = "operational-error"


def validate_json_mapping(
    model_type: type[ModelT], value: Mapping[str, Any]
) -> ModelT:
    """Validate and parse a JSON mapping (dict) as a typed model.

    Args:
        model_type: The Pydantic model class to validate against
        value: The mapping/dict to validate

    Returns:
        An instance of model_type with validated data

    Raises:
        ValidationError: If validation fails
    """
    return model_type.model_validate(value)
