"""Make ``lfx``'s Run Flow importable without a LangFlow server installation.

``lfx.base.tools.run_flow`` imports ``langflow.helpers.flow``, which ships with
the LangFlow *server* distribution, not with ``lfx`` -- and this repo pins only
``lfx`` (the LangFlow container supplies the rest). Without a stand-in, the
whole module, and therefore ``HulubulRunFlowComponent``, is unimportable here
and its two overrides could only be tested by reimplementing them.

The stub is registered before test collection, only when the real module is
genuinely absent, and only supplies the one symbol ``lfx`` imports at module
level. Nothing under test calls it: both overrides run entirely on data handed
to them.
"""

import importlib.util
import sys
import types
from typing import Any

_LANGFLOW = "langflow"
_LANGFLOW_HELPERS = "langflow.helpers"
_LANGFLOW_HELPERS_FLOW = "langflow.helpers.flow"


def _is_importable(module_name: str) -> bool:
    try:
        return importlib.util.find_spec(module_name) is not None
    except (ImportError, ValueError):
        return False


def _install_langflow_helpers_stub() -> None:
    if _is_importable(_LANGFLOW_HELPERS_FLOW):
        return

    async def get_flow_by_id_or_name(**kwargs: Any) -> Any:
        raise NotImplementedError(
            "langflow.helpers.flow is stubbed for unit tests; a test that "
            "needs real flow lookup belongs in tests/integration/langflow/."
        )

    flow_module = types.ModuleType(_LANGFLOW_HELPERS_FLOW)
    flow_module.get_flow_by_id_or_name = get_flow_by_id_or_name  # type: ignore[attr-defined]

    helpers_module = types.ModuleType(_LANGFLOW_HELPERS)
    helpers_module.flow = flow_module  # type: ignore[attr-defined]

    langflow_module = sys.modules.setdefault(_LANGFLOW, types.ModuleType(_LANGFLOW))
    langflow_module.helpers = helpers_module  # type: ignore[attr-defined]

    sys.modules.setdefault(_LANGFLOW_HELPERS, helpers_module)
    sys.modules.setdefault(_LANGFLOW_HELPERS_FLOW, flow_module)


_install_langflow_helpers_stub()
