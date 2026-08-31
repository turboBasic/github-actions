# Validation Guide: Self-checked commit-message workflow

Four scenarios. The first three are local and cheap; the fourth is the only one that actually proves
the feature, and it needs a real pull request.

## Prerequisites

```bash
mise run setup   # tools, dependencies, git hooks
```

`gh` authenticated with permission to edit the repository ruleset, for Scenario 3.

## Scenario 1 — the gates pass locally

```bash
mise run ci
```

Expected: green. Specifically, `actionlint` resolves the relative reusable-workflow reference,
`zizmor --pedantic` reports no findings (both `pull-requests: read` lines carry an explanatory
comment), and `pytest` passes with the updated caller list and the new relative-reference assertion.

A `zizmor` `undocumented-permissions` finding here means a permission line lost its trailing comment.

## Scenario 2 — the duplication is gone

```bash
rg -n 'refactor' .github/workflows/          # a type from the allowed list
```

Expected: exactly one match, the `types` default in `conventional-commits.yml`. Two matches means the
second declaration survived.

```bash
rg -n 'pull_request_target' .github/
```

Expected: no matches. This repository no longer has one.

## Scenario 3 — the required checks line up

```bash
gh api repos/turboBasic/github-actions/rulesets/20657426 \
  -q '.rules[] | select(.type=="required_status_checks") | .parameters.required_status_checks[].context'
```

Expected **after** the ruleset is updated: `CI`, `commits / PR title`, `commits / Commit messages`.

Order matters. Run this against the open pull request's checks first — the new names must have
reported at least once before they are made required.

**Measured correction.** `PR title` does keep reporting on *this* pull request, so the pull request is
not blocked on it: `semantic-pull-request.yml` triggers on `pull_request_target`, which resolves the
workflow from the **base** branch, where the file still exists until this merges. What is actually
blocking here is the ruleset's one-approving-review rule, which has nothing to do with this change.

The deadline is therefore the merge, not this pull request: the moment `semantic-pull-request.yml`
leaves `main`, `PR title` can never report again, and every *subsequent* pull request would be
permanently blocked on a required check no workflow produces. Drop it in the same edit that adds the
new names, at or before the merge.

## Scenario 4 — the acceptance test: a break fails its own pull request

This is the one that matters. Everything above passes equally well on a workflow that never runs.

With the pull request open and its checks green:

1. Break `conventional-commits.yml` on the branch — the smallest useful break is a `types` value the
   workflow's own bare-word guard rejects:

   ```text
   *[^a-zA-Z0-9_\|-]*) echo "::error::the types input must be bare words: ${types_pattern}"
   ```

   Add `not.a.type` to the list. **Not a value containing a space** — the guard runs on the pattern
   *after* `tr -s '[:space:]' '\n'`, so `not a type` arrives as three separate bare words and is
   accepted. Measured, not assumed. The character has to survive that normalisation: a dot does.

   Put the broken value last in the block, so `tests/test_action_pins.py` still passes and the only
   thing failing is the check under observation.

2. Push it. Expected: `commits / Commit messages` **fails**, on this pull request, naming that error.

3. Confirm the counterfactual: the failure must come from the branch's version of the workflow, not
   the tagged one. Check the failing job's log for the broken value. If it passes instead, the
   reference is resolving at a tag and the feature does not work — the most likely cause is a `uses:`
   line rewritten to `turboBasic/github-actions/.github/workflows/conventional-commits.yml@v2`.

4. Revert the break. Expected: the check goes green again.

Also worth confirming in the same pull request, since both are cheap and both are requirements:

- **FR-005** — edit the pull request title to something invalid (`nonsense title`) *without pushing*.
  Expected: `commits / PR title` re-runs and fails. Correct the title. Expected: it re-runs and
  passes. Neither edit may start a `CI` run.
- **FR-007** — while a `CI` run is in progress, edit the title. Expected: the `CI` run is not
  cancelled.

## Known gap

The fork path is not covered by any of this. `pull_request` from a fork receives a read-only
`GITHUB_TOKEN`, which is all the title check needs (research R3), but no fork pull request has ever
been opened against this repository, so the path is reasoned rather than observed. If one ever fails,
the remedy is a separate `pull_request_target` caller — not a change to `conventional-commits.yml`.
