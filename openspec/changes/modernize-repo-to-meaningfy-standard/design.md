> Parent: `modernize-repo-to-meaningfy-standard` (proposal.md)
> Document type: Implementation (PLAN design half — paired with `tasks.md`)

## Context

hulubul-broker is a product-archetype repo (LangFlow/Neo4j-backed broker
service, cosmic-python layered `hulubul` package, LinkML `model/`). It
already conforms on the dimensions that matter most for correctness —
`.importlinter` cosmic-python boundaries, Ruff/mypy/import-linter tool
choice, type-split BDD test tree, 80% coverage gate, CI calling `make`
targets — but has drifted on layout, config placement, task-runner
duplication, the agent file, and the OpenSpec schema pin. The full gap
report is in `../inputs/audit-and-elicitation.md`.

Current branch state: `feature/input-connector` (channel-gateway work,
clean tree) is behind `origin/develop`, which itself is ahead of `main`.

## Goals / Non-Goals

**Goals:**
- Every detected D1/D2/D4/D7/D8/D9/D11/D13 gap (see audit) closed, plus the
  four missing additive files, without touching business behavior.
- Each slice independently reviewable and green on `make check-all`.
- The four proof scenarios agreed during elicitation hold at the end.

**Non-Goals:**
- Antora docs (D10), Sonar integration — explicit no-gos (DEC-2, DEC-3).
- Any change to import-linter contract *content* (only paths may shift after
  the `/src` lift; the contracts themselves are already conformant).
- Any change to channel-gateway/request_intake runtime behavior.

## Decisions

New technical choices made while planning (EPIC-level decisions are cited by
DEC-n, not repeated here):

- **Order of slices** follows `modernizing-existing-projects.md`'s
  recommended sequence exactly, with docs (step 9) dropped per DEC-2:
  additive files → spine projection → agent file → pyproject
  normalization → tooling swap (already Ruff, N/A) → infra → `/src` lift.
  Tests are already type-split with the marker list in `pyproject.toml`, so
  the "test reorganization" step is reduced to nothing beyond what the
  `/src` lift's path updates require.
- **No `.claude/memory/MEMORY.md`** *(DEC-9, corrected during implementation)*:
  originally added per D9, then removed after the developer questioned it —
  it hand-restated the same facts already in `openspec/config.yaml`'s
  `context:` field, which is OpenSpec's own native, auto-injected
  orientation index. One index, not a hand-maintained duplicate at risk of
  drifting from it.
- **Per-change schema pinning**: rather than force-migrating the in-flight
  `deliver-phase-1-request-intake-thread` change's `superpowers-bridge`
  schema, this repo already scopes `schema:` per change via
  `.openspec.yaml` (confirmed by inspecting that change's file). The global
  `openspec/config.yaml` default becomes `meaningfy`; the in-flight change's
  own `.openspec.yaml` is untouched.
- **Infra Dockerfile consolidation approach** *(revised after developer
  feedback)*: originally a single `infra/docker/Dockerfile` with
  `--target channel-gateway`/`--target mcp` multi-target stages was tried.
  Reverted per explicit developer instruction: a Docker image must have a
  single purpose, even at the cost of duplicating boilerplate across two
  files — a shared multi-target file makes it too easy for one service's
  build args/stages to leak into the other, and is harder to reason about
  at a glance. Final shape: `infra/docker/channel-gateway/Dockerfile` and
  `infra/docker/mcp/Dockerfile`, each single-purpose and independently
  multistage where applicable (channel-gateway: builder→slim non-root; mcp:
  already minimal, digest-pinned, non-root). Both still use the repo-root
  build context (not a narrowed per-service context) for consistency
  between the two, per the same feedback. Each gets its own co-located
  `Dockerfile.dockerignore` per D11.

## Algorithm / approach

Nine slices, each its own commit, `make check-all` green before starting
the next. Idempotency note: every slice is either purely additive (new
files) or a mechanical move/rewrite of config — none of them are runtime
operations, so there is no retry/replay concern; a slice that fails
`make check-all` is fixed or reverted in place before the next slice starts.

1. **Branch sync** — merge `origin/develop` into a new branch cut from
   `feature/input-connector`; resolve conflicts; confirm `make check-all`
   still green on the merged base before any modernization work starts.
2. **Additive config files** — `ruff.toml`, `mypy.ini`, `pytest.ini`,
   `.coveragerc` populated from the current `[tool.*]` blocks (values
   copied, not yet removed from `pyproject.toml` — that's slice 5);
   `.pre-commit-config.yaml` wired to run `make lint-python`/`typecheck`/
   `check-architecture`; `CHANGELOG.md` (Keep a Changelog format, seeded
   with an "Unreleased" section). `SECURITY.md` was added here too,
   then removed (DEC-9) — its public-disclosure-process content doesn't
   fit an internal repo with no external security-research audience.
   Commit.
3. **tox → Makefile** — port `evaluation`, `evaluation-live`, and the
   live-model judge eval envs from `tox.ini` into the existing commented-out
   Makefile target stubs (`test-evaluation-recorded`, `test-evaluation-live`,
   `test-evaluation-judge`), uncomment and wire them; delete `tox.ini`.
   Commit.
4. **Spine schema pin** — copy `openspec/schemas/meaningfy/` (schema.yaml +
   templates/) into the repo; set `openspec/config.yaml`'s `schema:
   meaningfy`; add the project `context:` block (repo, layering, branch,
   commit conventions) and the 3 thin per-artifact rules. Commit.
5. **Agent file reconciliation** — delete the broken `CLAUDE.md` symlink
   (absolute-path target was the root cause); keep `AGENTS.md`'s content as
   the canonical file (DEC-8: reverses the project-setup standard's default
   CLAUDE-canonical choice, per explicit developer instruction — `AGENTS.md`
   is the cross-tool standard name and the developer wants it real);
   replace `CLAUDE.md` with a minimal pointer ("Read AGENTS.md"), not a
   symlink, so any tool reading `CLAUDE.md` directly is forced to go read
   the real file; add a "Golden thread" note per `spine-projection.md`.
   Commit. (`.claude/memory/MEMORY.md` was added here too, then removed —
   DEC-9.)
6. **pyproject normalization** — remove the `[tool.pytest.ini_options]`,
   `[tool.coverage.*]`, `[tool.ruff.*]`, `[tool.mypy]` blocks now that
   slice 2 has them in dedicated files; leave `[project]`/`[tool.poetry]`/
   dependency groups/`[build-system]` only. Commit.
7. **Infra Dockerfile consolidation** — introduce
   `infra/docker/channel-gateway/Dockerfile` and `infra/docker/mcp/Dockerfile`
   (each single-purpose, independently multistage where applicable, each
   with its own co-located `Dockerfile.dockerignore`); update
   `infra/docker-compose.yaml` build contexts (no `target:` needed — each
   file has exactly one image); remove the two old per-component
   Dockerfiles. Commit.
8. **`/src` lift** — `git mv src/hulubul hulubul` (root-level, preserves
   blame); update `pyproject.toml`'s `packages` entry (drop `from = "src"`);
   update `pytest.ini`'s `pythonpath` (drop `src`, or set to `.`); remove
   the manual `sys.path` shim in `tests/conftest.py` (no longer needed once
   the package is importable from repo root); update
   `.importlinter`'s `root_packages` if it referenced the `src` prefix
   (audit shows it already only says `hulubul`, so likely unaffected —
   verify at implementation time); update `.github/workflows/ci.yaml` if it
   references `src/` anywhere. Run the full test suite. Isolated commit.
9. **Full verification** — `make check-all`; open a fresh shell/clone check
   that `CLAUDE.md` resolves; `openspec validate --strict`; confirm CI
   workflow has no leftover `tox`/`src` references.

### Anti-patterns

- ❌ Editing `[tool.*]` blocks in `pyproject.toml` and the new dedicated file
  in the same commit as unrelated changes — each config file's introduction
  is its own concern.
- ❌ Doing the `/src` lift and any other slice in the same commit — it's
  explicitly isolated (DEC-4).
  ❌ An absolute-path symlink anywhere in the repo (that's the exact bug
  being fixed) — always use a relative symlink target.
- ❌ Silently dropping the 3 tox eval environments instead of porting them
  (DEC-5 requires zero capability loss).
- ❌ Touching `openspec/changes/deliver-phase-1-request-intake-thread/`'s
  own schema pin.

## Error matrix

| Failure mode | Expected handling |
|---|---|
| A slice's commit breaks `make check-all` | Fix forward within the same slice before starting the next; never carry a red slice forward. |
| `/src` lift breaks an import somewhere unexpected | GitNexus `check` showed 0 cycles pre-lift; re-run `make check-all` and `pytest` immediately after the `git mv`; since the package name doesn't change, only path-based configs (pyproject, pytest.ini, conftest.py, CI) need edits — grep for literal `src/` or `src.hulubul` strings across configs as a checklist. |
| Merging `origin/develop` into the new branch produces conflicts | Resolve manually, favoring `develop`'s content for anything outside this EPIC's scope (business logic) and this branch's content for anything this EPIC is actively changing; re-run `make check-all` on the merged result before slice 1 is considered done. |
| `openspec validate --strict` fails after the schema pin (slice 4) | Check the in-flight change's own `.openspec.yaml` schema pin is untouched; check the new change's own artifacts (this EPIC) validate under `meaningfy`. |
| Pre-commit hook (new in slice 2) rejects an already-committed file's formatting | Run `make format-python` once, commit the reformat separately from the hook's introduction. |

## Risks / Trade-offs

- [Risk] The `/src` lift touches every path-based config in one pass, so a
  missed reference (e.g. a stray `src/` string in a CI workflow or a
  gitignored local script) could silently break something outside
  `make check-all`'s coverage. → [Mitigation] grep the whole repo for `src/`
  and `from = "src"`/`pythonpath.*src` before considering the slice done,
  not just the files this design anticipates.
- [Risk] Introducing `.pre-commit-config.yaml` for the first time may
  surprise contributors with new local friction. → [Mitigation] wire it to
  call the same `make` targets CI already runs, so "pre-commit passes"
  never diverges from "CI passes"; document install (`pre-commit install`)
  in the README as opt-in, not a hard gate outside CI.
- [Risk] Splitting into two independent Dockerfiles, both multistage where
  applicable, could change build behavior subtly (layer caching, image
  size) for channel-gateway or mcp. → [Mitigation] no non-goal here is
  deploying — build both images locally
  (`docker build -f infra/docker/channel-gateway/Dockerfile .`,
  `docker build -f infra/docker/mcp/Dockerfile .`) and diff the resulting
  image's file listing against the pre-change image before considering
  slice 7 done.

## Open Questions

None outstanding — all ambiguity was resolved during elicitation (appetite,
`/src` timing, docs/infra scope, proof scenarios, base branch, tox handling;
see [Elicitation record](../inputs/audit-and-elicitation.md#elicitation-record-qa)).
Any *new* ambiguity discovered during implementation gets parked here rather
than guessed past.

## References

| Topic | Location |
|---|---|
| Full gap audit (all detected dimensions) | [inputs/audit-and-elicitation.md#gap-report-detected-violations-only](../inputs/audit-and-elicitation.md#gap-report-detected-violations-only) |
| Elicitation Q&A that resolved every scope decision | [inputs/audit-and-elicitation.md#elicitation-record-qa](../inputs/audit-and-elicitation.md#elicitation-record-qa) |
| Test/verification specifications (GWT scenarios, one per proof requirement) | [specs/repository-tooling-standard/spec.md](specs/repository-tooling-standard/spec.md) |
| Ordered, checkbox-tracked task breakdown | [tasks.md](tasks.md) |
| Parent EPIC (appetite, DEC-1..6, no-gos) | [proposal.md](proposal.md) |
