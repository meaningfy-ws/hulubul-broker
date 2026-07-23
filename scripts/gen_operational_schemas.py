#!/usr/bin/env python3
"""Deterministic JSON schema generator for operational contracts.

Generates one JSON schema per operational contract kind from Pydantic models.
Schemas are committed to ensure deterministic, version-controlled validation.

Usage (via entry point):
  poetry run gen-operational-schemas --output schemas/operational/v1
  poetry run gen-operational-schemas --output schemas/operational/v1 --check

Usage (direct script):
  python scripts/gen_operational_schemas.py --output schemas/operational/v1
  python scripts/gen_operational_schemas.py --output schemas/operational/v1 --check

Make target:
  make check-operational-schemas
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime
from importlib import import_module
from pathlib import Path
from typing import Any

import click


# Mapping: ContractKind value -> (module_path, model_class_name)
CONTRACT_MODEL_MAP = {
    "main-flow-input": ("hulubul.core.models.operational.envelope", "MainFlowInput"),
    "router-input": ("hulubul.core.models.operational.routing", "RouterInput"),
    "intake-input": ("hulubul.core.models.operational.intake", "IntakeInput"),
    "routing-context": ("hulubul.core.models.operational.routing", "RoutingContext"),
    "router-result": ("hulubul.core.models.operational.routing", "RouterResult"),
    "intake-facts": ("hulubul.core.models.operational.intake", "IntakeFacts"),
    "intake-result": ("hulubul.core.models.operational.intake", "IntakeResult"),
    "data-operation-request": ("hulubul.core.models.operational.data_operations", "DataOperationRequest"),
    "data-operation-result": ("hulubul.core.models.operational.data_operations", "DataOperationResult"),
    "delivery-request-snapshot": ("hulubul.core.models.operational.snapshots", "DeliveryRequestSnapshot"),
    "operational-error": ("hulubul.core.models.operational.errors", "OperationalError"),
}


def get_model_class(module_path: str, class_name: str) -> type:
    """Dynamically import and return a Pydantic model class."""
    try:
        module = import_module(module_path)
        return getattr(module, class_name)
    except (ImportError, AttributeError) as e:
        raise ValueError(
            f"Cannot import {class_name} from {module_path}: {e}"
        ) from e


def generate_schema(contract_kind: str) -> dict[str, Any]:
    """Generate JSON schema for a contract kind.

    Args:
        contract_kind: The contract kind identifier (e.g., "main-flow-input")

    Returns:
        The Pydantic model's JSON schema dict
    """
    if contract_kind not in CONTRACT_MODEL_MAP:
        raise ValueError(f"Unknown contract kind: {contract_kind}")

    from pydantic import TypeAdapter

    module_path, class_name = CONTRACT_MODEL_MAP[contract_kind]
    module = import_module(module_path)

    # Try to get as a model class first, then as a type annotation
    try:
        model_class = getattr(module, class_name)
        # Check if it's a model class with model_json_schema method
        if hasattr(model_class, 'model_json_schema'):
            return model_class.model_json_schema()
        else:
            # It's a type annotation, use TypeAdapter
            adapter = TypeAdapter(model_class)
            return adapter.json_schema()
    except (ImportError, AttributeError) as e:
        raise ValueError(
            f"Cannot import {class_name} from {module_path}: {e}"
        ) from e


def schema_sha256(schema: dict[str, Any]) -> str:
    """Compute stable SHA-256 hash of a schema dict.

    Uses JSON dump with sorted keys for deterministic output.
    """
    schema_json = json.dumps(schema, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(schema_json.encode()).hexdigest()


def generate_all_schemas() -> dict[str, tuple[dict, str]]:
    """Generate all 11 operational schemas.

    Returns:
        Dict mapping contract_kind -> (schema_dict, sha256_hash)
    """
    schemas: dict[str, tuple[dict, str]] = {}

    for contract_kind in sorted(CONTRACT_MODEL_MAP.keys()):
        try:
            schema = generate_schema(contract_kind)
            sha256 = schema_sha256(schema)
            schemas[contract_kind] = (schema, sha256)
        except Exception as e:
            raise RuntimeError(
                f"Failed to generate schema for {contract_kind}: {e}"
            ) from e

    return schemas


def write_schemas_to_disk(output_dir: Path, schemas: dict[str, tuple[dict, str]]) -> None:
    """Write generated schemas to disk.

    Args:
        output_dir: Directory to write schemas to
        schemas: Dict mapping contract_kind -> (schema_dict, sha256_hash)
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    for contract_kind, (schema, sha256) in schemas.items():
        schema_file = output_dir / f"{contract_kind}.schema.json"

        # Write schema with indentation for readability
        with open(schema_file, "w") as f:
            json.dump(schema, f, indent=2, sort_keys=True)
            f.write("\n")  # Trailing newline

    # Write manifest
    manifest = {
        "version": "1.0.0",
        "generated": datetime.utcnow().isoformat() + "Z",
        "schemas": {
            contract_kind: {
                "file": f"{contract_kind}.schema.json",
                "sha256": sha256,
            }
            for contract_kind, (_, sha256) in schemas.items()
        },
    }

    manifest_file = output_dir / "manifest.json"
    with open(manifest_file, "w") as f:
        json.dump(manifest, f, indent=2, sort_keys=True)
        f.write("\n")  # Trailing newline


def check_schemas_match(output_dir: Path, schemas: dict[str, tuple[dict, str]]) -> bool:
    """Verify that generated schemas match existing files.

    Args:
        output_dir: Directory containing existing schemas
        schemas: Dict mapping contract_kind -> (schema_dict, sha256_hash)

    Returns:
        True if all schemas match, False otherwise
    """
    output_dir = Path(output_dir)

    if not output_dir.exists():
        return False

    for contract_kind, (schema, sha256) in schemas.items():
        schema_file = output_dir / f"{contract_kind}.schema.json"

        if not schema_file.exists():
            return False

        try:
            with open(schema_file, "r") as f:
                existing_schema = json.load(f)

            existing_sha256 = schema_sha256(existing_schema)
            if existing_sha256 != sha256:
                return False
        except Exception:
            return False

    # Check manifest
    manifest_file = output_dir / "manifest.json"
    if not manifest_file.exists():
        return False

    return True


@click.command(name="gen-operational-schemas")
@click.option(
    "--output",
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
    required=True,
    help="Output directory for schemas",
)
@click.option(
    "--check",
    is_flag=True,
    help="Exit with code 1 if schemas are stale (don't write)",
)
@click.version_option("1.0.0", "-V", "--version")
def cli(output: Path, check: bool) -> None:
    """Generate deterministic JSON schemas for operational contracts.

    Generates 11 schemas (one per ContractKind) with stable SHA-256 hashing.
    If --check is set, verifies generated schemas match existing files and exits
    with code 1 if stale (useful for CI drift detection).
    """
    try:
        schemas = generate_all_schemas()

        if check:
            if check_schemas_match(output, schemas):
                click.echo("✓ Operational schemas are up-to-date")
                sys.exit(0)
            else:
                click.echo("✗ Operational schemas are stale", err=True)
                click.echo("  Run: gen-operational-schemas --output schemas/operational/v1", err=True)
                sys.exit(1)
        else:
            write_schemas_to_disk(output, schemas)
            click.echo(f"✓ Generated 11 operational schemas in {output}")
            manifest_file = output / "manifest.json"
            click.echo(f"✓ Generated manifest at {manifest_file}")
    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    cli()
