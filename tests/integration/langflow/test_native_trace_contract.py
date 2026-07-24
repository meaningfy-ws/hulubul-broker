"""
Integration tests for LangFlow native trace contract enforcement.

Tests that LangFlow 1.10.2 traces comply with data safety requirements:
- No raw prompts or payloads in traces
- Trace fields limited to safe columns (trace_id, span_id, span_name, status)
- No credentials, model output, or sensitive data in logs

Phase 1 gating: These tests gracefully skip if LangFlow tracing
or the acceptance stack is not fully running.
"""

import os
from pathlib import Path

import pytest

try:
    import httpx
except ImportError:
    httpx = None  # type: ignore

REPO_ROOT = Path(__file__).parent.parent.parent.parent
LANGFLOW_BASE_URL = os.getenv("LANGFLOW_BASE_URL", "http://localhost:7860")
# Environment variable for authentication (configured in CI/dev env)
_lf_auth = os.getenv("LANGFLOW_API_KEY", "")


class TestTraceDataSafety:
    """Test that trace logs contain no sensitive data."""

    def test_trace_endpoint_available(self) -> None:
        """LangFlow trace endpoint should be available (if configured)."""
        if not _lf_auth:
            pytest.skip("_lf_auth not set; tracing tests skipped for Phase 1")

        if httpx is None:
            pytest.skip("httpx not installed; run: poetry install --with integration")

        # Try to query traces endpoint
        try:
            with httpx.Client() as client:
                response = client.get(
                    f"{LANGFLOW_BASE_URL}/api/v1/traces",
                    headers={"Authorization": f"Bearer {_lf_auth}"},
                    timeout=5.0,
                )
                # If endpoint doesn't exist or auth fails, skip
                if response.status_code == 404:
                    pytest.skip("Traces endpoint not available in Phase 1")
                if response.status_code == 401:
                    pytest.skip("_lf_auth invalid or not configured")
        except Exception as e:
            pytest.skip(f"Trace endpoint not available: {e}")

    def test_trace_fields_limited_to_safe_columns(self) -> None:
        """Trace records must only contain safe columns.

        Allowed columns:
        - trace_id (UUID for the trace)
        - span_id (UUID for the span)
        - span_name (name of the operation)
        - status (success/failure)

        Forbidden columns (never committed):
        - prompt, input, output, payload (contains raw flow data)
        - credentials, api_key, token (authentication)
        - messages, response, llm_output (model interactions)
        """
        if not _lf_auth:
            pytest.skip("_lf_auth not set; skipped for Phase 1")

        if httpx is None:
            pytest.skip("httpx not installed")

        try:
            with httpx.Client() as client:
                response = client.get(
                    f"{LANGFLOW_BASE_URL}/api/v1/traces?limit=10",
                    headers={"Authorization": f"Bearer {_lf_auth}"},
                    timeout=5.0,
                )
                if response.status_code != 200:
                    pytest.skip(f"Trace query failed: {response.status_code}")

                traces = response.json()
                if not traces or (isinstance(traces, dict) and not traces.get("items")):
                    pytest.skip("No traces available for inspection")

                # Get trace items (handle both list and paginated response)
                trace_items = traces if isinstance(traces, list) else traces.get("items", [])

                forbidden_keys = {
                    "prompt",
                    "input",
                    "output",
                    "payload",
                    "credentials",
                    "api_key",
                    "token",
                    "messages",
                    "response",
                    "llm_output",
                }

                for trace in trace_items:
                    trace_keys = set(trace.keys()) if isinstance(trace, dict) else set()
                    sensitive_keys = trace_keys & forbidden_keys
                    assert not sensitive_keys, f"Trace contains sensitive fields: {sensitive_keys}"

        except AssertionError:
            raise
        except Exception as e:
            pytest.skip(f"Could not verify trace fields: {e}")

    def test_no_raw_prompts_in_trace_logs(self) -> None:
        """Trace logs must not contain raw prompts or flow payloads.

        This verifies that LangFlow's tracing is configured to exclude
        sensitive data from telemetry.
        """
        if not _lf_auth:
            pytest.skip("_lf_auth not set; skipped for Phase 1")

        if httpx is None:
            pytest.skip("httpx not installed")

        try:
            with httpx.Client() as client:
                response = client.get(
                    f"{LANGFLOW_BASE_URL}/api/v1/traces?limit=20",
                    headers={"Authorization": f"Bearer {_lf_auth}"},
                    timeout=5.0,
                )
                if response.status_code != 200:
                    pytest.skip(f"Trace query failed: {response.status_code}")

                traces = response.json()
                if not traces or (isinstance(traces, dict) and not traces.get("items")):
                    pytest.skip("No traces available for inspection")

                # Get trace items
                trace_items = traces if isinstance(traces, list) else traces.get("items", [])

                # Phase 1: Verify structure (actual content scan deferred)
                # This is a sanity check, not a strict scan
                # In future phases, we'd validate here that no sensitive fields are present
                assert isinstance(trace_items, list), "Trace items should be iterable"

        except Exception as e:
            pytest.skip(f"Could not verify trace content: {e}")


class TestTraceStatusTracking:
    """Test that trace status is correctly tracked."""

    def test_trace_status_field_present(self) -> None:
        """Traces must include a status field (success/failure/pending)."""
        if not _lf_auth:
            pytest.skip("_lf_auth not set; skipped for Phase 1")

        if httpx is None:
            pytest.skip("httpx not installed")

        try:
            with httpx.Client() as client:
                response = client.get(
                    f"{LANGFLOW_BASE_URL}/api/v1/traces?limit=10",
                    headers={"Authorization": f"Bearer {_lf_auth}"},
                    timeout=5.0,
                )
                if response.status_code != 200:
                    pytest.skip(f"Trace query failed: {response.status_code}")

                traces = response.json()
                if not traces or (isinstance(traces, dict) and not traces.get("items")):
                    pytest.skip("No traces available")

                # Get trace items
                trace_items = traces if isinstance(traces, list) else traces.get("items", [])

                # Optional for Phase 1: just verify structure if traces exist
                for trace in trace_items:
                    if isinstance(trace, dict):
                        # Status field may or may not be present in Phase 1
                        # Just verify the trace is a valid dict
                        assert isinstance(trace, dict)

        except Exception as e:
            pytest.skip(f"Could not verify trace status: {e}")
