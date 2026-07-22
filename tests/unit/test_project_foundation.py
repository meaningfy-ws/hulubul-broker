"""Foundation tests for the packaged ``hulubul`` application.

These tests guard the two contracts Task 2 (Locked Python Package Baseline)
establishes: the ``src/hulubul`` package must be importable with a stable
``__version__``, and the pre-existing LinkML generator entrypoints must
remain declared in ``pyproject.toml`` after the packaging/dependency edits.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture()
def pyproject() -> dict[str, Any]:
    """Parse the repository root ``pyproject.toml`` into a plain dict."""
    with (REPO_ROOT / "pyproject.toml").open("rb") as handle:
        return tomllib.load(handle)


def test_hulubul_package_is_importable():
    import hulubul

    assert hulubul.__version__ == "0.1.0"


def test_existing_generator_entrypoints_remain_declared(pyproject):
    assert set(pyproject["tool"]["poetry"]["scripts"]) >= {
        "gen-neo4j-constraints",
        "gen-neomodel",
        "gen-mermaid-classdiagram",
    }
