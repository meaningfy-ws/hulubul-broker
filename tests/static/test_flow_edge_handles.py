"""Every edge handle must match the node it claims to attach to.

LangFlow stores an edge's endpoints twice: as a structured
``data.sourceHandle``/``data.targetHandle``, and as an ``œ``-quoted JSON string
the frontend uses as the handle's identity. The canvas re-derives that identity
from the node's own outputs and template fields; if the stored handle disagrees,
it matches nothing and the edge is dropped on load as "invalid".

The backend does not care -- it resolves edges by node id -- so a mismatched
handle produces a flow that runs correctly over the Run API and appears broken
in the Playground, with connections quietly disappearing on save. That is not a
failure mode worth rediscovering by hand: caught once already on the
``lf-70-data-access-test`` result -> ChatOutput edge, whose generated handle
claimed ``output_types: ["Message"]`` for a boundary that emits ``["JSON"]``.
"""

import json
from pathlib import Path
from typing import Any

import pytest

FLOW_DIRECTORIES = ("langflow/flows", "langflow/test-flows")
HANDLE_QUOTE = "œ"

REPO_ROOT = Path(__file__).resolve().parents[2]


def _flow_files() -> list[Path]:
    files: list[Path] = []
    for directory in FLOW_DIRECTORIES:
        files.extend(sorted((REPO_ROOT / directory).glob("*.json")))
    return files


def _encode_handle(handle: dict[str, Any]) -> str:
    return json.dumps(handle, separators=(",", ":"), sort_keys=True).replace('"', HANDLE_QUOTE)


def _nodes_by_id(flow: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {node["id"]: node for node in flow["data"]["nodes"]}


def _edge_label(edge: dict[str, Any]) -> str:
    source = edge["data"]["sourceHandle"]
    target = edge["data"]["targetHandle"]
    return f"{source['id']}.{source['name']} -> {target['id']}.{target['fieldName']}"


@pytest.fixture(params=_flow_files(), ids=lambda path: path.name)
def flow(request: pytest.FixtureRequest) -> dict[str, Any]:
    result: dict[str, Any] = json.loads(Path(request.param).read_text())
    return result


class TestEdgeHandlesMatchTheirNodes:
    """A handle that disagrees with its node is dropped by the canvas."""

    def test_source_handles_match_a_real_output(self, flow: dict[str, Any]) -> None:
        nodes = _nodes_by_id(flow)

        for edge in flow["data"]["edges"]:
            handle = edge["data"]["sourceHandle"]
            node = nodes.get(handle["id"])
            assert node is not None, f"{_edge_label(edge)}: source node missing"

            outputs = {o["name"]: o for o in node["data"]["node"].get("outputs", [])}
            output = outputs.get(handle["name"])
            assert output is not None, (
                f"{_edge_label(edge)}: no output named {handle['name']!r}; "
                f"node declares {sorted(outputs)}"
            )
            assert handle["output_types"] == list(output.get("types") or []), (
                f"{_edge_label(edge)}: handle claims output_types="
                f"{handle['output_types']}, node emits {output.get('types')}"
            )
            assert handle["dataType"] == node["data"]["type"], (
                f"{_edge_label(edge)}: handle claims dataType={handle['dataType']!r}, "
                f"node is {node['data']['type']!r}"
            )

    def test_target_handles_match_a_real_template_field(self, flow: dict[str, Any]) -> None:
        nodes = _nodes_by_id(flow)

        for edge in flow["data"]["edges"]:
            handle = edge["data"]["targetHandle"]
            node = nodes.get(handle["id"])
            assert node is not None, f"{_edge_label(edge)}: target node missing"

            field = node["data"]["node"]["template"].get(handle["fieldName"])
            assert isinstance(field, dict), (
                f"{_edge_label(edge)}: no template field {handle['fieldName']!r}"
            )
            assert handle["inputTypes"] == list(field.get("input_types") or []), (
                f"{_edge_label(edge)}: handle claims inputTypes={handle['inputTypes']}, "
                f"field accepts {field.get('input_types')}"
            )
            assert handle["type"] == field.get("type"), (
                f"{_edge_label(edge)}: handle claims type={handle['type']!r}, "
                f"field is {field.get('type')!r}"
            )

    def test_encoded_handle_strings_match_their_structured_form(self, flow: dict[str, Any]) -> None:
        """The string is the frontend's lookup key; the dict is only advisory."""
        for edge in flow["data"]["edges"]:
            assert edge["sourceHandle"] == _encode_handle(edge["data"]["sourceHandle"]), (
                f"{_edge_label(edge)}: encoded sourceHandle disagrees with data.sourceHandle"
            )
            assert edge["targetHandle"] == _encode_handle(edge["data"]["targetHandle"]), (
                f"{_edge_label(edge)}: encoded targetHandle disagrees with data.targetHandle"
            )

    def test_edge_endpoints_agree_with_their_handles(self, flow: dict[str, Any]) -> None:
        for edge in flow["data"]["edges"]:
            assert edge["source"] == edge["data"]["sourceHandle"]["id"], _edge_label(edge)
            assert edge["target"] == edge["data"]["targetHandle"]["id"], _edge_label(edge)


class TestConnectionTypesOverlap:
    """An edge whose source emits nothing the target accepts is a dead wire."""

    def test_every_edge_has_a_compatible_type(self, flow: dict[str, Any]) -> None:
        for edge in flow["data"]["edges"]:
            emitted = set(edge["data"]["sourceHandle"]["output_types"])
            accepted = set(edge["data"]["targetHandle"]["inputTypes"])
            assert emitted & accepted, (
                f"{_edge_label(edge)}: source emits {sorted(emitted)}, "
                f"target accepts {sorted(accepted)} -- no overlap"
            )
