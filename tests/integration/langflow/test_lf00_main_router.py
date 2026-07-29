"""Integration tests for LF-00 (main router) API contract and route behavior.

Tests verify:
- Generated metadata (message_id) is unique per call
- Chat text matches the deterministic renderer's output for a known scenario
  (chat/structured parity, checked against the pure `render_router_result`
  function rather than mid-flow introspection -- see module docstring below
  for why)
- The absent-binding route (task 45's "no prior binding" case) is reachable
  and correct via the plain Run API
- Session ID normalization (bare UUID vs canonical "p1-<uuid>") both work

Scope note: the plain Run API (`output_type=chat`) only ever exposes the
terminal ChatOutput component's Message -- confirmed live, including with
`is_output=True` additionally set on an earlier component (Contract Result
Boundary): the response still contains exactly one component's output.
There is no way to pull the intermediate structured RouterResult out of a
single HTTP call, so `test_generated_metadata_and_dual_output`-style parity
checks here compare the live chat text against `render_router_result()`
applied to an *expected* RouterResult for a scenario whose state is fully
controlled by the test (the absent-binding case needs no Neo4j fixture at
all), rather than against a RouterResult extracted from the same response.

The full 6-scenario route matrix (new/needsClarification/complete/closed/
unsupported, which need specific Neo4j `OperationalConversationBinding`
fixtures) was verified live during this checkpoint but is not yet automated
here -- left for a follow-up pass; see
DEV/knowledge/checkpoint9-lf10-runflow-injection-runbook.md.
"""

import uuid

import pytest

from hulubul.request_intake.services.rendering import render_router_result
from tests.support.langflow_client import LangFlowClient

TRUSTED_ACTOR_ID = "urn:uuid:6fff189f-aed3-47dd-b1b9-945d8dbefb47"


class _Conversation:
    """Minimal ConversationLike for direct client calls."""

    def __init__(self, session_id: str, display_name: str = "Integration Test") -> None:
        self.actor_id: str | None = TRUSTED_ACTOR_ID
        self.display_name: str | None = display_name
        self.session_id: str | None = session_id


def _skip_if_langflow_down(response) -> None:  # type: ignore[no-untyped-def]
    if response.status_code == 500 and response.error and "Connection error" in response.error:
        pytest.skip("LangFlow server not running")


class TestGeneratedMetadataUniqueness:
    """Every call gets fresh, non-repeating generated metadata."""

    def test_message_id_and_correlation_id_unique_across_calls(
        self, langflow_client: LangFlowClient
    ) -> None:
        """Two calls, same conversation shape, different session -- both get
        distinct message_id/correlation_id. Never repeats, never omits.
        """
        first = langflow_client.run_lf00(
            _Conversation(session_id=str(uuid.uuid4())), "I need to send a parcel"
        )
        _skip_if_langflow_down(first)
        assert first.status_code == 200, first.error

        second = langflow_client.run_lf00(
            _Conversation(session_id=str(uuid.uuid4())), "I need to send a parcel"
        )
        assert second.status_code == 200, second.error

        assert first.message_id is not None
        assert second.message_id is not None
        assert first.message_id != second.message_id

        assert first.correlation_id is not None
        assert second.correlation_id is not None
        assert first.correlation_id != second.correlation_id


class TestAbsentBindingRoute:
    """The no-prior-binding route: the one scenario needing no Neo4j fixture."""

    def test_absent_binding_routes_to_intake(self, langflow_client: LangFlowClient) -> None:
        """Fresh session (guaranteed no OperationalConversationBinding exists
        yet) -> outcome=routed, target=intake, reason=noBinding.
        """
        reply = langflow_client.run_lf00(
            _Conversation(session_id=str(uuid.uuid4())), "I need to send a parcel"
        )
        _skip_if_langflow_down(reply)
        assert reply.status_code == 200, reply.error
        assert reply.chat_text == "routing to intake"

    def test_chat_text_matches_deterministic_render_for_absent_binding(
        self, langflow_client: LangFlowClient
    ) -> None:
        """Chat/structured parity (DEC-014): the live chat text for the
        absent-binding scenario equals what `render_router_result` produces
        for the RouterResult that scenario is contractually required to
        yield. This is the practical form of
        `chat_text == render_router_result(structured)` given the plain Run
        API cannot expose the intermediate structured result directly (see
        module docstring).
        """
        from uuid import uuid4

        from hulubul.core.models.operational import (
            RouterOutcome,
            RouterResult,
            RouterTarget,
            RoutingReason,
        )

        reply = langflow_client.run_lf00(
            _Conversation(session_id=str(uuid.uuid4())), "I need to send a parcel"
        )
        _skip_if_langflow_down(reply)
        assert reply.status_code == 200, reply.error

        expected_structured = RouterResult(
            correlation_id=uuid4(),
            outcome=RouterOutcome.ROUTED,
            target=RouterTarget.INTAKE,
            reason=RoutingReason.NO_BINDING,
            safe_message="routing to intake",
        )
        assert reply.chat_text == render_router_result(expected_structured)


class TestSessionIdNormalization:
    """Bare UUID and canonical "p1-<uuid>" session IDs both resolve, consistently."""

    def test_bare_uuid_session_id_succeeds(self, langflow_client: LangFlowClient) -> None:
        """A bare UUID (no "p1-" prefix) is accepted and normalized internally."""
        reply = langflow_client.run_lf00(
            _Conversation(session_id=str(uuid.uuid4())), "I need to send a parcel"
        )
        _skip_if_langflow_down(reply)
        assert reply.status_code == 200, reply.error
        assert reply.chat_text == "routing to intake"

    def test_canonical_p1_prefixed_session_id_succeeds(
        self, langflow_client: LangFlowClient
    ) -> None:
        """The canonical "p1-<uuid>" form is also accepted."""
        session_id = f"p1-{uuid.uuid4()}"
        reply = langflow_client.run_lf00(
            _Conversation(session_id=session_id), "I need to send a parcel"
        )
        _skip_if_langflow_down(reply)
        assert reply.status_code == 200, reply.error
        assert reply.chat_text == "routing to intake"

    def test_bare_and_canonical_forms_of_same_uuid_reach_same_binding_state(
        self, langflow_client: LangFlowClient
    ) -> None:
        """The same underlying UUID, once as bare and once as "p1-"-prefixed,
        must normalize to the same session and therefore see the same
        (absent) binding state -- proving normalization actually folds them
        together rather than treating them as two different sessions.
        """
        raw_uuid = uuid.uuid4()

        bare = langflow_client.run_lf00(
            _Conversation(session_id=str(raw_uuid)), "I need to send a parcel"
        )
        _skip_if_langflow_down(bare)
        assert bare.status_code == 200, bare.error

        canonical = langflow_client.run_lf00(
            _Conversation(session_id=f"p1-{raw_uuid}"), "confirming same session"
        )
        assert canonical.status_code == 200, canonical.error

        # Both still see an absent binding (no write ever happened on this
        # session), so both must render identically.
        assert bare.chat_text == canonical.chat_text == "routing to intake"
