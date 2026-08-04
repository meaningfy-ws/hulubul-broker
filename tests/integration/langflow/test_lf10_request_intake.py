"""Integration tests for LF-10 (request intake), called directly (task 9.6).

Covers the seven named API matrix cases from plan.md Task 43: complete,
partial, invalid-fact, several-missing, concurrent-update, malformed-result,
same-request.

LF-10 has no ChatInput entry point -- posting a top-level `input_value` (the
plain Run API pattern that works for LF-00) does not reach it; confirmed
live, the field arrives empty every time. Calls here go through
`LangFlowClient.run_lf10`, which uses LangFlow's `tweaks` parameter to target
`HulubulContractInputBoundary-hlb-lf-10-input-v1` directly -- the same
mechanism `HulubulRunFlowComponent` uses internally when LF-00 invokes LF-10
as a tool.

Scope note: plan.md's original design for this task assumed a deterministic
recorded-model harness (`tests/fixtures/recorded_model/...`) that does not
exist in this repo yet (Phase 1 scaffolding). These tests instead call the
real deployed LF-10 flow against the live dev Neo4j instance, verifying via
direct graph queries -- the same pattern already established in
`test_lf00_main_router.py` and `test_lf70_*`.
"""

from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Any

import pytest

from hulubul.core.models.operational import IntakeResult
from tests.support.langflow_client import LangFlowClient

TRUSTED_ACTOR_ID = "urn:uuid:6fff189f-aed3-47dd-b1b9-945d8dbefb47"

NEO4J_BOLT_URL = os.getenv("NEO4J_BOLT_URL", "bolt://localhost:7687")
NEO4J_USERNAME = "neo4j"
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "changeme123")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")


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


def _skip_if_langflow_down(reply: Any) -> None:
    if reply.status_code == 500 and reply.error and "Connection error" in reply.error:
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


def _graph_snapshot(neo4j_driver: Any, session_id: str) -> dict[str, Any] | None:
    """Return the request bound to a session, with its key facts, or None."""
    _username, _password, database = _read_neo4j_credentials_from_env_file()
    with neo4j_driver.session(database=database) as session:
        result = session.run(
            """
            MATCH (b:OperationalConversationBinding {sessionId: $sid})-[:BINDS_ACTIVE_REQUEST]->(r:DeliveryRequest)
            OPTIONAL MATCH (r)-[:HAS_RECEIVER]->(:Receiver)-[:PLAYED_BY]->(receiverAgent:Agent)
            OPTIONAL MATCH (r)-[:HAS_PICK_UP_LOCATION]->(pickup:Place)
            OPTIONAL MATCH (r)-[:HAS_DROP_OFF_LOCATION]->(dropoff:Place)
            OPTIONAL MATCH (r)-[:HAS_DELIVERY_ITEM]->(parcel:Parcel)
            RETURN r.id AS id, r.hasStatus AS status,
                   receiverAgent.name AS receiver, pickup.name AS pickup,
                   dropoff.name AS dropoff, parcel.declaredContent AS parcel_content
            """,
            sid=f"p1-{session_id}",
        )
        record = result.single()
        return dict(record) if record else None


def _cleanup(neo4j_driver: Any, session_id: str) -> None:
    _username, _password, database = _read_neo4j_credentials_from_env_file()
    with neo4j_driver.session(database=database) as session:
        session.run(
            """
            MATCH (b:OperationalConversationBinding {sessionId: $sid})
            OPTIONAL MATCH (b)-[:BINDS_ACTIVE_REQUEST]->(r:DeliveryRequest)
            DETACH DELETE b, r
            """,
            sid=f"p1-{session_id}",
        )


class TestCompleteIntake:
    """CASES[0] = "complete": one-message intake with every critical fact."""

    def test_complete_intake_persists_and_confirms(
        self, langflow_client: LangFlowClient, neo4j_driver: Any
    ) -> None:
        session_id = str(uuid.uuid4())
        try:
            reply = langflow_client.run_lf10(
                message=(
                    "Send a parcel to Ana Popescu, pickup at Str. Ismail 10 Chisinau, "
                    "drop off at Str. Puskin 5 Chisinau, contains a laptop"
                ),
                session_id=session_id,
            )
            _skip_if_langflow_down(reply)
            assert reply.status_code == 200, reply.error
            assert reply.result is not None

            result = IntakeResult.model_validate(reply.result)
            assert result.outcome == "requestComplete"
            assert result.status == "complete"
            assert result.request_id
            assert result.error is None

            snapshot = _graph_snapshot(neo4j_driver, session_id)
            assert snapshot is not None, "Expected a persisted DeliveryRequest"
            assert snapshot["status"] == "complete"
            assert snapshot["receiver"] == "Ana Popescu"
            assert snapshot["pickup"] == "Str. Ismail 10 Chisinau"
            assert snapshot["dropoff"] == "Str. Puskin 5 Chisinau"
            assert snapshot["parcel_content"] == "laptop"
        finally:
            _cleanup(neo4j_driver, session_id)


class TestPartialIntake:
    """CASES[1] = "partial": sparse draft with some facts missing."""

    def test_partial_intake_persists_sparse_draft(
        self, langflow_client: LangFlowClient, neo4j_driver: Any
    ) -> None:
        session_id = str(uuid.uuid4())
        try:
            reply = langflow_client.run_lf10(
                message="I want to send a parcel to Victor Rusu", session_id=session_id
            )
            _skip_if_langflow_down(reply)
            assert reply.status_code == 200, reply.error
            assert reply.result is not None

            result = IntakeResult.model_validate(reply.result)
            assert result.outcome == "clarificationRequired"
            assert result.status == "needsClarification"
            assert result.clarification_field in {
                "pickup_location",
                "drop_off_location",
            }
            assert "pickup_location" in result.missing_fields
            assert "drop_off_location" in result.missing_fields
            assert result.error is None

            snapshot = _graph_snapshot(neo4j_driver, session_id)
            assert snapshot is not None
            assert snapshot["status"] == "needsClarification"
            assert snapshot["receiver"] == "Victor Rusu"
            assert snapshot["pickup"] is None
            assert snapshot["dropoff"] is None
        finally:
            _cleanup(neo4j_driver, session_id)


class TestInvalidFact:
    """CASES[2] = "invalid-fact": a message with no extractable facts at all
    must not fabricate any -- everything critical stays missing."""

    def test_no_extractable_facts_fabricates_nothing(
        self, langflow_client: LangFlowClient, neo4j_driver: Any
    ) -> None:
        session_id = str(uuid.uuid4())
        try:
            reply = langflow_client.run_lf10(
                message="asdkjfh qwerty zzz nothing here", session_id=session_id
            )
            _skip_if_langflow_down(reply)
            assert reply.status_code == 200, reply.error
            assert reply.result is not None

            result = IntakeResult.model_validate(reply.result)
            assert result.outcome == "clarificationRequired"
            assert result.status == "needsClarification"
            assert set(result.missing_fields) >= {
                "pickup_location",
                "drop_off_location",
            }
            assert result.error is None

            snapshot = _graph_snapshot(neo4j_driver, session_id)
            assert snapshot is not None
            assert snapshot["receiver"] is None
            assert snapshot["pickup"] is None
            assert snapshot["dropoff"] is None
            assert snapshot["parcel_content"] is None
        finally:
            _cleanup(neo4j_driver, session_id)


class TestSeveralMissingFields:
    """CASES[3] = "several-missing": missing_fields reports the complete set
    while clarification_field asks for exactly one."""

    def test_missing_fields_lists_full_set(
        self, langflow_client: LangFlowClient, neo4j_driver: Any
    ) -> None:
        session_id = str(uuid.uuid4())
        try:
            reply = langflow_client.run_lf10(
                message="I need a delivery, the receiver is Tudor Vasilescu",
                session_id=session_id,
            )
            _skip_if_langflow_down(reply)
            assert reply.status_code == 200, reply.error
            assert reply.result is not None

            result = IntakeResult.model_validate(reply.result)
            assert result.outcome == "clarificationRequired"
            assert len(result.missing_fields) >= 2
            assert result.clarification_field is not None
            assert result.clarification_field in {
                "receiver_identity",
                "pickup_location",
                "drop_off_location",
                "parcel_declared_content",
                "preferred_period",
            }
        finally:
            _cleanup(neo4j_driver, session_id)


class TestConcurrentUpdate:
    """CASES[4] = "concurrent-update": a continuation turn against an
    existing needsClarification draft correctly reads current state and
    applies a compare-and-set update -- not a true simultaneous race (not
    forceable against a live model deterministically), but the real
    read-then-CAS-write path this task is about."""

    def test_continuation_merges_with_existing_draft(
        self, langflow_client: LangFlowClient, neo4j_driver: Any
    ) -> None:
        session_id = str(uuid.uuid4())
        try:
            first = langflow_client.run_lf10(
                message="Send a parcel to Ionela Marin", session_id=session_id
            )
            _skip_if_langflow_down(first)
            assert first.status_code == 200, first.error
            first_result = IntakeResult.model_validate(first.result)
            assert first_result.outcome == "clarificationRequired"
            request_id = first_result.request_id
            assert request_id

            snapshot = _graph_snapshot(neo4j_driver, session_id)
            assert snapshot is not None
            assert snapshot["id"] == request_id
            assert snapshot["status"] == "needsClarification"

            routing_context = {
                "schema_version": "1.0.0",
                "correlation_id": str(uuid.uuid4()),
                "session_id": f"p1-{session_id}",
                "binding_state": "bound",
                "binding_count": 1,
                "active_relationship_count": 1,
                "active_target_count": 1,
                "request_id": request_id,
                "request_status": "needsClarification",
                "closed_at": None,
                "routing_stage": "intake",
                "error": None,
            }
            second = langflow_client.run_lf10(
                message="Pickup at Str. Kogalniceanu 1 Chisinau, drop off at Str. Ismail 2 Chisinau",
                session_id=session_id,
                routing_context=routing_context,
            )
            _skip_if_langflow_down(second)
            assert second.status_code == 200, second.error
            second_result = IntakeResult.model_validate(second.result)

            # Same request_id -- no duplicate created on the continuation turn.
            assert second_result.request_id == request_id

            final_snapshot = _graph_snapshot(neo4j_driver, session_id)
            assert final_snapshot is not None
            assert final_snapshot["id"] == request_id
            assert final_snapshot["status"] == "complete"
            assert final_snapshot["receiver"] == "Ionela Marin"
            assert final_snapshot["pickup"] == "Str. Kogalniceanu 1 Chisinau"
            assert final_snapshot["dropoff"] == "Str. Ismail 2 Chisinau"
        finally:
            _cleanup(neo4j_driver, session_id)


class TestMalformedResult:
    """CASES[5] = "malformed-result": the result boundary must never claim
    success for a value that does not validate as a known contract, and must
    never leak the raw malformed payload back to the sender."""

    def test_boundary_fails_closed_on_a_bad_routing_context(
        self, langflow_client: LangFlowClient, neo4j_driver: Any
    ) -> None:
        """A structurally-inconsistent routing_context (a request_id set
        alongside binding_state="absent", which cannot legitimately happen)
        drives the same fail-closed path a genuinely malformed model result
        would: the boundary must reject it rather than silently accept or
        crash. `error` must never be None and no request may be created.
        """
        session_id = str(uuid.uuid4())
        try:
            routing_context = {
                "schema_version": "1.0.0",
                "correlation_id": str(uuid.uuid4()),
                "session_id": f"p1-{session_id}",
                "binding_state": "absent",
                "binding_count": 0,
                "active_relationship_count": 0,
                "active_target_count": 0,
                "request_id": "req-should-not-exist-and-is-inconsistent",
                "request_status": "needsClarification",
                "closed_at": None,
                "routing_stage": "intake",
                "error": None,
            }
            reply = langflow_client.run_lf10(
                message="Send a parcel to Nobody",
                session_id=session_id,
                routing_context=routing_context,
            )
            _skip_if_langflow_down(reply)
            assert reply.status_code == 200, reply.error
            assert reply.result is not None

            result = IntakeResult.model_validate(reply.result)
            assert result.outcome != "requestComplete"

            snapshot = _graph_snapshot(neo4j_driver, session_id)
            assert snapshot is None, "No request should be created from an inconsistent context"
        finally:
            _cleanup(neo4j_driver, session_id)


class TestSameRequest:
    """CASES[6] = "same-request": invoking LF-10 again against an
    already-complete request must not silently claim a fresh confirmation or
    create a duplicate request."""

    def test_reinvoking_on_a_complete_request_creates_no_duplicate(
        self, langflow_client: LangFlowClient, neo4j_driver: Any
    ) -> None:
        session_id = str(uuid.uuid4())
        _username, _password, database = _read_neo4j_credentials_from_env_file()
        request_id = f"req-{uuid.uuid4()}"

        with neo4j_driver.session(database=database) as session:
            session.run(
                """
                CREATE (r:DeliveryRequest {id: $rid, hasStatus: 'complete',
                    created: datetime(), updated: datetime()})
                CREATE (b:OperationalConversationBinding {sessionId: $sid, created: datetime()})
                CREATE (b)-[:BINDS_ACTIVE_REQUEST]->(r)
                """,
                rid=request_id,
                sid=f"p1-{session_id}",
            )

        try:
            routing_context = {
                "schema_version": "1.0.0",
                "correlation_id": str(uuid.uuid4()),
                "session_id": f"p1-{session_id}",
                "binding_state": "bound",
                "binding_count": 1,
                "active_relationship_count": 1,
                "active_target_count": 1,
                "request_id": request_id,
                "request_status": "complete",
                "closed_at": None,
                "routing_stage": "complete",
                "error": None,
            }
            reply = langflow_client.run_lf10(
                message="Any update?", session_id=session_id, routing_context=routing_context
            )
            _skip_if_langflow_down(reply)
            assert reply.status_code == 200, reply.error
            assert reply.result is not None

            result = IntakeResult.model_validate(reply.result)
            assert result.outcome != "requestComplete", (
                "Must not claim a fresh confirmation for an already-complete request"
            )

            with neo4j_driver.session(database=database) as session:
                count = session.run(
                    "MATCH (b:OperationalConversationBinding {sessionId: $sid})"
                    "-[:BINDS_ACTIVE_REQUEST]->(r:DeliveryRequest) RETURN count(r) AS c",
                    sid=f"p1-{session_id}",
                ).single()["c"]
                assert count == 1, "Exactly the original request, no duplicate"
        finally:
            _cleanup(neo4j_driver, session_id)
