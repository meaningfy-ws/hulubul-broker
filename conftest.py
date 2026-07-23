"""Root pytest conftest.

Its only purpose is to anchor pytest's rootdir at the repository root so
test modules under ``tests/`` can import top-level packages such as
``scripts`` (namespace package, no ``__init__.py``) and the application
package under ``src/hulubul/``.
"""
