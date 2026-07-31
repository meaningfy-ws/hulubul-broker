"""Read-only safe-projection probe over LangFlow's native trace/span data.

Selects only trace/flow/session identifiers and span id/parent/name/type/
status/start/end/latency from LangFlow's monitor API -- it never reads or
returns a trace's ``input``/``output`` fields or a span's ``inputs``/
``outputs``/``error``/``modelName``/``tokenUsage`` fields, all of which may
carry real user/model content. Those fields are dropped at the point the raw
JSON is parsed; they never reach a ``NativeSpanMetadata`` instance.

Verified live against LangFlow 1.10.2's actual `/api/v1/monitor/traces` and
`/api/v1/monitor/traces/{trace_id}` endpoints (`x-api-key` header auth) --
not the Postgres-direct-select design sketched speculatively in plan.md
before that contract was confirmed. A span has no explicit parent-id field
of its own; parentage is implicit in the API's nested ``children`` tree, so
``parent_span_id`` here is assigned while flattening that tree. There is
also no ``kind`` field on a real span (plan.md's "kind" column does not
exist in the live schema).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any

try:
    import httpx
except ImportError:
    httpx = None  # type: ignore

if TYPE_CHECKING:
    from uuid import UUID


@dataclass(frozen=True)
class NativeSpanMetadata:
    """One safe-projected span: identifiers, name/type/status, timing only.

    Never carries a span's payload (``inputs``/``outputs``/``error``/
    ``modelName``/``tokenUsage``) or a trace's ``input``/``output``.
    """

    trace_id: str
    flow_id: str
    session_id: str
    span_id: str
    parent_span_id: str | None
    name: str
    type: str
    status: str
    start_time: datetime
    end_time: datetime | None
    latency_ms: int | None


_SAFE_TRACE_SUMMARY_KEYS = frozenset({"id", "flowId", "sessionId"})
_SAFE_SPAN_KEYS = frozenset(
    {"id", "name", "type", "status", "startTime", "endTime", "latencyMs", "children"}
)


def _parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _project_span(
    raw: dict[str, Any],
    *,
    trace_id: str,
    flow_id: str,
    session_id: str,
    parent_span_id: str | None,
) -> tuple[NativeSpanMetadata, ...]:
    """Flatten one (possibly nested) raw span into safe-projected metadata.

    Only ``_SAFE_SPAN_KEYS`` are ever read off ``raw``; every other key
    (including any payload-bearing field LangFlow may add later) is ignored.
    """
    end_time_raw = raw.get("endTime")
    projected = NativeSpanMetadata(
        trace_id=trace_id,
        flow_id=flow_id,
        session_id=session_id,
        span_id=raw["id"],
        parent_span_id=parent_span_id,
        name=raw["name"],
        type=raw["type"],
        status=raw["status"],
        start_time=_parse_timestamp(raw["startTime"]),
        end_time=_parse_timestamp(end_time_raw) if end_time_raw else None,
        latency_ms=raw.get("latencyMs"),
    )
    results: tuple[NativeSpanMetadata, ...] = (projected,)
    for child in raw.get("children") or []:
        results += _project_span(
            child,
            trace_id=trace_id,
            flow_id=flow_id,
            session_id=session_id,
            parent_span_id=projected.span_id,
        )
    return results


NormalizedSpanTuple = tuple[str, str, bool, "int | None"]


def normalize_topology(spans: tuple[NativeSpanMetadata, ...]) -> tuple[NormalizedSpanTuple, ...]:
    """Fingerprint a span tree structurally, independent of per-run randomness.

    Replaces each span's random UUID and timestamps with its own preorder
    index and a ``parent_index`` pointing back into the same sequence (``None``
    for a root span), keeping only ``(name, type, status_ok, parent_index)``.
    Two runs of the same deterministic scenario should produce identical
    output; a difference means the topology actually changed.
    """
    id_to_index: dict[str, int] = {}
    normalized: list[NormalizedSpanTuple] = []
    for index, span in enumerate(spans):
        id_to_index[span.span_id] = index
        parent_index = id_to_index.get(span.parent_span_id) if span.parent_span_id else None
        normalized.append((span.name, span.type, span.status == "ok", parent_index))
    return tuple(normalized)


class TraceMetadataProbe:
    """Authenticated, read-only client for LangFlow's native trace endpoints.

    Attributes:
        base_url: Base URL of the LangFlow API (e.g. http://localhost:7860).
        _api_key: Private API key field (never exposed in repr).
    """

    def __init__(self, base_url: str, api_key: str | None = None) -> None:
        self.base_url = base_url
        self._api_key = api_key

    def __repr__(self) -> str:
        """Safe repr: never expose the API key."""
        return f"TraceMetadataProbe(base_url={self.base_url!r})"

    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {}
        if self._api_key:
            headers["x-api-key"] = self._api_key
        return headers

    def spans_for_session(
        self, *, flow_ids: tuple[UUID, ...], session_id: str
    ) -> tuple[NativeSpanMetadata, ...]:
        """Return every safe-projected span for the given flows and session.

        Queries each flow's trace list filtered by session, then fetches
        each trace's full span tree and flattens it. Never reads a trace's
        or span's payload-bearing fields (see module docstring).
        """
        if httpx is None:
            msg = "httpx not installed; run: poetry install --with integration"
            raise RuntimeError(msg)

        spans: tuple[NativeSpanMetadata, ...] = ()
        with httpx.Client() as client:
            for flow_id in flow_ids:
                list_response = client.get(
                    f"{self.base_url}/api/v1/monitor/traces",
                    headers=self._headers(),
                    params={"flow_id": str(flow_id), "session_id": session_id},
                    timeout=30.0,
                )
                list_response.raise_for_status()
                for trace_summary in list_response.json().get("traces", []):
                    trace_id = trace_summary["id"]
                    detail_response = client.get(
                        f"{self.base_url}/api/v1/monitor/traces/{trace_id}",
                        headers=self._headers(),
                        timeout=30.0,
                    )
                    detail_response.raise_for_status()
                    detail = detail_response.json()
                    for root_span in detail.get("spans", []):
                        spans += _project_span(
                            root_span,
                            trace_id=trace_id,
                            flow_id=str(flow_id),
                            session_id=session_id,
                            parent_span_id=None,
                        )
        return spans
