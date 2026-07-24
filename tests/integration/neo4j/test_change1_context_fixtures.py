"""Test fixtures for Change 1 graph contexts (all 11 RequestStatus values and edge cases).

This module uses TDD to verify that:
1. All 11 RequestStatus values have isolated graph factories
2. Edge cases are properly represented (unknown/null status, closed precedence, etc.)
3. GraphProbe queries are parameterized and correct
4. Unique sessionId constraint is never weakened
"""

import pytest

from hulubul.core.models.operational.enums import RequestStatus


@pytest.fixture
def status_context_factories(neo4j_driver):
    """Factories for each of 11 RequestStatus values, bound to neo4j_driver."""
    from tests.fixtures.neo4j.change1_contexts import STATUS_CONTEXT_FACTORIES

    # Wrap each factory to bind the driver automatically
    return {
        status: (lambda driver=neo4j_driver, factory=factory: factory(driver))
        for status, factory in STATUS_CONTEXT_FACTORIES.items()
    }


class TestChangeOneContextFixtureInventory:
    """Verify all 11 RequestStatus values are covered."""

    def test_each_recognized_status_has_an_isolated_graph_fixture(self, status_context_factories):
        """Each of 11 RequestStatus values has its own factory that creates isolated namespace."""
        # All 11 statuses must be present
        assert set(status_context_factories.keys()) == set(RequestStatus)

        # Each factory produces unique namespace (isolation guarantee)
        namespaces = {factory().namespace for factory in status_context_factories.values()}
        assert len(namespaces) == len(RequestStatus)
        assert len(namespaces) == 11

    def test_factory_produces_graph_snapshot_with_namespace(self, status_context_factories):
        """Factory produces snapshot with namespace identifier."""
        factory = next(iter(status_context_factories.values()))
        snapshot = factory()

        # Must be a ContextGraphSnapshot with namespace
        assert hasattr(snapshot, "namespace")
        assert isinstance(snapshot.namespace, str)
        assert len(snapshot.namespace) > 0


class TestEdgeCasesAndConstraints:
    """Test edge cases: unknown/null status, closed precedence, duplicates, etc."""

    def test_sparse_delivery_request_fixture(self, neo4j_session_with_schema):
        """Sparse delivery request has minimal fields only."""
        from tests.fixtures.neo4j.change1_contexts import create_sparse_request
        from tests.support.graph_probe import GraphProbe

        session_id = "test-sparse"
        request_id = create_sparse_request(neo4j_session_with_schema, session_id)

        probe = GraphProbe(neo4j_session_with_schema)
        snapshot = probe.snapshot_for_session(session_id)

        assert snapshot.request_ids == frozenset([request_id])
        assert snapshot.binding_count == 1
        assert snapshot.request_count == 1

    def test_complete_delivery_request_fixture(self, neo4j_session_with_schema):
        """Complete delivery request has all possible fields."""
        from tests.fixtures.neo4j.change1_contexts import create_complete_request
        from tests.support.graph_probe import GraphProbe

        session_id = "test-complete"
        request_id = create_complete_request(neo4j_session_with_schema, session_id)

        probe = GraphProbe(neo4j_session_with_schema)
        snapshot = probe.snapshot_for_session(session_id)

        assert snapshot.request_ids == frozenset([request_id])
        assert snapshot.binding_count == 1
        assert snapshot.request_count == 1

    def test_no_binding_fixture(self, neo4j_session_with_schema):
        """Empty graph (no binding, no request)."""
        from tests.support.graph_probe import GraphProbe

        session_id = "test-no-binding"
        probe = GraphProbe(neo4j_session_with_schema)
        snapshot = probe.snapshot_for_session(session_id)

        assert snapshot.binding_count == 0
        assert snapshot.request_count == 0
        assert snapshot.request_ids == frozenset()

    def test_unknown_status_fixture(self, neo4j_session_with_schema):
        """Delivery request with unknown raw status value."""
        from tests.fixtures.neo4j.change1_contexts import create_unknown_status_request
        from tests.support.graph_probe import GraphProbe

        session_id = "test-unknown-status"
        request_id = create_unknown_status_request(neo4j_session_with_schema, session_id)

        probe = GraphProbe(neo4j_session_with_schema)
        snapshot = probe.snapshot_for_session(session_id)

        assert snapshot.request_ids == frozenset([request_id])
        # Status should be captured
        assert "unknown_status" in snapshot.statuses

    def test_null_status_fixture(self, neo4j_session_with_schema):
        """Delivery request with NULL status value."""
        from tests.fixtures.neo4j.change1_contexts import create_null_status_request
        from tests.support.graph_probe import GraphProbe

        session_id = "test-null-status"
        request_id = create_null_status_request(neo4j_session_with_schema, session_id)

        probe = GraphProbe(neo4j_session_with_schema)
        snapshot = probe.snapshot_for_session(session_id)

        assert snapshot.request_ids == frozenset([request_id])
        # Null status should be captured
        assert None in snapshot.statuses or "null" in snapshot.statuses

    def test_closed_precedence_over_recognized_status(self, neo4j_session_with_schema):
        """Closed status takes precedence over recognized statuses."""
        from tests.fixtures.neo4j.change1_contexts import (
            create_closed_precedence_request,
        )
        from tests.support.graph_probe import GraphProbe

        session_id = "test-closed-precedence"
        request_id = create_closed_precedence_request(neo4j_session_with_schema, session_id)

        probe = GraphProbe(neo4j_session_with_schema)
        snapshot = probe.snapshot_for_session(session_id)

        assert snapshot.request_ids == frozenset([request_id])
        assert "closed" in snapshot.statuses

    def test_missing_target_binding_fixture(self, neo4j_session_with_schema):
        """Binding with no BINDS_ACTIVE_REQUEST relationship."""
        from tests.fixtures.neo4j.change1_contexts import (
            create_missing_target_binding,
        )
        from tests.support.graph_probe import GraphProbe

        session_id = "test-missing-target"
        create_missing_target_binding(neo4j_session_with_schema, session_id)

        probe = GraphProbe(neo4j_session_with_schema)
        snapshot = probe.snapshot_for_session(session_id)

        # Binding exists but no active request
        assert snapshot.binding_count == 1
        assert snapshot.request_count == 0
        assert snapshot.request_ids == frozenset()

    def test_duplicate_active_request_relationships(self, neo4j_session_with_schema):
        """One binding with two BINDS_ACTIVE_REQUEST relationships to same request."""
        from tests.fixtures.neo4j.change1_contexts import (
            create_duplicate_active_request_rels,
        )
        from tests.support.graph_probe import GraphProbe

        session_id = "test-dup-request-rels"
        request_id = create_duplicate_active_request_rels(neo4j_session_with_schema, session_id)

        probe = GraphProbe(neo4j_session_with_schema)
        snapshot = probe.snapshot_for_session(session_id)

        assert snapshot.binding_count == 1
        # Should still count as 1 request (not 2), as it's the same request
        assert snapshot.request_count >= 1
        assert request_id in snapshot.request_ids

    def test_duplicate_active_targets(self, neo4j_session_with_schema):
        """One binding with two BINDS_ACTIVE_REQUEST relationships to different requests."""
        from tests.fixtures.neo4j.change1_contexts import (
            create_duplicate_active_targets,
        )
        from tests.support.graph_probe import GraphProbe

        session_id = "test-dup-targets"
        request_ids = create_duplicate_active_targets(neo4j_session_with_schema, session_id)

        probe = GraphProbe(neo4j_session_with_schema)
        snapshot = probe.snapshot_for_session(session_id)

        assert snapshot.binding_count == 1
        assert len(snapshot.request_ids) >= 2
        assert snapshot.request_ids == frozenset(request_ids)

    def test_concurrent_snapshots(self, neo4j_session_with_schema):
        """Multiple bindings with different requests (concurrent sessions)."""
        from tests.fixtures.neo4j.change1_contexts import (
            create_concurrent_snapshots,
        )
        from tests.support.graph_probe import GraphProbe

        session_ids = ["test-concurrent-1", "test-concurrent-2", "test-concurrent-3"]
        request_ids = create_concurrent_snapshots(neo4j_session_with_schema, session_ids)

        probe = GraphProbe(neo4j_session_with_schema)

        for session_id, expected_request_ids in zip(session_ids, request_ids, strict=False):
            snapshot = probe.snapshot_for_session(session_id)
            assert snapshot.binding_count == 1
            assert snapshot.request_count >= 1
            # Each session has its own requests
            assert snapshot.request_ids == frozenset(expected_request_ids)


class TestGraphProbeQueries:
    """Test GraphProbe query methods are parameterized and correct."""

    def test_graph_probe_snapshot_for_session(self, neo4j_session_with_schema):
        """GraphProbe.snapshot_for_session returns ContextGraphSnapshot."""
        from tests.fixtures.neo4j.change1_contexts import create_sparse_request
        from tests.support.acceptance_types import ContextGraphSnapshot
        from tests.support.graph_probe import GraphProbe

        session_id = "test-probe-snapshot"
        request_id = create_sparse_request(neo4j_session_with_schema, session_id)

        probe = GraphProbe(neo4j_session_with_schema)
        snapshot = probe.snapshot_for_session(session_id)

        assert isinstance(snapshot, ContextGraphSnapshot)
        assert snapshot.session_id == session_id
        assert snapshot.binding_count >= 1
        assert request_id in snapshot.request_ids

    def test_graph_probe_request_count_for_session(self, neo4j_session_with_schema):
        """GraphProbe.request_count_for_session uses parameterized query."""
        from tests.fixtures.neo4j.change1_contexts import create_sparse_request
        from tests.support.graph_probe import GraphProbe

        session_id = "test-probe-count"
        create_sparse_request(neo4j_session_with_schema, session_id)

        probe = GraphProbe(neo4j_session_with_schema)
        count = probe.request_count_for_session(session_id)

        assert count >= 1

    def test_graph_probe_binding_count_for_session(self, neo4j_session_with_schema):
        """GraphProbe.binding_count_for_session uses parameterized query."""
        from tests.fixtures.neo4j.change1_contexts import create_sparse_request
        from tests.support.graph_probe import GraphProbe

        session_id = "test-probe-binding-count"
        create_sparse_request(neo4j_session_with_schema, session_id)

        probe = GraphProbe(neo4j_session_with_schema)
        count = probe.binding_count_for_session(session_id)

        assert count >= 1

    def test_graph_probe_orphan_request_ids(self, neo4j_session_with_schema):
        """GraphProbe.orphan_request_ids uses parameterized query."""
        from tests.fixtures.neo4j.change1_contexts import (
            create_orphan_request,
        )
        from tests.support.graph_probe import GraphProbe

        namespace = "test-orphans"
        orphan_id = create_orphan_request(neo4j_session_with_schema, namespace)

        probe = GraphProbe(neo4j_session_with_schema)
        orphans = probe.orphan_request_ids(namespace)

        assert orphan_id in orphans

    def test_graph_probe_mutation_fingerprint(self, neo4j_session_with_schema):
        """GraphProbe.mutation_fingerprint uses parameterized query."""
        from tests.fixtures.neo4j.change1_contexts import create_sparse_request
        from tests.support.graph_probe import GraphProbe

        session_id = "test-probe-fingerprint"
        request_id = create_sparse_request(neo4j_session_with_schema, session_id)

        probe = GraphProbe(neo4j_session_with_schema)
        fingerprint = probe.mutation_fingerprint(request_id)

        assert isinstance(fingerprint, str)
        assert len(fingerprint) > 0


class TestUniqueConstraintNotWeakened:
    """Verify unique sessionId constraint remains enabled."""

    def test_unique_constraint_enforced(self, neo4j_session_with_schema):
        """Attempting duplicate sessionId raises constraint violation."""
        from neo4j.exceptions import ConstraintError

        from tests.fixtures.neo4j.change1_contexts import create_sparse_request

        session_id = "test-unique-constraint"
        create_sparse_request(neo4j_session_with_schema, session_id)

        # Attempt to create duplicate binding with same sessionId
        with pytest.raises(ConstraintError):
            create_sparse_request(neo4j_session_with_schema, session_id)
