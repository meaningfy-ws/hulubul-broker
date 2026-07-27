"""Tests for FailureClassifierComponent: retry-loop gating from Agent output.

Verifies FailureClassifierComponent correctly derives the "true"/"false"
ConditionalRouter signal from an Agent's raw Message output, delegating to the
existing ERROR_POLICY.retryable table rather than any ad-hoc classification.
"""

import json

import pytest
from lfx.schema.message import Message

from hulubul.core.models.operational.enums import ErrorCode
from hulubul.core.models.operational.errors import ERROR_POLICY
from hulubul.request_intake.entrypoints.langflow.components.hulubul.failure_classifier import (
    FailureClassifierComponent,
)


@pytest.fixture
def classifier() -> FailureClassifierComponent:
    """Create a FailureClassifierComponent."""
    return FailureClassifierComponent()


def _confirmed_read_result() -> dict[str, object]:
    return {
        "operation": "readDeliveryRequest",
        "outcome": "confirmed",
        "success": True,
        "write_dispatched": False,
        "request_id": "req-1",
    }


def _rejected_result(error_code: str) -> dict[str, object]:
    return {
        "operation": "readDeliveryRequest",
        "outcome": "rejected",
        "success": False,
        "write_dispatched": False,
        "error_code": error_code,
    }


class TestSuccessNeverRetries:
    def test_confirmed_outcome_returns_false(self, classifier: FailureClassifierComponent) -> None:
        message = Message(text=json.dumps(_confirmed_read_result()))
        assert classifier.classify_failure(message) == "false"


class TestRetryableErrorCodes:
    """Every ErrorCode with ERROR_POLICY.retryable=True must return 'true'."""

    @pytest.mark.parametrize(
        "code",
        [c for c in ErrorCode if ERROR_POLICY[c].retryable],
    )
    def test_retryable_error_code_returns_true(
        self, classifier: FailureClassifierComponent, code: ErrorCode
    ) -> None:
        message = Message(text=json.dumps(_rejected_result(code.value)))
        assert classifier.classify_failure(message) == "true"


class TestNonRetryableErrorCodes:
    """Every ErrorCode with ERROR_POLICY.retryable=False must return 'false'."""

    @pytest.mark.parametrize(
        "code",
        [c for c in ErrorCode if not ERROR_POLICY[c].retryable],
    )
    def test_non_retryable_error_code_returns_false(
        self, classifier: FailureClassifierComponent, code: ErrorCode
    ) -> None:
        message = Message(text=json.dumps(_rejected_result(code.value)))
        assert classifier.classify_failure(message) == "false"

    def test_malformed_agent_result_is_not_retryable(
        self, classifier: FailureClassifierComponent
    ) -> None:
        """DEC-015: a malformed result gets tool-less repair (task 37), never
        a full Agent replay — never risking a duplicate dispatched write."""
        assert ERROR_POLICY[ErrorCode.MALFORMED_AGENT_RESULT].retryable is False


class TestMalformedOrEmptyResponses:
    """A response that never resolved into a coded result must not loop the Agent."""

    def test_empty_message_returns_false(self, classifier: FailureClassifierComponent) -> None:
        assert classifier.classify_failure(Message(text="")) == "false"

    def test_none_response_returns_false(self, classifier: FailureClassifierComponent) -> None:
        assert classifier.classify_failure(None) == "false"

    def test_unparseable_json_returns_false(self, classifier: FailureClassifierComponent) -> None:
        assert classifier.classify_failure(Message(text="not json")) == "false"

    def test_valid_json_missing_required_fields_returns_false(
        self, classifier: FailureClassifierComponent
    ) -> None:
        assert classifier.classify_failure(Message(text=json.dumps({"foo": "bar"}))) == "false"

    def test_rejected_without_error_code_returns_false(
        self, classifier: FailureClassifierComponent
    ) -> None:
        result = {
            "operation": "readDeliveryRequest",
            "outcome": "rejected",
            "success": False,
            "write_dispatched": False,
        }
        assert classifier.classify_failure(Message(text=json.dumps(result))) == "false"

    def test_unrecognized_error_code_string_returns_false(
        self, classifier: FailureClassifierComponent
    ) -> None:
        message = Message(text=json.dumps(_rejected_result("NOT_A_REAL_ERROR_CODE")))
        assert classifier.classify_failure(message) == "false"


class TestStringInput:
    def test_accepts_raw_string_response(self, classifier: FailureClassifierComponent) -> None:
        raw = json.dumps(_confirmed_read_result())
        assert classifier.classify_failure(raw) == "false"
