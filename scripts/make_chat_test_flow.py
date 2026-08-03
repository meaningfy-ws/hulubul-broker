#!/usr/bin/env python3
"""Derive a chat-driven ``-test`` copy of a canonical LangFlow flow.

The canonical flows are driven through the Run API against a custom boundary
component, so their runs leave nothing in LangFlow's chat history and cannot be
watched in the Playground. This script produces a copy that keeps the graph
under test byte-identical and only wraps it: a ``ChatInput`` feeding the flow's
public input component, and a ``ChatOutput`` fed by its public result component.

Everything a run exercises -- boundaries, agent, prompts, the Run Flow node --
is the same object as in the canonical flow, so what the copy demonstrates
holds for the original. Only the two ends differ.

Usage::

    make_chat_test_flow.py <source.json> <input-component-id> \\
        <result-component-id> <output.json> <flow-name>
"""

from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path
from typing import Any

# LangFlow serializes edge handles as JSON with `"` replaced by `œ`.
HANDLE_QUOTE = "œ"

# Namespace for the derived flows' stable UUIDv5 ids, matching how the
# canonical flow ids in langflow/flow-manifest.yaml are derived from names.
FLOW_ID_NAMESPACE = uuid.NAMESPACE_URL
FLOW_ID_PREFIX = "https://hulubul.meaningfy.ws/langflow/flow/"

CHAT_INPUT_TYPE = "ChatInput"
CHAT_OUTPUT_TYPE = "ChatOutput"
CHAT_INPUT_OUTPUT_NAME = "message"
CHAT_OUTPUT_FIELD_NAME = "input_value"
PUBLIC_INPUT_FIELD_NAME = "input_value"
RESULT_OUTPUT_NAME = "response"
FLOW_ID_TEMPLATE_FIELD = "_frontend_node_flow_id"

REFERENCE_FLOW = Path("langflow/flows/30-lf-00-main-router.json")
REFERENCE_CHAT_INPUT_ID = "ChatInput-hlb-lf-00-message-v1"
REFERENCE_CHAT_OUTPUT_ID = "ChatOutput-hlb-lf-00-chat-v1"


def _encode_handle(handle: dict[str, Any]) -> str:
    """Render a handle dict the way LangFlow's frontend serializes it."""
    return json.dumps(handle, separators=(",", ":"), sort_keys=True).replace('"', HANDLE_QUOTE)


def _edge(source_handle: dict[str, Any], target_handle: dict[str, Any]) -> dict[str, Any]:
    source_encoded = _encode_handle(source_handle)
    target_encoded = _encode_handle(target_handle)
    return {
        "animated": False,
        "className": "",
        "data": {"sourceHandle": source_handle, "targetHandle": target_handle},
        "id": (
            f"xy-edge__{source_handle['id']}{source_encoded}-{target_handle['id']}{target_encoded}"
        ),
        "selected": False,
        "source": source_handle["id"],
        "sourceHandle": source_encoded,
        "target": target_handle["id"],
        "targetHandle": target_encoded,
    }


def _reference_node(node_id: str) -> dict[str, Any]:
    """Lift a stock chat node's frontend template from the flow that has one."""
    reference = json.loads(REFERENCE_FLOW.read_text())
    for node in reference["data"]["nodes"]:
        if node["id"] == node_id:
            return dict(node)
    raise SystemExit(f"reference node {node_id} not found in {REFERENCE_FLOW}")


def _rehome(node: dict[str, Any], node_id: str, position: dict[str, float]) -> dict[str, Any]:
    node = json.loads(json.dumps(node))
    node["id"] = node_id
    node["data"]["id"] = node_id
    node["data"]["node"]["id"] = node_id
    node["position"] = position
    node["selected"] = False
    return node


def _find(nodes: list[dict[str, Any]], node_id: str) -> dict[str, Any]:
    for node in nodes:
        if node["id"] == node_id:
            return node
    raise SystemExit(f"component {node_id} not found in source flow")


def _source_handle(node: dict[str, Any], output_name: str) -> dict[str, Any]:
    """Build a source handle from the node's real output definition.

    The frontend derives a handle's identity from the output's declared
    ``types``. Guessing them produces a handle that matches nothing on the
    node, and the canvas silently drops the edge as invalid on load -- while
    the backend, which resolves edges by node id, still runs it. So the flow
    works over the API and looks broken in the Playground.
    """
    for output in node["data"]["node"].get("outputs", []):
        if output.get("name") == output_name:
            return {
                "dataType": node["data"]["type"],
                "id": node["id"],
                "name": output_name,
                "output_types": list(output.get("types") or []),
            }
    raise SystemExit(f"{node['id']} has no output named {output_name!r}")


def _target_handle(node: dict[str, Any], field_name: str) -> dict[str, Any]:
    """Build a target handle from the node's real template field."""
    field = node["data"]["node"]["template"].get(field_name)
    if not isinstance(field, dict):
        raise SystemExit(f"{node['id']} has no template field {field_name!r}")
    return {
        "fieldName": field_name,
        "id": node["id"],
        "inputTypes": list(field.get("input_types") or []),
        "type": field.get("type"),
    }


def build(
    source_path: Path,
    input_component_id: str,
    result_component_id: str,
    output_path: Path,
    flow_name: str,
) -> None:
    flow = json.loads(source_path.read_text())
    nodes = flow["data"]["nodes"]

    chat_input_id = f"{CHAT_INPUT_TYPE}-hlb-{flow_name}-in-v1"
    chat_output_id = f"{CHAT_OUTPUT_TYPE}-hlb-{flow_name}-out-v1"

    public_input = _find(nodes, input_component_id)
    public_result = _find(nodes, result_component_id)

    # The chat nodes take over as the flow's Run API entry and exit, so the
    # wrapped components must stop advertising themselves as such -- otherwise
    # the API injects into both ends and two vertices claim the same role.
    public_input["data"]["node"]["is_input"] = False
    public_result["data"]["node"]["is_output"] = False

    anchor = public_input["position"]
    chat_input = _rehome(
        _reference_node(REFERENCE_CHAT_INPUT_ID),
        chat_input_id,
        {"x": anchor["x"] - 420, "y": anchor["y"]},
    )
    chat_output = _rehome(
        _reference_node(REFERENCE_CHAT_OUTPUT_ID),
        chat_output_id,
        {"x": public_result["position"]["x"] + 420, "y": public_result["position"]["y"]},
    )
    nodes.insert(0, chat_input)
    nodes.append(chat_output)

    flow["data"]["edges"].extend(
        [
            _edge(
                _source_handle(chat_input, CHAT_INPUT_OUTPUT_NAME),
                _target_handle(public_input, PUBLIC_INPUT_FIELD_NAME),
            ),
            _edge(
                _source_handle(public_result, RESULT_OUTPUT_NAME),
                _target_handle(chat_output, CHAT_OUTPUT_FIELD_NAME),
            ),
        ]
    )

    flow["id"] = str(uuid.uuid5(FLOW_ID_NAMESPACE, FLOW_ID_PREFIX + flow_name))
    flow["name"] = flow_name

    # Nodes carry the id of the flow they belong to. Left pointing at the
    # source, LangFlow rewrites it on load and the committed copy immediately
    # reads as drifted against the server.
    for node in nodes:
        owner = node["data"]["node"]["template"].get(FLOW_ID_TEMPLATE_FIELD)
        if isinstance(owner, dict):
            owner["value"] = flow["id"]
    flow["description"] = (
        f"Chat-driven test copy of {source_path.stem}. Same graph, wrapped in "
        "ChatInput/ChatOutput so runs are observable in the Playground."
    )
    output_path.write_text(json.dumps(flow, indent=2, ensure_ascii=False) + "\n")
    print(f"{output_path} -> {flow['name']} ({flow['id']})")


if __name__ == "__main__":
    build(Path(sys.argv[1]), sys.argv[2], sys.argv[3], Path(sys.argv[4]), sys.argv[5])
