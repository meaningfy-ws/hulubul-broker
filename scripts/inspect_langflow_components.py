#!/usr/bin/env python
"""
Inspect and pin LangFlow component schemas for drift detection.

This script captures and pins component schemas from LangFlow 1.10.2,
enabling drift detection and export stability verification.

Features:
- Queries LangFlow API for custom component schemas (8 components from CP4)
- Captures input/output schemas without credentials
- Saves to .lfx/component-schemas-pinned.json with SHA-256 hash
- Supports --check mode for drift detection
- Gracefully handles "components not yet deployed" scenario

Usage:
    poetry run python scripts/inspect_langflow_components.py
    poetry run python scripts/inspect_langflow_components.py --check
    poetry run python scripts/inspect_langflow_components.py \\
        --langflow-url http://localhost:7860
    (Set auth environment variable for LangFlow authentication)
"""

import argparse
import hashlib
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import httpx
except ImportError:
    httpx = None  # type: ignore


REPO_ROOT = Path(__file__).parent.parent
LFX_DIR = REPO_ROOT / ".lfx"
COMPONENT_SCHEMAS_PATH = LFX_DIR / "component-schemas-pinned.json"

# Expected CP4 custom components
REQUIRED_COMPONENTS = {
    "HulubulDataOperationRequestBoundary-hlb-lf-70-request-v1",
    "HulubulDataOperationResultBoundary-hlb-lf-70-result-v1",
    "HulubulContractInputBoundary-hlb-lf-10-input-v1",
    "HulubulContractResultBoundary-hlb-lf-10-result-v1",
    "HulubulExecutionEnvelope-hlb-lf-00-envelope-v1",
    "HulubulDataOperationRequestBuilder-hlb-lf-00-routing-request-v1",
    "HulubulRetryDecision-hlb-lf-70-retry-v1",
    "HulubulDeterministicRenderer-hlb-lf-00-renderer-v1",
}

# Sensitive field indicators are checked inline to filter them from schemas
# (see _is_sensitive_field_name method)


@dataclass
class InspectionResult:
    """Result of component schema inspection."""

    components: dict[str, Any]
    timestamp: str
    deployed_components: set[str]
    missing_components: set[str]
    errors: list[str]

    def is_success(self) -> bool:
        """True if inspection succeeded (even if some components missing)."""
        return len(self.errors) == 0


class LangFlowComponentInspector:
    """Inspects LangFlow components and captures their schemas."""

    def __init__(
        self,
        langflow_url: str = "http://localhost:7860",
        api_key: str | None = None,
    ):
        """Initialize inspector.

        Args:
            langflow_url: Base URL of LangFlow API
            api_key: Optional LangFlow API key
        """
        self.langflow_url = langflow_url
        self.api_key = api_key

    def inspect(self) -> InspectionResult:
        """Inspect components and capture schemas.

        Returns:
            InspectionResult with captured schemas or errors
        """
        if httpx is None:
            return InspectionResult(
                components={},
                timestamp=datetime.now(timezone.utc).isoformat(),
                deployed_components=set(),
                missing_components=REQUIRED_COMPONENTS,
                errors=["httpx not installed; run: poetry install --with integration"],
            )

        components: dict[str, Any] = {}
        errors: list[str] = []
        deployed: set[str] = set()
        missing: set[str] = REQUIRED_COMPONENTS.copy()

        # Try to fetch components from LangFlow API
        try:
            with httpx.Client() as client:
                # Query custom components endpoint
                headers: dict[str, str] = {}
                if self.api_key:
                    headers["Authorization"] = f"Bearer {self.api_key}"

                response = client.get(
                    f"{self.langflow_url}/api/v1/custom_component",
                    headers=headers,
                    timeout=10.0,
                )

                if response.status_code == 404:
                    # Endpoint doesn't exist yet; components not deployed
                    return InspectionResult(
                        components={},
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        deployed_components=set(),
                        missing_components=REQUIRED_COMPONENTS,
                        errors=[
                            "LangFlow /api/v1/custom_component not available. "
                            "Components may not be deployed yet."
                        ],
                    )

                if response.status_code == 401:
                    errors.append("Unauthorized: LangFlow API key required or invalid")
                    return InspectionResult(
                        components={},
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        deployed_components=set(),
                        missing_components=REQUIRED_COMPONENTS,
                        errors=errors,
                    )

                if response.status_code != 200:
                    errors.append(
                        f"LangFlow API error: {response.status_code} {response.text[:200]}"
                    )
                    return InspectionResult(
                        components={},
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        deployed_components=set(),
                        missing_components=REQUIRED_COMPONENTS,
                        errors=errors,
                    )

                # Parse response: typically a list of components
                response_data = response.json()
                component_list = (
                    response_data
                    if isinstance(response_data, list)
                    else response_data.get("components", [])
                )

                # Extract required components
                for component_data in component_list:
                    if isinstance(component_data, dict):
                        name = component_data.get("name")
                        if name and name in REQUIRED_COMPONENTS:
                            # Extract schema without secrets
                            schema = self._extract_safe_schema(component_data)
                            components[name] = schema
                            deployed.add(name)
                            missing.discard(name)

        except httpx.ConnectError as e:
            errors.append(
                f"Failed to connect to LangFlow at {self.langflow_url}: {e}. "
                "Ensure LangFlow is running."
            )
        except Exception as e:
            errors.append(f"Error inspecting components: {str(e)[:200]}")

        return InspectionResult(
            components=components,
            timestamp=datetime.now(timezone.utc).isoformat(),
            deployed_components=deployed,
            missing_components=missing,
            errors=errors,
        )

    def _extract_safe_schema(self, component_data: dict[str, Any]) -> dict[str, Any]:
        """Extract component schema without sensitive fields.

        Args:
            component_data: Raw component data from LangFlow API

        Returns:
            Schema dict with secrets removed
        """
        schema: dict[str, Any] = {}

        # Include safe metadata fields
        safe_fields = {"name", "description", "category", "version", "type"}
        for field in safe_fields:
            if field in component_data:
                schema[field] = component_data[field]

        # Extract input/output schemas, filtering out sensitive fields
        if "inputs" in component_data:
            schema["inputs"] = self._filter_sensitive_fields(component_data["inputs"])

        if "outputs" in component_data:
            schema["outputs"] = self._filter_sensitive_fields(component_data["outputs"])

        return schema

    def _filter_sensitive_fields(self, fields: Any) -> Any:
        """Recursively filter out sensitive fields from schema.

        Args:
            fields: Schema field data (dict, list, or scalar)

        Returns:
            Filtered schema with sensitive fields removed
        """
        if isinstance(fields, dict):
            return {
                k: self._filter_sensitive_fields(v)
                for k, v in fields.items()
                if not self._is_sensitive_field_name(k)
            }
        elif isinstance(fields, list):
            return [self._filter_sensitive_fields(item) for item in fields]
        else:
            return fields

    def _is_sensitive_field_name(self, field_name: str) -> bool:
        """Check if field name indicates sensitive data.

        Args:
            field_name: Name of the field

        Returns:
            True if field should be excluded
        """
        normalized = field_name.lower()
        # Exclude fields with these substrings (avoid hardcoding full patterns)
        patterns = ["auth", "credential", "secret", "pass", "token", "key"]
        return any(p in normalized for p in patterns)


def compute_hash(data: dict[str, Any]) -> str:
    """Compute SHA-256 hash of data (excluding 'sha256' and 'timestamp').

    'timestamp' is excluded because it changes on every run and would make
    the hash useless for drift detection even when component schemas are
    identical.

    Args:
        data: Data dict to hash

    Returns:
        Hex string of SHA-256 hash
    """
    hashable = {k: v for k, v in data.items() if k not in ("sha256", "timestamp")}
    json_str = json.dumps(hashable, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(json_str.encode()).hexdigest()


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Inspect and pin LangFlow component schemas",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  poetry run python scripts/inspect_langflow_components.py
  poetry run python scripts/inspect_langflow_components.py --check
  poetry run python scripts/inspect_langflow_components.py \\
      --langflow-url http://langflow:7860
        """,
    )
    parser.add_argument(
        "--langflow-url",
        default=os.getenv("LANGFLOW_BASE_URL", "http://localhost:7860"),
        help="LangFlow API base URL (default: http://localhost:7860)",
    )
    parser.add_argument(
        "--auth-token",
        default=os.getenv("LANGFLOW_API_KEY"),
        help="LangFlow authentication token (from environment variable)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check mode: verify pinned schemas match current LangFlow (drift detection)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=COMPONENT_SCHEMAS_PATH,
        help=f"Output path for pinned schemas (default: {COMPONENT_SCHEMAS_PATH})",
    )

    args = parser.parse_args()

    # Ensure output directory exists
    args.output.parent.mkdir(parents=True, exist_ok=True)

    # Inspect components
    inspector = LangFlowComponentInspector(
        langflow_url=args.langflow_url,
        api_key=args.auth_token,
    )
    result = inspector.inspect()

    # Prepare output data
    output_data: dict[str, Any] = {
        "version": "1.0",
        "timestamp": result.timestamp,
        "components": result.components,
    }

    if args.check:
        # Check mode: verify schemas match pinned version
        if not args.output.exists():
            print(f"[ERROR] Pinned schemas not found: {args.output}")
            print("Run without --check to create initial pinned schemas")
            return 1

        # Load existing pinned schemas
        with open(args.output) as f:
            pinned = json.load(f)

        # Compute hashes
        pinned_hash = pinned.get("sha256", "unknown")
        current_hash = compute_hash(output_data)

        print(f"Pinned hash:  {pinned_hash}")
        print(f"Current hash: {current_hash}")

        if pinned_hash != current_hash:
            print("[WARNING] Schema drift detected: pinned schemas do not match current LangFlow")
            # List deployed components
            if result.deployed_components:
                print(f"Deployed components: {', '.join(sorted(result.deployed_components))}")
            if result.missing_components:
                print(f"Missing components: {', '.join(sorted(result.missing_components))}")
            return 1

        print("[OK] Schemas match pinned version (no drift)")
        return 0

    # Normal mode: save/update pinned schemas
    output_data["sha256"] = compute_hash(output_data)

    with open(args.output, "w") as f:
        json.dump(output_data, f, indent=2)

    print(f"[OK] Pinned schemas saved to {args.output}")
    print(f"Timestamp: {result.timestamp}")

    if result.deployed_components:
        print(f"Deployed components ({len(result.deployed_components)}):")
        for name in sorted(result.deployed_components):
            print(f"  - {name}")

    if result.missing_components:
        print(f"Missing components ({len(result.missing_components)}):")
        for name in sorted(result.missing_components):
            print(f"  - {name}")

    if result.errors:
        print("\nErrors/warnings:")
        for error in result.errors:
            print(f"  [!] {error}")

    return 0 if not result.errors else 1


if __name__ == "__main__":
    sys.exit(main())
