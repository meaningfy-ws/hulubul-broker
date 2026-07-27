> Derived from EPIC `modernize-repo-to-meaningfy-standard` (proposal.md)

## 1. Branch sync

- [x] 1.1 Create a new branch from `feature/input-connector`
- [x] 1.2 Merge `origin/develop` into it, resolve any conflicts
- [x] 1.3 Confirm `make check-all` is green on the merged base

## 2. Additive config files

- [x] 2.1 Add `ruff.toml` populated from `pyproject.toml`'s `[tool.ruff.*]`
- [x] 2.2 Add `mypy.ini` populated from `pyproject.toml`'s `[tool.mypy]`
- [x] 2.3 Add `pytest.ini` populated from `[tool.pytest.ini_options]`
- [x] 2.4 Add `.coveragerc` populated from `[tool.coverage.*]`
- [x] 2.5 Add `.pre-commit-config.yaml` wired to `make lint-python`/`typecheck`/`check-architecture`
- [x] 2.6 Add `CHANGELOG.md` (Keep a Changelog format, seeded "Unreleased")
- [x] 2.7 Add `SECURITY.md` (standard disclosure template)
- [x] 2.8 Add `sonar-project.properties` stub (DEC-3, revised — not wired into CI)
- [x] 2.9 Commit

## 3. tox removal

- [x] 3.1 Port `tox.ini`'s 2 real `evaluation`/`evaluation-live` envs (marker-based) to real Makefile targets; drop the never-real "judge" placeholder (DEC-5, corrected — tox only had 2 envs, not 3)
- [x] 3.2 Delete `tox.ini`
- [x] 3.3 Remove the `tox` dependency from `pyproject.toml`'s `quality` group
- [x] 3.4 Commit

## 4. Spine schema pin

- [x] 4.1 Copy `openspec/schemas/meaningfy/` (schema.yaml + templates/) into the repo
- [x] 4.2 Set `openspec/config.yaml`'s `schema: meaningfy`, add project `context:` + the 3 thin per-artifact rules
- [x] 4.3 Run `openspec validate --all --strict`; confirm the in-flight `deliver-phase-1-request-intake-thread` change (its own `superpowers-bridge` pin) is untouched
- [x] 4.4 Commit

## 5. Agent file reconciliation

- [x] 5.1 Remove the broken `CLAUDE.md` symlink
- [x] 5.2 Keep `AGENTS.md`'s content as canonical (DEC-8, reversed from CLAUDE-canonical per developer instruction); add the "Golden thread" spine note
- [x] 5.3 Replace `CLAUDE.md` with a minimal pointer ("Read AGENTS.md"), not a symlink
- [x] 5.4 Add `.claude/memory/MEMORY.md` (regenerable index, ≤200 lines)
- [x] 5.5 Verify `CLAUDE.md`/`AGENTS.md` resolve correctly from a clean `git clone` (portability check)
- [x] 5.6 Commit

## 6. pyproject normalization

- [x] 6.1 Remove `[tool.pytest.ini_options]`, `[tool.coverage.*]`, `[tool.ruff.*]`, `[tool.mypy]` from `pyproject.toml`
- [x] 6.2 Confirm `pyproject.toml` holds only `[project]`/`[tool.poetry]`/dependency groups/`[build-system]`
- [x] 6.3 `make check-all` green
- [x] 6.4 Commit

## 7. Infra Dockerfile consolidation

- [x] 7.1 Create `infra/docker/channel-gateway/Dockerfile` and `infra/docker/mcp/Dockerfile` (single-purpose each, revised from an initial multi-target approach per developer feedback — one image, one purpose)
- [x] 7.2 Create each one's co-located `Dockerfile.dockerignore`
- [x] 7.3 Update `infra/docker-compose.yaml` build contexts (no `target:` needed)
- [x] 7.4 Remove `infra/channel-gateway/Dockerfile` and `infra/mcp/Dockerfile`
- [x] 7.5 Build both images locally and diff the resulting image file listings against pre-change images
- [x] 7.6 Commit

## 8. `/src` lift

- [x] 8.1 `git mv src/hulubul hulubul` (preserve blame)
- [x] 8.2 Update `pyproject.toml`'s `packages` entry (drop `from = "src"`)
- [x] 8.3 Update `pytest.ini`'s `pythonpath`
- [x] 8.4 Remove the manual `sys.path` shim in `tests/conftest.py`
- [x] 8.5 Grep the repo for remaining `src/` / `from = "src"` / `pythonpath.*src` references (Makefile, CI, `.importlinter`, scripts) and fix each
- [x] 8.6 Run the full test suite (`make test-unit test-feature`) and `make check-architecture`
- [x] 8.7 Commit (isolated — no other change in this commit)

## 9. Full verification

- [x] 9.1 `make check-all` green
- [x] 9.2 `openspec validate --all --strict` green
- [x] 9.3 Confirm `.github/workflows/ci.yaml` has no leftover `tox`/`src/` references
- [x] 9.4 Confirm the four proof scenarios hold (check-all per slice already true by construction; agent-file resolution; strict validation; CI/local parity)

## Roadmap

- [x] 1.1 · [x] 1.2 · [x] 1.3 · [x] 2.1 · [x] 2.2 · [x] 2.3 · [x] 2.4 · [x] 2.5 · [x] 2.6 · [x] 2.7 · [x] 2.8 · [x] 2.9 · [x] 3.1 · [x] 3.2 · [x] 3.3 · [x] 3.4 · [x] 4.1 · [x] 4.2 · [x] 4.3 · [x] 4.4 · [x] 5.1 · [x] 5.2 · [x] 5.3 · [x] 5.4 · [x] 5.5 · [x] 5.6 · [x] 6.1 · [x] 6.2 · [x] 6.3 · [x] 6.4 · [x] 7.1 · [x] 7.2 · [x] 7.3 · [x] 7.4 · [x] 7.5 · [x] 7.6 · [x] 8.1 · [x] 8.2 · [x] 8.3 · [x] 8.4 · [x] 8.5 · [x] 8.6 · [x] 8.7 · [x] 9.1 · [x] 9.2 · [x] 9.3 · [x] 9.4

## Verification

`make check-all` after every slice (2–8), plus `openspec validate --all --strict`
and a fresh-clone agent-file check in the final verification group (9).
