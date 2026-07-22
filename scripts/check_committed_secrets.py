"""Static scanner for literal secrets in git-tracked files.

Scans every path returned by ``git ls-files`` (i.e. content already tracked
or staged) for env-style assignments (``NAME=value``) where the variable
name looks like a credential (``*_API_KEY``, ``*_TOKEN``, ``*_SECRET``,
``*_PASSWORD``, ...) and the value is neither empty nor a known placeholder
(for example the repo-wide ``changeme`` convention used in
``infra/.env.example``).

Findings never carry the matched value: ``SecretFinding`` only records the
relative path and the id of the rule that fired, so it is always safe to
print, log, or assert on.
"""
from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Tuple

RULE_ID_CREDENTIAL_PATTERN = "credential-pattern"

_CREDENTIAL_NAME_SUFFIXES: Tuple[str, ...] = (
    "API_KEY",
    "APIKEY",
    "SECRET",
    "TOKEN",
    "PASSWORD",
    "PASSWD",
    "PRIVATE_KEY",
    "CREDENTIAL",
)

# Matches `NAME=value` and `export NAME=value` style assignment lines only
# at the start of a (non-comment) line, so occurrences inside prose,
# shell interpolations (`--env NAME=$(VAR)`), or `NAME := ...` Makefile
# syntax are not mistaken for a literal credential assignment.
_ASSIGNMENT_PATTERN = re.compile(
    r"^[ \t]*(?:export[ \t]+)?([A-Za-z_][A-Za-z0-9_]*)[ \t]*=[ \t]*(\S.*)$"
)

# Known non-secret placeholder values already used as convention in this
# repo (see infra/.env.example: POSTGRES_PASSWORD=changeme,
# NEO4J_PASSWORD=changeme123). Kept narrow and explicit on purpose.
_PLACEHOLDER_VALUE_PATTERN = re.compile(r"(?i)^changeme\d*$")


@dataclass(frozen=True)
class SecretFinding:
    """A single static-scan hit: where and by which rule, never the value."""

    path: str
    rule_id: str


def _looks_like_credential_name(name: str) -> bool:
    upper_name = name.upper()
    return any(upper_name.endswith(suffix) for suffix in _CREDENTIAL_NAME_SUFFIXES)


def _is_placeholder_value(value: str) -> bool:
    return bool(_PLACEHOLDER_VALUE_PATTERN.match(value))


def _file_has_credential_assignment(contents: str) -> bool:
    for line in contents.splitlines():
        match = _ASSIGNMENT_PATTERN.match(line)
        if not match:
            continue
        name, raw_value = match.group(1), match.group(2).strip()
        if not raw_value or not _looks_like_credential_name(name):
            continue
        if _is_placeholder_value(raw_value):
            continue
        return True
    return False


def _list_tracked_files(repo: Path) -> Tuple[str, ...]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    raw_paths = result.stdout.decode("utf-8", errors="surrogateescape").split("\0")
    return tuple(path for path in raw_paths if path)


def scan_tracked_files(repo: Path) -> Tuple[SecretFinding, ...]:
    """Scan every git-tracked file under ``repo`` for literal credential values.

    Binary or otherwise undecodable files are skipped. The returned findings
    never carry the matched value, only the relative path and rule id.
    """
    findings = []
    for relative_path in _list_tracked_files(repo):
        file_path = repo / relative_path
        try:
            contents = file_path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if _file_has_credential_assignment(contents):
            findings.append(
                SecretFinding(path=relative_path, rule_id=RULE_ID_CREDENTIAL_PATTERN)
            )
    return tuple(findings)


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    findings = scan_tracked_files(repo_root)
    for finding in findings:
        print(f"{finding.path}: {finding.rule_id}")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
