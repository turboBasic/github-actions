---

description: "Task list template for feature implementation"
---

# Tasks: Self-checked commit-message workflow

**Input**: Design documents from `/specs/001-reuse-conventional-commits/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md),
[quickstart.md](./quickstart.md)

**Tests**: Included, but not as TDD. `tests/` here asserts properties of the YAML, and two existing
assertions couple to a filename this change deletes — so the test edits are not optional extras, they
are part of making each phase green.

**Organization**: Grouped by user story. Note the unusual shape: this feature cannot be fully verified
inside the repository, so the pull request is opened *during* User Story 1 rather than after
everything. Phases 3–5 each end with a check that only an open pull request can perform.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

Repository root. Workflows in `.github/workflows/`, tests in `tests/`, documentation in `docs/` and
`README.md`. No `src/` — this repository ships no application code.

---

## Phase 1: Setup

**Purpose**: Capture the state the change has to be reverted to, and establish that the branch is
green before anything is touched.

- [X] T001 Record the current required status checks as the rollback target, from
  `gh api repos/turboBasic/github-actions/rulesets/20657426`, into the pull request description draft
  at `tmp/pr-body.md` — expect exactly `CI` and `PR title`, both with `integration_id` 15368
- [X] T002 Establish the baseline with `mise run ci` on the branch tip, so any later failure is
  attributable to a task rather than pre-existing

---

## Phase 2: Foundational (Blocking Prerequisites)

**None.** This change adds no shared infrastructure, no schema, no base module — nothing that a later
phase would have to be built on top of. The phase is retained only to record that it was considered
and is empty; skip straight to Phase 3.

---

## Phase 3: User Story 1 - The workflow proves itself (Priority: P1) 🎯 MVP

**Goal**: `conventional-commits.yml` runs at the commit under review, so a defect in it fails the
pull request that introduces it. Closes the constitution principle VI gap.

**Independent Test**: T007 — break the workflow on the branch, watch this pull request fail, revert.
Deliverable on its own: at the end of this phase `semantic-pull-request.yml` still exists, so the
title is checked twice (once under each name). Redundant, temporary, and harmless.

### Implementation for User Story 1

- [X] T003 [US1] Create `.github/workflows/commit-messages.yml`: `on: pull_request` with
  `types: [opened, edited, reopened, synchronize]`, workflow-level `permissions: contents: read` and
  `pull-requests: read`, `concurrency` keyed on `${{ github.workflow }}-${{ github.head_ref }}` with
  `cancel-in-progress: true`, and a single job `commits` whose `uses:` is
  `./.github/workflows/conventional-commits.yml` with the same two permissions repeated at job level.
  Every permission line needs a trailing explanatory comment or `zizmor --pedantic` fails
  (`undocumented-permissions`, research R4). A header comment must state why the reference is
  relative — the `@v2` form resolves at the tag and would validate a change against the previous
  version of itself. No `timeout-minutes`: a calling job may not set it, and the callee defaults to 5
- [X] T004 [US1] In `tests/test_action_pins.py`, add `commit-messages.yml` to the caller exclusion set
  in `test_every_reusable_workflow_declares_workflow_call` (line ~65) — without this the new caller is
  swept as a reusable workflow and the test fails — and add a new test asserting the self-call is
  relative: the caller's `uses:` must be `./.github/workflows/conventional-commits.yml`, never a
  `turboBasic/github-actions/...@vN` form, which every existing gate would accept while silently
  restoring the staleness bug (research R8). Scope the new test to the caller only:
  `precommit-advisory.yml` references `turboBasic/github-actions/actions/precommit-advisory-pr@v2`
  deliberately
- [X] T005 [US1] Run `mise run ci` — `actionlint`, `zizmor --pedantic`, the workflow-timeout schema,
  `yamllint --strict` and `pytest` must all pass (all four were probed against this exact shape in
  research R5)
- [X] T006 [US1] Open the pull request with `gh pr create`, title in Conventional Commits form. Both
  `PR title` and `commits / PR title` should report — the old required check still exists at this point,
  so the pull request is not yet blocked
- [X] T007 [US1] Run quickstart Scenario 4 against the open pull request: push a break to
  `.github/workflows/conventional-commits.yml` (a `types` value containing a **dot**, e.g.
  `not.a.type` — *not* a value containing a space, as quickstart originally said: `tr -s '[:space:]'
  '\n'` splits on the space before the bare-word guard sees it, so `not a type` is accepted as three
  bare words. Corrected in quickstart.md by T020), confirm `commits / Commit messages` fails **and that the log names the
  broken value** — a pass here means the reference is resolving at a tag and the feature does not work
  — then revert the break and confirm the check goes green

**Checkpoint**: Principle VI closed. The workflow is now exercised by every pull request in this
repository at the commit under review.

---

## Phase 4: User Story 2 - One declaration of the allowed types (Priority: P2)

**Goal**: The allowed commit types are declared once, and no hand-written copy of either check
survives.

**Independent Test**: `rg -n 'refactor' .github/workflows/` returns exactly one match, the `types`
default in `conventional-commits.yml`; `rg -n 'pull_request_target' .github/` returns nothing.

### Implementation for User Story 2

- [X] T008 [US2] Delete `.github/workflows/semantic-pull-request.yml`, and with it the second copy of
  the allowed-types list and the repository's only `pull_request_target` trigger
- [X] T009 [US2] In `tests/test_action_pins.py`, remove `"semantic-pull-request.yml"` from the caller
  exclusion set (line ~65) and drop the `("semantic-pull-request.yml", "types")` case from
  `test_allowed_types_match_the_commitizen_builtin_set`'s parametrisation (line ~92), leaving the
  single `conventional-commits.yml` `default` case
- [X] T010 [US2] Remove the entire `dangerous-triggers` rule block from `.github/zizmor.yml`, leaving
  `unpinned-uses` as the only rule. Its justifying comment is factually wrong (a fork pull request's
  title *is* readable under `pull_request` — research R3) and the workflow it exempted no longer
  exists. Deleting a suppression rather than adding one is why this satisfies principle VII
- [X] T011 [US2] In `.github/workflows/ci.yml`, delete the `Check commit messages` step and its
  `if: github.event_name == 'pull_request'` guard, and drop `fetch-depth: 0` with its
  "cz check needs the full range" comment from the checkout — nothing else in that job reads git
  history, so leaving it makes the comment a lie about why a full clone is fetched (research R7)
- [X] T012 [US2] Run `mise run ci`, then push. The pull request does become **blocked** — but not for
  the reason predicted here. `PR title` *keeps reporting*: `semantic-pull-request.yml` triggers on
  `pull_request_target`, which resolves the workflow from the **base** branch, where the file survives
  until this merges. Measured on the head commit: all four checks green. The block is the ruleset's
  one-approving-review rule, unrelated to this change. Corrected in plan.md and quickstart.md

**Checkpoint**: One declaration of the types. No `pull_request_target` anywhere in the repository. The
pull request is green on every check that runs, and blocked on one that cannot.

---

## Phase 5: User Story 3 - No regression for a contributor (Priority: P3)

**Goal**: The same things are enforced before a merge as before the change, and a correction still
clears the check without a forced push.

**Independent Test**: T015 and T016 — both performed by editing the pull request title, with nothing
pushed.

### Implementation for User Story 3

- [X] T013 [US3] Confirm the check names on the open pull request with
  `gh pr checks` — expect `CI`, `commits / PR title` and `commits / Commit messages`. The `commits /`
  prefix is the calling job's id; if it reads otherwise, the job in
  `.github/workflows/commit-messages.yml` is misnamed
- [X] T014 [US3] Update ruleset `20657426` via
  `gh api --method PUT repos/turboBasic/github-actions/rulesets/20657426`: drop `PR title`, add
  `commits / PR title` and `commits / Commit messages`, keep `CI`, preserve `integration_id` 15368 and
  every other rule (squash-only, linear history, one approving review). This cannot be done in a
  commit and cannot be done before T013 — the new names must have reported at least once.
  **Applied.** Required contexts are now `CI`, `commits / PR title` and `commits / Commit messages`,
  with `integration_id` 15368 and the squash-only, linear-history and one-approval rules intact. The
  deadline was the merge: once `semantic-pull-request.yml` leaves `main`, `PR title` can never report
  again, and a ruleset still requiring it would block every subsequent pull request. Rolling this
  change back means restoring `PR title` and dropping the two new contexts by hand — the one step no
  revert commit performs
- [X] T015 [US3] Verify FR-005: edit the pull request title to something invalid without pushing
  anything, confirm `commits / PR title` re-runs and fails, correct it, confirm it re-runs and passes
- [X] T016 [US3] Verify FR-007: with a `CI` run in progress, edit the pull request title and confirm
  the `CI` run is neither restarted nor cancelled — the two workflows have separate `concurrency`
  groups and separate triggers

**Checkpoint**: All three stories verified against a real pull request.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: The documentation this change falsifies, and the final pass.

- [X] T017 [P] In `docs/ai-instructions.md`, change the workflow-table row (line ~93) from
  `{ci,semantic-pull-request}.yml` to `{ci,commit-messages}.yml`; rewrite the allowed-types bullet
  (line ~155) from two workflows to one; and rewrite the CI paragraph claiming this repository cannot
  call its own reusable workflows — the claim is true of the `@vN` form only, and the relative form
  that resolves at the caller's commit is now the repository's own practice
- [X] T018 [P] In `docs/consumers.md`, correct "Every other consumer grants `contents: read` and
  nothing more" — every consumer of `conventional-commits.yml` also grants `pull-requests: read`, as
  `python-app-baseline`'s call site shows, and without it the run dies as `startup_failure` before any
  job exists (research R4)
- [X] T019 [P] Verify `README.md` needs no edit: its canonical `conventional-commits.yml` call site
  (lines ~100-131) already documents the `pull_request` trigger and both `pull-requests: read` grants,
  which is now exactly what this repository's own caller does. Correct it only if it disagrees
- [X] T020 Run `mise run ci` and walk quickstart Scenarios 1–3 end to end as a final pass
- [ ] T021 Squash merge

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies
- **Foundational (Phase 2)**: empty
- **User Story 1 (Phase 3)**: depends on Setup. Blocks US2 and US3 — deleting the old checks before
  the new caller works would leave the repository with no commit-message enforcement at all
- **User Story 2 (Phase 4)**: depends on US1 through T006 (the pull request must exist)
- **User Story 3 (Phase 5)**: depends on US2 through T012 — the ruleset must not be edited until the
  old check is actually gone and the new ones have reported
- **Polish (Phase 6)**: T017 and T018 depend on US2 landing, since they describe its result

### Ordering constraint that is not a code dependency

T014 lives outside the repository. It cannot be committed, cannot precede T013, and must precede the
merge. It is also the one step that has to be reverted by hand if this change is rolled back.

### Within Each User Story

- The test edit accompanies the workflow change in the same task group, never after it — T004 exists
  because T003 breaks an existing test on its own
- Local gates (`mise run ci`) before any push
- Real-invocation verification last, and only it counts as verification

### Parallel Opportunities

- T017, T018 and T019 touch three different files with no shared content — genuinely parallel
- Nothing else is. T004 and T009 both edit `tests/test_action_pins.py`; T003 and T011 are ordered by
  the requirement that enforcement never lapses; T013–T016 are inherently sequential observations of
  one pull request

---

## Parallel Example: Phase 6

```bash
Task: "Correct the workflow table row and types bullet in docs/ai-instructions.md"
Task: "Correct the consumer permissions sentence in docs/consumers.md"
Task: "Verify the canonical call site in README.md still reads true"
```

---

## Implementation Strategy

### MVP

Phase 1 + Phase 3 (T001–T007). That is the whole point of the feature: the reusable workflow becomes
self-verifying. Everything after it is cleanup of what the new caller makes redundant, plus the
documentation and the ruleset catching up.

Stopping after Phase 3 leaves a working repository with one redundant check. Stopping after Phase 4
leaves a *blocked* pull request — Phase 5 is not optional once Phase 4 has landed.

### Incremental Delivery

1. Setup → baseline green, rollback target recorded
2. US1 → the workflow verifies itself; pull request open; the break test proves it
3. US2 → the duplication and the `pull_request_target` trigger go away
4. US3 → the ruleset catches up; contributor experience confirmed intact
5. Polish → documentation stops describing a structure that no longer exists

### Parallel Team Strategy

Not applicable. One branch, one pull request, one sequence of observations against it.

---

## Notes

- [P] tasks = different files, no dependencies
- Commit per task or per logical group; every commit message is itself checked by the workflow this
  change is about
- `mise run ci` before every push
- The only irreversible-by-commit step is T014, the ruleset edit
