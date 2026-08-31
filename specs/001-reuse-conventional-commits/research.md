# Phase 0 Research: Self-checked commit-message workflow

The spec left no `NEEDS CLARIFICATION` markers. What follows is the evidence behind each decision the
plan rests on, including two places where a claim already written down in this repository turned out
to be wrong.

## R1: The reference form is a relative path

**Decision**: The caller references the reusable workflow as `./.github/workflows/conventional-commits.yml`
— no `{owner}/{repo}`, no `@{ref}`.

**Rationale**: GitHub's documentation is explicit — "When you reference a reusable workflow in the
same repository using `$/` or `./` (without `{owner}/{repo}` and `@{ref}`), the called workflow is
from the same commit as the caller workflow." That property is the entire feature: it is what makes a
defect in the workflow fail the pull request that introduces it.

**Alternatives considered**:

- `turboBasic/github-actions/.github/workflows/conventional-commits.yml@v2` — resolves at the tag, so
  a pull request changing the workflow would be validated by the previous release of itself. This is
  the failure mode the existing comments in `ci.yml` and `semantic-pull-request.yml` describe, and
  those comments are correct *about this form*. They are wrong only in implying it is the only form.
- A full commit SHA — pins to a commit that by definition is not the one under review, and adds
  dependency-bot churn for a first-party reference. Rejected on both counts.

**Consequence**: The two comments claiming this repository cannot call its own reusable workflows
become false and must be rewritten, not merely trimmed.

## R2: The call gets a caller of its own

**Decision**: A new workflow, `.github/workflows/commit-messages.yml`, holds the call.
`ci.yml` loses its `Check commit messages` step and gains nothing.

**Rationale**: Measured, not assumed. `ci.yml` declares a bare `pull_request:`, which subscribes to
the default activity types — `opened`, `synchronize`, `reopened` — and *not* `edited`. The deleted
title check subscribes to `edited` explicitly. The repository's ruleset (below) allows squash as the
only merge method, so the title becomes the commit subject on the default branch: a rejected title is
the single most likely check for a contributor to have to fix, and fixing it is an edit, not a push.
Folding the call into `ci.yml` therefore forces a choice between adding `edited` to the
repository-wide trigger — re-running lint, schema validation, type checking and tests for a one-word
title fix, and cancelling any run already in flight via `cancel-in-progress` — and losing the
re-check altogether.

**Alternatives considered**: both arms of that choice, recorded as Q1 options B and C in the spec's
clarification round and rejected there.

**Naming**: `commit-messages.yml`. `conventional-commits.yml` is taken by the reusable workflow it
calls, and keeping the name `semantic-pull-request.yml` would misname a workflow that now checks the
commits as well as the title. The consumer `python-app-baseline` faces no such collision and names its
own caller `conventional-commits.yml`.

## R3: Fork pull requests — the repository's own note is wrong

**Decision**: The caller triggers on `pull_request` with `pull-requests: read`, and the
`dangerous-triggers` ignore entry in `.github/zizmor.yml` is deleted along with the workflow it
exempts.

**Rationale**: `.github/zizmor.yml` currently justifies `pull_request_target` with "a fork PR's title
is not readable under `pull_request`". That is not accurate. GitHub's documentation states: "With the
exception of `GITHUB_TOKEN`, secrets are not passed to the runner when a workflow is triggered from a
forked repository" — `GITHUB_TOKEN` is the stated exception, supplied read-only, and read-only is all
the title check needs. The claim appears to have been inherited from the action's own README, which
says a `pull_request` trigger "will only work if the branch is based in the repository itself …
you'll encounter an error as the GitHub token environment parameter is not available". That statement
predates the current fork-token behaviour.

**Consequence**: This is a *strengthening*, which is why it is worth doing rather than merely safe to
do. The change removes a `pull_request_target` trigger from the repository entirely, and with it the
only `dangerous-triggers` suppression in the zizmor config. Constitution principle IV gets shorter to
satisfy, not longer.

**Residual risk, accepted**: the fork path is not exercised here — this repository has a single owner
and no external contributors, and no fork pull request has ever been opened against it. If the
action does misbehave on a fork, the symptom is a failing title check on a fork's pull request, which
is loud rather than silent, and the remedy is a separate `pull_request_target` caller rather than any
change to the reusable workflow. `docs/consumers.md` already directs consumers to `pull_request` and
`python-app-baseline` already calls it that way, so this decision introduces no new exposure.

## R4: Permissions must be granted at the call site

**Decision**: The caller declares `contents: read` and `pull-requests: read` at workflow level and
again on the calling job, each with a trailing comment.

**Rationale**: A called workflow's permissions can only be equal to or narrower than its caller's, and
they are validated when the run starts, before any `if:` can skip a job. The title job inside
`conventional-commits.yml` asks for `pull-requests: read`; a caller granting only `contents: read`
reduces that to none and the run fails as `startup_failure` — no job, no log, no diagnostic.
`README.md` already documents exactly this shape as the canonical call site, and the consumer
`python-app-baseline` matches it. This repository's own caller becomes a live instance of the
documented example, which is the second-order benefit of the change.

**Measured**: `zizmor --pedantic` raises `undocumented-permissions` on each `pull-requests: read`
without a trailing comment. Both occurrences need one, matching the style already in
`conventional-commits.yml` (`# the action reads the PR title from the API`).

**Incidental documentation defect found**: `docs/consumers.md` states "Every other consumer grants
`contents: read` and nothing more." Every consumer of `conventional-commits.yml` also grants
`pull-requests: read`, as `python-app-baseline`'s call site shows. The sentence is contrasting against
`pull-requests: write`, but as written it is false and it sits in the blast-radius document.

## R5: The gates were probed, not predicted

A candidate caller was written to a scratch file and run through every gate that will judge it:

| Gate | Result |
| --- | --- |
| `actionlint` | passes — the relative reusable-workflow reference resolves and its inputs check out |
| `check-jsonschema --builtin-schema custom.github-workflows-require-timeout` | passes — a `uses:` job is not required to declare `timeout-minutes`, which it cannot |
| `yamllint --strict` | passes |
| `zizmor --pedantic` | two `undocumented-permissions` findings, resolved by R4's trailing comments |

`timeout-minutes` stays where it belongs: the callee's own input default of 5. A calling job may not
declare it.

## R6: Required status checks, and the order the change lands in

**Measured** from the repository's ruleset (`main`, id `20657426`, enforcement active):

- Required checks today: `CI` and `PR title`.
- Other rules: squash-only merges, linear history, one approving review, stale-review dismissal.

After the change the check names are:

| Check | Before | After |
| --- | --- | --- |
| Repository-wide checks | `CI` | `CI` — unchanged |
| Title validation | `PR title` | `commits / PR title` |
| Commit-message validation | *(a step inside `CI`, never its own check)* | `commits / Commit messages` |

Routing a job through a call renames its check to `<calling job id> / <called job name>`, which is
why the calling job is named `commits`: it reproduces the names `docs/consumers.md` already records
for `python-app-baseline`.

**Ordering constraint**: the required check `PR title` cannot report on the pull request that deletes
the workflow producing it, so that pull request is blocked until the ruleset is updated. The ruleset
must therefore be edited while the pull request is open, after the new checks have reported at least
once, and before merge. It cannot be done in the same commit, and it cannot be done first.

## R7: `fetch-depth: 0` in `ci.yml` leaves with the step it served

`ci.yml`'s checkout carries `fetch-depth: 0` with the comment "cz check needs the full range, not
just the tip". Nothing else in that job reads git history — lint, schema validation, type checking and
the tests all work from the working tree. The option and its comment go with the step, or the comment
becomes a lie about why a full clone is being fetched.

## R8: What the tests currently assert, and what has to move

`tests/test_action_pins.py` couples to the workflow filenames in two places, and lacks a guard for the
property this change introduces:

1. `test_every_reusable_workflow_declares_workflow_call` sweeps `.github/workflows/*.yml` minus a
   by-name list of callers, `{"ci.yml", "semantic-pull-request.yml"}`. The new caller must replace the
   deleted name in that list or it is swept as a reusable workflow and fails.
2. `test_allowed_types_match_the_commitizen_builtin_set` is parametrised over two workflows; the
   `("semantic-pull-request.yml", "types")` case goes, leaving the single declaration in
   `conventional-commits.yml`.
3. Nothing currently asserts that the self-call is *relative*. Rewriting it to
   `turboBasic/github-actions/.github/workflows/conventional-commits.yml@v2` would silently restore
   the staleness bug and pass every existing gate, including
   `test_first_party_references_use_the_major_tag`, which such a reference satisfies. A new test
   closes that hole. It must be scoped to the caller: `precommit-advisory.yml` references
   `turboBasic/github-actions/actions/precommit-advisory-pr@v2` deliberately, because a reusable
   workflow cannot interpolate its own ref into `uses:`.
