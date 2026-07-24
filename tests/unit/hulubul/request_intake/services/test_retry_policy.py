"""Unit tests for the retry policy service.

Covers the exhaustive FailureKind -> retry decision matrix (transient retry,
permanent fail, and the one tool-less MALFORMED_RESULT repair) per plan
Task 14 and DEC-015 (design.md): retryable reads/model calls get exactly one
retry after a fixed delay, permanent failures never retry, and a malformed
result gets one tool-less repair attempt instead of a replay. The service
never decides to replay a dispatched write; callers own that prohibition
using the write-scoped result they already hold.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from hulubul.core.models.operational.enums import ErrorCode, FailureKind, RetryAction
from hulubul.core.models.operational.errors import ERROR_POLICY, OperationalError
from hulubul.request_intake.services.retry_policy import (
    RETRY_ACTION_BY_FAILURE_KIND,
    classify_failure,
    max_retries,
    retry_action,
    should_retry,
)

TRANSIENT_FAILURE_KINDS = (
    FailureKind.TIMEOUT,
    FailureKind.CONNECTION,
    FailureKind.PROTOCOL,
    FailureKind.HTTP_STATUS,
    FailureKind.NEO4J_TRANSIENT,
    FailureKind.SERVICE_UNAVAILABLE,
)

TOOL_LESS_REPAIR_FAILURE_KINDS = (FailureKind.MALFORMED_RESULT,)

PERMANENT_FAILURE_KINDS = (
    FailureKind.AUTHENTICATION,
    FailureKind.VALIDATION,
    FailureKind.UNSUPPORTED_OPERATION,
    FailureKind.CYPHER_CLIENT,
    FailureKind.CYPHER_SYNTAX,
    FailureKind.CONSTRAINT,
    FailureKind.AFFECTED_COUNT,
)


def _operational_error(code: ErrorCode) -> OperationalError:
    """Build a policy-compliant OperationalError for the given code."""
    policy = ERROR_POLICY[code]
    return OperationalError(
        correlation_id=uuid4(),
        code=code,
        category=policy.category,
        message=policy.safe_message,
        retryable=policy.retryable,
    )


# ============================================================================
# Exhaustive FailureKind coverage
# ============================================================================


class TestExhaustiveFailureKindCoverage:
    """The decision matrix explicitly handles every FailureKind, no defaults."""

    def test_every_failure_kind_has_an_explicit_retry_action(self) -> None:
        assert set(RETRY_ACTION_BY_FAILURE_KIND) == set(FailureKind)

    def test_transient_repair_and_permanent_sets_partition_every_failure_kind(self) -> None:
        classified = (
            set(TRANSIENT_FAILURE_KINDS)
            | set(TOOL_LESS_REPAIR_FAILURE_KINDS)
            | set(PERMANENT_FAILURE_KINDS)
        )
        assert classified == set(FailureKind)
        total_named = (
            len(TRANSIENT_FAILURE_KINDS)
            + len(TOOL_LESS_REPAIR_FAILURE_KINDS)
            + len(PERMANENT_FAILURE_KINDS)
        )
        assert len(classified) == total_named, "buckets must not overlap"


# ============================================================================
# retry_action
# ============================================================================


class TestRetryAction:
    """Each failure kind maps to exactly one RetryAction."""

    @pytest.mark.parametrize("failure_kind", TRANSIENT_FAILURE_KINDS)
    def test_transient_failures_map_to_retry(self, failure_kind: FailureKind) -> None:
        assert retry_action(failure_kind) is RetryAction.RETRY

    @pytest.mark.parametrize("failure_kind", TOOL_LESS_REPAIR_FAILURE_KINDS)
    def test_malformed_result_maps_to_repair_raw_result(self, failure_kind: FailureKind) -> None:
        assert retry_action(failure_kind) is RetryAction.REPAIR_RAW_RESULT

    @pytest.mark.parametrize("failure_kind", PERMANENT_FAILURE_KINDS)
    def test_permanent_failures_map_to_fail(self, failure_kind: FailureKind) -> None:
        assert retry_action(failure_kind) is RetryAction.FAIL


# ============================================================================
# should_retry
# ============================================================================


class TestShouldRetry:
    """Retryable and tool-less-repairable kinds warrant another attempt."""

    @pytest.mark.parametrize(
        "failure_kind", TRANSIENT_FAILURE_KINDS + TOOL_LESS_REPAIR_FAILURE_KINDS
    )
    def test_retryable_and_repairable_kinds_should_retry(self, failure_kind: FailureKind) -> None:
        assert should_retry(failure_kind) is True

    @pytest.mark.parametrize("failure_kind", PERMANENT_FAILURE_KINDS)
    def test_permanent_kinds_should_not_retry(self, failure_kind: FailureKind) -> None:
        assert should_retry(failure_kind) is False


# ============================================================================
# max_retries
# ============================================================================


class TestMaxRetries:
    """Transient and repair kinds allow exactly one further attempt."""

    @pytest.mark.parametrize("failure_kind", TRANSIENT_FAILURE_KINDS)
    def test_transient_failures_allow_exactly_one_retry(self, failure_kind: FailureKind) -> None:
        assert max_retries(failure_kind) == 1

    @pytest.mark.parametrize("failure_kind", TOOL_LESS_REPAIR_FAILURE_KINDS)
    def test_malformed_result_allows_one_repair_attempt(self, failure_kind: FailureKind) -> None:
        assert max_retries(failure_kind) == 1

    @pytest.mark.parametrize("failure_kind", PERMANENT_FAILURE_KINDS)
    def test_permanent_failures_allow_zero_retries(self, failure_kind: FailureKind) -> None:
        assert max_retries(failure_kind) == 0


# ============================================================================
# classify_failure - raw exceptions
# ============================================================================


class TestClassifyFailureFromExceptions:
    """Raw exceptions surfaced by adapter calls classify into a FailureKind."""

    def test_timeout_error_classifies_as_timeout(self) -> None:
        assert classify_failure(TimeoutError("slow")) is FailureKind.TIMEOUT

    def test_connection_error_classifies_as_connection(self) -> None:
        assert classify_failure(ConnectionError("refused")) is FailureKind.CONNECTION

    def test_permission_error_classifies_as_authentication(self) -> None:
        assert classify_failure(PermissionError("denied")) is FailureKind.AUTHENTICATION

    def test_value_error_classifies_as_validation(self) -> None:
        assert classify_failure(ValueError("bad payload")) is FailureKind.VALIDATION

    def test_unrecognized_exception_type_raises_value_error(self) -> None:
        with pytest.raises(ValueError):
            classify_failure(RuntimeError("unclassified"))


# ============================================================================
# classify_failure - OperationalError
# ============================================================================


class TestClassifyFailureFromOperationalError:
    """Only unambiguous, always-non-retryable codes classify from OperationalError."""

    def test_model_authentication_failure_classifies_as_authentication(self) -> None:
        error = _operational_error(ErrorCode.MODEL_AUTHENTICATION_FAILURE)
        assert classify_failure(error) is FailureKind.AUTHENTICATION

    def test_mcp_authentication_failure_classifies_as_authentication(self) -> None:
        error = _operational_error(ErrorCode.MCP_AUTHENTICATION_FAILURE)
        assert classify_failure(error) is FailureKind.AUTHENTICATION

    def test_unsupported_operational_error_code_raises_value_error(self) -> None:
        error = _operational_error(ErrorCode.INVALID_INPUT)
        with pytest.raises(ValueError):
            classify_failure(error)

    def test_exhausted_retry_terminal_code_raises_value_error(self) -> None:
        """MODEL_TRANSIENT_FAILURE is a post-retry terminal code; reclassifying
        it as still-retryable would violate the one-retry-only rule."""
        error = _operational_error(ErrorCode.MODEL_TRANSIENT_FAILURE)
        with pytest.raises(ValueError):
            classify_failure(error)


# ============================================================================
# Hard gate: never replay a dispatched write
# ============================================================================


class TestNeverReplayDispatchedWrite:
    """MCP write ambiguity is never modeled as a retryable FailureKind."""

    def test_no_failure_kind_action_implies_write_replay(self) -> None:
        """Every action is RETRY, REPAIR_RAW_RESULT, or FAIL; REPAIR_RAW_RESULT
        (the only "try again" action besides RETRY) is reserved for the
        tool-less MALFORMED_RESULT repair, never for re-dispatching a write."""
        for failure_kind, action in RETRY_ACTION_BY_FAILURE_KIND.items():
            if action is RetryAction.REPAIR_RAW_RESULT:
                assert failure_kind is FailureKind.MALFORMED_RESULT
