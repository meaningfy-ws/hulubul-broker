"""Run Flow variant that fixes stock ``RunFlow``'s cross-flow defects.

Drop-in replacement for LangFlow's built-in **Run Flow** node. It changes
exactly two decisions and inherits everything else, so flow selection, output
mapping, graph caching and tool exposure keep working as they do upstream:

1. which target-flow fields become model-callable tool arguments
   (``get_required_data``), and
2. which input category runtime payloads carry
   (``_build_inputs_from_ioputs``).

Both decisions live in
:mod:`hulubul.request_intake.entrypoints.langflow.run_flow_policy`, which
documents the two ``lfx==1.10.2`` defects being worked around and is unit-
tested without a LangFlow installation. Nothing here monkey-patches ``lfx``.

Both overrides call private ``lfx`` methods, so re-run the unit tests after
every ``lfx`` upgrade -- upstream may fix either defect, at which point the
corresponding override should be deleted rather than left as dead
compatibility code.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

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
