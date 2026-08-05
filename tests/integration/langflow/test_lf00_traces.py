"""Integration tests for LF-00's runtime trace boundary (task 10.4).

Verifies, via LangFlow's native trace/span data (never the flow's own chat
response), three architectural invariants for the "complete status"
no-mutation route:

- LF-00 always loads routing context (a `Run Flow` call to LF-70) before the
  Router Agent runs.
- No raw MCP tool (the real `hulubul_neo4j` server tools:
  `get_neo4j_schema`/`read_neo4j_cypher`/`write_neo4j_cypher`) is ever
  invoked directly by LF-00 -- only LF-70 may call one, via its `MCP Tools`
  component.
- The Router model is invoked exactly once for a scenario with no reason to
  call any tool.

Scenario choice: deliberately the "complete status" no-mutation route, not
the absent-binding/"routes to intake" one. The Router Agent's decision to
invoke the LF-10 tool for the intake route is a genuine, confirmed LLM
behavioral non-determinism (verified live: identical repeated calls
sometimes produced 15 spans/1 LLM call, sometimes 26 spans/multiple LLM
calls) -- not something these tests, or the frozen topology fixture, can
honestly assert on. The complete-status route has no plausible reason for
the Router to call any tool and was verified deterministic across repeated
live runs.
"""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import uuid4

import pytest

from tests.support.langflow_client import LangFlowClient
from tests.support.trace_metadata_probe import TraceMetadataProbe, normalize_topology

if TYPE_CHECKING:
    from tests.support.trace_metadata_probe import NativeSpanMetadata

LF_00_FLOW_ID = uuid.UUID("29c624c0-7940-48c3-8164-123620c53562")
LF_70_FLOW_ID = uuid.UUID("94f6774d-ebc7-5bf1-8486-886f91886a5f")
TRUSTED_ACTOR_ID = "urn:uuid:6fff189f-aed3-47dd-b1b9-945d8dbefb47"

# Real MCP tool names, the mcp-neo4j-cypher server's exact inventory --
# see infra/scripts/mcp-readiness.py's EXPECTED_TOOLS and infra/README.md.
# A RunFlow-as-tool span (e.g. "lf-10-request-intake_tool") also has
# type=="tool" but is not a raw MCP call, so name must be checked too.
KNOWN_MCP_TOOL_NAMES = frozenset({"get_neo4j_schema", "read_neo4j_cypher", "write_neo4j_cypher"})

NEO4J_BOLT_URL = os.getenv("NEO4J_BOLT_URL", "bolt://localhost:7687")
NEO4J_USERNAME = "neo4j"
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "changeme123")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")

FIXTURE_PATH = (
    Path(__file__).resolve().parents[2] / "fixtures" / "langflow" / "trace_topology_v1.json"
)


def _read_neo4j_credentials_from_env_file() -> tuple[str, str, str]:
    """Read Neo4j credentials from infra/.env if environment vars are not set."""
    env_file = Path(__file__).resolve().parents[4] / "infra" / ".env"
    if not env_file.exists():
        return NEO4J_USERNAME, NEO4J_PASSWORD, NEO4J_DATABASE

    config: dict[str, str] = {}
    with open(env_file) as f:
        for line in f:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if "=" in stripped:
                key, value = stripped.split("=", 1)
                config[key.strip()] = value.strip()

    return (
        config.get("NEO4J_USERNAME", NEO4J_USERNAME),
        config.get("NEO4J_PASSWORD", NEO4J_PASSWORD),
        config.get("NEO4J_DATABASE", NEO4J_DATABASE),
    )


class _Conversation:
    """Minimal ConversationLike for direct client calls."""

    def __init__(self, session_id: str, display_name: str = "Trace Integration Test") -> None:
        self.actor_id: str | None = TRUSTED_ACTOR_ID
        self.display_name: str | None = display_name
        self.session_id: str | None = session_id


def _skip_if_langflow_down(response: Any) -> None:
    if response.status_code == 500 and response.error and "Connection error" in response.error:
        pytest.skip("LangFlow server not running")


@pytest.fixture
def neo4j_driver() -> Any:
    """Create a Neo4j driver for the live dev instance."""
    try:
        from neo4j import GraphDatabase
    except ImportError:
        pytest.skip("neo4j not installed; run: poetry install --with integration")

    username, password, database = _read_neo4j_credentials_from_env_file()

    try:
        driver = GraphDatabase.driver(NEO4J_BOLT_URL, auth=(username, password))
        with driver.session(database=database) as session:
            session.run("RETURN 1")
    except Exception as e:
        pytest.skip(f"Cannot connect to Neo4j at {NEO4J_BOLT_URL}: {e}")

    yield driver
    driver.close()


@pytest.fixture
def trace_probe() -> TraceMetadataProbe:
    """Create a TraceMetadataProbe for the live dev LangFlow instance."""
    base_url = os.getenv("LANGFLOW_URL", "http://localhost:7860")
    api_key = os.getenv("LANGFLOW_API_KEY", "local-dev-key-hulubul-phase1")
    return TraceMetadataProbe(base_url=base_url, api_key=api_key)


@pytest.fixture
def complete_status_scenario(
    langflow_client: LangFlowClient,
    neo4j_driver: Any,
    trace_probe: TraceMetadataProbe,
) -> Any:
    """Run the deterministic "complete status" no-mutation route once.

    Seeds a bound, complete-status DeliveryRequest, invokes LF-00, and
    returns (session_id, lf00_spans, lf70_spans) -- cleans up the Neo4j
    fixture afterward regardless of outcome.
    """
    username, password, database = _read_neo4j_credentials_from_env_file()
    session_id = f"p1-{uuid4()}"
    request_id = str(uuid4())

    with neo4j_driver.session(database=database) as session:
        session.run(
            """
            CREATE (r:DeliveryRequest {
                id: $request_id,
                hasStatus: 'complete',
                created: datetime(),
                updated: datetime()
            })
            """,
            request_id=request_id,
        )
        session.run(
            """
            MATCH (r:DeliveryRequest {id: $request_id})
            CREATE (b:OperationalConversationBinding {
                sessionId: $session_id,
                created: datetime()
            })
            CREATE (b)-[:BINDS_ACTIVE_REQUEST]->(r)
            """,
            session_id=session_id,
            request_id=request_id,
        )

    try:
        reply = langflow_client.run_lf00(_Conversation(session_id=session_id), "Status update?")
        _skip_if_langflow_down(reply)
        assert reply.status_code == 200, reply.error
        assert reply.chat_text == "request intake complete"

        lf00_spans = trace_probe.spans_for_session(flow_ids=(LF_00_FLOW_ID,), session_id=session_id)
        lf70_spans = trace_probe.spans_for_session(flow_ids=(LF_70_FLOW_ID,), session_id=session_id)
        yield session_id, lf00_spans, lf70_spans
    finally:
        with neo4j_driver.session(database=database) as session:
            session.run(
                "MATCH (b:OperationalConversationBinding {sessionId: $sid}) DETACH DELETE b",
                sid=session_id,
            )
            session.run("MATCH (r:DeliveryRequest {id: $rid}) DETACH DELETE r", rid=request_id)


def _find_span(spans: tuple[NativeSpanMetadata, ...], name: str) -> NativeSpanMetadata:
    for span in spans:
        if span.name == name:
            return span
    pytest.fail(f"No span named {name!r} found among {[s.name for s in spans]}")


class TestContextLookupOrdering:
    """LF-00 always loads routing context before the Router Agent runs."""

    def test_context_lookup_precedes_router(self, complete_status_scenario: Any) -> None:
        _session_id, lf00_spans, _lf70_spans = complete_status_scenario
        assert lf00_spans, "No LF-00 spans found for this session"

        context_lookup = _find_span(lf00_spans, "Run Flow")
        router_agent = _find_span(lf00_spans, "Router Agent")

        assert context_lookup.start_time < router_agent.start_time, (
            "Routing context lookup must start before the Router Agent"
        )


class TestNoMcpToolBoundary:
    """Raw MCP tools may only ever be invoked by LF-70."""

    def test_no_raw_mcp_tool_in_lf00(self, complete_status_scenario: Any) -> None:
        _session_id, lf00_spans, _lf70_spans = complete_status_scenario
        mcp_spans = [s for s in lf00_spans if s.type == "tool" and s.name in KNOWN_MCP_TOOL_NAMES]
        assert not mcp_spans, f"LF-00 must never call a raw MCP tool directly: {mcp_spans}"

    def test_mcp_tool_present_in_lf70_companion_trace(self, complete_status_scenario: Any) -> None:
        _session_id, _lf00_spans, lf70_spans = complete_status_scenario
        mcp_spans = [s for s in lf70_spans if s.type == "tool" and s.name in KNOWN_MCP_TOOL_NAMES]
        assert mcp_spans, "Expected LF-70's companion trace to show a raw MCP tool call"


class TestRouterModelInvocationCount:
    """The Router model runs exactly once when there is no reason to call a tool."""

    def test_router_model_invoked_exactly_once(self, complete_status_scenario: Any) -> None:
        _session_id, lf00_spans, _lf70_spans = complete_status_scenario
        llm_spans = [s for s in lf00_spans if s.type == "llm"]
        assert len(llm_spans) == 1, f"Expected exactly one model call, got {len(llm_spans)}"


class TestFrozenTopologyFixture:
    """The live topology for this scenario matches the frozen fixture."""

    @pytest.fixture(scope="class")
    def fixture_data(self) -> dict[str, Any]:
        if not FIXTURE_PATH.exists():
            pytest.skip(f"Trace topology fixture not found: {FIXTURE_PATH}")
        with open(FIXTURE_PATH) as f:
            data: dict[str, Any] = json.load(f)
        return data

    def test_fixture_is_well_formed(self, fixture_data: dict[str, Any]) -> None:
        assert fixture_data["flows"]["lf_00"]["flow_id"] == str(LF_00_FLOW_ID)
        assert fixture_data["flows"]["lf_70"]["flow_id"] == str(LF_70_FLOW_ID)
        assert fixture_data["flows"]["lf_00"]["spans"]
        assert fixture_data["flows"]["lf_70"]["spans"]

    def test_live_lf00_topology_matches_fixture(
        self, complete_status_scenario: Any, fixture_data: dict[str, Any]
    ) -> None:
        _session_id, lf00_spans, _lf70_spans = complete_status_scenario
        live_topology = [list(t) for t in normalize_topology(lf00_spans)]
        assert live_topology == fixture_data["flows"]["lf_00"]["spans"]

    def test_live_lf70_topology_matches_fixture(
        self, complete_status_scenario: Any, fixture_data: dict[str, Any]
    ) -> None:
        _session_id, _lf00_spans, lf70_spans = complete_status_scenario
        live_topology = [list(t) for t in normalize_topology(lf70_spans)]
        assert live_topology == fixture_data["flows"]["lf_70"]["spans"]
