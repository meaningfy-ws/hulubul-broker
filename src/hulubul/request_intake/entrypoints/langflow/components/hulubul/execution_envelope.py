"""Trusted execution envelope component: user prose isolation and session normalization."""

import os
from uuid import UUID, uuid4

from lfx.custom.custom_component.component import Component
from lfx.inputs.inputs import MessageInput
from lfx.schema.data import Data
from lfx.schema.message import Message
from lfx.template.field.base import Output

from hulubul.core.models.operational import (
    ActorContext,
    ActorRole,
    IdentityAssurance,
    InvocationSource,
    MainFlowInput,
)

__all__ = ["ExecutionEnvelopeComponent"]


class ExecutionEnvelopeComponent(Component):
    """Message-only execution envelope with trusted metadata.

    This component is the trust boundary between untrusted user prose (Message.text)
    and the trusted operational envelope (MainFlowInput). It:
    - Accepts exactly one Message (never a free string)
    - Normalizes session_id (bare UUID or p1-<uuid> → lowercase p1-<uuid>)
    - Requires Message.session_id == active graph session
    - Derives source (api or playground) from trusted path
    - Hard-codes role=sender, assurance=simulated
    - Rejects: empty/malformed/mismatched sessions, flow-ID fallback, prose identity override
    - Generates unique message_id, correlation_id per call

    Deliberately has no `__init__` override: pre-assigning a declared input
    field (e.g. `self.message = None`) in `__init__` collides with LangFlow's
    `Component.set_attributes()` the moment a differing value arrives via a
    real graph edge -- confirmed live ("ExecutionEnvelopeComponent defines
    an input parameter named 'message' that is a reserved word and cannot
    be used"), the same reserved-word class of bug already fixed in every
    other boundary component in this module. Let the framework's own
    declarative default populate `self.message` instead.
    """

    display_name = "Execution Envelope"
    description = "Trust boundary: builds MainFlowInput from a Message plus trusted metadata."
    icon = "shield-check"
    name = "HulubulExecutionEnvelope"

    inputs = [  # noqa: RUF012
        MessageInput(  # type: ignore[call-arg]
            name="message",
            display_name="Message",
            info="The inbound chat Message (never a free string).",
            required=True,
        ),
    ]

    outputs = [  # noqa: RUF012
        Output(  # type: ignore[call-arg]
            display_name="Envelope", name="response", type_=Data, method="build_envelope"
        ),
    ]

    def build_envelope(self) -> Data:
        """Build MainFlowInput from Message and trusted metadata.

        Returns:
            Data: An LFX Data object with MainFlowInput serialized as JSON

        Raises:
            ValueError: If validation fails (empty/malformed/mismatched session,
                      missing required actor ID, etc.)
        """
        if self.message is None:
            raise ValueError("INVALID_INPUT: message is required")

        if not isinstance(self.message, Message):
            raise ValueError("INVALID_INPUT: message must be a Message object, not a string")

        # Determine invocation source (api or playground)
        source = self._get_invocation_source()

        # Read trusted actor metadata based on source
        if source == InvocationSource.API:
            actor_id = self._get_api_actor_id()
            display_name = self._get_api_display_name()
        else:  # InvocationSource.PLAYGROUND
            actor_id = self._get_playground_actor_id()
            display_name = self._get_playground_display_name()

        if not actor_id:
            raise ValueError(f"INVALID_INPUT: actor_id is required for {source.value} invocation")

        # Provide default display name if not specified
        if not display_name:
            display_name = "User"

        # Validate and normalize session_id
        raw_session = self.message.session_id
        if isinstance(raw_session, UUID):
            raw_session = str(raw_session)
        session_id = self._normalize_and_validate_session(raw_session)

        # Generate unique message_id and correlation_id
        message_id = uuid4()
        correlation_id = uuid4()

        # Build the trusted actor context
        actor = ActorContext(
            actor_id=actor_id,
            display_name=display_name,
            actor_role=ActorRole.SENDER,
            identity_assurance=IdentityAssurance.SIMULATED,
        )

        # Build the main flow input
        message_text = self.message.text
        if not isinstance(message_text, str):
            raise ValueError("INVALID_INPUT: message.text must be a string")
        envelope = MainFlowInput(
            message_id=message_id,
            session_id=session_id,
            actor=actor,
            source=source,
            message=message_text,
            correlation_id=correlation_id,
        )

        # Return as Data object
        return Data(data=envelope.model_dump())

    def _get_invocation_source(self) -> InvocationSource:
        """Determine if this is an API or Playground invocation.

        API invocations have actor ID in headers (via LangFlow global variables).
        Playground invocations have actor ID in environment variables.

        Returns:
            InvocationSource.API or InvocationSource.PLAYGROUND
        """
        playground_actor_id = os.environ.get("HULUBUL_PHASE1_PLAYGROUND_ACTOR_ID")
        if playground_actor_id:
            return InvocationSource.PLAYGROUND
        return InvocationSource.API

    def _get_request_variable(self, name: str) -> str | None:
        """Read a single `X-LANGFLOW-GLOBAL-VAR-<name>` header value.

        LangFlow does not expose these as flat top-level keys on
        `Component.ctx` -- confirmed live (a debug print showed
        `self.ctx.keys() == ['request_variables']`, never the variable name
        itself). They live one level down, under
        `self.ctx["request_variables"][name]`. A previous version of this
        method checked `name in self.ctx` directly, which was always False,
        so every API-path actor/display-name read silently fell through to
        the (unset) environment-variable fallback -- this broke every LF-00
        API invocation until caught live.

        `ctx` is a property that proxies to `self.graph.context` and
        actively *raises* `ValueError` (not just returns empty/None) when
        `self.graph` isn't set yet -- confirmed by reading
        `lfx.custom.custom_component.component.Component.ctx`'s own
        source, not assumed. Catch `(AttributeError, ValueError)`, not just
        `AttributeError`.
        """
        try:
            request_variables = self.ctx.get("request_variables", {})
        except (AttributeError, ValueError):
            return None
        value = request_variables.get(name) if isinstance(request_variables, dict) else None
        return value if isinstance(value, str) else None

    def _get_api_actor_id(self) -> str | None:
        """Read actor ID from API header (X-LANGFLOW-GLOBAL-VAR-HULUBUL_PHASE1_ACTOR_ID).

        Returns:
            Actor ID string or None if not provided
        """
        value = self._get_request_variable("HULUBUL_PHASE1_ACTOR_ID")
        if value:
            return value
        # Fallback for testing or if LangFlow doesn't inject headers.
        return os.environ.get("HULUBUL_PHASE1_ACTOR_ID")

    def _get_api_display_name(self) -> str | None:
        """Read display name from API header (X-LANGFLOW-GLOBAL-VAR-
        HULUBUL_PHASE1_ACTOR_DISPLAY_NAME).

        Returns:
            Display name string or None if not provided (optional field)
        """
        value = self._get_request_variable("HULUBUL_PHASE1_ACTOR_DISPLAY_NAME")
        if value:
            return value
        return os.environ.get("HULUBUL_PHASE1_ACTOR_DISPLAY_NAME")

    def _get_playground_actor_id(self) -> str | None:
        """Read actor ID from Playground environment variable (HULUBUL_PHASE1_PLAYGROUND_ACTOR_ID).

        Returns:
            Actor ID string or None if not provided
        """
        return os.environ.get("HULUBUL_PHASE1_PLAYGROUND_ACTOR_ID")

    def _get_playground_display_name(self) -> str | None:
        """Read display name from Playground environment variable
        (HULUBUL_PHASE1_PLAYGROUND_ACTOR_DISPLAY_NAME).

        Returns:
            Display name string or None if not provided (optional field)
        """
        return os.environ.get("HULUBUL_PHASE1_PLAYGROUND_ACTOR_DISPLAY_NAME")

    def _get_graph_session_id(self) -> str | None:
        """Read the active LangFlow graph session ID.

        In LangFlow, the graph context may have a session ID. We compare this
        with the Message.session_id to ensure they match.

        Returns:
            Session ID from graph context or None
        """
        # `self.ctx` never carries a "session_id" key (confirmed live -- see
        # `_get_request_variable`'s docstring for how that was diagnosed);
        # the graph's own run session lives on `self.graph.session_id`
        # (falling back to `self._session_id`), matching `lfx`'s own
        # internal usage (`Component.set_class_code`/`_get_result`).
        graph = getattr(self, "graph", None)
        session_id = getattr(graph, "session_id", None)
        if session_id is None:
            session_id = getattr(self, "_session_id", None)
        if isinstance(session_id, str):
            return session_id

        # No fallback to Message.session_id here: that would compare the
        # message's session against itself, silently defeating the
        # message-vs-graph mismatch check in _normalize_and_validate_session.
        return None

    def _normalize_and_validate_session(self, session_id: str | None) -> str:
        """Normalize and validate session ID.

        Accepts:
        - Bare UUID: "12345678-1234-4000-8000-000000000000"
        - Canonical: "p1-12345678-1234-4000-8000-000000000000"

        Both normalize to: "p1-<lowercase-uuid>"

        Rejects:
        - Empty values
        - Malformed UUIDs
        - Mismatched message/graph sessions
        - Flow-ID fallback (when session is omitted)

        Args:
            session_id: The session ID to normalize

        Returns:
            Normalized session ID in form "p1-<lowercase-uuid>"

        Raises:
            ValueError: If validation fails
        """
        if not session_id:
            raise ValueError("INVALID_INPUT: session_id is required and cannot be empty")

        # Try to parse as UUID to validate format
        normalized = session_id.lower().strip()

        # Remove p1- prefix if present
        uuid_part = normalized[3:] if normalized.startswith("p1-") else normalized

        # Validate UUID format
        try:
            UUID(uuid_part)
        except ValueError as err:
            msg = f"INVALID_INPUT: session_id must be a valid UUID, got '{session_id}'"
            raise ValueError(msg) from err

        # Return in canonical form
        canonical_session = f"p1-{uuid_part}"

        # Check if graph session matches message session (if both are available)
        graph_session = self._get_graph_session_id()
        if graph_session:
            # Normalize graph session for comparison
            graph_normalized = graph_session.lower().strip()
            if graph_normalized.startswith("p1-"):
                graph_uuid = graph_normalized[3:]
            else:
                graph_uuid = graph_normalized

            # Ensure they match after normalization
            if graph_uuid != uuid_part:
                raise ValueError(
                    f"INVALID_INPUT: message session_id does not match graph session: "
                    f"'{session_id}' vs graph '{graph_session}'"
                )

        return canonical_session
