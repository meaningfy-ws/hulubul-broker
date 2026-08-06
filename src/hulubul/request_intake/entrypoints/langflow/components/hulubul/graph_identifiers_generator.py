"""Graph identifiers generator component for LF-10 deterministic ID allocation.

Implements Task 9 (checkpoint 9, task 9.2) per DEC-010: graph node identifiers
(request_id, sender_id, sender_agent_id, receiver_id, etc.) must be generated
deterministically by code *before* the operation reaches LF-70, not invented by
the LLM in LF-70's own Agent.

Wraps `new_graph_identifiers()` as a deterministic, pure-Python LangFlow component
exposed as an Agent tool in LF-10, so the Agent can call it before constructing
the createDeliveryRequest/updateDeliveryRequest payload.

Inputs:
- actor_id: The sender's stable identifier (required)
- receiver_stable_id: Stable receiver identifier (optional)
- receiver_name: Human-supplied receiver name (optional)
- parcel_declared_content: Parcel content description (optional)
- pickup_location: Pickup location (optional)
- drop_off_location: Drop-off location (optional)

Outputs:
- identifiers: Message containing JSON string (GraphIdentifiers) for the Agent
  to use verbatim in the createDeliveryRequest/updateDeliveryRequest payload
  under the `identifiers` field.
"""

from lfx.custom.custom_component.component import Component
from lfx.inputs.inputs import MessageTextInput
from lfx.schema.message import Message
from lfx.template.field.base import Output

from hulubul.request_intake.services.graph_identifiers import new_graph_identifiers

__all__ = ["HulubulGraphIdentifiersGenerator"]


class HulubulGraphIdentifiersGenerator(Component):
    """Deterministically generate graph node identifiers for intake operations.

    Pure deterministic component (no I/O, no LLM) -- calls `new_graph_identifiers()`
    with facts extracted by the Agent and returns the prefixed identifiers as-is.

    Exposed as an Agent tool (`component_as_tool` output) so the Agent can call it
    before constructing createDeliveryRequest/updateDeliveryRequest operations.
    """

    display_name = "Graph Identifiers Generator"
    description = (
        "Generate graph node identifiers (request_id, sender_id, etc.) deterministically. "
        "Pure deterministic component -- returns identifiers to be used verbatim in "
        "createDeliveryRequest/updateDeliveryRequest operations."
    )
    icon = "key"
    name = "HulubulGraphIdentifiersGenerator"

    inputs = [  # noqa: RUF012
        MessageTextInput(  # type: ignore[call-arg]
            name="actor_id",
            display_name="Actor ID",
            info="Sender's stable identifier (URN or email).",
            required=True,
        ),
        MessageTextInput(  # type: ignore[call-arg]
            name="receiver_stable_id",
            display_name="Receiver Stable ID",
            info="Stable receiver identifier (email, phone). If absent, name-only.",
            required=False,
        ),
        MessageTextInput(  # type: ignore[call-arg]
            name="receiver_name",
            display_name="Receiver Name",
            info="Human-supplied receiver name. Allocates receiver role if present.",
            required=False,
        ),
        MessageTextInput(  # type: ignore[call-arg]
            name="parcel_declared_content",
            display_name="Parcel Content",
            info="Declared content. Allocates parcel role if present.",
            required=False,
        ),
        MessageTextInput(  # type: ignore[call-arg]
            name="pickup_location",
            display_name="Pickup Location",
            info="Pickup location. Allocates pickup place if present.",
            required=False,
        ),
        MessageTextInput(  # type: ignore[call-arg]
            name="drop_off_location",
            display_name="Drop-off Location",
            info="Drop-off location. Allocates drop-off place if present.",
            required=False,
        ),
    ]

    outputs = [  # noqa: RUF012
        Output(  # type: ignore[call-arg]
            display_name="Identifiers",
            name="identifiers",
            type_=Message,
            method="build_output",
        ),
    ]

    def build_output(self) -> Message:
        """Generate graph identifiers and return as Message with JSON text.

        Derives include_receiver/include_parcel/include_pickup/include_drop_off from
        the presence of facts. Always includes request and sender IDs; receiver,
        parcel, and place IDs are sparse (only if their facts are present).

        Returns:
            Message: JSON-serialized GraphIdentifiers for the Agent to use as-is

        Raises:
            ValueError: If required fields are missing or invalid
        """
        # Validate required inputs
        if not self.actor_id:
            raise ValueError("actor_id is required for identifier generation")

        # Derive sparse allocation flags from fact presence
        include_receiver = bool(self.receiver_name)
        include_parcel = bool(self.parcel_declared_content)
        include_pickup = bool(self.pickup_location)
        include_drop_off = bool(self.drop_off_location)

        # Generate identifiers deterministically
        identifiers = new_graph_identifiers(
            actor_id=self.actor_id,
            receiver_stable_id=self.receiver_stable_id if self.receiver_stable_id else None,
            include_receiver=include_receiver,
            include_parcel=include_parcel,
            include_pickup=include_pickup,
            include_drop_off=include_drop_off,
        )

        # Return as Message with JSON serialization (compatible with Agent tool output)
        return Message(text=identifiers.model_dump_json())
