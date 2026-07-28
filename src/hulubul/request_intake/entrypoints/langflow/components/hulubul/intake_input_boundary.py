"""Intake input boundary component: assembles IntakeInput from fixed edges.

Split from the former contract_boundary.py (which held three components)
because LangFlow's directory-based custom component loader registers exactly
one component per file, named after the file -- extra classes in the same
file are silently dropped from the sidebar palette. See
router_input_boundary.py and contract_result_boundary.py for the other two.
"""

from typing import Any

from lfx.custom.custom_component.component import Component
from lfx.inputs.inputs import HandleInput
from lfx.schema.message import Message
from lfx.template.field.base import Output

from hulubul.core.models.operational import IntakeInput, MainFlowInput, RoutingContext

__all__ = ["IntakeInputBoundaryComponent"]


class IntakeInputBoundaryComponent(Component):
    """Assembles IntakeInput from fixed advanced envelope/context edges + validated Data payload.

    The envelope and routing_context are advanced (fixed) fields, absent from model tool schemas.
    They cannot be overridden by user input, model output, prose, or tweaks.
    """

    display_name = "Intake Input Boundary"
    description = "Assembles IntakeInput from fixed envelope/routing_context edges."
    icon = "shield-check"
    name = "HulubulIntakeInputBoundary"

    inputs = [  # noqa: RUF012
        HandleInput(  # type: ignore[call-arg]
            name="envelope",
            display_name="Envelope",
            info="Fixed MainFlowInput envelope (advanced, not model-editable).",
            input_types=["Data", "JSON"],
            advanced=True,
            required=True,
        ),
        HandleInput(  # type: ignore[call-arg]
            name="routing_context",
            display_name="Routing Context",
            info="Fixed RoutingContext (advanced, not model-editable).",
            input_types=["Data", "JSON"],
            advanced=True,
            required=True,
        ),
    ]

    outputs = [  # noqa: RUF012
        Output(  # type: ignore[call-arg]
            display_name="Message", name="response", type_=Message, method="build_intake_input"
        ),
    ]

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the IntakeInputBoundaryComponent."""
        super().__init__(**kwargs)
        self.envelope: MainFlowInput | None = None
        self.routing_context: RoutingContext | None = None

    def build_intake_input(self) -> Message:
        """Build IntakeInput from fixed envelope/context edges.

        Returns:
            Message: An LFX Message with IntakeInput serialized as JSON

        Raises:
            ValueError: If envelope or routing_context is missing
        """
        if self.envelope is None:
            raise ValueError("INVALID_CONFIGURATION: envelope is required")

        if self.routing_context is None:
            raise ValueError("INVALID_CONFIGURATION: routing_context is required")

        # Assemble IntakeInput from fixed edges
        wrapper = IntakeInput(
            schema_version=self.envelope.schema_version,
            correlation_id=self.envelope.correlation_id,
            envelope=self.envelope,
            routing_context=self.routing_context,
        )

        # Return as Message with JSON text
        return Message(text=wrapper.model_dump_json())
