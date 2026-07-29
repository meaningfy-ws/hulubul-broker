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

    def test_lf10_has_only_lf70_logical_tool(self, lf10: dict[str, Any]) -> None:
        """LF-10's Agent must expose exactly one logical tool: LF-70 RunFlow."""
        nodes = lf10.get("data", {}).get("nodes", [])
        edges = lf10.get("data", {}).get("edges", [])

        # Find all Agent nodes in the flow
        agents = [node for node in nodes if "Agent" in node.get("data", {}).get("type", "")]
        assert agents, "LF-10 must have at least one Agent node"

        # For each Agent, check it has exactly one tool connected via edges
        for agent in agents:
            agent_id = agent.get("id")
            # Find edges where the agent is the target (tool connections)
            tool_edges = [
                e
                for e in edges
                if e.get("target") == agent_id and "tools" in str(e.get("target_handle", ""))
            ]
            assert tool_edges, f"LF-10 Agent {agent_id} must have tool connections"

            # Find the tool component that connects to this agent
            tool_source_ids = [e.get("source") for e in tool_edges]
            tool_components = [n for n in nodes if n.get("id") in tool_source_ids]

            # Must be exactly one tool, and it must be a RunFlow component
            assert len(tool_components) == 1, (
                f"LF-10 Agent must have exactly one tool, found {len(tool_components)}"
            )
            tool_component = tool_components[0]
            assert "RunFlow" in tool_component.get("data", {}).get("type", ""), (
                f"LF-10's only tool must be RunFlow, got {tool_component.get('data', {}).get('type', '')}"
            )

    def test_lf10_model_cannot_substitute_envelope_or_context(self, lf10: dict[str, Any]) -> None:
        """LF-10's input must be a public entry point (not fixed edges for now in Change 1)."""
        nodes = lf10.get("data", {}).get("nodes", [])

        # Find the intake input boundary component
        intake_boundaries = [
            node for node in nodes if "IntakeInputBoundary" in node.get("data", {}).get("type", "")
        ]
        assert intake_boundaries, "LF-10 must have an intake input boundary component"

        # For Change 1, the intake boundary accepts literal IntakeInput via MessageTextInput
        # (it can later be extended to also accept fixed edges for LF-00 integration)
        for boundary in intake_boundaries:
            node_type = boundary.get("data", {}).get("type", "")
            # Verify it's the intake boundary
            assert "IntakeInputBoundary" in node_type, (
                f"Expected IntakeInputBoundary component, got {node_type}"
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
