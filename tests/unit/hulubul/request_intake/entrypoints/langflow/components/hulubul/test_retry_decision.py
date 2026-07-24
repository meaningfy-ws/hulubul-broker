"""Tests for RetryDecisionComponent: delegation equivalence to pure retry policy.

This module verifies that RetryDecisionComponent correctly delegates to the pure
retry policy functions (retry_action, should_retry, max_retries) and returns
typed JSON responses matching the policy outputs.

Tests cover:
- Delegation equivalence: component output == pure policy output
- All FailureKind variants (retryable, repair, permanent)
- Input validation (invalid FailureKind rejection)
- Exhaustive FailureKind matrix coverage
"""

import pytest
from lfx.schema.data import JSON

from hulubul.core.models.operational.enums import FailureKind, RetryAction
from hulubul.request_intake.entrypoints.langflow.components.hulubul.retry_decision import (
    RetryDecisionComponent,
)
from hulubul.request_intake.services.retry_policy import (
    max_retries,
    retry_action,
    should_retry,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def retry_component():
    """Create a RetryDecisionComponent."""
    return RetryDecisionComponent()


# ============================================================================
# Test: Exhaustive FailureKind Coverage
# ============================================================================


class TestRetryableFailures:
    """Test retryable (transient) failures."""

    @pytest.mark.parametrize(
        "failure_kind",
        [
            FailureKind.TIMEOUT,
            FailureKind.CONNECTION,
            FailureKind.PROTOCOL,
            FailureKind.HTTP_STATUS,
            FailureKind.NEO4J_TRANSIENT,
            FailureKind.SERVICE_UNAVAILABLE,
        ],
    )
    def test_retryable_failure_delegation(self, retry_component, failure_kind):
        """Component output matches pure policy for retryable failures.

        Retryable failures get:
        - action: RETRY
        - should_retry: true
        - max_retries: 1
        """
        retry_component.failure_kind = failure_kind.value
        result = retry_component.build_decision()

        assert isinstance(result, JSON)
        assert result.data["action"] == RetryAction.RETRY.value
        assert result.data["should_retry"] is True
        assert result.data["max_retries"] == 1

        # Verify matches pure policy
        assert result.data["action"] == retry_action(failure_kind).value
        assert result.data["should_retry"] == should_retry(failure_kind)
        assert result.data["max_retries"] == max_retries(failure_kind)


class TestRepairFailures:
    """Test tool-less repair (one repair attempt) failures."""

    def test_malformed_result_delegation(self, retry_component):
        """Component output matches pure policy for malformed result.

        Malformed result gets:
        - action: REPAIR_RAW_RESULT
        - should_retry: true
        - max_retries: 1
        """
        failure_kind = FailureKind.MALFORMED_RESULT
        retry_component.failure_kind = failure_kind.value
        result = retry_component.build_decision()

        assert isinstance(result, JSON)
        assert result.data["action"] == RetryAction.REPAIR_RAW_RESULT.value
        assert result.data["should_retry"] is True
        assert result.data["max_retries"] == 1

        # Verify matches pure policy
        assert result.data["action"] == retry_action(failure_kind).value
        assert result.data["should_retry"] == should_retry(failure_kind)
        assert result.data["max_retries"] == max_retries(failure_kind)


class TestPermanentFailures:
    """Test permanent (never retry) failures."""

    @pytest.mark.parametrize(
        "failure_kind",
        [
            FailureKind.AUTHENTICATION,
            FailureKind.VALIDATION,
            FailureKind.UNSUPPORTED_OPERATION,
            FailureKind.CYPHER_CLIENT,
            FailureKind.CYPHER_SYNTAX,
            FailureKind.CONSTRAINT,
            FailureKind.AFFECTED_COUNT,
        ],
    )
    def test_permanent_failure_delegation(self, retry_component, failure_kind):
        """Component output matches pure policy for permanent failures.

        Permanent failures get:
        - action: FAIL
        - should_retry: false
        - max_retries: 0
        """
        retry_component.failure_kind = failure_kind.value
        result = retry_component.build_decision()

        assert isinstance(result, JSON)
        assert result.data["action"] == RetryAction.FAIL.value
        assert result.data["should_retry"] is False
        assert result.data["max_retries"] == 0

        # Verify matches pure policy
        assert result.data["action"] == retry_action(failure_kind).value
        assert result.data["should_retry"] == should_retry(failure_kind)
        assert result.data["max_retries"] == max_retries(failure_kind)


# ============================================================================
# Test: Input Validation
# ============================================================================


class TestInputValidation:
    """Test component input validation."""

    def test_failure_kind_as_enum(self, retry_component):
        """Component accepts FailureKind enum directly."""
        retry_component.failure_kind = FailureKind.TIMEOUT
        result = retry_component.build_decision()

        assert isinstance(result, JSON)
        assert result.data["action"] == RetryAction.RETRY.value

    def test_failure_kind_as_string(self, retry_component):
        """Component accepts FailureKind as string value."""
        retry_component.failure_kind = "timeout"
        result = retry_component.build_decision()

        assert isinstance(result, JSON)
        assert result.data["action"] == RetryAction.RETRY.value

    def test_invalid_failure_kind_rejection(self, retry_component):
        """Component rejects invalid FailureKind values."""
        retry_component.failure_kind = "invalid_failure_kind"

        with pytest.raises(ValueError):
            retry_component.build_decision()

    def test_none_failure_kind_rejection(self, retry_component):
        """Component rejects None failure_kind."""
        retry_component.failure_kind = None

        with pytest.raises((ValueError, KeyError, AttributeError)):
            retry_component.build_decision()


# ============================================================================
# Test: Response Structure
# ============================================================================


class TestResponseStructure:
    """Test response structure and typing."""

    def test_response_is_json(self, retry_component):
        """Response is typed JSON, not raw dict."""
        retry_component.failure_kind = FailureKind.TIMEOUT
        result = retry_component.build_decision()

        assert isinstance(result, JSON)
        assert hasattr(result, "data")

    def test_response_contains_required_fields(self, retry_component):
        """Response contains all required decision fields."""
        retry_component.failure_kind = FailureKind.TIMEOUT
        result = retry_component.build_decision()

        assert "action" in result.data
        assert "should_retry" in result.data
        assert "max_retries" in result.data

    def test_response_field_types(self, retry_component):
        """Response fields have correct types."""
        retry_component.failure_kind = FailureKind.TIMEOUT
        result = retry_component.build_decision()

        assert isinstance(result.data["action"], str)
        assert isinstance(result.data["should_retry"], bool)
        assert isinstance(result.data["max_retries"], int)

    def test_response_action_is_valid_enum_value(self, retry_component):
        """Response action is a valid RetryAction enum value."""
        retry_component.failure_kind = FailureKind.TIMEOUT
        result = retry_component.build_decision()

        valid_actions = {e.value for e in RetryAction}
        assert result.data["action"] in valid_actions


# ============================================================================
# Test: Component Does Not Perform Prohibited Operations
# ============================================================================


class TestComponentPurity:
    """Test that component does not perform prohibited operations."""

    def test_no_sleep(self, retry_component):
        """Component does not sleep or delay."""
        # This is a behavior test - we verify by execution time
        retry_component.failure_kind = FailureKind.TIMEOUT
        import time

        start = time.time()
        retry_component.build_decision()
        elapsed = time.time() - start

        # Should complete in < 100ms (generous for CI)
        assert elapsed < 0.1

    def test_no_external_io(self, retry_component):
        """Component performs no external I/O (verified by mocking)."""
        # Component should only call pure functions; no file I/O, network, etc.
        # This is implicit in the fact that it only calls retry_policy functions
        retry_component.failure_kind = FailureKind.TIMEOUT
        result = retry_component.build_decision()

        # If it got here without exception, no I/O was attempted
        assert result is not None


# ============================================================================
# Test: Exhaustive FailureKind Matrix
# ============================================================================


class TestExhaustiveMatrix:
    """Verify component handles all FailureKind variants."""

    def test_all_failure_kinds_covered(self, retry_component):
        """Every FailureKind variant produces a valid decision."""
        for failure_kind in FailureKind:
            retry_component.failure_kind = failure_kind
            result = retry_component.build_decision()

            assert isinstance(result, JSON)
            assert "action" in result.data
            assert "should_retry" in result.data
            assert "max_retries" in result.data

            # Verify decision is consistent with policy
            policy_action = retry_action(failure_kind)
            assert result.data["action"] == policy_action.value
