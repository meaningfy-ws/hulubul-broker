"""Retry decision component: thin adapter delegating to pure retry policy.

This LFX component encapsulates the retry policy decision-making:
- Accepts a failure_kind (string or FailureKind enum)
- Validates it against the FailureKind enum
- Delegates to pure policy functions (retry_action, should_retry, max_retries)
- Returns typed JSON with the decision

The component performs no orchestration, no retries, no delays, no I/O,
and makes no model calls. It is a thin, deterministic adapter.
"""

from lfx.custom.custom_component.component import Component
from lfx.schema.data import JSON

from hulubul.core.models.operational.enums import FailureKind
from hulubul.request_intake.services.retry_policy import (
    max_retries,
    retry_action,
    should_retry,
)

__all__ = ["RetryDecisionComponent"]


class RetryDecisionComponent(Component):
    """Thin adapter delegating to pure retry policy.

    Validates failure_kind input and returns a typed JSON decision
    containing action, should_retry bool, and max_retries int.
    """

    def __init__(self, **kwargs) -> None:
        """Initialize the RetryDecisionComponent."""
        super().__init__(**kwargs)
        self.failure_kind: str | FailureKind | None = None

    def build_decision(self) -> JSON:
        """Build retry decision from failure classification.

        - Validate failure_kind input (convert string to enum if needed)
        - Delegate to pure policy: retry_action, should_retry, max_retries
        - Return typed JSON with decision fields

        Returns:
            JSON: Decision with action, should_retry, max_retries fields

        Raises:
            ValueError: If failure_kind is invalid or missing
        """
        if self.failure_kind is None:
            raise ValueError("INVALID_INPUT: failure_kind is required")

        # Convert string to FailureKind enum if necessary
        if isinstance(self.failure_kind, str):
            try:
                failure_kind = FailureKind(self.failure_kind)
            except ValueError as e:
                raise ValueError(
                    f"INVALID_INPUT: '{self.failure_kind}' is not a valid FailureKind"
                ) from e
        else:
            failure_kind = self.failure_kind

        # Validate that we received a FailureKind enum
        if not isinstance(failure_kind, FailureKind):
            raise ValueError(
                f"INVALID_INPUT: failure_kind must be FailureKind enum or string, got {type(failure_kind)}"
            )

        # Delegate to pure policy functions
        action = retry_action(failure_kind)
        should_retry_result = should_retry(failure_kind)
        max_retries_result = max_retries(failure_kind)

        # Return typed JSON with decision
        return JSON(
            data={
                "action": action.value,
                "should_retry": should_retry_result,
                "max_retries": max_retries_result,
            }
        )
