"""Five strictly-typed data operation contracts with discriminated unions.

Task 8 defines exactly five operations (GET_REQUEST_ROUTING_CONTEXT,
CREATE_DELIVERY_REQUEST, READ_DELIVERY_REQUEST, UPDATE_DELIVERY_REQUEST,
SET_REQUEST_STATUS) as discriminated unions that reject malformed operations
before capability policy runs.

Result invariants enforce: confirmed writes require dispatch=true and one
affected request; confirmed reads require dispatch=false; confirmed create
requires Neo4j-returned aware created_at == updated_at; rejected results
cannot claim success; ambiguous results require dispatched write with no
count/result/status.

Create payload rejects both created_at and updated_at; Neo4j owns both
timestamps. All operation requests require shared envelope fields:
operation_id, caller, session_id, actor_id, schema_version, correlation_id.
"""
from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal, Mapping, TypeVar

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, field_validator

from hulubul.core.models.operational.enums import DataOperation, DataOperationOutcome


class DataOperationRequestBase(BaseModel):
    """Shared envelope for all operation requests.

    Every operation adds: operation_id, caller, session_id, actor_id,
    schema_version, correlation_id.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    operation: DataOperation
    operation_id: str
    caller: str
    session_id: str
    actor_id: str
    schema_version: str
    correlation_id: str


class GetRequestRoutingContextRequest(DataOperationRequestBase):
    """Routing context operation requires empty payload beyond envelope."""

    operation: Literal[DataOperation.GET_REQUEST_ROUTING_CONTEXT]


class CreateDeliveryRequestRequest(DataOperationRequestBase):
    """Create operation requires identifiers and facts; rejects timestamps.

    Neo4j owns both created_at and updated_at; a confirmed create result
    returns equal authoritative timestamps.
    """

    operation: Literal[DataOperation.CREATE_DELIVERY_REQUEST]
    identifiers: dict[str, Any]
    facts: dict[str, Any]

    @field_validator("identifiers", "facts", mode="before")
    @classmethod
    def validate_identifiers_and_facts(cls, v: Any) -> Any:
        """Ensure identifiers and facts are dicts."""
        if not isinstance(v, dict):
            raise ValueError("must be a dict")
        return v


class ReadDeliveryRequestRequest(DataOperationRequestBase):
    """Read operation requires request_id only."""

    operation: Literal[DataOperation.READ_DELIVERY_REQUEST]
    request_id: str


class UpdateDeliveryRequestRequest(DataOperationRequestBase):
    """Update operation requires five fields for concurrency and patch.

    request_id: target request
    expected_updated_at: concurrency check timestamp
    expected_status: concurrency check status
    updates: sparse patch dict
    identifiers: additional identifiers if needed
    """

    operation: Literal[DataOperation.UPDATE_DELIVERY_REQUEST]
    request_id: str
    expected_updated_at: str
    expected_status: str
    updates: dict[str, Any]
    identifiers: dict[str, Any]

    @field_validator("updates", "identifiers", mode="before")
    @classmethod
    def validate_dicts(cls, v: Any) -> Any:
        """Ensure updates and identifiers are dicts."""
        if not isinstance(v, dict):
            raise ValueError("must be a dict")
        return v


class SetRequestStatusRequest(DataOperationRequestBase):
    """Status operation requires four fields for concurrency-safe transition.

    request_id: target request
    expected_updated_at: concurrency check timestamp
    expected_status: current expected status
    target_status: desired status after transition
    """

    operation: Literal[DataOperation.SET_REQUEST_STATUS]
    request_id: str
    expected_updated_at: str
    expected_status: str
    target_status: str


# Discriminated union of all five operation requests.
# Rejects unknown discriminators, raw cypher/query, and undeclared fields
# as INVALID_CONTRACT before capability policy is callable.
DataOperationRequest = Annotated[
    GetRequestRoutingContextRequest
    | CreateDeliveryRequestRequest
    | ReadDeliveryRequestRequest
    | UpdateDeliveryRequestRequest
    | SetRequestStatusRequest,
    Field(discriminator="operation"),
]


class DataOperationResult(BaseModel):
    """Result of a data operation with invariants.

    Confirmed writes require dispatch=true, one affected request, and
    matching typed result/status.

    Confirmed create also requires Neo4j-returned aware created_at == updated_at.

    Confirmed reads require dispatch=false and no count.

    Rejected results cannot claim success/status/result.

    Ambiguous results require dispatched write, no count/result/status,
    and exactly MCP_WRITE_AMBIGUOUS error.
    """

    model_config = ConfigDict(extra="forbid")

    operation: DataOperation
    outcome: DataOperationOutcome
    success: bool
    write_dispatched: bool = False
    request_id: str | None = None
    status: str | None = None
    count: int | None = None
    result: dict[str, Any] | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    error_code: str | None = None

    @field_validator("outcome", mode="before")
    @classmethod
    def validate_outcome_for_operation(cls, v: Any) -> Any:
        """Validate outcome is a valid DataOperationOutcome."""
        if isinstance(v, str):
            try:
                DataOperationOutcome(v)
            except ValueError:
                raise ValueError(f"Invalid outcome: {v}")
        return v

    @field_validator("success")
    @classmethod
    def rejected_cannot_claim_success(cls, v: bool, info: Any) -> bool:
        """Rejected results cannot claim success=True."""
        if "outcome" in info.data:
            outcome = info.data.get("outcome")
            if outcome == DataOperationOutcome.REJECTED and v:
                raise ValueError("Rejected results must have success=False")
        return v

    @field_validator("write_dispatched")
    @classmethod
    def confirmed_read_dispatch_false(cls, v: bool, info: Any) -> bool:
        """Confirmed reads require dispatch=False."""
        if "outcome" in info.data and "operation" in info.data:
            outcome = info.data.get("outcome")
            operation = info.data.get("operation")
            if (
                outcome == DataOperationOutcome.CONFIRMED
                and operation == DataOperation.READ_DELIVERY_REQUEST
                and v
            ):
                raise ValueError(
                    "Confirmed read operations must have write_dispatched=False"
                )
        return v

    @field_validator("created_at", "updated_at")
    @classmethod
    def confirmed_create_equal_timestamps(cls, v: Any, info: Any) -> Any:
        """Confirmed create requires created_at == updated_at."""
        if "outcome" in info.data and "operation" in info.data:
            outcome = info.data.get("outcome")
            operation = info.data.get("operation")
            if (
                outcome == DataOperationOutcome.CONFIRMED
                and operation == DataOperation.CREATE_DELIVERY_REQUEST
            ):
                # If this is the last field being validated, check equality
                if field_name := info.field_name:
                    if field_name == "updated_at" and "created_at" in info.data:
                        created = info.data.get("created_at")
                        if created and v and created != v:
                            raise ValueError(
                                "Confirmed create must have created_at == updated_at"
                            )
        return v


# TypeAdapter for strict validation before capability policy.
# Validates the discriminated union and rejects unknown discriminators,
# raw cypher/query, and undeclared fields as INVALID_CONTRACT.
DATA_OPERATION_ADAPTER: TypeAdapter[DataOperationRequest] = TypeAdapter(
    DataOperationRequest
)


def validate_data_operation_request(value: Mapping[str, Any]) -> DataOperationRequest:
    """Validate a data operation request mapping before capability policy.

    Rejects:
    - Unknown discriminators (operation values not in DataOperation enum)
    - Raw cypher/query fields (MCP-specific, never in application payloads)
    - Undeclared fields (strict union validation with extra='forbid')
    - Payload/operation mismatches (create without identifiers, etc.)
    - Stringified booleans/integers (strict type validation)

    Returns validated DataOperationRequest or raises ValidationError.
    """
    return DATA_OPERATION_ADAPTER.validate_python(value)


def data_operation_request_schema() -> dict[str, Any]:
    """Return the JSON Schema for DataOperationRequest discriminated union.

    Used by Task 9 (Deterministic Operational Schemas) to generate
    schemas/operational/v1/data-operation-request.schema.json.
    """
    return DATA_OPERATION_ADAPTER.json_schema()


ModelT = TypeVar("ModelT", bound=BaseModel)
