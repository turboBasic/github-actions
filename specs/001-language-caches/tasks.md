# Tasks: Language Dependency Caches

**Input**: Design documents from `specs/001-language-caches/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`

**Tests**: Required by the accepted requirements in #114; add tests before implementation.

## Phase 1: Setup

**Purpose**: Record the approved policy change before its code depends on it.

- [x] T001 Mark `docs/decisions/0004-bound-a-ci-capability-by-the-component.md` superseded and add ADR 0005 in `docs/decisions/0005-cache-component-dependencies.md`.
- [x] T002 Update the capability language rule in `docs/ai-instructions.md` and cache behavior notes in `README.md`.

---

## Phase 2: Foundational

**Purpose**: Establish helper and workflow contract tests before cache behavior changes.

- [x] T003 [P] Add default path, directory creation, and `GITHUB_OUTPUT` tests in `tests/test_cache_paths.py`.
- [x] T004 [P] Update cache-input and stage-contract tests in `tests/test_workflow_properties.py`.
- [x] T005 [P] Add the `cache-paths` command to the expected CLI registry in `tests/test_cli_commands.py`.
- [x] T006 Add the six optional cache input names to `[project-ci].inputs` in `tests/published_surface.toml`.

**Checkpoint**: Contract expectations describe the new behavior while still pinning the existing check and task contract.

---

## Phase 3: User Story 1 - Reuse detected ecosystem caches (Priority: P1)

**Goal**: Restore and save only the package and build caches for ecosystems detected recursively in the checkout.

**Independent Test**: Workflow fixtures with each supported manifest verify only matching caches are enabled; a repository with no supported manifests has no language cache steps.

### Tests for User Story 1

- [x] T007 [US1] Add detection, nested-manifest, and no-manifest workflow assertions in `tests/test_workflow_properties.py`.
- [x] T008 [US1] Add native default and Cargo credential exclusion cases in `tests/test_cache_paths.py`.

### Implementation for User Story 1

- [x] T009 [US1] Implement ecosystem detection, native cache path resolution, and safe directory creation in `actions/tbga/cache_paths.py`.
- [x] T010 [US1] Dispatch `cache-paths` from `actions/tbga/__main__.py` and expose resolved paths/manifest presence through `GITHUB_OUTPUT`.
- [x] T011 [US1] Add conditional UV, Cargo registry/git/target, Go module/build, and npm cache steps to `.github/workflows/project-ci.yml`.

---

## Phase 4: User Story 2 - Override each cache location (Priority: P2)

**Goal**: Let callers redirect one cache location without changing other defaults.

**Independent Test**: Set a single cache path input and confirm only that output changes; empty inputs select defaults.

### Tests for User Story 2

- [x] T012 [US2] Add independent override and empty-input tests in `tests/test_cache_paths.py`.
- [x] T013 [US2] Assert the six optional workflow input names and defaults in `tests/test_workflow_properties.py` and `tests/published_surface.toml`.

### Implementation for User Story 2

- [x] T014 [US2] Declare the six optional workflow inputs and pass them to the resolver as environment values in `.github/workflows/project-ci.yml`.
- [x] T015 [US2] Apply each override independently in `actions/tbga/cache_paths.py` without putting caller paths on a command line.

---

## Phase 5: User Story 3 - Compatible, best-effort cache reuse (Priority: P1)

**Goal**: Partition cache data by platform/toolchain/dependencies and prevent cache failures from changing the task verdict.

**Independent Test**: Change OS, architecture, toolchain, and a lockfile independently; assert key isolation and compatible restore prefixes. Simulate missing paths and cache failures without skipping stages.

### Tests for User Story 3

- [x] T016 [US3] Add key-input, restore-prefix, cache-failure, and unchanged stage/check assertions in `tests/test_workflow_properties.py`.
- [x] T017 [US3] Add multi-workspace Cargo target path and environment-derived Go/UV/npm default cases in `tests/test_cache_paths.py`.

### Implementation for User Story 3

- [x] T018 [US3] Add OS, architecture, toolchain declaration, and ecosystem manifest inputs to cache keys and restore prefixes in `.github/workflows/project-ci.yml`.
- [x] T019 [US3] Keep every cache action best-effort and the existing stage conditions/check name unchanged in `.github/workflows/project-ci.yml`.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Verify the integrated contract and documentation.

- [x] T020 [P] Document automatic cache detection and direct consumers to the workflow's authoritative input list in `README.md`.
- [x] T021 Run the full pytest suite and Pyright for `actions/tbga/cache_paths.py` and `tests/test_cache_paths.py` through `mise run test` and `mise run typecheck`.
- [ ] T022 Run Prek's lint hooks and exercise cache miss/hit behavior for `.github/workflows/project-ci.yml` in `github-actions-test` using a PR ref.

## Dependencies & Execution Order

### Phase Dependencies

- **Setup**: Records the policy change before implementation.
- **Foundational**: Depends on Setup; tests and the published-surface fixture define the contract.
- **User Story 1**: Depends on the foundational assertions and delivers automatic cache selection.
- **User Story 2**: Builds on the resolved paths from User Story 1.
- **User Story 3**: Builds on the cache steps from User Story 1 and path handling from User Story 2.
- **Polish**: Local tests and typecheck are complete; lint and external consumer workflow exercise
  remain.

### User Story Dependencies

- **US1 (P1)**: Required MVP; provides detected defaults.
- **US2 (P2)**: Depends on US1's path resolver; adds individual caller overrides.
- **US3 (P1)**: Depends on US1/US2; adds verified reuse boundaries and best-effort behavior.

### Parallel Opportunities

- T003, T004, and T005 touch separate test files and can run in parallel.
- T007 and T008 touch separate test files and can run in parallel.
- T012 and T013 touch separate test files and can run in parallel.
- Different user stories cannot be implemented independently because they share `project-ci.yml` and the path resolver.

## Implementation Strategy

### MVP First

Complete Setup and Foundational, then US1 to restore/save detected caches using defaults. Continue through US2 and US3 before calling the feature complete because path overrides and cache safety are explicit requirements.

### Validation

Run targeted tests for `cache_paths.py` and workflow properties during implementation, then the repository CI entry point and the consumer scenarios in `quickstart.md`.
