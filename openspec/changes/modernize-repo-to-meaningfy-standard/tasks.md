> Derived from EPIC `modernize-repo-to-meaningfy-standard` (proposal.md)

## 1. Branch sync

- [ ] 1.1 Create a new branch from `feature/input-connector`
- [ ] 1.2 Merge `origin/develop` into it, resolve any conflicts
- [ ] 1.3 Confirm `make check-all` is green on the merged base

## 2. Additive config files

- [ ] 2.1 Add `ruff.toml` populated from `pyproject.toml`'s `[tool.ruff.*]`
- [ ] 2.2 Add `mypy.ini` populated from `pyproject.toml`'s `[tool.mypy]`
- [ ] 2.3 Add `pytest.ini` populated from `[tool.pytest.ini_options]`
- [ ] 2.4 Add `.coveragerc` populated from `[tool.coverage.*]`
- [ ] 2.5 Add `.pre-commit-config.yaml` wired to `make lint-python`/`typecheck`/`check-architecture`
- [ ] 2.6 Add `CHANGELOG.md` (Keep a Changelog format, seeded "Unreleased")
- [ ] 2.7 Add `SECURITY.md` (standard disclosure template)
- [ ] 2.8 Commit

## 3. tox removal

- [ ] 3.1 Port `tox.ini`'s `evaluation`/`evaluation-live`/live-model-judge envs into the Makefile's commented-out `test-evaluation-*` stubs, uncomment and wire them
- [ ] 3.2 Delete `tox.ini`
- [ ] 3.3 Remove the `tox` dependency from `pyproject.toml`'s `quality` group
- [ ] 3.4 Commit

## 4. Spine schema pin

- [ ] 4.1 Copy `openspec/schemas/meaningfy/` (schema.yaml + templates/) into the repo
- [ ] 4.2 Set `openspec/config.yaml`'s `schema: meaningfy`, add project `context:` + the 3 thin per-artifact rules
- [ ] 4.3 Run `openspec validate --strict`; confirm the in-flight `deliver-phase-1-request-intake-thread` change (its own `superpowers-bridge` pin) is untouched
- [ ] 4.4 Commit

## 5. Agent file reconciliation

- [ ] 5.1 Remove the broken `CLAUDE.md` symlink
- [ ] 5.2 Move `AGENTS.md`'s content into `CLAUDE.md` (canonical); add the "Golden thread" spine note
- [ ] 5.3 Create `AGENTS.md` as a relative symlink to `CLAUDE.md` (`ln -s CLAUDE.md AGENTS.md`)
- [ ] 5.4 Add `.claude/memory/MEMORY.md` (regenerable index, ≤200 lines)
- [ ] 5.5 Verify `CLAUDE.md`/`AGENTS.md` resolve correctly from a clean `git clone` (portability check)
- [ ] 5.6 Commit

## 6. pyproject normalization

- [ ] 6.1 Remove `[tool.pytest.ini_options]`, `[tool.coverage.*]`, `[tool.ruff.*]`, `[tool.mypy]` from `pyproject.toml`
- [ ] 6.2 Confirm `pyproject.toml` holds only `[project]`/`[tool.poetry]`/dependency groups/`[build-system]`
- [ ] 6.3 `make check-all` green
- [ ] 6.4 Commit

## 7. Infra Dockerfile consolidation

- [ ] 7.1 Create `infra/docker/Dockerfile` (multistage, multi-target: `channel-gateway`, `mcp`)
- [ ] 7.2 Create co-located `infra/docker/Dockerfile.dockerignore`
- [ ] 7.3 Update `infra/docker-compose.yaml` build contexts/targets
- [ ] 7.4 Remove `infra/channel-gateway/Dockerfile` and `infra/mcp/Dockerfile`
- [ ] 7.5 Build both targets locally and diff the resulting image file listings against pre-change images
- [ ] 7.6 Commit

## 8. `/src` lift

- [ ] 8.1 `git mv src/hulubul hulubul` (preserve blame)
- [ ] 8.2 Update `pyproject.toml`'s `packages` entry (drop `from = "src"`)
- [ ] 8.3 Update `pytest.ini`'s `pythonpath`
- [ ] 8.4 Remove the manual `sys.path` shim in `tests/conftest.py`
- [ ] 8.5 Grep the repo for remaining `src/` / `from = "src"` / `pythonpath.*src` references (Makefile, CI, `.importlinter`, scripts) and fix each
- [ ] 8.6 Run the full test suite (`make test-unit test-feature`) and `make check-architecture`
- [ ] 8.7 Commit (isolated — no other change in this commit)

## 9. Full verification

- [ ] 9.1 `make check-all` green
- [ ] 9.2 `openspec validate --strict` green
- [ ] 9.3 Confirm `.github/workflows/ci.yaml` has no leftover `tox`/`src/` references
- [ ] 9.4 Confirm the four proof scenarios hold (check-all per slice already true by construction; agent-file resolution; strict validation; CI/local parity)

## Roadmap

- [ ] 1.1 · [ ] 1.2 · [ ] 1.3 · [ ] 2.1 · [ ] 2.2 · [ ] 2.3 · [ ] 2.4 · [ ] 2.5 · [ ] 2.6 · [ ] 2.7 · [ ] 2.8 · [ ] 3.1 · [ ] 3.2 · [ ] 3.3 · [ ] 3.4 · [ ] 4.1 · [ ] 4.2 · [ ] 4.3 · [ ] 4.4 · [ ] 5.1 · [ ] 5.2 · [ ] 5.3 · [ ] 5.4 · [ ] 5.5 · [ ] 5.6 · [ ] 6.1 · [ ] 6.2 · [ ] 6.3 · [ ] 6.4 · [ ] 7.1 · [ ] 7.2 · [ ] 7.3 · [ ] 7.4 · [ ] 7.5 · [ ] 7.6 · [ ] 8.1 · [ ] 8.2 · [ ] 8.3 · [ ] 8.4 · [ ] 8.5 · [ ] 8.6 · [ ] 8.7 · [ ] 9.1 · [ ] 9.2 · [ ] 9.3 · [ ] 9.4

## Verification

`make check-all` after every slice (2–8), plus `openspec validate --strict`
and a fresh-clone agent-file check in the final verification group (9).
