"""Direct Neo4j query helpers for graph assertions (GraphProbe).

All queries use parameterized form (no string interpolation). Queries are
organized by concern: session snapshot, counts, orphan detection, mutation fingerprinting.
"""

from neo4j import Driver

from tests.support.acceptance_types import ContextGraphSnapshot


class GraphProbe:
    """Helper class for direct Neo4j queries against test graphs.

    Provides parameterized query methods to capture graph state and verify
    acceptance test expectations without relying on application code.
    """

    def __init__(self, driver: Driver):
        """Initialize probe with Neo4j driver.

        Args:
            driver: Neo4j driver instance (session-scoped fixture).
        """
        self.driver = driver

    def snapshot_for_session(self, session_id: str) -> ContextGraphSnapshot:
        """Capture complete graph snapshot for a session.

        Returns binding count, request count, request IDs, and request statuses
        for the given session ID.

        Args:
            session_id: OperationalConversationBinding.sessionId to query.

        Returns:
            ContextGraphSnapshot with binding, request, and status information.
        """
        binding_count = self.binding_count_for_session(session_id)
        request_count = self.request_count_for_session(session_id)
        request_ids = self._query_request_ids_for_session(session_id)
        statuses = self._query_request_statuses_for_session(session_id)

        return ContextGraphSnapshot(
            session_id=session_id,
            binding_count=binding_count,
            request_count=request_count,
            request_ids=frozenset(request_ids),
            statuses=frozenset(statuses),
        )

    def request_count_for_session(self, session_id: str) -> int:
        """Count distinct DeliveryRequest nodes bound to a session.

        Uses parameterized query to count requests linked via BINDS_ACTIVE_REQUEST.

        Args:
            session_id: OperationalConversationBinding.sessionId to query.

        Returns:
            Count of distinct DeliveryRequest nodes for this session.
        """
        query = """
        MATCH (:OperationalConversationBinding {sessionId: $session_id})-[:BINDS_ACTIVE_REQUEST]->(r:DeliveryRequest)
        RETURN count(DISTINCT r.id) AS count
        """
        result = self.driver.execute_query(query, session_id=session_id)
        if result.records:
            return int(result.records[0]["count"])
        return 0

    def binding_count_for_session(self, session_id: str) -> int:
        """Count OperationalConversationBinding nodes for a session.

        Uses parameterized query to count bindings by sessionId.

        Args:
            session_id: OperationalConversationBinding.sessionId to query.

        Returns:
            Count of OperationalConversationBinding nodes (should be 0 or 1 due to unique constraint).
        """
        query = """
        MATCH (b:OperationalConversationBinding {sessionId: $session_id})
        RETURN count(b) AS count
        """
        result = self.driver.execute_query(query, session_id=session_id)
        if result.records:
            return int(result.records[0]["count"])
        return 0

    def orphan_request_ids(self, namespace: str) -> frozenset[str]:
        """Find DeliveryRequest nodes not bound to any OperationalConversationBinding.

        Queries for requests that exist but have no incoming BINDS_ACTIVE_REQUEST relationship.
        Used to detect requests created but not linked to a session.

        Args:
            namespace: Accepted for interface consistency with other probe
                methods; does not currently filter results (there is no
                namespace property on DeliveryRequest nodes).

        Returns:
            Frozenset of request IDs that are orphaned (not bound to any binding).
        """
        query = """
        MATCH (r:DeliveryRequest)
        WHERE NOT EXISTS { MATCH (b:OperationalConversationBinding)-[:BINDS_ACTIVE_REQUEST]->(r) }
        RETURN r.id AS id
        """
        result = self.driver.execute_query(query)
        ids = [record["id"] for record in result.records if record["id"]]
        return frozenset(ids)

    def mutation_fingerprint(self, request_id: str) -> str:
        """Compute stable fingerprint of request state for mutation detection.

        Fingerprint includes request ID, status, and update timestamp to detect
        concurrent modifications or stale reads.

        Args:
            request_id: DeliveryRequest.id to fingerprint.

        Returns:
            Stable string fingerprint of request state.
        """
        query = """
        MATCH (r:DeliveryRequest {id: $request_id})
        RETURN r.hasStatus AS status, toString(r.updated) AS updated
        """
        result = self.driver.execute_query(query, request_id=request_id)

        if not result.records:
            return f"missing:{request_id}"

        record = result.records[0]
        status = record.get("status") or "null"
        updated = record.get("updated") or "unknown"

        # Stable fingerprint format: request_id:status:timestamp
        return f"{request_id}:{status}:{updated}"

    def _query_request_ids_for_session(self, session_id: str) -> list[str]:
        """Query all distinct request IDs bound to a session.

        Internal helper using parameterized query.

        Args:
            session_id: OperationalConversationBinding.sessionId to query.

        Returns:
            List of request IDs.
        """
        query = """
        MATCH (:OperationalConversationBinding {sessionId: $session_id})-[:BINDS_ACTIVE_REQUEST]->(r:DeliveryRequest)
        RETURN DISTINCT r.id AS id
        ORDER BY r.id
        """
        result = self.driver.execute_query(query, session_id=session_id)
        return [record["id"] for record in result.records]

    def _query_request_statuses_for_session(self, session_id: str) -> list[str | None]:
        """Query all request statuses for a session.

        Internal helper to capture status values (including null).

        Args:
            session_id: OperationalConversationBinding.sessionId to query.

        Returns:
            List of hasStatus values (may include None).
        """
        query = """
        MATCH (:OperationalConversationBinding {sessionId: $session_id})-[:BINDS_ACTIVE_REQUEST]->(r:DeliveryRequest)
        RETURN DISTINCT r.hasStatus AS status
        ORDER BY status
        """
        result = self.driver.execute_query(query, session_id=session_id)
        return [record["status"] for record in result.records]
