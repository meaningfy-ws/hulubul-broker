"""Foundation tests for the packaged ``hulubul`` application.

These tests guard the contracts the Section 1 foundation tasks establish:
Task 2 (Locked Python Package Baseline) makes ``src/hulubul`` importable with
a stable ``__version__`` and keeps the pre-existing LinkML generator
entrypoints declared in ``pyproject.toml``; Task 3 (Python Quality And Tox
Configuration) keeps the default tox environment list fast (unit tests plus
static checks only) while excluding the live-model evaluation environment
from that default run.
"""
from __future__ import annotations

import configparser
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


@pytest.fixture()
def tox_config() -> dict[str, dict[str, str]]:
    """Parse ``tox.ini`` into a dict keyed by section name.

    Section names are stripped of the ``testenv:`` prefix so that both the
    ``[tox]`` section and each ``[testenv:<name>]`` environment are reachable
    by their short name, e.g. ``tox_config["tox"]`` and
    ``tox_config["evaluation-live"]``.
    """
    parser = configparser.ConfigParser()
    read_files = parser.read(REPO_ROOT / "tox.ini")
    if not read_files:
        raise FileNotFoundError(f"tox.ini not found under {REPO_ROOT}")
    return {
        section.rsplit(":", 1)[-1]: dict(parser.items(section))
        for section in parser.sections()
    }


def test_hulubul_package_is_importable():
    import hulubul

    assert hulubul.__version__ == "0.1.0"


def test_existing_generator_entrypoints_remain_declared(pyproject):
    assert set(pyproject["tool"]["poetry"]["scripts"]) >= {
        "gen-neo4j-constraints",
        "gen-neomodel",
        "gen-mermaid-classdiagram",
    }


def test_default_tox_envs_are_fast(tox_config):
    assert tox_config["tox"]["env_list"] == "py310, architecture, schemas"
    assert "evaluation-live" in tox_config
