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

CHAT_OUTPUT_INPUT_TYPES = ["Data", "JSON", "DataFrame", "Table", "Message"]

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
    nodes.insert(
        0,
        _rehome(
            _reference_node(REFERENCE_CHAT_INPUT_ID),
            chat_input_id,
            {"x": anchor["x"] - 420, "y": anchor["y"]},
        ),
    )
    nodes.append(
        _rehome(
            _reference_node(REFERENCE_CHAT_OUTPUT_ID),
            chat_output_id,
            {"x": public_result["position"]["x"] + 420, "y": public_result["position"]["y"]},
        )
    )

    flow["data"]["edges"].extend(
        [
            _edge(
                {
                    "dataType": CHAT_INPUT_TYPE,
                    "id": chat_input_id,
                    "name": CHAT_INPUT_OUTPUT_NAME,
                    "output_types": ["Message"],
                },
                {
                    "fieldName": PUBLIC_INPUT_FIELD_NAME,
                    "id": input_component_id,
                    "inputTypes": ["Message"],
                    "type": "str",
                },
            ),
            _edge(
                {
                    "dataType": public_result["data"]["type"],
                    "id": result_component_id,
                    "name": RESULT_OUTPUT_NAME,
                    "output_types": ["Message"],
                },
                {
                    "fieldName": CHAT_OUTPUT_FIELD_NAME,
                    "id": chat_output_id,
                    "inputTypes": CHAT_OUTPUT_INPUT_TYPES,
                    "type": "other",
                },
            ),
        ]
    )

    flow["id"] = str(uuid.uuid5(FLOW_ID_NAMESPACE, FLOW_ID_PREFIX + flow_name))
    flow["name"] = flow_name
    flow["description"] = (
        f"Chat-driven test copy of {source_path.stem}. Same graph, wrapped in "
        "ChatInput/ChatOutput so runs are observable in the Playground."
    )
    output_path.write_text(json.dumps(flow, indent=2, ensure_ascii=False) + "\n")
    print(f"{output_path} -> {flow['name']} ({flow['id']})")


if __name__ == "__main__":
    build(Path(sys.argv[1]), sys.argv[2], sys.argv[3], Path(sys.argv[4]), sys.argv[5])
