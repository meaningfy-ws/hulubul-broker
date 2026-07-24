"""Foundation tests for the packaged ``hulubul`` application.

These tests guard the contracts the Section 1 foundation tasks establish:
Task 2 (Locked Python Package Baseline) makes ``src/hulubul`` importable with
a stable ``__version__`` and keeps the pre-existing LinkML generator
entrypoints declared in ``pyproject.toml``; Task 3 (Python Quality And Tox
Configuration) keeps the default tox environment list fast (unit tests plus
static checks only) while excluding the live-model evaluation environment
from that default run; Task 4 (Canonical Make Targets) adds the namespaced
Python/CI/acceptance Make targets without changing the pre-existing
``lint`` (LinkML-only) target.
"""

from __future__ import annotations

import configparser
import re
import sys
from pathlib import Path
from typing import Any

import pytest

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

REPO_ROOT = Path(__file__).resolve().parents[2]

# The canonical Make target set locked by Task 4. Every name here must exist
# as a target in the root Makefile; the scripts/tests some of these recipes
# invoke are introduced by later plan tasks and are allowed to fail until
# then (see task-4-brief.md step 3).
CANONICAL_PYTHON_AND_CI_TARGETS = (
    "install",
    "lint-python",
    "format-check-python",
    "typecheck",
    "test-unit",
    "check-architecture",
    "operational-schemas",
    "format-python",
    "check-model-generated",
    "check-operational-schemas",
    "check-secrets",
    "test-integration",
    "test-system",
    "test-bdd",
    "ci-static",
    "ci-acceptance",
    "ci",
    "acceptance-up",
    "acceptance-ready",
    "acceptance-deploy",
    "preflight-langflow-1-10-2",
    "acceptance-diagnostics",
    "acceptance-down",
    "release-evidence",
)

# New quality/CI targets must stay usable without the local Docker stack, so
# none of them may read the gitignored runtime env files directly.
_NEW_QUALITY_TARGETS_WITHOUT_ENV_FILES = (
    "install",
    "lint-python",
    "format-check-python",
    "typecheck",
    "test-unit",
    "check-architecture",
    "operational-schemas",
    "format-python",
    "check-model-generated",
    "check-operational-schemas",
    "check-secrets",
    "ci-static",
)


def _target_declaration_pattern(name: str) -> re.Pattern[str]:
    """Match a Makefile target declaration line, not a variable assignment.

    Excludes ``:=`` / ``::=`` assignment operators so variables such as
    ``ACCEPTANCE_PROJECT ?= ...`` are never mistaken for a target named
    ``ACCEPTANCE_PROJECT``.
    """
    return re.compile(rf"^{re.escape(name)}:(?!=)(.*)$", re.MULTILINE)


def target_body(makefile_text: str, name: str) -> str:
    """Return the tab-indented recipe body that follows ``name:``."""
    lines = makefile_text.splitlines()
    declaration = re.compile(rf"^{re.escape(name)}:(?!=)")
    for index, line in enumerate(lines):
        if declaration.match(line):
            body_lines = []
            for later_line in lines[index + 1 :]:
                if later_line.startswith("\t"):
                    body_lines.append(later_line[1:])
                else:
                    break
            return "\n".join(body_lines)
    raise AssertionError(f"target {name!r} not found in Makefile")


def target_prerequisites(makefile_text: str, name: str) -> list[str]:
    """Return the prerequisite names listed on a target's own declaration line."""
    match = _target_declaration_pattern(name).search(makefile_text)
    if match is None:
        raise AssertionError(f"target {name!r} not found in Makefile")
    return match.group(1).split()


@pytest.fixture()
def makefile_text() -> str:
    """Read the root Makefile as plain text for target-contract assertions."""
    return (REPO_ROOT / "Makefile").read_text()


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
        section.rsplit(":", 1)[-1]: dict(parser.items(section)) for section in parser.sections()
    }


def test_hulubul_package_is_importable() -> None:
    import hulubul

    assert hulubul.__version__ == "0.1.0"


def test_existing_generator_entrypoints_remain_declared(pyproject: dict[str, Any]) -> None:
    assert set(pyproject["tool"]["poetry"]["scripts"]) >= {
        "gen-neo4j-constraints",
        "gen-neomodel",
        "gen-mermaid-classdiagram",
    }


def test_default_tox_envs_are_fast(tox_config: dict[str, dict[str, str]]) -> None:
    assert tox_config["tox"]["env_list"] == "py310, architecture, schemas"
    assert "evaluation-live" in tox_config


def test_python_make_targets_exist(makefile_text: str) -> None:
    for target_name in CANONICAL_PYTHON_AND_CI_TARGETS:
        target_body(makefile_text, target_name)  # raises AssertionError if missing


def test_make_lint_still_invokes_linkml_lint_only(makefile_text: str) -> None:
    body = target_body(makefile_text, "lint")
    assert "linkml-lint" in body
    assert "ruff" not in body


def test_install_uses_full_dependency_groups(makefile_text: str) -> None:
    body = target_body(makefile_text, "install")
    assert "poetry install --with test,quality,langflow,integration" in body


def test_test_unit_enforces_coverage_threshold(makefile_text: str) -> None:
    body = target_body(makefile_text, "test-unit")
    assert "--cov=hulubul" in body
    assert "--cov-branch" in body
    assert "--cov-fail-under=80" in body


def test_check_architecture_runs_lint_imports(makefile_text: str) -> None:
    body = target_body(makefile_text, "check-architecture")
    assert "poetry run lint-imports" in body


def test_ci_static_lists_expected_prerequisites_in_order(makefile_text: str) -> None:
    assert target_prerequisites(makefile_text, "ci-static") == [
        "lint",
        "check-model-generated",
        "lint-python",
        "format-check-python",
        "typecheck",
        "check-architecture",
        "check-operational-schemas",
        "check-secrets",
        "test-unit",
    ]


def test_ci_acceptance_lists_expected_prerequisites_in_order(makefile_text: str) -> None:
    assert target_prerequisites(makefile_text, "ci-acceptance") == [
        "test-integration",
        "test-system",
        "test-bdd",
        "release-evidence",
    ]


def test_ci_composes_static_and_acceptance(makefile_text: str) -> None:
    assert target_prerequisites(makefile_text, "ci") == ["ci-static", "ci-acceptance"]


def test_acceptance_deploy_pushes_flows_in_pipeline_order(makefile_text: str) -> None:
    body = target_body(makefile_text, "acceptance-deploy")
    assert (
        body.index("10-lf-70-data-access.json")
        < body.index("20-lf-10-request-intake.json")
        < body.index("30-lf-00-main-router.json")
    )


def test_release_evidence_builds_change1_evidence_report(makefile_text: str) -> None:
    body = target_body(makefile_text, "release-evidence")
    assert "scripts/build_change1_evidence.py" in body
    assert "reports/change1/release-evidence.json" in body


@pytest.mark.parametrize("target_name", _NEW_QUALITY_TARGETS_WITHOUT_ENV_FILES)
def test_new_targets_do_not_read_local_env_files(makefile_text: str, target_name: str) -> None:
    body = target_body(makefile_text, target_name)
    assert "infra/.env" not in body
    assert "infra/langflow.env" not in body
