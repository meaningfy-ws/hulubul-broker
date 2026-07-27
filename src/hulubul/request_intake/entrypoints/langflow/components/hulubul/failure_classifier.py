"""Failure classification component for retry decision (DEC-015).

This component runs on Agent's raw output (after operation execution,
before result validation) to extract and classify any failures for
the retry decision logic.
"""

import json

from lfx.custom.custom_component.component import Component
from lfx.inputs.inputs import MessageInput
from lfx.schema.message import Message
from lfx.template.field.base import Output
from pydantic import ValidationError

from hulubul.core.models.operational import DataOperationResult
from hulubul.core.models.operational.enums import ErrorCode
from hulubul.core.models.operational.errors import ERROR_POLICY

__all__ = ["FailureClassifierComponent"]


class FailureClassifierComponent(Component):
    """Classify failures from Agent's raw response for retry decision.

    Parses Agent's Message output to extract failure classification
    per DEC-015. Runs BEFORE result validation, so Classification
    feeds ConditionalRouter to control retry loop (with optional
    RetryDecision for detailed decision info).

    Outputs the string value of should_retry ("true" or "false")
    for ConditionalRouter to use directly.
    """

    display_name = "Failure Classifier"
    description = "Classifies an Agent's raw response into a should_retry signal (DEC-015)."
    icon = "shield-check"
    name = "HulubulFailureClassifier"

    inputs = [  # noqa: RUF012
        MessageInput(  # type: ignore[call-arg]
            name="agent_response",
            display_name="Agent Response",
            info="Agent's raw output Message containing the operation result.",
            required=True,
        ),
    ]

    outputs = [  # noqa: RUF012
        Output(  # type: ignore[call-arg]
            display_name="Should Retry",
            name="response",
            type_=Message,
            method="build_classification",
        ),
    ]

    def build_classification(self) -> Message:
        """LFX-facing output: classify self.agent_response, wrapped as a Message."""
        return Message(text=self.classify_failure(self.agent_response))

    def classify_failure(self, agent_response: Message | str | None) -> str:
        """Classify failure from Agent's raw response for retry decision.

        Parses Agent's Message output to extract failure classification per DEC-015.
        Returns "true" or "false" string indicating whether to retry, for direct
        use by ConditionalRouter.

        Args:
            agent_response: Message from Agent containing operation result

        Returns:
            str: "true" if operation should be retried, "false" otherwise
        """
        # Extract text from Message
        if isinstance(agent_response, Message):
            # LFX Message.text can be str, Iterator, or None
            # For non-string types (Iterator, etc.), treat as missing
            text_value = agent_response.text
            raw_text = text_value if isinstance(text_value, str) else ""
        elif isinstance(agent_response, str):
            raw_text = agent_response
        else:
            # Fallback: convert to string or use empty
            raw_text = str(agent_response) if agent_response else ""

        # An empty or unparseable response is itself a malformed result, not a
        # transient failure. ERROR_POLICY[MALFORMED_AGENT_RESULT].retryable is
        # False by design (DEC-015): a malformed result gets a separate,
        # narrower tool-less repair against the existing raw output (task 37),
        # never a full Agent re-invocation, since re-running the Agent could
        # replay an already-dispatched write.
        try:
            if not raw_text:
                return "false"

            result_dict = json.loads(raw_text)
            result = DataOperationResult.model_validate(result_dict)

            if result.outcome.value == "confirmed":
                return "false"

            if not result.error_code:
                return "false"

            try:
                error_code = ErrorCode(result.error_code)
            except ValueError:
                return "false"

            return "true" if ERROR_POLICY[error_code].retryable else "false"

        except (ValidationError, ValueError, json.JSONDecodeError):
            return "false"
