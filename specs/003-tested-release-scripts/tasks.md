---

description: "Task list for tested release scripts"
---

# Tasks: Tested Release Scripts

**Input**: Design documents from `/specs/003-tested-release-scripts/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md),
[data-model.md](./data-model.md), [contracts/](./contracts/)

**Tests**: Included, and not optional here. The feature's entire purpose is that this logic becomes
testable, so a test task that does not exist is a requirement that did not ship.

**Two stages, two releases.** Forced by [research.md D9](./research.md#d9), not chosen: `release.yml`'s
`uses: …@v4` cannot resolve until a release exists whose tree contains the action, and pinning a branch
instead fails `test_first_party_actions_use_the_major_tag`. Stage 1 is Phases 1–6; stage 2 is Phases 7–8.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: no ordering constraint against its neighbours and a different file, so it can be batched
- **[Story]**: US1, US2, US3, mapping to the spec's user stories
- Exact file paths in every description

## Path Conventions

Repository layout is load-bearing and is not the template's default. Per
[plan.md](./plan.md#source-code-repository-root):

- `actions/release-decisions/` — the logic, reachable from a cross-repo caller
- `.github/workflows/` — the two workflows being thinned
- `tests/` — the offline suite; there is no `src/`

---

## Stage 1 — the action and `release-proposal.yml`

Adds no `uses:`, so nothing resolves `@v4` and nothing can deadlock.

### Phase 1: Setup (Shared Infrastructure)

- [X] T001 Add `pythonpath = ["actions/release-decisions"]` under `[tool.pytest.ini_options]` and
      `extraPaths = ["actions/release-decisions"]` under `[tool.pyright]` in `pyproject.toml` — the two
      lines that make the module importable by the suite with no path shim in a test file (FR-012)
- [X] T002 [P] Create `actions/release-decisions/action.yml` declaring only the required `decision`
      input and a `python3` run step, per [contracts/action.md](./contracts/action.md) — no logic yet

**Verified in [research.md D2](./research.md#d2)**: nothing else in `pyproject.toml` changes.
`[tool.ruff].src` and `[tool.pyright].include` already list `actions`, and `mise.toml`'s `lint` task
already globs `actions/*/action.yml` for `check-jsonschema` and passes `actions` to `zizmor`.

---

### Phase 2: Foundational (Blocking Prerequisites)

**⚠️ CRITICAL**: no user story work begins until T005 passes.

- [X] T003 Create `actions/release-decisions/decisions.py` holding only the `ReleaseVerdict` result type
      (`proceed`, `severity`, `message`) per [data-model.md](./data-model.md#releaseverdict) — full type
      hints, no docstring
- [X] T004 [P] Add `test_the_release_job_names_are_pinned` to `tests/test_action_pins.py` asserting
      `release.yml`'s job name is `tag-and-publish` and `release-proposal.yml`'s is `propose` — passes
      immediately, and fails the moment a rename retires the required check `github-actions-test` reports
      (FR-009a, SC-008)
- [X] T005 Run `mise run lint` and `mise run typecheck` to confirm the empty module and `action.yml` are
      picked up clean by the existing gates, pyright strict, no suppression (FR-013)

---

### Phase 3: User Story 1 - Prove a release decision offline (Priority: P1) 🎯 MVP

**Goal**: every decision the release path makes becomes a pure function with a test, reachable without
GitHub. No workflow is rewired; both keep their shell and keep working.

**Independent Test**: `mise run ci` green offline, with `tests/test_release_decisions.py` covering every
invariant in [contracts/decisions.md](./contracts/decisions.md). Shippable on its own.

### Tests for User Story 1 ⚠️

> Write these first and confirm they fail. All land in one file, so none carries `[P]` — same-file tasks
> are ordered even when logically independent.

- [X] T006 [US1] Create `tests/test_release_decisions.py` with tests for `next_version` and
      `increment_reason`: breaking → next major zeroed, feature → next minor zeroed, neither → next
      patch, and breaking winning when both verdicts are true (AS-1, AS-2, AS-3, FR-001)
- [X] T007 [US1] Add tests for `notes_are_empty` in `tests/test_release_decisions.py`. **One test name
      must contain `one_byte`** — `quickstart.md` rung 1 filters on it — covering the lone-newline render,
      plus `""` and a body with a word being non-empty (AS-4, SC-002, FR-002)
- [X] T008 [US1] Add tests for `verdicts` in `tests/test_release_decisions.py`. **One test name must
      contain `absent_breaking`**, asserting a payload whose commits carry no `breaking` key yields
      `False`, plus one proving the key is read as identity against `true` rather than truthiness
      (AS-5, SC-002, FR-005)
- [X] T009 [US1] Add tests for `parse_version`, `highest_version` and `is_ahead` in
      `tests/test_release_decisions.py`: `4.0`, `v4.0.3`, `4.0.3rc1` and `4.0.3+1` are rejected; an empty
      tag set gives `None` and `is_ahead(v, None)` is `True`; ordering is component-wise so `4.10.0` beats
      `4.9.0`; the highest spans majors (FR-004(a), FR-004(b), spec Edge Cases)
- [X] T010 [US1] Add tests for `breaks_under_non_major` in `tests/test_release_decisions.py` — FR-004's
      **third** comparison, which had no function before this: same major plus breaking is `True`, a new
      major is `False`, a `None` highest major is `False`, and a non-breaking range is always `False`
      (FR-004(c), SC-001)
- [X] T011 [US1] Add tests for `declared_version` in `tests/test_release_decisions.py` proving it reads
      the `[project]` table rather than the first `version =` line, using a fixture whose earlier table
      also carries a `version` key (FR-003)
- [X] T012 [US1] Add tests for `release_verdict` in `tests/test_release_decisions.py` covering all three
      severities: notice with `proceed=false` on `push`, notice-and-continue on a dry run, error on a real
      dispatch (FR-010, [data-model.md](./data-model.md#releaseverdict) state table)
- [X] T013 [US1] Add `test_the_decisions_module_imports_only_the_standard_library` to
      `tests/test_release_decisions.py`, walking `decisions.py`'s module-level imports — this is what keeps
      `mise run ci` offline (FR-014)

### Implementation for User Story 1

- [X] T014 [US1] Implement `parse_version`, `highest_version` and `is_ahead` in
      `actions/release-decisions/decisions.py`
- [X] T015 [US1] Implement `next_version` and `increment_reason` in
      `actions/release-decisions/decisions.py`
- [X] T016 [US1] Implement `notes_are_empty` in `actions/release-decisions/decisions.py` — content test,
      never size, never exit code
- [X] T017 [US1] Implement `verdicts` in `actions/release-decisions/decisions.py` using `json`
- [X] T018 [US1] Implement `breaks_under_non_major` in `actions/release-decisions/decisions.py`
- [X] T019 [US1] Implement `declared_version` in `actions/release-decisions/decisions.py` using `tomllib`
- [X] T020 [US1] Implement `release_verdict` in `actions/release-decisions/decisions.py`
- [X] T021 [US1] Run `mise run ci` and confirm green, offline, pyright strict clean, no suppression added
      (SC-001, SC-005)

**Checkpoint**: US1 complete and shippable. Both workflows still run their original shell.

---

### Phase 4: User Story 3 - One definition of the consumer surface (Priority: P3)

**Executed before US2 despite its lower priority**, because the constant is module content and stage 1 must
ship the action complete. Priority orders value, not execution.

**Independent Test**: a disagreement between the constant and `OWN_CI` fails a test naming both lists.

- [X] T022 [US3] Add `SURFACE_INCLUDE`, `SURFACE_EXCLUDE` and `surface_args()` to
      `actions/release-decisions/decisions.py`, deriving the exclusions from the workflow names rather
      than restating them (FR-006)
- [X] T023 [US3] Add a test to `tests/test_release_decisions.py` asserting `SURFACE_EXCLUDE` equals
      `OWN_CI` mapped to workflow paths, with a failure message naming both lists (SC-004, US3 AS-2)

---

### Phase 5: User Story 2a - `release-proposal.yml` (Priority: P2)

**Goal**: the workflow with no callers stops holding logic, and the action becomes complete.

**Depends on US1 and US3.** Not independently orderable.

- [ ] T024 [US2] Add the `__main__` dispatch to `actions/release-decisions/decisions.py`: read every
      argument from the environment, branch on `decision` across **all three** values, write results to
      `GITHUB_OUTPUT`, emit `::notice::`/`::error::`, exit non-zero only to refuse, per
      [contracts/action.md](./contracts/action.md). Every argument arrives through `env`; no `${{ }}`
      reaches a script argument or a shell line (FR-011, Principle IV)
- [ ] T025 [US2] Complete `actions/release-decisions/action.yml`: declare every input from the contract
      with a `description` and explicit `default`, map each to `env`, declare the outputs. Ships
      `verify-version` and `check-notes` too, though only stage 2 calls them — otherwise stage 2's branch
      and `@v4` would hold different code
- [ ] T026 [US2] Replace `release-proposal.yml`'s "Decide whether a proposal is wanted" and "Decide the
      version" logic with `python3` invocations of `actions/release-decisions/decisions.py` by in-repo
      path, keeping `gh api`, `gh pr` and `uv version` as shell (FR-007). **No `uses:`** — that is what
      keeps stage 1 free of the deadlock
- [ ] T027 [US2] Remove the surface argument array from `.github/workflows/release-proposal.yml`, taking
      it from `surface_args()` instead (FR-006)
- [ ] T028 [US2] Rewrite `test_the_surface_filter_agrees_with_own_ci` in `tests/test_release_notes.py` to
      import `SURFACE_EXCLUDE` and compare it to `OWN_CI` directly, and retire the `SURFACE_FILTERED`
      parametrization — it breaks here for `release-proposal.yml` and again in stage 2 (FR-017, D6)
- [ ] T029 [US2] Cut the comments in `release-proposal.yml` that narrate an incident, keeping those that
      state a rule; move any rule a test can hold into a test name instead
- [ ] T030 [US2] Diff every `release-proposal.yml` refusal and notice against its pre-change wording and
      confirm each says the same thing (FR-010)

---

### Phase 6: Stage-1 verification, documentation and release

- [ ] T031 Run quickstart rung 1 against `mise run ci`, including
      `uv run pytest tests/test_release_decisions.py -k "one_byte or absent_breaking" -v` and a check that
      `test_first_party_actions_use_the_major_tag` is unmodified and green (SC-001, SC-002, SC-005, SC-010)
- [ ] T032 Confirm no gate from
      [contracts/decisions.md](./contracts/decisions.md#existing-tests-this-change-breaks) is left failing
      or silently deleted — at this stage only `test_the_surface_filter_agrees_with_own_ci` should have
      moved (FR-017, SC-011)
- [ ] T033 Run quickstart rung 2: dispatch `.github/workflows/release-proposal.yml` from the stage-1
      branch, confirm the increment matches what the old shell proposed for the same range, then **tear
      down** the `release-proposal` branch and its pull request
- [ ] T034 Correct `docs/ai-instructions.md`'s "This repo ships no application code — the Python here
      exists to test the YAML", which this change falsifies (FR-016)
- [ ] T035 [P] Add `release-decisions` to `README.md`'s composite actions list
- [ ] T036 [P] Confirm `docs/consumers.md` still reads true — `github-actions-test` calls `release` at
      `@v4`, unchanged by stage 1
- [ ] T037 Merge stage 1 and let `ci.yml` cut its release. `release.yml` is untouched here, so the old
      shell cuts it — which is what makes this safe (quickstart rung 3)
- [ ] T038 Confirm `@v4` now contains the action before starting stage 2:
      `gh api repos/turboBasic/github-actions/contents/actions/release-decisions/action.yml?ref=v4`.
      **A 404 blocks stage 2 entirely**

---

## Stage 2 — `release.yml`

`@v4` now contains the action, so `uses:` resolves from a branch as well as from `main`.

### Phase 7: User Story 2b - `release.yml` (Priority: P2)

- [ ] T039 [US2] Replace `release.yml`'s "Verify the release" logic with a `uses:` of
      `turboBasic/github-actions/actions/release-decisions@v4` at `decision: verify-version`, keeping the
      `gh api` matching-refs call as shell — **and keeping the `workflow_dispatch`-only check-runs query
      for `"ci / python-ci"` as shell**, because `test_the_release_gates_on_a_required_context` asserts
      that literal is in this file (FR-007)
- [ ] T040 [US2] Replace `release.yml`'s emptiness and breaking-under-a-non-major refusals with a `uses:`
      at `decision: check-notes`, keeping both `git-cliff` invocations as shell
- [ ] T041 [US2] Remove the surface argument array from `.github/workflows/release.yml`, taking it from
      `surface_args()` instead, and confirm the two range reads stay distinct — whole range for the notes,
      filtered for the refusal (FR-006, US3 AS-3)
- [ ] T042 [US2] Rewrite `test_the_release_refuses_notes_with_no_content` in `tests/test_action_pins.py`:
      the literal `[^[:space:]]` no longer appears in `release.yml`, so it must assert the `check-notes`
      invocation instead, with `notes_are_empty`'s own tests now carrying the rule (FR-017)
- [ ] T043 [US2] Rewrite `_surface_flags` and
      `test_only_a_breaking_change_to_the_surface_refuses_a_release` in `tests/test_release_notes.py` to
      take flags from `surface_args()` rather than scraping workflow text. Left alone it hard-fails, since
      empty flags make its second assertion `not _breaking(unfiltered)` (FR-017)
- [ ] T044 [US2] Extend the `SURFACE_FILTERED` retirement from T028 to `release.yml` in
      `tests/test_release_notes.py` (FR-017)
- [ ] T045 [US2] Add a guard to `tests/test_release_notes.py` asserting no `run:` block in either workflow
      holds a comparison, an arithmetic increment, a version parse, or a `jq` filter over commit data
      (SC-003, US2 AS-1)
- [ ] T046 [US2] Add a guard to `tests/test_release_notes.py` asserting neither workflow contains an
      `--include-path` or `--exclude-path` flag (SC-004, US3 AS-1)
- [ ] T047 [US2] Add a guard to `tests/test_action_pins.py` asserting both workflows' `workflow_call`
      inputs and job `permissions` blocks are unchanged from stage 0 — the interface FR-009 freezes
- [ ] T048 [US2] Cut the comments in `release.yml` that narrate an incident, keeping those that state a
      rule
- [ ] T049 [US2] Diff every `release.yml` refusal against its pre-change wording (FR-010, US2 AS-2)

---

### Phase 8: Stage-2 verification and release

- [ ] T050 Run `mise run ci` and confirm green — including that
      `test_first_party_actions_use_the_major_tag` still passes unmodified with the new `@v4` reference in
      `release.yml` (SC-005, SC-010)
- [ ] T051 Run quickstart rung 4: dispatch `.github/workflows/release.yml` with `dry-run=true` from the
      stage-2 branch; confirm the not-ahead case reports as a **notice**, the notes render to the step
      summary, and nothing is created (SC-006). Read the summary in a browser — no `gh` or REST route
      reaches it
- [ ] T052 Run quickstart rung 5: repoint `github-actions-test`'s `release` job at the stage-2 branch, bump
      its `[project].version`, merge there, and confirm a release is published, `v0` moves, and
      `release / tag-and-publish` reports under that exact name (SC-007, SC-008). Only the consumer is
      repointed — nothing here is pinned, so SC-010 holds
- [ ] T053 Revert `github-actions-test`'s `release` job to `@v4`
- [ ] T054 Confirm every FR-017 gate now asserts the new form or is gone with its reason recorded, and none
      is left failing (SC-011)
- [ ] T055 Merge stage 2 and watch `ci.yml` cut the first release under the new `release.yml`
      (quickstart rung 6). Recovery from a bad release is a bump to the next patch, never a re-run

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 Setup**: no dependencies
- **Phase 2 Foundational**: needs Phase 1. Blocks every story
- **Phase 3 US1**: needs Phase 2
- **Phase 4 US3**: needs US1 — the constant is module content
- **Phase 5 US2a**: needs US1 and US3
- **Phase 6 stage-1 release**: needs Phases 1–5. **T038 is a hard gate on stage 2**
- **Phase 7 US2b**: needs T038 to have returned `action.yml`, not a 404
- **Phase 8 stage-2 release**: needs Phase 7, and its tasks are strictly ordered

### An honest note on story independence

The template assumes stories can be built in any order by different people. **These cannot.** They are
layers of one refactor: US1 the logic, US3 the shared constant, US2 the wiring — and US2 is itself split
across two releases by a mechanical constraint. Each is independently *testable*: every phase ends green
with its own failing-then-passing test, which is what the spec's Independent Test lines claim. Only US1 is
independently *deliverable*.

Execution order deviates from priority order — US3 before US2 — because stage 1 must ship the action
complete. Priority orders value; this orders work.

### Parallel Opportunities

Thin, and that is the honest answer for a single-maintainer refactor of two files.

- T002 alongside T001, and T004 alongside T003 — different files
- T035 and T036 together — different documents, neither touching code
- Nothing in US1's test block is `[P]`: all eight tasks write `tests/test_release_decisions.py`
- Nothing in Phases 5, 7 or 8 is `[P]`: they serialise on the two workflows, `decisions.py`, and two test
  files

---

## Parallel Example: Phases 1 and 2

```bash
# The only genuine batches in this feature — different files, no ordering constraint:
Task: "T001 Add pythonpath and extraPaths to pyproject.toml"
Task: "T002 Create actions/release-decisions/action.yml with the decision input"

Task: "T003 Create actions/release-decisions/decisions.py with the ReleaseVerdict type"
Task: "T004 Add test_the_release_job_names_are_pinned to tests/test_action_pins.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 only)

1. Phase 1 Setup — two config lines and an `action.yml` stub
2. Phase 2 Foundational — the module, the result type, the job-name guard
3. Phase 3 US1 — every decision as a tested pure function, including FR-004's third comparison
4. **STOP and VALIDATE**: `mise run ci` green offline; both workflows untouched and still working
5. Shippable on its own

### Incremental Delivery

1. Phases 1–2 → an importable module resolves under pyright strict
2. Phase 3 US1 → the logic is tested → **ship here if the appetite runs out**
3. Phase 4 US3 → one surface definition, held to `OWN_CI` by import
4. Phase 5 US2a → `release-proposal.yml` reads as plumbing
5. Phase 6 → verify, document, **release stage 1**, confirm `@v4` carries the action
6. Phases 7–8 → `release.yml`, verified on disposable tags, then released

### Where the risk actually is

Not in the Python. In three places:

- **T038.** A 404 there means stage 1 did not actually ship the action, and every stage-2 task fails at
  workflow startup with no job and no log
- **T052 before T055.** `ci.yml` resolves `release.yml` at the merge commit, so merging stage 2 runs new
  code against tags a ruleset makes undeletable. `github-actions-test`'s cost nothing
- **T042, T043, T044.** Three existing gates break in stage 2. T043's fails loudly; the danger is
  responding to a red suite by deleting a guard rather than rewriting it (Principle VII, FR-017)

---

## Notes

- **Three requirements carry no task, deliberately.** FR-008 (four files untouched), FR-015
  (`[project].dependencies` stays empty) and SC-009 (a step's decisions are nameable) are reviewer
  discipline, not tooling. They are listed here so nobody mistakes them for covered
- Every task names a file. A task that cannot name one is not a task
- Commit per task or per logical group; every phase boundary is a green commit
- No docstrings, no multi-line comment blocks; comments only where the WHY is non-obvious
- State the rule, not the incident that taught it — in the new code's comments as much as in the docs
- The suite stays offline. Nothing added here carries the `drift` marker
- **Nothing is ever pinned to a branch in this repository, and no gate is relaxed** (FR-018, SC-010)
