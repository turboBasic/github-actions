---

description: "Task list for the declared consumer surface"
---

# Tasks: Declared Consumer Surface

**Input**: Design documents from `/specs/004-declared-consumer-surface/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md),
[data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md)

**Tests**: included, and not optional here — `docs/ai-instructions.md` makes pytest a gate, and FR-013
requires every decision be provable offline. Each task below is **one green commit**: its implementation
and the test that holds it land together, because a commit that deletes a constant the suite imports is
not green on its own.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel — different files, no dependency on an incomplete task
- **[Story]**: which user story the task serves (US1–US4)

## Path Conventions

This repository ships no application. Paths are real and there are only six files:
`actions/release-decisions/decisions.py`, `pyproject.toml`, `tests/test_release_decisions.py`,
`README.md`, `docs/consumers.md`, and one comment in `.github/workflows/release.yml`.

## A note on story independence

The four stories are independently **testable** and are not independently **shippable**: they share one
function in one module and arrive in one release. The checkpoints below verify each story's behaviour on
its own; they do not imply a release per story. US4 is also a **hard sequencing constraint** rather than a
free-standing increment — deleting the module constants without our own table in place puts this
repository's release on the unfiltered path, so those land in the same commit.

---

## Phase 1: Setup

**Purpose**: nothing to scaffold. One task, and it exists so SC-001 can be a byte comparison rather than an
argument.

- [x] T001 Capture today's rendered filter as fixture data for the byte-identical comparison: run `DECISION=surface-args python3 actions/release-decisions/decisions.py`, and record the exact output as the expected value of a new test in `tests/test_release_decisions.py` that currently passes against the constants. Per `docs/ai-instructions.md`, pre-flight the line out of the file rather than retyping it.

**Checkpoint**: the suite now pins the current behaviour, so every later task can be checked against it.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: the parse, the validation and the render. Every story needs all three.

**⚠️ CRITICAL**: no story phase can begin until T005 lands, because until then the surface still comes from
a constant.

- [x] T002 [P] Declare this repository's own surface in `pyproject.toml`: add `[tool.turbobasic-release]` with `surface-include` and `surface-exclude` reproducing exactly what the module's constants hold, per [data-model.md](./data-model.md#this-repositorys-own-declaration). Nothing reads it yet, so this commit is green on its own and is deliberately separate — it is the one file a reviewer should read closely.
- [x] T003 Add `SURFACE_TABLE` and `surface_config(raw: bytes) -> tuple[list[str], list[str]] | None` to `actions/release-decisions/decisions.py`, returning `None` for an absent table and raising with the key named for a mis-shaped value; with tests in `tests/test_release_decisions.py` for absent, declared, declared-empty, one key present and the other absent, a bare string where a list belongs, and a list holding a non-string.
- [x] T004 [P] Add `unusable_paths(paths: Iterable[str]) -> list[str]` to `actions/release-decisions/decisions.py`, returning every entry that is empty, holds whitespace, or begins with `-`, in declaration order; with tests in `tests/test_release_decisions.py` covering each of the five rejections in [data-model.md](./data-model.md#validation) plus a valid glob that must **not** be caught.
- [x] T005 Give `surface_args` the two lists as parameters, rewrite `_surface_args` to compose T003–T004 against the file `PYPROJECT` already names, and delete `SURFACE_INCLUDE`, `OWN_WORKFLOWS` and `SURFACE_EXCLUDE` from `actions/release-decisions/decisions.py`; in the same commit relocate `test_the_surface_exclusions_are_own_ci_as_workflow_paths` in `tests/test_release_decisions.py` to read `pyproject.toml`'s `surface-exclude`, and rewrite `test_the_surface_arguments_pair_every_path_with_its_flag` around the parameters. One commit because the suite imports the constants being deleted.

**Checkpoint**: `mise run ci` green, and T001's fixture still matches — the filter this repository renders
is unchanged (SC-001).

---

## Phase 3: User Story 4 - One definition for our list (Priority: P1) 🎯 gate

**Goal**: the `OWN_CI` equality survives the move intact, and the failure the move creates is caught.

**Independent Test**: edit `OWN_CI` alone, then our table alone, then delete our table — the suite fails
each time and names both sides.

Listed first among the stories because T005 already relocated the equality and this phase is what proves
the relocation is not a loosening (principle VII).

- [x] T006 [US4] Add a test in `tests/test_release_decisions.py` asserting `[tool.turbobasic-release]` is present in `pyproject.toml` at all, with a message naming the consequence — our own release silently going unfiltered and refusing over changes to `ci.yml`, which is what 003 fixed.
- [x] T007 [P] [US4] Verify the relocated gate fails as intended: temporarily add a workflow to `OWN_CI` in `tests/test_action_pins.py`, confirm the failure message names both sides, revert. Then temporarily delete the table from `pyproject.toml`, confirm T006 fires, revert. No commit of its own — the evidence goes in the PR description.

**Checkpoint**: SC-005 and SC-006 hold. Neither side of the equality can move alone, and neither can vanish.

---

## Phase 4: User Story 1 - Refuse on the caller's surface (Priority: P1) 🎯 MVP

**Goal**: a caller's declared surface is what its refusal is measured against.

**Independent Test**: with a `pyproject.toml` declaring `src/**`, the rendered filter names `src/**` and
nothing of ours.

- [x] T008 [US1] Add tests in `tests/test_release_decisions.py` driving `surface_config` and `surface_args` from a caller-shaped `pyproject.toml` — one declaring `src/**` with an exclusion — and asserting the rendered flags are exactly that caller's paths, include before exclude, flag before path.
- [x] T009 [US1] Add the `[tool.turbobasic-release]` table to `README.md`'s `release.yml` section: what a caller declares, the two keys, and a copyable example, replacing the paragraph that currently documents the miss in both directions as the workaround. Content is [contracts/config.md](./contracts/config.md); FR-012.

**Checkpoint**: a declared surface is used and documented. SC-007 answerable by reading `README.md` alone.

---

## Phase 5: User Story 2 - Stop refusing over files nobody resolves (Priority: P2)

**Goal**: no path of ours is added to a caller's declared surface, so no exclusion of ours can drop one of
its files by filename coincidence.

**Independent Test**: a caller declaring only `src/**` renders no `.github/workflows/**` include and no
`ci.yml` exclusion.

- [x] T010 [US2] Add a test in `tests/test_release_decisions.py` asserting a caller's declared surface is used alone — no path from this repository appears in the rendered flags, asserted by name against the six exclusions the constants used to hold, so the old name-coincidence behaviour cannot return unnoticed (FR-004).

**Checkpoint**: US1 and US2 both hold. The two directions #110 named are closed in the module.

---

## Phase 6: User Story 3 - Never guess a caller's surface (Priority: P1)

**Goal**: an undeclared surface is unfiltered and says so; a declared-empty one is unfiltered and silent.

**Independent Test**: a `pyproject.toml` with no table renders no flags and prints a notice; one with an
empty table renders no flags and prints nothing.

- [x] T011 [US3] Make `_surface_args` print a `::notice::` when `surface_config` returns `None`, naming the omission and where to declare a surface, and print nothing for a declared-empty table; with tests in `tests/test_release_decisions.py` asserting both states render no flags and that only the undeclared one is announced (FR-002, FR-003).

**Checkpoint**: all four stories hold offline. `mise run ci`, `mise run lint`, `mise run typecheck` green.

---

## Phase 7: Documentation & the record

- [x] T012 [P] Correct the stale comment on `release.yml`'s `Read the consumer-surface filter` step: it currently states the paths are deliberately not an input and points at #110 as owning that. Replace it with what is now true — the surface comes from the released repository's own `pyproject.toml`, and there is deliberately no input to override it (FR-010).
- [x] T013 [P] Record the obligation on `release.yml`'s callers in `docs/consumers.md`: `github-actions-test` declares its own surface, an undeclared caller gets the unfiltered range, and `release-decisions` still has no external caller (FR-012).
- [ ] T014 [P] Comment on [#110](https://github.com/turboBasic/github-actions/issues/110) recording that the input was rejected and why, linking [research.md D1](./research.md#d1), so the issue closes against a decision rather than against a different implementation.

**Checkpoint**: every document the change affects is correct in the same change, per
`docs/ai-instructions.md`.

---

## Phase 8: Verification by real invocation (Priority: P1 — principle VI)

**Purpose**: nothing above proves a caller's path. [quickstart.md](./quickstart.md) is the ladder; these are
its rungs as tasks.

- [x] T015 Run quickstart rungs 1–2 locally: the offline suite, then the filter rendered by hand from the file, plus the three rejection commands, confirming each names the offending value.
- [ ] T016 Run quickstart rung 3: dispatch `release.yml` with `dry-run: true` from this branch, and read the `Read the consumer-surface filter` and `Render the notes` step logs. This proves our path is unchanged, including that `read -ra` handles the flag line — the one shell behaviour no offline test covers.
- [ ] T017 Cut the release: merge, let `release-proposal.yml` open its proposal, and check the increment is a **minor** rather than accepting the number — a patch proposal would mean the surface filter is not seeing this change, which is itself a finding ([research.md D7](./research.md#d7)).
- [ ] T018 [US3] Run quickstart rung 4 in `github-actions-test` **before** it declares a surface: dispatch with `dry-run: true`, confirm the notice and an unfiltered refusal. This state disappears the moment T019 lands, so it is seen now or not at all (SC-003).
- [ ] T019 [US1] [US2] Run quickstart rung 5 in `github-actions-test`: add `[tool.turbobasic-release]` declaring `src/**`, then two dry-run dispatches — a breaking commit in `src/` under a non-major must be refused, and a breaking commit touching only its own workflows under a patch must proceed. Both directions, because either alone proves half of SC-002.
- [ ] T020 Run quickstart rung 6: a real release in `github-actions-test` with `dry-run` dropped. Confirm the tag, the release, the moved major tag, and that the notes describe the **whole** range rather than the filtered one (FR-011).

**Checkpoint**: SC-002 and SC-003 satisfied on real runs. The feature is verified, not merely linted.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: no dependencies. T001 must precede Phase 2 or SC-001 loses its baseline.
- **Phase 2 (Foundational)**: T002 is independent; T003 and T004 are independent of each other; **T005
  depends on T002, T003 and T004** and is the atomic commit that switches the source of truth.
- **Phases 3–6 (Stories)**: all depend on T005. Among themselves they are independent and may land in any
  order — Phase 3 is listed first only because it guards the sequencing constraint.
- **Phase 7 (Docs)**: T012 and T013 depend on Phases 3–6 being settled, since they describe the result.
  T014 depends only on the design being decided, so it can go at any point.
- **Phase 8 (Verification)**: T015–T016 depend on all of Phases 2–6. **T017 gates T018–T020**: a consumer
  can only exercise this at a released ref, since `github-actions-test` pins `@v4` and cannot resolve an
  unreleased commit.

### Within Each Task

Implementation and its test land together. There is no red-then-green step, because a commit that deletes a
constant the suite imports is not independently green — the repo's rule is one green commit per task, which
is stricter than TDD ordering here, not looser.

### Parallel Opportunities

- T002 ‖ T003 ‖ T004 — three different concerns, and T002 touches a different file entirely
- T012 ‖ T013 ‖ T014 — three different files, none reading the others
- T006 ‖ T007 — a test and a manual check of that test

Everything else is serial, and that is the honest shape: this is one module, one function, and roughly
sixty lines of change.

---

## Implementation Strategy

### The MVP is Phase 2 plus Phase 4

T001–T005 and T008–T009 give a caller a declared surface that is used and documented. Stories 2 and 3
harden it; Story 4 is the gate that keeps our own side honest and cannot be deferred past T005.

### The sequencing that is not negotiable

1. **T002 before T005.** Deleting the constants without our table in place puts this repository's own
   release on the unfiltered path, and it would start refusing over changes to `ci.yml`.
2. **T017 before T018.** `github-actions-test` resolves `@v4`; it cannot exercise an unreleased commit.
3. **T018 before T019.** Declaring a surface there destroys the undeclared state, and SC-003 requires it be
   observed on a real run.

### Stopping points

After Phase 6 the change is complete and provable offline, and is a reasonable place to open the pull
request. It is **not** a reasonable place to call the feature done: principle VI is explicit that a
reusable workflow whose behaviour depends on caller-side configuration is unverified until a consumer has
exercised it at the ref that consumer pins. Phase 8 is the difference between green and verified.

---

## Notes

- Every changed document is corrected in the same change, never deferred — stale framing is a defect.
- `git-cliff` path globs are passed through unaltered. An unusable one is refused, never repaired.
- The one place a concrete major may be written literally is `README.md`'s Versioning section. Nothing in
  this change touches it.
