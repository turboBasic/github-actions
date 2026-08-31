# Feature Specification: Self-checked commit-message workflow

**Feature Branch**: `001-reuse-conventional-commits`

**Created**: 2026-08-31

**Status**: Draft

**Input**: User description: "Replace this repo's two hand-written commit-message checks with a same-commit call to its own conventional-commits.yml. ci.yml calls ./.github/workflows/conventional-commits.yml (relative ref → resolves at the caller's commit, so a broken change to it fails its own PR); the inline cz check step in ci.yml and the whole semantic-pull-request.yml file go away, and with them the second copy of the allowed-types list. Out of scope: any change to conventional-commits.yml's inputs."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The workflow proves itself (Priority: P1)

A maintainer edits the workflow that other repositories rely on to check their commit messages. Today
nothing in this repository runs that workflow, so the edit reaches a release tag having never
executed: the only signal was lint, which passes on a workflow no caller can run. After this change,
the maintainer's own pull request runs the workflow as it stands in that pull request, and a mistake
in it fails the pull request that introduced it.

**Why this priority**: This is the point of the feature. The repository's constitution treats a
reusable workflow as unverified until a real pull request has exercised it, and this workflow is the
one gap where that is achievable at zero infrastructure cost. Everything else here is a consequence.

**Independent Test**: On a branch, break the workflow (an invalid types value, a malformed generated
schema) and open a pull request. The pull request must fail. Revert the break and it must pass.

**Acceptance Scenarios**:

1. **Given** a pull request that changes the commit-message workflow, **When** its checks run,
   **Then** the version of the workflow under review is the version that executes — not the version
   at the last release tag.
2. **Given** a pull request that breaks the commit-message workflow, **When** its checks run,
   **Then** that pull request reports a failure.
3. **Given** a pull request that does not touch the workflow, **When** its checks run, **Then** the
   commit-message verdicts are the same as before this change.

---

### User Story 2 - One declaration of what commit types are allowed (Priority: P2)

A maintainer adds or removes an allowed commit type. Today the list is written out twice, in two
workflow files, and a test exists solely to catch the two copies disagreeing with each other and
with the tool that enforces them locally. After this change there is one copy, and editing it cannot
leave a second copy behind.

**Why this priority**: Real but secondary — the duplication is currently guarded, so it is a
maintenance cost rather than an active defect. It becomes free to remove once User Story 1 lands.

**Independent Test**: Search the repository for the allowed-types list and find exactly one
declaration outside the tests.

**Acceptance Scenarios**:

1. **Given** the repository after this change, **When** the allowed commit types are searched for,
   **Then** exactly one workflow declares them.
2. **Given** a change to that one declaration, **When** the test suite runs, **Then** any
   disagreement with the locally enforced set is still reported as a failure.

---

### User Story 3 - A contributor sees no change in what is enforced (Priority: P3)

A contributor opens a pull request with a bad title or a bad commit message. They are told, before
merge, by a named check, exactly as they were before this change. Fixing the problem clears the
check.

**Why this priority**: This is a no-regression requirement rather than new value, but it is the
constraint that decides the shape of the implementation.

**Independent Test**: Open a pull request with a non-conforming title, then correct the title; open
one with a non-conforming commit message, then amend it. Both must fail and then pass.

**Acceptance Scenarios**:

1. **Given** a pull request whose title is not a valid Conventional Commit, **When** its checks run,
   **Then** a check fails and names the title as the cause.
2. **Given** that pull request, **When** the contributor corrects the title and changes nothing else,
   **Then** the title check runs again and passes.
3. **Given** a pull request containing a commit message that is not a valid Conventional Commit,
   **When** its checks run, **Then** a check fails and names the commit.
4. **Given** a pull request opened from a fork, **When** its checks run, **Then** the title and the
   commit messages are still both checked.

---

### Edge Cases

- **A title corrected after the pull request was opened.** The existing title check re-runs when a
  title is edited; the existing repository-wide checks do not. The commit-message checks therefore
  keep their own trigger rather than joining the repository-wide ones, so that an edit re-checks the
  title in seconds without re-running lint, type checking and tests, and without cancelling a
  repository-wide run already in flight.
- **A fork's pull request.** The check must work with the reduced token a fork's pull request gets.
  Read access to pull requests is available there, which is all the title check needs.
- **A push to the default branch, with no pull request.** The called workflow's jobs are gated on
  the pull request event, so they are skipped rather than failed. No verdict is expected or lost.
- **The required status checks in branch protection.** Routing a check through a call renames it to
  `<calling job> / <called job>`. A required check under the old name stops reporting and blocks
  every merge until branch protection is updated.
- **A test that enumerates workflow files by name.** At least one test keeps a by-name list of the
  workflows that are callers rather than reusable workflows, and requires everything else to be
  callable. A caller that is renamed, added or deleted without that list being updated turns into a
  false failure.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The repository MUST check the pull request title and every commit message in the pull
  request range through its own reusable commit-message workflow, referenced so that the version
  under review is the version that runs.
- **FR-002**: A defect introduced into that workflow MUST fail the pull request that introduces it.
- **FR-003**: The repository MUST NOT retain a second, hand-written implementation of either check.
- **FR-004**: The allowed commit types MUST be declared in exactly one place, and the test that
  holds that declaration equal to the locally enforced set MUST still fail when they diverge.
- **FR-005**: A pull request title corrected after the pull request is opened MUST be re-checked
  without the contributor having to push a commit or ask for a re-run.
- **FR-006**: The checks MUST return a verdict on pull requests opened from forks.
- **FR-007**: The commit-message checks MUST be triggered independently of the repository-wide
  checks, so that re-checking an edited title neither re-runs lint, type checking and tests nor
  cancels a repository-wide run already in progress.
- **FR-008**: No workflow in the repository MUST request a permission it does not need in order to
  satisfy FR-001 — in particular, the title check needs only read access to pull requests.
- **FR-009**: The change MUST state the new names of the checks that branch protection requires, so
  that branch protection can be updated as part of the same landing.
- **FR-010**: The documentation that describes the removed duplication MUST be corrected in the same
  change as the code, not left describing a structure that no longer exists.
- **FR-011**: The repository's own quality gates MUST pass unchanged — no test deleted, no rule
  disabled, and no linter finding silenced, to accommodate the new structure.

### Key Entities

- **Commit-message workflow**: the repository's own reusable workflow that checks a pull request
  title and the commit messages in its range, and that carries the authoritative list of allowed
  commit types. Its input contract is out of scope here.
- **Same-commit reference**: a reference from one workflow in this repository to another that
  resolves at the commit being tested, rather than at a release tag. This is what makes the workflow
  verify itself.
- **Allowed types list**: the set of commit types the repository accepts, enforced identically by
  the local commit hook, the title check and the commit check.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A deliberate defect in the commit-message workflow is caught by the pull request that
  introduces it, in 100% of cases, where today it is caught by none.
- **SC-002**: The number of places the allowed commit types are declared falls from two to one.
- **SC-003**: The set of things checked before a merge is unchanged: a bad title fails, a bad commit
  message fails, and a correction to either clears the check without a forced push or a manual
  re-run.
- **SC-004**: A contributor correcting a rejected title gets a fresh verdict within the time the
  check took before this change, and no slower.
- **SC-005**: Every consumer of this repository keeps working with no change to its call sites — zero
  consumer pull requests are required.

## Cross-Repository Impact

Required by the constitution before a plan may be written.

- **Affected consumers**: none. From `docs/consumers.md`, `python-app-baseline` and `opus-magnum`
  call the commit-message workflow; neither is touched, because nothing about the workflow itself
  changes. `repo-factory` calls only a composite action and is unaffected.
- **Interface delta**: none. No input is added, removed, renamed or given a new default; no
  permission the workflow requests changes; no output changes. The change is confined to this
  repository's own callers of it, plus its documentation and tests.
- **Compatibility**: every existing call site keeps working untouched. No major bump is warranted;
  this rides a `v1.x.y` patch or minor.
- **Rollout and rollback**: no consumer migrates, so there is no ordering. The only irreversible
  coupling is branch protection in *this* repository: the required check names change with the
  landing, so reverting the change also requires reverting the branch protection edit. Reverting
  otherwise costs one revert commit.

## Assumptions

- The repository's own checks move from the pull-request-target trigger the deleted title check used
  to the ordinary pull request trigger. This is forced rather than chosen: the called workflow gates
  both of its jobs on the pull request event, so under pull-request-target they would silently skip.
  It also removes a pull-request-target surface, which the constitution treats as a hazard.
- Read access to pull requests is sufficient for the title check on a fork's pull request. The check
  reads the title through the API and writes nothing.
- The allowed-types list survives in the reusable workflow, not in the caller. The caller passes no
  types input, so the single declaration is the workflow's own default.
- Branch protection is edited by a human or a scripted call as a landing step; it is not something
  the change can do to itself.
- The call lives in a caller of its own, not in the repository-wide checks (decided, Q1). The
  existing title-check workflow becomes that caller — reduced to a trigger and a single call, with no
  check logic of its own — and the repository-wide checks simply drop their hand-written commit
  check. The alternative, folding the call into the repository-wide checks, would either re-run
  minutes of lint, type checking and tests for a one-word title fix or stop re-checking edited titles
  altogether. The literal reading of the feature description — delete the title workflow outright —
  is therefore not what ships; the file is replaced, not removed, and the duplication it carried is
  what goes away.
- One caller invokes both of the workflow's jobs. The title check and the commit check are not split
  across two callers, so the commit check also re-runs on a title edit; at a checkout and one tool
  invocation, that is cheaper than the coordination of splitting them.
