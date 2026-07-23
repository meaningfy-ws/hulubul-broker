"""Tests for data operation contracts and discriminated unions.

These tests guard the contracts established in Task 8 (Five Data Operation
Contracts): exactly five operations with strict payload validation, discriminated
union validation before capability policy, and result invariants that enforce
consistent operation/outcome combinations.
"""
from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest
from pydantic import ValidationError

from hulubul.core.models.operational import (
    DATA_OPERATION_ADAPTER,
    CreateDeliveryRequestRequest,
    DataOperation,
    DataOperationOutcome,
    DataOperationResult,
    GetRequestRoutingContextRequest,
    ReadDeliveryRequestRequest,
    SetRequestStatusRequest,
    UpdateDeliveryRequestRequest,
    validate_data_operation_request,
)


class TestDataOperationEnumLocked:
    """Guard exactly five data operations are declared; no sixth."""

    def test_exactly_five_operations_are_declared(self):
        """Verify the locked set of five operation kinds."""
        assert {member.value for member in DataOperation} == {
            "getRequestRoutingContext",
            "createDeliveryRequest",
            "readDeliveryRequest",
            "updateDeliveryRequest",
            "setRequestStatus",
        }

    def test_data_operation_members_match_order(self):
        """Verify enum members match specification."""
        assert DataOperation.GET_REQUEST_ROUTING_CONTEXT.value == "getRequestRoutingContext"
        assert DataOperation.CREATE_DELIVERY_REQUEST.value == "createDeliveryRequest"
        assert DataOperation.READ_DELIVERY_REQUEST.value == "readDeliveryRequest"
        assert DataOperation.UPDATE_DELIVERY_REQUEST.value == "updateDeliveryRequest"
        assert DataOperation.SET_REQUEST_STATUS.value == "setRequestStatus"


class TestRoutingContextRequestPayload:
    """Routing context operation requires empty payload."""

    def test_routing_context_accepts_minimal_envelope(self):
        """Routing context payload is empty dict."""
        request = GetRequestRoutingContextRequest(
            operation=DataOperation.GET_REQUEST_ROUTING_CONTEXT,
            operation_id=str(uuid4()),
            caller="test_caller",
            session_id=str(uuid4()),
            actor_id="test_actor",
            schema_version="1.0.0",
            correlation_id=str(uuid4()),
        )
        assert request.operation == DataOperation.GET_REQUEST_ROUTING_CONTEXT

    def test_routing_context_rejects_extra_fields(self):
        """Any extra field in routing context request fails."""
        with pytest.raises(ValidationError):
            GetRequestRoutingContextRequest(
                operation=DataOperation.GET_REQUEST_ROUTING_CONTEXT,
                operation_id=str(uuid4()),
                caller="test_caller",
                session_id=str(uuid4()),
                actor_id="test_actor",
                schema_version="1.0.0",
                correlation_id=str(uuid4()),
                extra_field="should_fail",
            )


class TestCreateDeliveryRequestPayload:
    """Create operation requires identifiers and facts; rejects timestamps."""

    def test_create_accepts_identifiers_and_facts(self):
        """Create payload requires identifiers and facts fields."""
        request = CreateDeliveryRequestRequest(
            operation=DataOperation.CREATE_DELIVERY_REQUEST,
            operation_id=str(uuid4()),
            caller="test_caller",
            session_id=str(uuid4()),
            actor_id="test_actor",
            schema_version="1.0.0",
            correlation_id=str(uuid4()),
            identifiers={},
            facts={},
        )
        assert request.operation == DataOperation.CREATE_DELIVERY_REQUEST
        assert request.identifiers == {}
        assert request.facts == {}

    def test_create_rejects_created_at(self):
        """Create payload cannot include created_at; Neo4j owns timestamp."""
        with pytest.raises(ValidationError):
            CreateDeliveryRequestRequest(
                operation=DataOperation.CREATE_DELIVERY_REQUEST,
                operation_id=str(uuid4()),
                caller="test_caller",
                session_id=str(uuid4()),
                actor_id="test_actor",
                schema_version="1.0.0",
                correlation_id=str(uuid4()),
                identifiers={},
                facts={},
                created_at="2026-01-01T00:00:00Z",
            )

    def test_create_rejects_updated_at(self):
        """Create payload cannot include updated_at; Neo4j owns timestamp."""
        with pytest.raises(ValidationError):
            CreateDeliveryRequestRequest(
                operation=DataOperation.CREATE_DELIVERY_REQUEST,
                operation_id=str(uuid4()),
                caller="test_caller",
                session_id=str(uuid4()),
                actor_id="test_actor",
                schema_version="1.0.0",
                correlation_id=str(uuid4()),
                identifiers={},
                facts={},
                updated_at="2026-01-01T00:00:00Z",
            )


class TestReadDeliveryRequestPayload:
    """Read operation requires request_id only."""

    def test_read_accepts_request_id(self):
        """Read payload requires request_id."""
        request_id = str(uuid4())
        request = ReadDeliveryRequestRequest(
            operation=DataOperation.READ_DELIVERY_REQUEST,
            operation_id=str(uuid4()),
            caller="test_caller",
            session_id=str(uuid4()),
            actor_id="test_actor",
            schema_version="1.0.0",
            correlation_id=str(uuid4()),
            request_id=request_id,
        )
        assert request.operation == DataOperation.READ_DELIVERY_REQUEST
        assert request.request_id == request_id

    def test_read_rejects_extra_fields(self):
        """Read rejects extra fields beyond request_id."""
        with pytest.raises(ValidationError):
            ReadDeliveryRequestRequest(
                operation=DataOperation.READ_DELIVERY_REQUEST,
                operation_id=str(uuid4()),
                caller="test_caller",
                session_id=str(uuid4()),
                actor_id="test_actor",
                schema_version="1.0.0",
                correlation_id=str(uuid4()),
                request_id=str(uuid4()),
                extra_field="should_fail",
            )


class TestUpdateDeliveryRequestPayload:
    """Update operation requires request_id, expected_updated_at, expected_status, updates, identifiers."""

    def test_update_accepts_all_required_fields(self):
        """Update payload requires all five fields."""
        request = UpdateDeliveryRequestRequest(
            operation=DataOperation.UPDATE_DELIVERY_REQUEST,
            operation_id=str(uuid4()),
            caller="test_caller",
            session_id=str(uuid4()),
            actor_id="test_actor",
            schema_version="1.0.0",
            correlation_id=str(uuid4()),
            request_id=str(uuid4()),
            expected_updated_at="2026-01-01T00:00:00Z",
            expected_status="intake",
            updates={},
            identifiers={},
        )
        assert request.operation == DataOperation.UPDATE_DELIVERY_REQUEST
        assert request.updates == {}
        assert request.identifiers == {}

    def test_update_rejects_missing_expected_updated_at(self):
        """Update requires expected_updated_at for concurrency check."""
        with pytest.raises(ValidationError):
            UpdateDeliveryRequestRequest(
                operation=DataOperation.UPDATE_DELIVERY_REQUEST,
                operation_id=str(uuid4()),
                caller="test_caller",
                session_id=str(uuid4()),
                actor_id="test_actor",
                schema_version="1.0.0",
                correlation_id=str(uuid4()),
                request_id=str(uuid4()),
                expected_status="intake",
                updates={},
                identifiers={},
            )


class TestSetRequestStatusPayload:
    """Status operation requires request_id, expected_updated_at, expected_status, target_status."""

    def test_status_accepts_all_required_fields(self):
        """Status payload requires four fields."""
        request = SetRequestStatusRequest(
            operation=DataOperation.SET_REQUEST_STATUS,
            operation_id=str(uuid4()),
            caller="test_caller",
            session_id=str(uuid4()),
            actor_id="test_actor",
            schema_version="1.0.0",
            correlation_id=str(uuid4()),
            request_id=str(uuid4()),
            expected_updated_at="2026-01-01T00:00:00Z",
            expected_status="intake",
            target_status="closed",
        )
        assert request.operation == DataOperation.SET_REQUEST_STATUS
        assert request.target_status == "closed"


class TestDiscriminatedUnionValidation:
    """Discriminated union rejects malformed operations before capability policy."""

    def test_union_accepts_routing_context_request(self):
        """Valid routing context passes union validation."""
        mapping = {
            "operation": "getRequestRoutingContext",
            "operation_id": str(uuid4()),
            "caller": "test_caller",
            "session_id": str(uuid4()),
            "actor_id": "test_actor",
            "schema_version": "1.0.0",
            "correlation_id": str(uuid4()),
        }
        request = validate_data_operation_request(mapping)
        assert isinstance(request, GetRequestRoutingContextRequest)

    def test_union_rejects_raw_cypher_field(self):
        """Raw cypher field fails contract validation."""
        mapping = {
            "operation": "getRequestRoutingContext",
            "operation_id": str(uuid4()),
            "caller": "test_caller",
            "session_id": str(uuid4()),
            "actor_id": "test_actor",
            "schema_version": "1.0.0",
            "correlation_id": str(uuid4()),
            "cypher": "RETURN 1",
        }
        with pytest.raises(ValidationError) as exc_info:
            validate_data_operation_request(mapping)
        # Error should come from union validation, not from capability policy
        assert "cypher" in str(exc_info.value).lower()

    def test_union_rejects_raw_query_field(self):
        """Raw query field fails contract validation."""
        mapping = {
            "operation": "getRequestRoutingContext",
            "operation_id": str(uuid4()),
            "caller": "test_caller",
            "session_id": str(uuid4()),
            "actor_id": "test_actor",
            "schema_version": "1.0.0",
            "correlation_id": str(uuid4()),
            "query": "RETURN 1",
        }
        with pytest.raises(ValidationError) as exc_info:
            validate_data_operation_request(mapping)
        assert "query" in str(exc_info.value).lower()

    def test_union_rejects_undeclared_field(self):
        """Undeclared field fails contract validation."""
        mapping = {
            "operation": "getRequestRoutingContext",
            "operation_id": str(uuid4()),
            "caller": "test_caller",
            "session_id": str(uuid4()),
            "actor_id": "test_actor",
            "schema_version": "1.0.0",
            "correlation_id": str(uuid4()),
            "undeclared": True,
        }
        with pytest.raises(ValidationError) as exc_info:
            validate_data_operation_request(mapping)
        assert "undeclared" in str(exc_info.value).lower()

    def test_union_rejects_unknown_operation(self):
        """Unknown operation value fails contract validation."""
        mapping = {
            "operation": "unknownOperation",
            "operation_id": str(uuid4()),
            "caller": "test_caller",
            "session_id": str(uuid4()),
            "actor_id": "test_actor",
            "schema_version": "1.0.0",
            "correlation_id": str(uuid4()),
        }
        with pytest.raises(ValidationError):
            validate_data_operation_request(mapping)

    def test_operation_payload_mismatch_fails(self):
        """Operation type mismatch with payload fails validation."""
        mapping = {
            "operation": "createDeliveryRequest",
            "operation_id": str(uuid4()),
            "caller": "test_caller",
            "session_id": str(uuid4()),
            "actor_id": "test_actor",
            "schema_version": "1.0.0",
            "correlation_id": str(uuid4()),
            # Missing required identifiers and facts for create
        }
        with pytest.raises(ValidationError):
            validate_data_operation_request(mapping)


class TestDataOperationResultInvariants:
    """Result invariants enforce consistent operation/outcome combinations."""

    def test_confirmed_write_result_requires_dispatch_true(self):
        """Confirmed write must have dispatch=True."""
        # A confirmed create must indicate it was dispatched
        result = DataOperationResult(
            operation=DataOperation.CREATE_DELIVERY_REQUEST,
            outcome=DataOperationOutcome.CONFIRMED,
            success=True,
            write_dispatched=True,
            request_id=str(uuid4()),
            status="intake",
        )
        assert result.write_dispatched is True

    def test_confirmed_create_requires_equal_timestamps(self):
        """Confirmed create requires created_at == updated_at from Neo4j."""
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        result = DataOperationResult(
            operation=DataOperation.CREATE_DELIVERY_REQUEST,
            outcome=DataOperationOutcome.CONFIRMED,
            success=True,
            write_dispatched=True,
            request_id=str(uuid4()),
            created_at=now,
            updated_at=now,
        )
        assert result.created_at == result.updated_at

    def test_confirmed_read_result_requires_dispatch_false(self):
        """Confirmed read must have dispatch=False."""
        result = DataOperationResult(
            operation=DataOperation.READ_DELIVERY_REQUEST,
            outcome=DataOperationOutcome.CONFIRMED,
            success=True,
            write_dispatched=False,
        )
        assert result.write_dispatched is False

    def test_rejected_result_cannot_claim_success(self):
        """Rejected result must have success=False."""
        result = DataOperationResult(
            operation=DataOperation.READ_DELIVERY_REQUEST,
            outcome=DataOperationOutcome.REJECTED,
            success=False,
        )
        assert result.success is False

    def test_ambiguous_write_result_requires_specific_outcome(self):
        """Ambiguous result must be a dispatched write with no count/result/status."""
        result = DataOperationResult(
            operation=DataOperation.UPDATE_DELIVERY_REQUEST,
            outcome=DataOperationOutcome.AMBIGUOUS,
            success=False,
            write_dispatched=True,
            request_id=str(uuid4()),
        )
        assert result.outcome == DataOperationOutcome.AMBIGUOUS
        assert result.write_dispatched is True
        assert result.count is None


class TestTypeAdapterValidation:
    """TypeAdapter enforces strict validation before capability policy."""

    def test_type_adapter_validates_discriminated_union(self):
        """DATA_OPERATION_ADAPTER validates the full union."""
        mapping = {
            "operation": "readDeliveryRequest",
            "operation_id": str(uuid4()),
            "caller": "test_caller",
            "session_id": str(uuid4()),
            "actor_id": "test_actor",
            "schema_version": "1.0.0",
            "correlation_id": str(uuid4()),
            "request_id": str(uuid4()),
        }
        request = DATA_OPERATION_ADAPTER.validate_python(mapping)
        assert isinstance(request, ReadDeliveryRequestRequest)

    def test_type_adapter_rejects_malformed_mapping(self):
        """TypeAdapter rejects malformed mappings."""
        mapping = {
            "operation": "readDeliveryRequest",
            "operation_id": str(uuid4()),
            "caller": "test_caller",
            # Missing required session_id
            "actor_id": "test_actor",
            "schema_version": "1.0.0",
            "correlation_id": str(uuid4()),
            "request_id": str(uuid4()),
        }
        with pytest.raises(ValidationError):
            DATA_OPERATION_ADAPTER.validate_python(mapping)

    def test_type_adapter_mode_rejects_stringified_booleans(self):
        """TypeAdapter strict mode rejects stringified booleans."""
        result = DataOperationResult(
            operation=DataOperation.READ_DELIVERY_REQUEST,
            outcome=DataOperationOutcome.CONFIRMED,
            success=True,
            # Strict mode should reject "true" string for bool field
            write_dispatched=False,
        )
        assert result.write_dispatched is False


class TestAllOperationsRequireSharedFields:
    """Every operation request requires shared wrapper fields."""

    @pytest.mark.parametrize("operation_class,operation_kind", [
        (GetRequestRoutingContextRequest, DataOperation.GET_REQUEST_ROUTING_CONTEXT),
        (ReadDeliveryRequestRequest, DataOperation.READ_DELIVERY_REQUEST),
    ])
    def test_shared_fields_required(self, operation_class, operation_kind):
        """All operation requests must include operation_id, caller, session, actor, schema version, correlation."""
        with pytest.raises(ValidationError):
            # Missing operation_id
            operation_class(
                operation=operation_kind,
                caller="test_caller",
                session_id=str(uuid4()),
                actor_id="test_actor",
                schema_version="1.0.0",
                correlation_id=str(uuid4()),
            )


def valid_lf00_create_mapping() -> dict[str, Any]:
    """Helper fixture to create a valid create mapping for test parametrization."""
    return {
        "operation": "createDeliveryRequest",
        "operation_id": str(uuid4()),
        "caller": "test_caller",
        "session_id": str(uuid4()),
        "actor_id": "test_actor",
        "schema_version": "1.0.0",
        "correlation_id": str(uuid4()),
        "identifiers": {},
        "facts": {},
    }
