"""Deterministic renderer component: thin adapter delegating to pure rendering policy.

This LFX component encapsulates safe, deterministic result rendering:
- Accepts validated IntakeResult, RouterResult, or OperationalError (never free text)
- Validates the contract structure and outcome discriminator
- Dispatches to the matching pure renderer function
- Returns typed Message with canonical, safe user-facing text

The component performs no orchestration, no model calls, no I/O,
and makes no decisions. It is a thin, deterministic adapter that ensures
structured and chat output can never diverge (per DEC-014).
"""

from typing import Any

from lfx.custom.custom_component.component import Component
from lfx.schema.message import Message
from pydantic import ValidationError

from hulubul.core.models.operational.enums import IntakeOutcome, RouterOutcome
from hulubul.core.models.operational.errors import OperationalError
from hulubul.core.models.operational.intake import IntakeResult
from hulubul.core.models.operational.routing import RouterResult
from hulubul.request_intake.services.rendering import (
    render_intake_result,
    render_operational_error,
    render_router_result,
)

__all__ = ["DeterministicRendererComponent"]


class DeterministicRendererComponent(Component):
    """Thin adapter delegating to pure rendering policy.

    Validates typed contract input and returns a Message with canonical,
    safe, deterministic user-facing text. Never accepts Agent free text
    or unvalidated prose.
    """

    def __init__(self, **kwargs) -> None:
        """Initialize the DeterministicRendererComponent."""
        super().__init__(**kwargs)
        self.result: dict[str, Any] | Any = None

    def build_message(self) -> Message:
        """Build rendered message from validated result contract.

        - Accept validated IntakeResult, RouterResult, or OperationalError
        - Validate contract structure and discriminator
        - Dispatch to matching pure renderer
        - Return Message with canonical text

        Returns:
            Message: LFX Message with canonical rendered text

        Raises:
            ValueError: If result is invalid, missing, or not a typed contract
            KeyError: If discriminator is missing or invalid
        """
        if self.result is None:
            raise ValueError("INVALID_INPUT: result is required")

        if not isinstance(self.result, dict):
            raise ValueError(
                "INVALID_INPUT: result must be a dict (validated contract), "
                "not raw text or prose"
            )

        # Attempt to detect and validate contract type
        rendered_text = self._render_result(self.result)

        return Message(text=rendered_text)

    def _render_result(self, result_dict: dict[str, Any]) -> str:
        """Dispatch to the matching pure renderer based on contract type.

        Tries to validate against each contract type and dispatch to the
        matching renderer. Raises ValueError if contract is invalid.

        Args:
            result_dict: The result contract as a dict

        Returns:
            str: Rendered canonical safe message

        Raises:
            ValueError: If result_dict does not match any valid contract
            KeyError: If required discriminator fields are missing
        """
        # Strategy: Try to match based on discriminators, then validate
        outcome_value = result_dict.get("outcome")

        # Try IntakeResult if outcome is IntakeOutcome value
        if isinstance(outcome_value, str) and outcome_value in {
            e.value for e in IntakeOutcome
        }:
            try:
                intake_result = IntakeResult.model_validate(result_dict)
                return render_intake_result(intake_result)
            except (ValidationError, ValueError):
                pass

        # Try RouterResult if outcome is RouterOutcome value
        if isinstance(outcome_value, str) and outcome_value in {
            e.value for e in RouterOutcome
        }:
            try:
                router_result = RouterResult.model_validate(result_dict)
                return render_router_result(router_result)
            except (ValidationError, ValueError):
                pass

        # Try OperationalError (has code discriminator)
        if "code" in result_dict:
            try:
                error = OperationalError.model_validate(result_dict)
                return render_operational_error(error)
            except (ValidationError, ValueError):
                pass

        # No valid contract type matched
        raise ValueError(
            "INVALID_CONTRACT: result does not match IntakeResult, RouterResult, "
            "or OperationalError structure. Never accept Agent free text."
        )
