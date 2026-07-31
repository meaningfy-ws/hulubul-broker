"""Run Flow variant that fixes stock ``RunFlow``'s cross-flow defects.

Drop-in replacement for LangFlow's built-in **Run Flow** node. It fixes three
``lfx==1.10.2`` defects and inherits everything else, so flow selection, output
mapping, graph caching and tool exposure keep working as they do upstream:

1. which target-flow fields become model-callable tool arguments
   (``get_required_data``),
2. which input category runtime payloads carry
   (``_build_inputs_from_ioputs``), and
3. whether an agent's tool arguments reach the run that consumes them
   (``_register_flow_output_method`` and ``__deepcopy__`` together).

The first two decisions live in
:mod:`hulubul.request_intake.entrypoints.langflow.run_flow_policy`, which
documents the defects being worked around and is unit-tested without a
LangFlow installation. Nothing here monkey-patches ``lfx``.

Every override touches private ``lfx`` internals, so re-run the unit tests
after every ``lfx`` upgrade -- upstream may fix any of these, at which point
the corresponding override should be deleted rather than left as dead
compatibility code.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, cast

from lfx.components.flow_controls.run_flow import RunFlowComponent
from lfx.log.logger import logger
from lfx.schema.dotdict import dotdict

from hulubul.request_intake.entrypoints.langflow.run_flow_policy import (
    excluded_field_names,
    select_model_callable_fields,
    with_unrestricted_input_type,
)

__all__ = ["HulubulRunFlowComponent"]


class HulubulRunFlowComponent(RunFlowComponent):
    """Execute another flow, with the cross-flow schema and injection fixes."""

    display_name = "Hulubul Run Flow"
    description = (
        "Executes another flow from within the same project, with Hulubul's "
        "cross-flow tool-schema and input-injection fixes. Can also be used as "
        "a tool for agents.\n **Select a Flow to use the tool mode**"
    )
    documentation: str = "https://docs.langflow.org/run-flow"
    name = "HulubulRunFlow"
    icon = "Workflow"

    # Detach the templates from the built-in component's class attributes, for
    # the same reason the built-in detaches from its own base: the per-instance
    # copies Component.__init__ makes must not alias a shared list.
    inputs = deepcopy(RunFlowComponent.inputs)
    outputs = deepcopy(RunFlowComponent.outputs)

    async def get_required_data(self) -> tuple[str, list[dotdict]] | None:
        """Expose only the target-flow fields that are safe as tool arguments.

        Withholding a field here keeps it off the model-callable tool schema
        only; the node's own build config still carries it, so a fixed edge
        into that field survives and keeps feeding the target flow.
        """
        required_data = await super().get_required_data()
        if required_data is None:
            return None

        flow_description, fields = required_data
        if withheld := excluded_field_names(fields):
            logger.debug(
                f"{self.name}: withheld {withheld} from the tool schema of "
                f"flow {self.flow_name_selected!r} (connection-only or "
                f"unmappable field types)"
            )
        return flow_description, [dotdict(field) for field in select_model_callable_fields(fields)]

    def _build_inputs_from_ioputs(
        self,
        ioputs: dict[str, dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Stop the target flow's non-ChatInput boundary from being skipped."""
        return with_unrestricted_input_type(super()._build_inputs_from_ioputs(ioputs))

    def _register_flow_output_method(self, *, vertex_id: str, output_name: str) -> str:
        """Name the dynamic resolver after the attribute it is published under.

        Half of the tool-argument fix. Upstream stores the resolver as an
        instance attribute named ``_resolve_flow_output__<vertex>__<output>``
        while the closure behind it is still called ``_dynamic_resolver``.
        ``ComponentToolkit`` re-resolves the method on the per-call copy it
        makes, by ``getattr(copy, output_method.__name__)`` -- so it looks for
        ``_dynamic_resolver``, misses, and silently falls back to the method
        bound to the *original* component. See :meth:`__deepcopy__` for what
        that costs and for the other half.

        Each registration builds its own closure, so this renames nothing
        shared.
        """
        method_name = super()._register_flow_output_method(
            vertex_id=vertex_id, output_name=output_name
        )
        getattr(self, method_name).__func__.__name__ = method_name
        return method_name

    def __deepcopy__(self, memo: dict[Any, Any]) -> HulubulRunFlowComponent:
        """Carry the dynamic flow-output resolvers onto the per-call copy.

        The other half of the tool-argument fix. ``ComponentToolkit`` copies the
        component per tool call, applies the agent's arguments to the copy, and
        then calls the resolver. But ``Component.__deepcopy__`` rebuilds the
        instance from its config and inputs and re-attaches a fixed set of
        fields, so dynamically registered resolvers do not come across -- the
        lookup on the copy fails and execution lands on the original, which
        never received ``flow_tweak_data``. The target flow then runs with an
        empty ``input_value`` and its boundary rejects the call as
        ``INVALID_CONTRACT``, with nothing in the agent's own trace to explain
        it: the tool call it logged was well-formed.

        The copy's ``_outputs_map`` is restored by the time we get here, so
        re-registering from it rebinds one resolver per dynamic flow output to
        the copy.
        """
        duplicate = cast("HulubulRunFlowComponent", super().__deepcopy__(memo))
        duplicate._ensure_flow_output_methods()
        return duplicate
