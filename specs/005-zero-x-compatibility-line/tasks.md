---

description: "Task list for the 0.x compatibility line"
---

# Tasks: The 0.x Compatibility Line

**Input**: Design documents from `/specs/005-zero-x-compatibility-line/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md),
[contracts/decisions.md](./contracts/decisions.md), [quickstart.md](./quickstart.md)

**Tests**: included. Each task is **one green commit** — implementation and the tests holding it land
together, because renaming a function the suite imports is not green on its own.

## Format: `[ID] [P?] [Story] Description`

## Phase 1: Foundational

**Purpose**: the entity every other task reads. Nothing else can start until it exists.

- [x] T001 Add `compatibility_line(version)` to `actions/release-decisions/decisions.py`, returning `(major,)` from `1.0.0` up and `(major, minor)` below, with tests for `0.0.3`, `0.1.0`, `0.2.0`, `1.0.0` and `4.1.1` in `tests/test_release_decisions.py`.
- [x] T002 Add a test in `tests/test_release_decisions.py` asserting `major == 0` appears exactly once in the module, so the 0.x rule cannot be restated by a fourth reader. This is the design in [plan.md](./plan.md), and without it the three readers can drift apart.

**Checkpoint**: the line exists and is provably the only place the split lives.

---

## Phase 2: US1 — the refusal (P1) 🎯 MVP

**Goal**: the refusal fires when the ref this release would move already exists, and not otherwise.

**Independent Test**: every row of the table in [contracts/decisions.md](./contracts/decisions.md), the `0.2.1`-over-`0.2.0` row included.

- [x] T003 [US1] Replace `breaks_under_non_major` with `moves_a_ref_onto_a_break(version, highest, *, breaking)` in `actions/release-decisions/decisions.py`, comparing lines rather than majors; rename its four existing tests in `tests/test_release_decisions.py` keeping their cases verbatim as the above-0.x no-change evidence, and add the 0.x rows beside them. One commit: the suite imports the old name.
- [x] T004 [US1] Change `_verify_version` to output `highest-version` alongside `highest-major`, and `_check_notes` to read `HIGHEST_VERSION`, in `actions/release-decisions/decisions.py`; declare both in `actions/release-decisions/action.yml` and pass both from `release.yml`'s `check-notes` step. **Both, not one** — `release.yml` resolves as `$/` while the action resolves at `@v4`, so one release runs the new workflow against the old module, and passing only the new input would leave that module's refusal permanently false ([research.md D5](./research.md#d5)).

**Checkpoint**: SC-002 holds offline, and the interim window is closed rather than accepted.

---

## Phase 3: US2 — the increment (P1)

**Goal**: a breaking 0.x range is proposed as the next minor, not as `1.0.0`.

**Independent Test**: every row of the increment table.

- [x] T005 [US2] Change `next_version` in `actions/release-decisions/decisions.py` so a breaking range starts a new line and a feature never advances the minor under 0.x, with tests in `tests/test_release_decisions.py` for all four 0.x rows. Keep the existing `(4, 0, 3)` cases untouched — they are what proves nothing above 0.x moved (FR-007).
- [x] T006 [P] [US2] Add a test in `tests/test_release_decisions.py` pinning the consequence in [research.md D3](./research.md#d3): under 0.x a `feat` and a `fix` propose the same version while `increment_reason` still distinguishes them. Deliberate, so it is asserted rather than discovered.

**Checkpoint**: SC-003 holds, and the refusal and the proposal agree on what 0.x means.

---

## Phase 4: US3 — the moving ref (P2)

**Goal**: a release publishes the ref naming its line, and never `v0`.

**Independent Test**: `moving_tag` over the line table; no workflow spells a tag.

- [x] T007 [US3] Add `moving_tag(version)` to `actions/release-decisions/decisions.py` and output it from `_verify_version` as `moving-tag`, declaring the output in `actions/release-decisions/action.yml`, with tests in `tests/test_release_decisions.py` covering `v0.0`, `v0.1`, `v1`, `v4` and asserting no input ever yields `v0`.
- [x] T008 [US3] Replace `major="v${VERSION%%.*}"` in `.github/workflows/release.yml`'s tag step with the `moving-tag` output carried through `env`, updating the step's summary line and the comment that calls the `POST` fallback "a new major" rather than a new line (FR-006).
- [x] T009 [P] [US3] Add a test asserting no workflow composes a moving tag itself — no `%%.*` expansion over a version in `.github/workflows/*.yml` — so the name cannot drift back out of the module (SC-005).
- [x] T010 [P] [US3] Extend `test_tag_pattern_excludes_the_moving_major_tags` in `tests/test_release_notes.py` to reject `v0.1` as well as `v1`, `v2` and `v2.0`. The same assertion over a larger set: a moving ref that matched `tag_pattern` would become a range's lower bound and render empty notes (FR-009).

**Checkpoint**: SC-004 and SC-005 hold. All four stories provable offline.

---

## Phase 5: Documentation

- [x] T011 [P] Document in `README.md`'s Versioning section what a 0.x consumer pins and why it is `v0.1` rather than `v0` — without naming a concrete major outside the one sentence that owns that value, which `test_ai_instructions_names_no_concrete_major` and `test_readme_names_the_declared_major` both depend on.
- [x] T012 [P] Describe the 0.x increment in `CONTRIBUTING.md`'s Releasing section, beside the existing statement that the proposal is computed from surface-touching commits.

---

## Phase 6: Verification by real invocation (P1 — principle VI)

**Purpose**: the pure functions are covered offline; creating and force-moving a `v0.1` ref is not. [quickstart.md](./quickstart.md) is the route.

- [x] T013 Run quickstart rungs 1–2: the offline suite, then the decisions by hand out of the file.
- [x] T014 Cut the release here. Read the `Check the notes` step's env and confirm **both** `HIGHEST_MAJOR` and `HIGHEST_VERSION` are present and the first is not empty — that is the interim window of D5 being closed, and the one thing to check before trusting this release's own refusal.
- [x] T015 Reset `github-actions-test` per quickstart rung 4: delete all five releases, delete all eight tags, rewrite `main` to its functional commits — dropping the release bumps and the two `004` probes but keeping the surface table — and set `[project].version = 0.1.0`. No ruleset change is needed: it has no tag ruleset, and its `main` ruleset already bypasses for the Repository admin role.
- [x] T016 [US3] Rung 5a: the reset push itself releases `0.1.0`. Confirm `v0.1.0` **and `v0.1`**, and that **no `v0` exists** — this is where `v0` would appear if the tag name were still a shell expansion.
- [x] T017 [US3] Rung 5b: land a `fix:` and release `0.1.1`. Confirm `v0.1` now resolves to it — the moving ref moving within its line.
- [x] T018 [US1] Rung 5c: land a `feat!:` touching `src/` and declare `0.1.2`. Confirm it is **refused** and no tag exists. The pass condition is the job going red.
- [x] T019 [US1] [US2] Rung 5d: declare `0.2.0` over the same range. Confirm it **proceeds**, `v0.2` is created and `v0.1` still resolves to `0.1.1`. This is the defect #107 was filed about, and rung 5c before it is what makes it evidence rather than a coincidence.
- [~] T020 **Not run, deliberately** [US2] Rung 6: check what `release-proposal.yml` offered for 5c's breaking range — it must be `0.2.0`, not `1.0.0` — and that a non-breaking `feat` under 0.x is proposed as a patch.
- [~] T021 **Not run, deliberately** Rung 7: release `1.0.0` over a breaking range. Confirm it proceeds, `v1.0.0` and `v1` are created, and `v0.2` is left where it is — the line comparison handling a régime change rather than each régime alone.

---

## Phase 7: Close out

- [x] T022 Remove `highest-major` from `actions/release-decisions/action.yml`, from `_verify_version`'s outputs and from `release.yml`'s `check-notes` step, **only after T014 has moved `v4`**. Until then it is what keeps the old module's refusal working; after, it is a second value describing one fact, and the one that is wrong under 0.x.
- [x] T023 [P] Fill in quickstart's Outcome section with the run or PR each rung is evidenced by, and tick this list.

---

## Dependencies

- **T001 blocks everything.** T002 needs T001.
- **T003–T004** (refusal), **T005–T006** (increment) and **T007–T010** (moving ref) are independent of each
  other once T001 lands, and may go in any order.
- **T014 gates T015–T021**: `github-actions-test` resolves `@v4` and cannot see an unreleased commit.
- **T015 gates T016.** A single leftover `vN.N.N` tag makes every 0.x version not-ahead.
- **T018 gates T019.** The same range must be refused and then released; reversing them proves nothing.
- **T022 depends on T014**, and is deliberately last — doing it earlier reopens D5's window.

### Parallel opportunities

T006 ‖ T009 ‖ T010 ‖ T011 ‖ T012 — different files, none reading the others. Everything else is serial,
which is the honest shape of a change to one module.

## Implementation Strategy

**MVP is Phase 1 plus Phase 2**: the refusal becomes correct. Phase 3 makes it reachable, Phase 4 makes it
safe to allow. Shipping Phase 2 alone would allow `0.2.0` and then force-move `v0` onto it, which is worse
than the defect — so Phase 4 is not optional and Phase 2 must not be released without it.

**Stopping point**: after Phase 5 the change is complete and provable offline, and is where the pull request
opens. It is not where the feature is done — principle VI is explicit, and Phase 6 is the difference between
green and verified.

## Notes

- No behaviour at or above `1.0.0` may change. Where an existing test covers that, it is kept verbatim
  rather than rewritten, so a regression above 0.x fails an assertion that predates this change.
- `docs/consumers.md` needs no edit: no consumer's row moves, and both consumers are `1.x`+.

`[~]` marks a task deliberately not run, with the reason in [quickstart.md](./quickstart.md)'s Outcome:
T020 because the test consumer has no `release-proposal.yml` to exercise, T021 because releasing `1.0.0`
there would destroy the only repository able to exercise the 0.x path at all.
