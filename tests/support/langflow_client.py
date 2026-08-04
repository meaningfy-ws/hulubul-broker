"""Authenticated LangFlow API client with actor context support.

Provides a typed client for programmatic LangFlow API calls with:
- API key authentication
- Actor context request-variable headers
- Typed response objects
- Safe repr (no secret exposure)
"""

import json
import logging
import time
import uuid
from dataclasses import dataclass
from typing import Any, Protocol

logger = logging.getLogger(__name__)

try:
    import httpx
except ImportError:
    httpx = None  # type: ignore


class ConversationLike(Protocol):
    """Structural contract for the conversation context passed to run_lf00."""

    actor_id: str | None
    display_name: str | None
    session_id: str | None


@dataclass
class FlowReply:
    """Typed response from LangFlow flow run.

    Attributes:
        status_code: HTTP status code from LangFlow API
        flow_id: Identifier of the flow that was run (optional)
        correlation_id: Request correlation ID (optional)
        result: Flow result data (optional)
        error: Error message (optional)
        message_id: The terminal Message's own `.id` (globally unique per
            LangFlow-generated message) -- LF-00's plain Run API response
            (output_type=chat) only exposes the terminal ChatOutput
            component's Message, not intermediate components' structured
            output, so this is the practical proxy for
            "generated metadata is unique per call" rather than a
            hulubul-internal correlation_id, which lives inside the
            RouterInput/RouterResult contract and isn't surfaced at the
            Message-envelope level via this endpoint.
        chat_text: The rendered chat text (DeterministicRenderer's output,
            what a real chat client would display).
    """

    status_code: int
    flow_id: str | None = None
    correlation_id: str | None = None
    result: dict[str, Any] | None = None
    error: str | None = None
    message_id: str | None = None
    chat_text: str | None = None

    def __repr__(self) -> str:
        """Safe repr: never expose API key or sensitive data."""
        parts = [f"status={self.status_code}"]
        if self.flow_id:
            parts.append(f"flow_id={self.flow_id}")
        if self.error:
            parts.append(f"error={self.error}")
        return f"FlowReply({', '.join(parts)})"


class LangFlowClient:
    """Authenticated LangFlow API client with actor context support.

    Attributes:
        base_url: Base URL of the LangFlow API (e.g., http://localhost:7860)
        _api_key: Private API key field (never exposed in repr)
    """

    def __init__(self, base_url: str, api_key: str | None = None) -> None:
        """Initialize LangFlow client.

        Args:
            base_url: Base URL of the LangFlow API
            api_key: Optional API key for authentication
        """
        self.base_url = base_url
        self._api_key = api_key

    def _get_headers(self, actor_id: str, display_name: str | None = None) -> dict[str, str]:
        """Build request headers with actor context and API key.

        Args:
            actor_id: Actor identifier (required)
            display_name: Optional human-readable actor display name

        Returns:
            Dictionary of request headers including actor context and auth
        """
        headers: dict[str, str] = {
            "X-LANGFLOW-GLOBAL-VAR-HULUBUL_PHASE1_ACTOR_ID": actor_id,
        }
        if display_name:
            headers["X-LANGFLOW-GLOBAL-VAR-HULUBUL_PHASE1_ACTOR_DISPLAY_NAME"] = display_name
        if self._api_key:
            # LangFlow's api_key_security dependency reads the literal header
            # name "x-api-key" (see langflow.services.auth.utils.api_key_header),
            # not a Bearer Authorization header -- confirmed live: every call
            # through this client 403'd regardless of payload shape until this
            # was fixed.
            headers["x-api-key"] = self._api_key
        return headers

    # Pinned per langflow/flow-manifest.yaml -- POST /api/v1/run/lf-00 (a name,
    # not this UUID) 404s: LangFlow's Run API resolves by exact flow name or
    # UUID, and this flow's registered name is "lf-00-main-router", not
    # "lf-00". Confirmed live.
    LF00_FLOW_ID = "38b7ee64-26c8-5d4d-97e4-6e62a0fcb557"

    def run_lf00(self, conversation: ConversationLike, message: str) -> FlowReply:
        """Run LF-00 (main router) flow with actor context.

        Args:
            conversation: Conversation object with actor_id (required)
                         and optional display_name and session_id
            message: User message to process

        Returns:
            FlowReply with status, flow_id, message_id, chat_text, result, or error
        """
        if not conversation.actor_id:
            return FlowReply(status_code=400, error="Missing required actor_id")

        url = f"{self.base_url}/api/v1/run/{self.LF00_FLOW_ID}"
        headers = self._get_headers(conversation.actor_id, conversation.display_name)
        # LF-00 has a genuine ChatInput entry point (unlike LF-70/LF-10's
        # custom-component entry points), so the API default input_type
        # "chat" actually reaches it -- no "any" override needed here.
        body = {"input_value": message, "session_id": conversation.session_id}

        try:
            if httpx is None:
                return FlowReply(
                    status_code=500,
                    error="httpx not installed; run: poetry install --with integration",
                )

            with httpx.Client() as client:
                response = client.post(
                    url,
                    json=body,
                    headers=headers,
                    params={"output_type": "chat", "input_type": "chat"},
                    timeout=60.0,
                )

                if response.status_code == 403:
                    return FlowReply(
                        status_code=403,
                        error="Unauthorized (missing or invalid API key)",
                    )

                if response.status_code == 200:
                    result = response.json()
                    message_data = self._extract_chat_message_data(result)
                    return FlowReply(
                        status_code=200,
                        flow_id=self.LF00_FLOW_ID,
                        correlation_id=(message_data or {})
                        .get("session_metadata", {})
                        .get("graph_run_id"),
                        message_id=(message_data or {}).get("id"),
                        chat_text=(message_data or {}).get("text"),
                        result=result,
                    )

                return FlowReply(
                    status_code=response.status_code,
                    error=f"LangFlow error: {response.text[:200]}",
                )
        except Exception as e:
            error_str = str(e)
            return FlowReply(status_code=500, error=f"Connection error: {error_str[:200]}")

    @staticmethod
    def _extract_chat_message_data(response: dict[str, Any]) -> dict[str, Any] | None:
        """Pull the terminal ChatOutput Message's own `.data` dict out of the
        Run API's nested response envelope
        (`outputs[0].outputs[0].results.message.data`).

        This is LangFlow's own Message-envelope metadata (id, text,
        session_metadata.graph_run_id, ...), not a hulubul contract --
        `output_type=chat` only ever exposes the terminal component's
        output, confirmed live: setting `is_output` on an earlier component
        (e.g. the Contract Result Boundary) too does not make the plain Run
        API return more than one component's result.
        """
        try:
            outputs = response["outputs"][0]["outputs"]
        except (KeyError, IndexError, TypeError):
            return None
        for output in outputs:
            data = output.get("results", {}).get("message", {}).get("data")
            if isinstance(data, dict):
                return data
        return None

    def run_without_key(self, flow_id: str, input_data: dict[str, Any]) -> FlowReply:
        """Unauthenticated request (for testing 403 rejection).

        Args:
            flow_id: Flow identifier (e.g., "lf-00")
            input_data: Input data payload

        Returns:
            FlowReply with HTTP status code
        """
        url = f"{self.base_url}/api/v1/run/{flow_id}"

        try:
            if httpx is None:
                return FlowReply(
                    status_code=500,
                    error="httpx not installed; run: poetry install --with integration",
                )

            with httpx.Client() as client:
                response = client.post(url, json=input_data, timeout=30.0)
                return FlowReply(status_code=response.status_code)
        except Exception as e:
            return FlowReply(status_code=500, error=f"Connection error: {str(e)[:200]}")

    def run_with_wrong_key(self, flow_id: str, input_data: dict[str, Any]) -> FlowReply:
        """Request with wrong API key (for testing 403 rejection).

        Args:
            flow_id: Flow identifier (e.g., "lf-00")
            input_data: Input data payload

        Returns:
            FlowReply with HTTP status code
        """
        url = f"{self.base_url}/api/v1/run/{flow_id}"
        headers = {"x-api-key": "wrong-key-12345"}

        try:
            if httpx is None:
                return FlowReply(
                    status_code=500,
                    error="httpx not installed; run: poetry install --with integration",
                )

            with httpx.Client() as client:
                response = client.post(url, json=input_data, headers=headers, timeout=30.0)
                return FlowReply(status_code=response.status_code)
        except Exception as e:
            return FlowReply(status_code=500, error=f"Connection error: {str(e)[:200]}")

    def run_flow_with_actor(
        self,
        flow_uuid: str,
        input_data: dict[str, Any],
        actor_id: str = "test-actor",
        *,
        max_attempts: int = 2,
    ) -> FlowReply:
        """Call a flow by stable UUID with actor context headers.

        Used for calling LF-70 and other data operation flows that require
        typed actor context via request-variable headers.

        Args:
            flow_uuid: Stable flow UUID (e.g., "94f6774d-ebc7-5bf1-8486-886f91886a5f")
            input_data: Input data payload (e.g., DataOperationRequest)
            actor_id: Actor identifier for context (default: "test-actor")
            max_attempts: Retry budget (default 2, one retry) for the case
                where the flow returns HTTP 200 but the terminal component's
                message can't be parsed as a DataOperationResult -- observed,
                input-independent flakiness where the same well-formed
                request sometimes gets a clean result and sometimes an
                OperationalError, because the model's final answer wasn't
                valid JSON or didn't extract cleanly (checkpoint8 runbook
                bug #17). Retrying the whole flow call is safe here (unlike
                DEC-015's prohibited write-retry): a retry of an
                already-succeeded write comes back REJECTED/
                CONCURRENT_MODIFICATION via the OperationalConversationBinding
                uniqueness constraint or the update/status compare-and-set,
                never a silent duplicate mutation. Pass 1 to disable.

        Returns:
            FlowReply with status, flow_id, correlation_id, result, or error
        """
        url = f"{self.base_url}/api/v1/run/{flow_uuid}"
        headers = self._get_headers(actor_id)

        # LangFlow's SimplifiedAPIRequest wants the payload serialized under
        # `input_value` (a JSON string), not posted as the raw top-level body --
        # a flat body silently validates as an empty request (input_value=None),
        # which is dropped before it ever reaches the flow's entry component.
        # `input_type`/`output_type` must be "any": LF-70 has no ChatInput/
        # ChatOutput component, and "chat" (the API default) filters out every
        # vertex whose declared type isn't literally "ChatInput". A distinct
        # `session_id` per call keeps chat memory (if any) from bleeding
        # between test invocations that hit the same flow_id.
        session_id = str(input_data.get("correlation_id") or uuid.uuid4())
        body = {
            "input_value": json.dumps(input_data),
            "input_type": "any",
            "output_type": "any",
            "session_id": session_id,
        }

        if httpx is None:
            return FlowReply(
                status_code=500,
                error="httpx not installed; run: poetry install --with integration",
            )

        last_reply: FlowReply | None = None
        for attempt in range(1, max_attempts + 1):
            try:
                with httpx.Client() as client:
                    # Write operations (createDeliveryRequest especially) can
                    # legitimately take 60-120s+ end-to-end (get_neo4j_schema +
                    # write_neo4j_cypher, each a real LLM tool-call round trip) --
                    # confirmed live: a correct, successful create took ~120s.
                    # 60s was cutting off genuinely-succeeding calls, not timing
                    # out on a stuck/looping one.
                    response = client.post(url, json=body, headers=headers, timeout=240.0)

                    if response.status_code == 403:
                        return FlowReply(
                            status_code=403,
                            error="Unauthorized (missing or invalid API key)",
                        )

                    if response.status_code == 200:
                        result = self._extract_result_message(response.json())
                        if result is not None and "success" in result:
                            return FlowReply(status_code=200, flow_id=flow_uuid, result=result)

                        last_reply = FlowReply(status_code=200, flow_id=flow_uuid, result=result)
                        if attempt < max_attempts:
                            # Log shape only (type + top-level keys), never the payload
                            # itself -- for LF-70, `result` can carry user-supplied
                            # facts/identifiers, which the module docstring's "no secret
                            # exposure" promise forbids putting in logs.
                            logger.warning(
                                "run_flow_with_actor: attempt %d/%d for flow %s got an "
                                "unparseable result, retrying in 0.5s; result_type=%s, keys=%s",
                                attempt,
                                max_attempts,
                                flow_uuid,
                                type(result).__name__,
                                sorted(result.keys()) if isinstance(result, dict) else None,
                            )
                            time.sleep(0.5)
                            continue
                        return last_reply

                    return FlowReply(
                        status_code=response.status_code,
                        error=f"LangFlow error: {response.text[:200]}",
                    )
            except Exception as e:
                error_str = str(e)
                return FlowReply(status_code=500, error=f"Connection error: {error_str[:200]}")

        # Unreachable: the loop above always returns on its final iteration.
        raise AssertionError("run_flow_with_actor: retry loop exited without returning")

    # Pinned per langflow/flow-manifest.yaml.
    LF10_FLOW_ID = "6843ae79-147f-55d4-a25b-01d6143a12cc"

    def run_lf10(
        self,
        *,
        message: str,
        session_id: str | None = None,
        actor_id: str = "urn:uuid:6fff189f-aed3-47dd-b1b9-945d8dbefb47",
        display_name: str = "Dev User",
        routing_context: dict[str, Any] | None = None,
    ) -> FlowReply:
        """Call LF-10 directly, bypassing LF-00, with a hand-built IntakeInput.

        LF-10 has no ChatInput entry point -- its only entry is
        ContractInputBoundary's `input_value` field. Posting a top-level
        `input_value` (the plain Run API pattern that works for LF-00, whose
        ChatInput IS the graph's recognized input vertex) does NOT reach it --
        confirmed live: the field arrives empty every time. The mechanism that
        does work is LangFlow's `tweaks` parameter, targeting the node by ID
        directly, exactly as `HulubulRunFlowComponent` does internally when
        LF-00 invokes LF-10 as a tool.

        Args:
            message: The sender's message text.
            session_id: Bare UUID string (no "p1-" prefix); a fresh one is
                generated if omitted.
            actor_id: Sender actor_id (default: the shared trusted dev actor).
            display_name: Sender display name.
            routing_context: Full RoutingContext dict. Defaults to an
                absent-binding, routing_stage="intake" context (a fresh,
                unbound sender) if omitted -- pass an explicit one to test a
                bound/needsClarification continuation turn.

        Returns:
            FlowReply with status, flow_id, result (the parsed IntakeResult
            dict), or error.
        """
        sid = session_id or str(uuid.uuid4())
        correlation_id = str(uuid.uuid4())
        canonical_session_id = f"p1-{sid}"

        if routing_context is None:
            routing_context = {
                "schema_version": "1.0.0",
                "correlation_id": correlation_id,
                "session_id": canonical_session_id,
                "binding_state": "absent",
                "binding_count": 0,
                "active_relationship_count": 0,
                "active_target_count": 0,
                "request_id": None,
                "request_status": None,
                "closed_at": None,
                "routing_stage": "intake",
                "error": None,
            }

        intake_input = {
            "schema_version": "1.0.0",
            "correlation_id": correlation_id,
            "envelope": {
                "schema_version": "1.0.0",
                "correlation_id": correlation_id,
                "message_id": str(uuid.uuid4()),
                "session_id": canonical_session_id,
                "actor": {
                    "actor_id": actor_id,
                    "display_name": display_name,
                    "actor_role": "sender",
                    "identity_assurance": "simulated",
                },
                "source": "playground",
                "message": message,
            },
            "routing_context": routing_context,
        }

        url = f"{self.base_url}/api/v1/run/{self.LF10_FLOW_ID}"
        headers = self._get_headers(actor_id, display_name)
        body = {
            "input_value": "",
            "session_id": sid,
            "tweaks": {
                "HulubulContractInputBoundary-hlb-lf-10-input-v1": {
                    "input_value": json.dumps(intake_input),
                }
            },
        }

        if httpx is None:
            return FlowReply(
                status_code=500,
                error="httpx not installed; run: poetry install --with integration",
            )

        try:
            with httpx.Client() as client:
                response = client.post(
                    url,
                    json=body,
                    headers=headers,
                    params={"output_type": "any", "input_type": "any"},
                    timeout=300.0,
                )

                if response.status_code == 403:
                    return FlowReply(
                        status_code=403,
                        error="Unauthorized (missing or invalid API key)",
                    )

                if response.status_code == 200:
                    raw = self._extract_lf10_raw_text(response.json())
                    if raw is None:
                        return FlowReply(
                            status_code=200,
                            flow_id=self.LF10_FLOW_ID,
                            error="Could not extract IntakeResult text from response",
                        )
                    try:
                        result = json.loads(raw)
                    except json.JSONDecodeError:
                        return FlowReply(
                            status_code=200,
                            flow_id=self.LF10_FLOW_ID,
                            error=f"IntakeResult text was not valid JSON: {raw[:200]}",
                        )
                    return FlowReply(status_code=200, flow_id=self.LF10_FLOW_ID, result=result)

                return FlowReply(
                    status_code=response.status_code,
                    error=f"LangFlow error: {response.text[:200]}",
                )
        except Exception as e:
            return FlowReply(status_code=500, error=f"Connection error: {str(e)[:200]}")

    @staticmethod
    def _extract_lf10_raw_text(response: dict[str, Any]) -> str | None:
        """Pull the terminal component's raw IntakeResult JSON text out of the
        Run API's nested response envelope
        (`outputs[0].outputs[0].artifacts.response.raw`).
        """
        try:
            outputs = response["outputs"][0]["outputs"]
        except (KeyError, IndexError, TypeError):
            return None
        for output in outputs:
            raw = output.get("artifacts", {}).get("response", {}).get("raw")
            if isinstance(raw, str):
                return raw
        return None

    @staticmethod
    def _extract_result_message(response: dict[str, Any]) -> dict[str, Any] | None:
        """Pull the terminal component's `DataOperationResult`/error dict out of
        the Run API's nested response envelope (`outputs[0].outputs[0].outputs.response.message`).
        """
        try:
            outputs = response["outputs"][0]["outputs"]
        except (KeyError, IndexError, TypeError):
            return None
        for output in outputs:
            message = output.get("outputs", {}).get("response", {}).get("message")
            if isinstance(message, dict):
                return message
        return None
