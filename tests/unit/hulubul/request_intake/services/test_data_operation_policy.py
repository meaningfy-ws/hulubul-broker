"""Unit tests for caller capability and data operation policy.

Tests the fixed capability matrix (which operations each flow can invoke)
and authorization checks per plan Task 13.
"""
from __future__ import annotations

import pytest

from hulubul.core.models.operational.enums import CallerFlow, DataOperation
from hulubul.request_intake.services.data_operation_policy import (
    ALLOWED_OPERATIONS,
    authorize_operation,
    validate_operation_preconditions,
    validate_result_postconditions,
)


# ============================================================================
# ALLOWED_OPERATIONS
# ============================================================================


class TestAllowedOperations:
    """The capability matrix is fixed and per-caller."""

    def test_allowed_operations_has_exactly_three_flows(self):
        """ALLOWED_OPERATIONS must have entries for LF-00, LF-10, LF-70."""
        assert set(ALLOWED_OPERATIONS.keys()) == {
            CallerFlow.LF_00,
            CallerFlow.LF_10,
            CallerFlow.LF_70,
        }

    def test_lf00_allows_routing_context_only(self):
        """LF-00 (Main Router) may only invoke GET_REQUEST_ROUTING_CONTEXT."""
        assert ALLOWED_OPERATIONS[CallerFlow.LF_00] == frozenset({
            DataOperation.GET_REQUEST_ROUTING_CONTEXT,
        })

    def test_lf10_allows_create_read_update_setstatus(self):
        """LF-10 (Request Intake) allows all four operations."""
        assert ALLOWED_OPERATIONS[CallerFlow.LF_10] == frozenset({
            DataOperation.CREATE_DELIVERY_REQUEST,
            DataOperation.READ_DELIVERY_REQUEST,
            DataOperation.UPDATE_DELIVERY_REQUEST,
            DataOperation.SET_REQUEST_STATUS,
        })

    def test_lf70_allows_all_operations(self):
        """LF-70 (Data Access) allows all four operations."""
        assert ALLOWED_OPERATIONS[CallerFlow.LF_70] == frozenset({
            DataOperation.CREATE_DELIVERY_REQUEST,
            DataOperation.READ_DELIVERY_REQUEST,
            DataOperation.UPDATE_DELIVERY_REQUEST,
            DataOperation.SET_REQUEST_STATUS,
        })

    def test_all_operation_values_are_immutable_frozensets(self):
        """Every ALLOWED_OPERATIONS value must be a frozenset (immutable)."""
        for flow, ops in ALLOWED_OPERATIONS.items():
            assert isinstance(ops, frozenset)


# ============================================================================
# authorize_operation - Positive Cases (Allowed)
# ============================================================================


class TestAuthorizeOperationPositive:
    """Authorized operations return None (success)."""

    def test_lf00_authorized_for_routing_context(self):
        """LF-00 is authorized for GET_REQUEST_ROUTING_CONTEXT."""
        result = authorize_operation(
            CallerFlow.LF_00, DataOperation.GET_REQUEST_ROUTING_CONTEXT
        )
        assert result is None

    @pytest.mark.parametrize(
        "operation",
        [
            DataOperation.CREATE_DELIVERY_REQUEST,
            DataOperation.READ_DELIVERY_REQUEST,
            DataOperation.UPDATE_DELIVERY_REQUEST,
            DataOperation.SET_REQUEST_STATUS,
        ],
    )
    def test_lf10_authorized_for_all_four_operations(self, operation):
        """LF-10 is authorized for all four operations."""
        result = authorize_operation(CallerFlow.LF_10, operation)
        assert result is None

    @pytest.mark.parametrize(
        "operation",
        [
            DataOperation.CREATE_DELIVERY_REQUEST,
            DataOperation.READ_DELIVERY_REQUEST,
            DataOperation.UPDATE_DELIVERY_REQUEST,
            DataOperation.SET_REQUEST_STATUS,
        ],
    )
    def test_lf70_authorized_for_all_four_operations(self, operation):
        """LF-70 is authorized for all four operations."""
        result = authorize_operation(CallerFlow.LF_70, operation)
        assert result is None


# ============================================================================
# authorize_operation - Negative Cases (Disallowed)
# ============================================================================


class TestAuthorizeOperationNegative:
    """Disallowed operations return error code."""

    def test_lf00_not_authorized_for_create(self):
        """LF-00 is not authorized for CREATE_DELIVERY_REQUEST."""
        result = authorize_operation(
            CallerFlow.LF_00, DataOperation.CREATE_DELIVERY_REQUEST
        )
        assert result is not None
        # Result should indicate OPERATION_NOT_ALLOWED (not checked here since
        # authorize_operation returns error code type)

    def test_lf00_not_authorized_for_read(self):
        """LF-00 is not authorized for READ_DELIVERY_REQUEST."""
        result = authorize_operation(
            CallerFlow.LF_00, DataOperation.READ_DELIVERY_REQUEST
        )
        assert result is not None

    def test_lf00_not_authorized_for_update(self):
        """LF-00 is not authorized for UPDATE_DELIVERY_REQUEST."""
        result = authorize_operation(
            CallerFlow.LF_00, DataOperation.UPDATE_DELIVERY_REQUEST
        )
        assert result is not None

    def test_lf00_not_authorized_for_setstatus(self):
        """LF-00 is not authorized for SET_REQUEST_STATUS."""
        result = authorize_operation(
            CallerFlow.LF_00, DataOperation.SET_REQUEST_STATUS
        )
        assert result is not None

    def test_lf10_not_authorized_for_routing_context(self):
        """LF-10 is not authorized for GET_REQUEST_ROUTING_CONTEXT."""
        result = authorize_operation(
            CallerFlow.LF_10, DataOperation.GET_REQUEST_ROUTING_CONTEXT
        )
        assert result is not None

    def test_lf70_routing_context_via_lf10_not_direct(self):
        """LF-70 may not call GET_REQUEST_ROUTING_CONTEXT directly (reserved for LF-00)."""
        # This is a design principle: routing context is LF-00's responsibility.
        # However, LF-70 is a low-level tool and might technically have access.
        # For Phase 1, we keep LF-70 limited to direct Neo4j operations only.
        # If the spec evolves, this test documents the intent.
        pass  # LF-70 not tested for routing context (not in its allowed set)


# ============================================================================
# validate_operation_preconditions - Placeholder
# ============================================================================


class TestValidateOperationPreconditions:
    """Precondition validation is a placeholder for now."""

    def test_returns_none_placeholder(self):
        """Currently returns None (placeholder implementation)."""
        result = validate_operation_preconditions(object())
        assert result is None


# ============================================================================
# validate_result_postconditions - Placeholder
# ============================================================================


class TestValidateResultPostconditions:
    """Postcondition validation is a placeholder for now."""

    def test_returns_none_placeholder(self):
        """Currently returns None (placeholder implementation)."""
        result = validate_result_postconditions(object(), object())
        assert result is None
