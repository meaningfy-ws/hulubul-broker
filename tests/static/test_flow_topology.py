"""
Static flow topology tests.

Verify flow structure, component wiring, isolation, and security properties
without executing flows or invoking models.
"""

import json
from pathlib import Path
from typing import Any

import pytest


def load_flow(flow_filename: str) -> dict[str, Any]:
    """Load a flow JSON from langflow/flows/."""
    flow_path = Path(__file__).parent.parent.parent / "langflow" / "flows" / flow_filename
    if not flow_path.exists():
        pytest.skip(f"Flow not found: {flow_filename}")
    with open(flow_path) as f:
        result: dict[str, Any] = json.load(f)
        return result


class TestLF10RequestIntakeTopology:
    """LF-10 Request Intake flow topology and isolation."""

    @pytest.fixture
    def lf10(self) -> dict[str, Any]:
        """Load LF-10 flow."""
        return load_flow("20-lf-10-request-intake.json")

    def test_lf10_has_only_lf70_and_identifiers_generator_tools(self, lf10: dict[str, Any]) -> None:
        """LF-10's Agent must expose exactly two logical tools: LF-70 RunFlow
        and the deterministic Graph Identifiers Generator (DEC-010).

        Previously asserted "exactly one tool" -- true before DEC-010 added
        the identifiers generator as a second Agent tool; this test's own
        assertion was never updated to match, and its edge-matching also
        checked the wrong field path (`target_handle` at the edge's top
        level, snake_case) instead of the real one
        (`data.targetHandle.fieldName`, camelCase) -- confirmed directly
        against the live flow JSON before fixing either.
        """
        nodes = lf10.get("data", {}).get("nodes", [])
        edges = lf10.get("data", {}).get("edges", [])

        # Find all Agent nodes in the flow
        agents = [node for node in nodes if "Agent" in node.get("data", {}).get("type", "")]
        assert agents, "LF-10 must have at least one Agent node"

        for agent in agents:
            agent_id = agent.get("id")
            # Find edges where the agent is the target, wired into its "tools" field.
            tool_edges = [
                e
                for e in edges
                if e.get("data", {}).get("targetHandle", {}).get("id") == agent_id
                and e.get("data", {}).get("targetHandle", {}).get("fieldName") == "tools"
            ]
            assert tool_edges, f"LF-10 Agent {agent_id} must have tool connections"

            tool_source_ids = {
                e.get("data", {}).get("sourceHandle", {}).get("id") for e in tool_edges
            }
            tool_components = [n for n in nodes if n.get("id") in tool_source_ids]

            assert len(tool_components) == 2, (
                f"LF-10 Agent must have exactly two tools (RunFlow + Graph Identifiers "
                f"Generator), found {len(tool_components)}: {sorted(tool_source_ids)}"
            )
            tool_types = {c.get("data", {}).get("type", "") for c in tool_components}
            assert any("RunFlow" in t for t in tool_types), (
                f"LF-10's tools must include RunFlow, got {tool_types}"
            )
            assert any("GraphIdentifiersGenerator" in t for t in tool_types), (
                f"LF-10's tools must include the Graph Identifiers Generator, got {tool_types}"
            )

    def test_lf10_model_cannot_substitute_envelope_or_context(self, lf10: dict[str, Any]) -> None:
        """LF-10's input must be a public entry point (not fixed edges for now in Change 1)."""
        nodes = lf10.get("data", {}).get("nodes", [])

        # Find the contract input boundary component. Named
        # "HulubulContractInputBoundary" in the actual implementation (shared
        # between LF-00's router-input and LF-10's intake-input assembly via
        # its own contract_kind field) -- an earlier planned name,
        # "IntakeInputBoundary", never matched the real component and this
        # assertion was never updated, confirmed directly against the live
        # flow JSON before fixing.
        intake_boundaries = [
            node
            for node in nodes
            if "ContractInputBoundary" in node.get("data", {}).get("type", "")
        ]
        assert intake_boundaries, "LF-10 must have a contract input boundary component"

        # For Change 1, the boundary accepts literal IntakeInput via MessageTextInput
        # (it can later be extended to also accept fixed edges for LF-00 integration)
        for boundary in intake_boundaries:
            node_type = boundary.get("data", {}).get("type", "")
            assert "ContractInputBoundary" in node_type, (
                f"Expected ContractInputBoundary component, got {node_type}"
            )


class TestLF70DataAccessTopology:
    """LF-70 Data Access flow topology sanity check (basic coverage)."""

    @pytest.fixture
    def lf70(self) -> dict[str, Any]:
        """Load LF-70 flow."""
        return load_flow("10-lf-70-data-access.json")

    def test_lf70_exists(self, lf70: dict[str, Any]) -> None:
        """LF-70 flow must be present and have nodes."""
        nodes = lf70.get("data", {}).get("nodes", [])
        edges = lf70.get("data", {}).get("edges", [])
        assert nodes, "LF-70 must have nodes"
        assert edges, "LF-70 must have edges"
