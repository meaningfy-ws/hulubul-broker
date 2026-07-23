"""Tests for operational error codes and error policy."""

from uuid import UUID

import pytest
from pydantic import ValidationError

from hulubul.core.models.operational.base import StrictModel
from hulubul.core.models.operational.enums import ErrorCategory, ErrorCode, ErrorEscalation
from hulubul.core.models.operational.errors import (
    ERROR_POLICY,
    OperationalError,
    validation_error_to_operational_error,
)


class TestErrorCodeEnum:
    """ErrorCode must contain all 21 required error codes."""

    def test_has_all_required_codes(self) -> None:
        """ErrorCode must have exactly the 21 required codes."""
        required_codes = {
            "INVALID_INPUT",
            "INVALID_CONTRACT",
            "OPERATION_NOT_ALLOWED",
            "BINDING_REQUEST_MISMATCH",
            "GRAPH_CONTEXT_INCONSISTENT",
            "UNSUPPORTED_PHASE1_STATUS",
            "UNSUPPORTED_REQUEST_STATUS",
            "INVALID_EXPECTED_STATUS",
            "INVALID_STATUS_TRANSITION",
            "CONCURRENT_MODIFICATION",
            "AFFECTED_RECORD_COUNT_MISMATCH",
            "MODEL_TRANSIENT_FAILURE",
            "MODEL_AUTHENTICATION_FAILURE",
            "MALFORMED_AGENT_RESULT",
            "MCP_READ_TRANSIENT_FAILURE",
            "MCP_WRITE_AMBIGUOUS",
            "MCP_AUTHENTICATION_FAILURE",
            "MCP_OPERATION_FAILURE",
            "DEPENDENCY_UNAVAILABLE",
        }

        error_codes = {code.name for code in ErrorCode}
        assert error_codes == required_codes

    @pytest.mark.parametrize("code", tuple(ErrorCode))
    def test_every_error_code_has_policy(self, code: ErrorCode) -> None:
        """Every ErrorCode must have one policy row in ERROR_POLICY."""
        assert code in ERROR_POLICY
        policy = ERROR_POLICY[code]
        assert policy.code is code


class TestErrorPolicy:
    """ERROR_POLICY must contain exhaustive, immutable, canonical row data."""

    def test_policy_dict_is_complete(self) -> None:
        """ERROR_POLICY must have a policy for every ErrorCode."""
        for code in ErrorCode:
            assert code in ERROR_POLICY

    def test_policy_rows_have_required_fields(self) -> None:
        """Each policy row must have category, retryable, message, and escalation."""
        for code, policy in ERROR_POLICY.items():
            assert policy.code is code
            assert isinstance(policy.category, ErrorCategory)
            assert isinstance(policy.retryable, bool)
            assert isinstance(policy.safe_message, str)
            assert len(policy.safe_message) > 0
            assert isinstance(policy.log_level, str)
            assert policy.log_level in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
            assert isinstance(policy.log_fields, tuple)
            assert len(policy.log_fields) > 0
            assert all(isinstance(f, str) for f in policy.log_fields)
            assert isinstance(policy.escalation, ErrorEscalation)

    def test_policy_category_values_are_valid(self) -> None:
        """All category values must be from ErrorCategory enum."""
        valid_categories = set(ErrorCategory)
        for policy in ERROR_POLICY.values():
            assert policy.category in valid_categories

    def test_policy_escalation_values_are_valid(self) -> None:
        """All escalation values must be from ErrorEscalation enum."""
        valid_escalations = set(ErrorEscalation)
        for policy in ERROR_POLICY.values():
            assert policy.escalation in valid_escalations

    def test_policy_log_fields_from_allowlist(self) -> None:
        """All log fields must come from the allowed set."""
        allowed_fields = {
            "correlation_id",
            "operation_id",
            "request_id",
            "session_id",
            "flow_id",
            "component_id",
            "retry_attempt",
            "error_code",
            "schema_version",
        }

        for policy in ERROR_POLICY.values():
            for field in policy.log_fields:
                msg = f"Policy {policy.code} has disallowed field: {field}"
                assert field in allowed_fields, msg

    def test_controlled_errors_have_required_fields_always_available(self) -> None:
        """Controlled errors must always have correlation_id and error_code."""
        required_always = {
            "correlation_id",
            "error_code",
            "schema_version",
        }

        for policy in ERROR_POLICY.values():
            for field in required_always:
                assert field in policy.log_fields, (
                    f"Policy {policy.code} missing required field: {field}"
                )

    def test_specific_error_code_policies(self) -> None:
        """Test specific error codes have correct policy data."""
        # INVALID_INPUT
        invalid_input = ERROR_POLICY[ErrorCode.INVALID_INPUT]
        assert invalid_input.category == ErrorCategory.INPUT
        assert invalid_input.retryable is False
        assert invalid_input.log_level == "WARNING"
        assert "correlation_id" in invalid_input.log_fields
        assert "operation_id" not in invalid_input.log_fields

        # MODEL_TRANSIENT_FAILURE (retryable)
        model_transient = ERROR_POLICY[ErrorCode.MODEL_TRANSIENT_FAILURE]
        assert model_transient.category == ErrorCategory.DEPENDENCY
        assert model_transient.retryable is True
        assert model_transient.log_level == "ERROR"
        assert "retry_attempt" in model_transient.log_fields

        # MCP_WRITE_AMBIGUOUS (special escalation)
        mcp_ambiguous = ERROR_POLICY[ErrorCode.MCP_WRITE_AMBIGUOUS]
        assert mcp_ambiguous.escalation == ErrorEscalation.MANUAL_AMBIGUOUS_WRITE_GRAPH_INSPECTION


class TestOperationalError:
    """OperationalError enforces strict contract."""

    def test_rejects_noncanonical_message(self) -> None:
        """OperationalError must reject message different from policy."""
        # Try to create with wrong message
        with pytest.raises(ValidationError):
            OperationalError(  # type: ignore[call-arg]
                code=ErrorCode.INVALID_INPUT,
                message="Wrong message",
                correlation_id=UUID("12345678-1234-5678-1234-567812345678"),
            )

    def test_rejects_noncanonical_category(self) -> None:
        """OperationalError must reject category different from policy."""
        # Try to create with wrong category
        with pytest.raises(ValidationError):
            OperationalError(  # type: ignore[call-arg]
                code=ErrorCode.INVALID_INPUT,
                category=ErrorCategory.DEPENDENCY,  # Wrong category
                message=ERROR_POLICY[ErrorCode.INVALID_INPUT].safe_message,
                correlation_id=UUID("12345678-1234-5678-1234-567812345678"),
            )

    def test_rejects_noncanonical_retryable(self) -> None:
        """OperationalError must reject retryable different from policy."""
        # Try to create with wrong retryable value
        with pytest.raises(ValidationError):
            OperationalError(
                code=ErrorCode.INVALID_INPUT,
                category=ErrorCategory.INPUT,
                message=ERROR_POLICY[ErrorCode.INVALID_INPUT].safe_message,
                retryable=True,  # Wrong value (should be False)
                correlation_id=UUID("12345678-1234-5678-1234-567812345678"),
            )

    def test_accepts_canonical_error(self) -> None:
        """OperationalError must accept canonical policy values."""
        policy = ERROR_POLICY[ErrorCode.INVALID_INPUT]
        error = OperationalError(
            code=ErrorCode.INVALID_INPUT,
            category=policy.category,
            message=policy.safe_message,
            retryable=policy.retryable,
            correlation_id=UUID("12345678-1234-5678-1234-567812345678"),
        )
        assert error.code == ErrorCode.INVALID_INPUT
        assert error.message == policy.safe_message

    def test_is_frozen(self) -> None:
        """OperationalError must be frozen."""
        policy = ERROR_POLICY[ErrorCode.INVALID_INPUT]
        error = OperationalError(
            code=ErrorCode.INVALID_INPUT,
            category=policy.category,
            message=policy.safe_message,
            retryable=policy.retryable,
            correlation_id=UUID("12345678-1234-5678-1234-567812345678"),
        )

        with pytest.raises((ValidationError, Exception)):
            error.message = "changed"


class TestValidationErrorConversion:
    """validation_error_to_operational_error must convert Pydantic ValidationError correctly."""

    def test_converts_validation_error(self) -> None:
        """validation_error_to_operational_error converts ValidationError."""

        class TestModel(StrictModel):
            count: int

        try:
            TestModel(count="not-an-int")  # type: ignore[arg-type]
        except ValidationError as e:
            error = validation_error_to_operational_error(
                e, correlation_id=UUID("12345678-1234-5678-1234-567812345678")
            )

            assert isinstance(error, OperationalError)
            assert error.code == ErrorCode.INVALID_CONTRACT
            assert error.correlation_id == UUID("12345678-1234-5678-1234-567812345678")

    def test_records_pydantic_rule_ids_only(self) -> None:
        """Conversion must record only Pydantic rule IDs, never rejected values."""

        class TestModel(StrictModel):
            text: str

        try:
            TestModel(text="")  # string_type validation
        except ValidationError as e:
            error = validation_error_to_operational_error(
                e, correlation_id=UUID("12345678-1234-5678-1234-567812345678")
            )

            # Error should not contain the actual rejected value
            assert error.violations is not None
            # Violations should only reference rule IDs/normalized locations
            for violation in error.violations:
                # Rule ID should be present (e.g., "string_type", "value_error")
                assert violation.rule_id is not None
                # Violated value should not be stored
                assert not hasattr(violation, "violated_value")

    def test_omits_unavailable_identifiers_from_violations(self) -> None:
        """Violations must not fabricate unavailable identifiers."""

        class TestModel(StrictModel):
            count: int

        try:
            TestModel(count="not-an-int")  # type: ignore[arg-type]
        except ValidationError as e:
            error = validation_error_to_operational_error(
                e, correlation_id=UUID("12345678-1234-5678-1234-567812345678")
            )

            # Should have no request_id or operation_id
            for violation in error.violations:
                # These fields should be absent, not null
                assert not hasattr(violation, "request_id") or violation.request_id is None  # type: ignore[attr-defined]
                assert not hasattr(violation, "operation_id") or violation.operation_id is None  # type: ignore[attr-defined]
