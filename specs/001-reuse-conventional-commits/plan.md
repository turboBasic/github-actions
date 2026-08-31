# Implementation Plan: Self-checked commit-message workflow

**Branch**: `001-reuse-conventional-commits` | **Date**: 2026-08-31 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-reuse-conventional-commits/spec.md`

## Summary

`conventional-commits.yml` is the reusable workflow two other repositories rely on, and nothing in
this repository runs it — so it reaches a release tag having never executed. This change points a new
caller at it through a relative reference, `./.github/workflows/conventional-commits.yml`, which
GitHub resolves at the caller's own commit. A defect in the workflow now fails the pull request that
introduces it.

The two hand-written checks it replaces go away: the `Check commit messages` step in `ci.yml` and the
whole of `semantic-pull-request.yml`, along with the second copy of the allowed-types list that
`semantic-pull-request.yml` carried and a test parametrisation whose only job was to hold the two
copies equal. A `pull_request_target` trigger and the only `dangerous-triggers` suppression in the
zizmor config leave with it.

The call lives in its own caller rather than in `ci.yml` because `ci.yml` does not subscribe to the
`edited` activity type, and squash is the only merge method this repository allows — a rejected title
must be re-checked when it is edited, not only when a commit is pushed.

## Technical Context

**Language/Version**: GitHub Actions workflow YAML; Python 3.14 for the tests that assert properties
of that YAML.

**Primary Dependencies**: the repository's own `conventional-commits.yml`;
`amannn/action-semantic-pull-request` and `commitizen` transitively, through it. No dependency is
added, removed or repinned.

**Storage**: N/A.

**Testing**: `pytest` over `tests/test_action_pins.py`; `actionlint`, `zizmor --pedantic`, `yamllint
--strict` and `check-jsonschema` through prek; `mise run ci` locally. Final verification is a real
pull request, per constitution principle VI.

**Target Platform**: `ubuntu-latest` GitHub-hosted runners.

**Project Type**: reusable CI infrastructure consumed by other repositories.

**Performance Goals**: re-checking an edited title costs a checkout and one tool invocation — seconds,
and unchanged from today. It must not pull the repository-wide checks along with it.

**Constraints**: no change to `conventional-commits.yml`'s input contract (out of scope by the spec);
no consumer pull request required; the repository's ruleset must be updated while the pull request is
open, since the required check `PR title` cannot report once the workflow producing it is deleted.

**Scale/Scope**: four workflow files touched (one added, one deleted, two edited), one zizmor config,
one test module, three documents, one repository ruleset.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Verdict | Basis |
| --- | --- | --- |
| I. Consumer Contract Stability | **Pass** | No input, output, secret or permission of any reusable workflow changes. Interface delta is empty; see the spec's Cross-Repository Impact. No tag semantics change. |
| II. Supply-Chain Pinning | **Pass** | No third-party reference is touched. The one reference added is first-party and relative, which is neither a tag nor a SHA — a case the principle does not contemplate and R1 justifies on its own terms. |
| III. Least Privilege | **Pass** | The caller grants `contents: read` and `pull-requests: read`, at workflow level and on the calling job. `pull-requests: read` is not optional: without it the run fails as `startup_failure` (R4). Nothing is granted `write`. |
| IV. Untrusted Input Is Data, Never Code | **Strengthened** | A `pull_request_target` trigger is removed from the repository, and with it the only `dangerous-triggers` suppression in `.github/zizmor.yml`. No `run:` block is added; no `${{ }}` reaches a shell. |
| V. Secrets Never Persist | **Pass** | No secret is read, written or referenced. The called workflow uses `secrets.GITHUB_TOKEN` through `env`, unchanged. |
| VI. Verification By Real Invocation | **This is the feature** | The change exists to close a principle VI gap. It is itself verified the same way: the deliberate-break scenario in [quickstart.md](./quickstart.md) is the acceptance test, and lint alone does not close it. |
| VII. Gates Are Never Loosened | **Pass** | No rule disabled, no mode relaxed, no finding silenced. A zizmor suppression is *removed*. Two test assertions change because the thing they asserted no longer exists, and a new assertion is added to cover the property this change introduces (R8). Measured after the fact: the collected-test count is flat at 18, not risen — the new relative-reference test and the two file-parametrised cases the new caller adds are offset exactly by the three cases the deleted workflow took with it. No property lost coverage. |

**Cross-Repository Impact**: answered in the spec — no affected consumers, empty interface delta, no
migration, one revert commit plus a ruleset revert to roll back.

**Post-design re-check**: no violation appeared during Phase 0 or Phase 1. The Complexity Tracking
table stays empty.

## Project Structure

### Documentation (this feature)

```text
specs/001-reuse-conventional-commits/
├── spec.md                    # Feature specification
├── plan.md                    # This file
├── research.md                # Phase 0 output
├── quickstart.md              # Phase 1 output — the validation guide
├── checklists/requirements.md # Spec quality checklist
└── tasks.md                   # Phase 2 output (/speckit-tasks — NOT created here)
```

`data-model.md` and `contracts/` are deliberately absent. There is no data and no entity to model —
the spec's Key Entities are vocabulary, not structures. There is no contract to define either: the
interface delta is empty by design, and the one contract in play, `conventional-commits.yml`'s input
list, is documented in `README.md` and out of scope. Generating either file would produce a document
restating that nothing changed.

### Source Code (repository root)

```text
.github/workflows/
├── ci.yml                     # EDIT — drop the `Check commit messages` step and `fetch-depth: 0`
├── commit-messages.yml        # ADD  — trigger plus one relative call, no logic of its own
├── conventional-commits.yml   # UNCHANGED — the workflow under test; sole types declaration
├── precommit-advisory.yml     # UNCHANGED
├── python-ci.yml              # UNCHANGED
└── semantic-pull-request.yml  # DELETE

.github/zizmor.yml             # EDIT — remove the `dangerous-triggers` rule entirely
tests/test_action_pins.py      # EDIT — caller list, drop one parametrisation, add the relative-ref test
docs/ai-instructions.md        # EDIT — the workflow table row, and the inline-CI rationale that R1 falsifies
docs/consumers.md              # EDIT — the `contents: read and nothing more` sentence (R4)
README.md                      # VERIFY — the canonical call site already matches; no edit expected
```

**Structure Decision**: The repository layout is load-bearing and unchanged by this feature — reusable
workflows and callers both live in `.github/workflows/`, distinguished by the presence of
`workflow_call`, which is exactly what `tests/test_action_pins.py` asserts and why its by-name caller
list has to be kept current. No directory is added or moved.

## Landing order

Not a normal implementation ordering — one step is outside the repository and cannot be sequenced
inside it.

1. Everything in the tree, as one series of commits on this branch. `mise run ci` green locally.
2. Open the pull request. `commits / PR title` and `commits / Commit messages` report for the first
   time. The old required check `PR title` does not report and cannot: its workflow is deleted in this
   very pull request.
3. Update the ruleset: drop `PR title`, add `commits / PR title` and `commits / Commit messages`,
   keep `CI`. A landing step, not a follow-up — though not for the reason recorded here originally.
   `PR title` does keep reporting on this pull request, because `pull_request_target` resolves its
   workflow from the base branch, where the file survives until the merge. The deadline is the merge
   itself: once `semantic-pull-request.yml` leaves `main`, `PR title` can never report again and every
   subsequent pull request is blocked on a required check nothing produces.
4. Prove the point before merging: push a commit that deliberately breaks `conventional-commits.yml`,
   confirm the pull request fails, then revert it. This is the principle VI acceptance test and the
   only evidence that the feature works — see [quickstart.md](./quickstart.md).
5. Squash merge.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No violations. Table intentionally empty.
