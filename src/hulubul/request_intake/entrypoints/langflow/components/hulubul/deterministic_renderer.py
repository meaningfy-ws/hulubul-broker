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

import json
from typing import Any

from lfx.custom.custom_component.component import Component
from lfx.inputs.inputs import HandleInput
from lfx.schema.message import Message
from lfx.template.field.base import Output
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

    display_name = "Deterministic Renderer"
    description = "Renders a validated IntakeResult/RouterResult/OperationalError to safe text."
    icon = "shield-check"
    name = "HulubulDeterministicRenderer"

    inputs = [  # noqa: RUF012
        HandleInput(  # type: ignore[call-arg]
            name="result",
            display_name="Result",
            info="Validated IntakeResult, RouterResult, or OperationalError (never free text).",
            input_types=["Message", "Data", "JSON"],
            required=True,
        ),
    ]

    outputs = [  # noqa: RUF012
        Output(  # type: ignore[call-arg]
            display_name="Message", name="response", type_=Message, method="build_message"
        ),
    ]

    @staticmethod
    def _as_dict(value: Any) -> dict[str, Any]:
        """Coerce a Message/Data/JSON edge value into a plain dict.

        `ContractResultBoundaryComponent` (the predecessor in every wiring
        that reaches this component) emits its validated contract as a
        `Message` wrapping JSON text, not a `Data`/`JSON` object -- discovered
        only when actually building a live LF-00 flow (Result Boundary ->
        Renderer edge), not by any prior unit test. Undecodable text becomes
        an empty dict, matching this codebase's established
        never-crash-on-malformed-JSON convention, so it is rejected as
        INVALID_INPUT below rather than raising here.
        """
        if isinstance(value, Message):
            text = value.text
            if not isinstance(text, str):
                return {}
            try:
                decoded = json.loads(text)
            except json.JSONDecodeError:
                return {}
            return decoded if isinstance(decoded, dict) else {}
        if hasattr(value, "data"):
            return dict(value.data)
        return dict(value) if value else {}

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

        result_dict = self._as_dict(self.result)
        if not result_dict:
            raise ValueError(
                "INVALID_INPUT: result must be a non-empty dict (validated contract), "
                "not raw text or prose"
            )

        # Attempt to detect and validate contract type
        rendered_text = self._render_result(result_dict)

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
        # Strategy: Try to match based on discriminators, then validate.
        # `model_validate_json` (not `.model_validate(dict)`) on purpose: this
        # project's contracts are strict-typed and reject a plain python dict
        # containing JSON-primitive values (string UUIDs, string enum values --
        # exactly what a real Message-wrapped edge value decodes to) via
        # ordinary python-mode construction; only JSON-mode coercion applies
        # the standard UUID/enum/datetime parsing rules. `default=str` handles
        # the other calling shape too (a dict of already-native UUID/enum
        # instances, from `.model_dump()` rather than a decoded wire payload).
        result_json = json.dumps(result_dict, default=str)
        outcome_value = result_dict.get("outcome")

        # Try IntakeResult if outcome is IntakeOutcome value
        if isinstance(outcome_value, str) and outcome_value in {e.value for e in IntakeOutcome}:
            try:
                intake_result = IntakeResult.model_validate_json(result_json)
                return render_intake_result(intake_result)
            except (ValidationError, ValueError):
                pass

        # Try RouterResult if outcome is RouterOutcome value
        if isinstance(outcome_value, str) and outcome_value in {e.value for e in RouterOutcome}:
            try:
                router_result = RouterResult.model_validate_json(result_json)
                return render_router_result(router_result)
            except (ValidationError, ValueError):
                pass

        # Try OperationalError (has code discriminator)
        if "code" in result_dict:
            try:
                error = OperationalError.model_validate_json(result_json)
                return render_operational_error(error)
            except (ValidationError, ValueError):
                pass

        # No valid contract type matched
        raise ValueError(
            "INVALID_CONTRACT: result does not match IntakeResult, RouterResult, "
            "or OperationalError structure. Never accept Agent free text."
        )
