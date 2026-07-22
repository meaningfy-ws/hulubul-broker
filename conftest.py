"""Root pytest conftest.

Its only purpose is to anchor pytest's rootdir at the repository root so
test modules under ``tests/`` can import top-level packages such as
``scripts`` (namespace package, no ``__init__.py``) without requiring
`pyproject.toml`/dependency changes, which belong to a later foundation
task (pinning test dependencies and packaging `src/hulubul`).
"""
