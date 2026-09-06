# Validation Guide: Tested Release Scripts

How to prove this works. The rungs are **ordered**, and they are split across two releases because
[research.md D9](./research.md#d9) forces that split — `release.yml`'s `uses: …@v4` cannot resolve until a
release exists whose tree contains the action.

Principle VI is why lint is not the end of this: every linter here passes on a workflow that fails on its
first run.

## Prerequisites

```bash
mise run setup
```

Nothing else. Rungs 1 and 2 need no network and no token.

---

## Stage 1 — the action and `release-proposal.yml`

Adds no `uses:`, so nothing resolves `@v4` and nothing can deadlock.

### Rung 1 — the offline suite

The point of the change: every decision is now reachable without GitHub.

```bash
mise run ci          # lint + typecheck + test, all offline
mise run test        # just the suite, while iterating
```

**Expected**: green, with `tests/test_release_decisions.py` covering every invariant in
[contracts/decisions.md](./contracts/decisions.md). Confirm these two by name, since they are the defects
that shipped:

```bash
uv run pytest tests/test_release_decisions.py -k "one_byte or absent_breaking" -v
```

A mismatch here exits 5 (`no tests ran`) rather than passing vacuously, but the test names must contain
those substrings for the filter to mean anything.

**Also confirm nothing loosened** (Principle VII, SC-010):

```bash
uv run pytest tests/test_action_pins.py -k first_party_actions_use_the_major_tag -v
git diff --stat main -- tests/test_action_pins.py   # no relaxation of that gate
```

**And that no gate was left failing** (FR-017, SC-011): the four gates in
[contracts/decisions.md](./contracts/decisions.md#existing-tests-this-change-breaks) either assert the new
form or are gone with a recorded reason.

**Fails if**: the suite needs the network. `mise run ci` must never reach `api.github.com` — that is what
`drift` is for, and nothing added here carries that marker.

### Rung 2 — `release-proposal.yml`, with teardown

This is stage 1's real invocation, and it is the whole reason stage 1 can stand alone: the workflow
invokes the module **by in-repo path**, so it exercises the new Python at this commit with nothing pinned.

It can be exercised nowhere but this repository — no `workflow_call` trigger, so nothing can call it — and
it has no `dry-run` input. Its dispatch has real side effects.

```bash
GH_TOKEN=$(gh auth token -u turboBasic) gh workflow run release-proposal.yml \
  --repo turboBasic/github-actions --ref 003-tested-release-scripts
GH_TOKEN=$(gh auth token -u turboBasic) gh run watch --repo turboBasic/github-actions
```

**Expected**: it computes an increment matching what the old shell proposed for the same range, writes the
`release-proposal` branch, and opens or refreshes a pull request whose body is the notes.

**Teardown is mandatory** — it wrote a branch and a pull request:

```bash
GH_TOKEN=$(gh auth token -u turboBasic) gh pr list --repo turboBasic/github-actions \
  --head release-proposal --state open
GH_TOKEN=$(gh auth token -u turboBasic) gh pr close <n> --repo turboBasic/github-actions --delete-branch
```

**Fails if**: the increment disagrees with the old shell's for the same range, or the `release-proposal`
branch is left behind.

### Rung 3 — merge stage 1, then merge the bump it proposes

**Merging a stage cuts nothing.** `ci.yml`'s `$/` self-call does resolve `release.yml` at the merge commit
and run it, but the declared version is already tagged by then, so it answers with a notice — "v4.0.3 is
already released, so this merge cuts nothing" — and stops. That is the ordinary path, and it is what
happened on the stage-1 merge. The release arrives one merge later: `release-proposal.yml` runs on the same
push and opens a `bump: release vX.Y.Z` pull request, and **merging that** is what tags and publishes.

`release.yml` is **unchanged** in stage 1, so the old shell cuts that release — which is exactly what makes
it safe.

```bash
GH_TOKEN=$(gh auth token -u turboBasic) gh run list --repo turboBasic/github-actions \
  --workflow ci.yml --branch main --limit 3
```

**Expected**: once the bump pull request has merged, a release published and `v4` moved onto a tree that now
contains `actions/release-decisions/`. Confirm that before starting stage 2:

```bash
GH_TOKEN=$(gh auth token -u turboBasic) gh api \
  repos/turboBasic/github-actions/contents/actions/release-decisions/action.yml?ref=v4 --jq .name
```

**Fails if**: that last call 404s. Stage 2 cannot begin until it returns `action.yml`.

---

## Stage 2 — `release.yml`

Now that `@v4` contains the action, `release.yml`'s `uses:` resolves — from a branch as well as from
`main`, which is what makes the next two rungs reachable with nothing pinned.

### Rung 4 — dry-run dispatch of `release.yml`

Exercises every refusal and renders the real notes, creating no tag. The cheapest real invocation of the
rewired workflow.

```bash
GH_TOKEN=$(gh auth token -u turboBasic) gh workflow run release.yml \
  --repo turboBasic/github-actions --ref <stage-2 branch> -f dry-run=true
GH_TOKEN=$(gh auth token -u turboBasic) gh run watch --repo turboBasic/github-actions
```

**Expected**: the not-ahead case reports as a **notice**, not an error — on a branch the declared version
is the released one by definition, so a dry run must get past it — then the notes render to the step
summary and nothing is created.

**Compare against the same dispatch before the change**: same notes, same refusals, same wording (FR-010,
SC-006). The step summary is browser-only; no `gh` or REST route reaches it, so read it there.

**Fails if**: the action cannot be found (stage 1 did not actually release), a `decision` input is mapped
wrong, or a refusal changed severity.

### Rung 5 — a real release, on disposable tags first

The one rung that proves tagging end to end, and the reason it comes **before** merging stage 2.

`ci.yml` resolves `release.yml` at the merge commit, so the instant stage 2 merges the new workflow cuts
this repository's release. Our version tags are immutable: `refs/tags/v*.*.*` is covered by a ruleset with
`bypass_actors: []`, so a wrong tag cannot be deleted by anyone, admin included.
`docs/consumers.md` says `github-actions-test`'s "costs a tag nobody resolves". Spend those first.

1. In `github-actions-test/.github/workflows/ci.yml`, repoint the `release` job at the stage-2 branch:

   ```yaml
       uses: turboBasic/github-actions/.github/workflows/release.yml@<stage-2 branch>
   ```

   Only the *consumer* is repointed. Nothing in this repository is pinned, so
   `test_first_party_actions_use_the_major_tag` stays green here (SC-010).

2. Bump `github-actions-test`'s `[project].version` and merge, so its `release` job has something to cut.
3. **Expected**: a release published there, its `v0` tag moved onto it, and `release / tag-and-publish`
   reporting green under that exact name (SC-007, SC-008).
4. Revert `github-actions-test` to `@v4`.

**Fails if**: a tag is created but no release attached — ordering regressed, and notes must render before
any tag exists — or the major tag does not move, or the check reports under a different name.

### Rung 6 — merge stage 2, then merge the bump it proposes

Two merges again, for the reason rung 3 gives: the stage-2 merge runs the new `release.yml` and it declines,
because the declared version is already tagged. That decline is itself the first real exercise of the
rewritten path — the `verify-version` decision answering `proceed=false` on a push — so watch it. The
release comes when the bump pull request `release-proposal.yml` opens is merged, and **that** is the first
release the new `release.yml` cuts.

```bash
GH_TOKEN=$(gh auth token -u turboBasic) gh run list --repo turboBasic/github-actions \
  --workflow ci.yml --branch main --limit 3
```

**Recovery if it goes wrong**: bump to the next patch version and merge that. Never re-run — a version tag
already created cannot be deleted.

---

## Documentation checks before calling either stage done

- `docs/ai-instructions.md`'s "the Python here exists to test the YAML" is corrected (FR-016) — stage 1
- `README.md`'s composite actions list gains `release-decisions` (stage 1); its `release.yml` section still
  describes the surface paths accurately, since they did not become an input
- `docs/consumers.md` still reads true — `github-actions-test` calls `release` at `@v4`, unchanged once
  rung 5's revert lands
- No war stories in the new comments: state the rule, not the incident
