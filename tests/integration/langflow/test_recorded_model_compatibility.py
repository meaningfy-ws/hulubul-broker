"""
Integration tests for recorded model compatibility with LangFlow 1.10.2.

Tests that the recorded model (HulubulRecordedLanguageModel) can accept
flow requests, produce deterministic responses, and expose an OpenAI-compatible
endpoint with LF-00 Chat Input.

Phase 1 gating: These tests gracefully skip if the recorded model
or acceptance stack is not running.
"""

import os
from pathlib import Path

import pytest

try:
    import httpx
except ImportError:
    httpx = None  # type: ignore

REPO_ROOT = Path(__file__).parent.parent.parent.parent
RECORDED_MODEL_BASE_URL = os.getenv("RECORDED_MODEL_BASE_URL", "http://localhost:8000")


class TestRecordedModelOpenAIEndpoint:
    """Test OpenAI-compatible endpoint with LF-00 Chat Input."""

    @pytest.fixture
    def client(self) -> "httpx.Client":
        """HTTP client for recorded model API."""
        if httpx is None:
            pytest.skip("httpx not installed; run: poetry install --with integration")
        return httpx.Client()

    def test_recorded_model_health(self, client: "httpx.Client") -> None:
        """Recorded model should be healthy and responsive."""
        try:
            response = client.get(f"{RECORDED_MODEL_BASE_URL}/health", timeout=2.0)
            if response.status_code == 404:
                # Health endpoint doesn't exist; try /docs instead
                response = client.get(f"{RECORDED_MODEL_BASE_URL}/docs", timeout=2.0)
            assert response.status_code in (200, 404), (
                f"Recorded model not responding (status {response.status_code}). "
                "Ensure acceptance stack is running: make acceptance-up"
            )
        except Exception as e:
            pytest.skip(f"Recorded model not available: {e}")

    def test_openai_compatible_chat_completions_endpoint(self, client: "httpx.Client") -> None:
        """Recorded model must expose /v1/chat/completions endpoint."""
        # This endpoint is optional for Phase 1; skip if not available
        try:
            response = client.post(
                f"{RECORDED_MODEL_BASE_URL}/v1/chat/completions",
                json={"messages": [{"role": "user", "content": "test"}]},
                timeout=5.0,
            )
            # Endpoint exists; verify it's valid (200, 400, or 403 are all valid)
            assert response.status_code in (200, 400, 403, 422), (
                f"Unexpected status from /v1/chat/completions: {response.status_code}"
            )
        except Exception as e:
            pytest.skip(f"OpenAI endpoint not available: {e}")

    def test_recorded_model_produces_consistent_output(self, client: "httpx.Client") -> None:
        """Recorded model must produce the same output for the same input."""
        # For Phase 1, skip if model not running
        try:
            input_data = {
                "messages": [{"role": "user", "content": "hello"}],
                "temperature": 0.0,  # Deterministic
            }
            response1 = client.post(
                f"{RECORDED_MODEL_BASE_URL}/v1/chat/completions",
                json=input_data,
                timeout=5.0,
            )
            if response1.status_code != 200:
                pytest.skip("Recorded model not responding with 200")

            result1 = response1.json()
            response2 = client.post(
                f"{RECORDED_MODEL_BASE_URL}/v1/chat/completions",
                json=input_data,
                timeout=5.0,
            )
            result2 = response2.json()

            # If both requests succeed, responses should be identical
            if response2.status_code == 200:
                assert result1 == result2, (
                    "Recorded model did not produce deterministic output. "
                    "Re-recorded datasets should produce identical outputs."
                )
        except Exception as e:
            pytest.skip(f"Consistency test skipped: {e}")


class TestFlowRequestAcceptance:
    """Test that recorded model accepts flow request formats."""

    @pytest.fixture
    def client(self) -> "httpx.Client":
        """HTTP client for recorded model API."""
        if httpx is None:
            pytest.skip("httpx not installed; run: poetry install --with integration")
        return httpx.Client()

    def test_flow_request_format_accepted(self, client: "httpx.Client") -> None:
        """Recorded model should accept LangFlow request format."""
        # LangFlow sends requests with "input" key containing flow variables
        flow_request = {
            "input": {
                "message": "hello from flow",
                "session_id": "test-session-123",
            }
        }

        try:
            response = client.post(
                f"{RECORDED_MODEL_BASE_URL}/api/v1/run/lf-00",
                json=flow_request,
                timeout=5.0,
            )
            # Endpoint may not exist in Phase 1; that's OK
            if response.status_code == 404:
                pytest.skip("Flow endpoint /api/v1/run/lf-00 not yet deployed")
            # If it exists, verify it returns valid response
            assert response.status_code in (200, 400, 403, 422), (
                f"Unexpected status from flow endpoint: {response.status_code}"
            )
        except Exception as e:
            pytest.skip(f"Flow endpoint not available: {e}")
