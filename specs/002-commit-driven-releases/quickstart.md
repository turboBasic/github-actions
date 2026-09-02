# Quickstart: validating commit-driven releases

Runnable checks, in the order they stop being cheap. Everything in stages 1 and 2 is offline and
creates nothing; stage 3 writes to GitHub; stage 4 cannot happen until this is merged.

Details are in [contracts/release-notes.md](contracts/release-notes.md) and
[contracts/workflow-triggers.md](contracts/workflow-triggers.md) rather than repeated here.

## Prerequisites

```sh
mise install          # picks up the new git-cliff pin
mise run ci           # lint, typecheck, test — must be green before anything below
```

A **full clone** is required from stage 2 onward: git-cliff needs tags to find a range's lower bound,
and a shallow checkout renders an empty range without complaining.

```sh
git rev-parse --is-shallow-repository   # must print false
git tag --list 'v*' | head             # must include vX.Y.Z tags, not just v1/v2
```

## Stage 1 — the mapping, offline

```sh
mise run test         # includes tests/test_release_notes.py
```

Asserts what a rendering cannot: all twelve allowed types placed or skipped, the seven titles in order,
`bump` the only exclusion, the catch-all parser last, `tag_pattern` still excluding two-component tags,
and the surface path filter agreeing with `OWN_CI`.

**Expected**: green, with no network access and no git-cliff invocation.

## Stage 2 — the notes, against real history

This is where SC-001, SC-002 and SC-006 are measured. Nothing here creates anything.

```sh
mise run release-notes                       # the current unreleased range
```

**SC-006 — reproducible offline.** Re-run with networking off and diff:

```sh
mise run release-notes > /tmp/online.md
# disable networking, then:
mise run release-notes | diff /tmp/online.md -
```

**Expected**: identical. If it differs, `--remote.github` has been switched on somewhere.

**SC-002 — the breaking change shipped in v2.0.0.** Render the range that produced it. The previous
version tag is `v1.0.1`, not `v1.1.0` — there is no `v1.1.0`, and a nonexistent revspec exits 1 rather
than rendering empty, which is how that typo was caught:

```sh
git-cliff v1.0.1..v2.0.0
```

**Already confirmed** with the candidate config:

```text
### 💥 Breaking changes

- split the advisory job into its own reusable workflow (#5) — python-ci.yml no longer accepts
  advisory-all-files. Call precommit-advisory.yml alongside it instead, granting pull-requests: write
  there. …

### 🚀 Features

- split the advisory job into its own reusable workflow (#5)

### 🧹 Maintenance

- set version to 2.0.0 (#6)
```

The breaking change is in the breaking section **with its explanatory text**, and again under its own
type. Today the published v2.0.0 release shows it under "Other changes" — that contrast is the whole
point of Story 1.

Two things this render also settles:

- **The spec's Assumption about version commits holds.** `set version to 2.0.0 (#6)` is a `chore:`, not
  a `bump:`, so it appears under Maintenance. Only ranges from here forward are fully clean, exactly as
  the spec says — this is not a defect to fix.
- **Collapsing the footer's newlines leaves a double space** where the original had a paragraph break.
  Cosmetic, visible, and worth squeezing in the template.

**SC-001 — every commit accounted for, exactly once.** Walk every historical range:

```sh
prev=""
for tag in $(git tag --list --sort=v:refname | grep -E '^v[0-9]+\.[0-9]+\.[0-9]+$'); do
  if [ -n "$prev" ]; then
    bullets=$(git-cliff "$prev..$tag" | grep -c '^- ')
    commits=$(git log --no-merges --format=%s "$prev..$tag" | grep -cvE '^bump(\([^)]*\))?!?:')
    printf '%-8s %-18s bullets=%s commits=%s\n' "$tag" "$prev..$tag" "$bullets" "$commits"
  fi
  prev=$tag
done
```

**Already run against the candidate config, and SC-001 holds exactly:**

```text
v1.0.1   v1.0.0..v1.0.1     bullets=3  commits=3
v2.0.0   v1.0.1..v2.0.0     bullets=3  commits=2
v2.0.1   v2.0.0..v2.0.1     bullets=5  commits=5
v2.0.2   v2.0.1..v2.0.2     bullets=32 commits=32
```

Every range matches one-for-one except `v1.0.1..v2.0.0`, which is over by exactly one — the breaking
change counted a second time under its own type, which is FR-005 working rather than a miscount.

Pairs only — a range needs two endpoints, so the first release ever has none and is checked by hand if
wanted. Compare the two counts per range, remembering that a breaking commit is *expected* to be
counted twice (FR-005) and a `bump` commit zero times (FR-004). Two of the three historical version
commits predate the `bump` type, so ranges before it show one extra line under Maintenance — as the
v2.0.0 render above demonstrates. The spec records this under Assumptions; only ranges from here
forward are fully clean.

**SC-007 — no raw commit type as a heading.** Skim the output of the loop above; every heading must be
one of the seven titles.

## Stage 3 — the workflows, dispatched from this branch

Both new trigger paths are unreachable from a branch, so dispatch is the pre-flight. **Pre-flight the
exact line out of the file, never a retyping of it** — that rule exists because a retyped
`gh release create` once passed a pre-flight with the `--repo` the file was missing.

The three git-cliff flags are **already pre-flighted**, and
[contracts/release-notes.md](contracts/release-notes.md) records what came back. Re-run these when the
pin moves:

```sh
git-cliff --unreleased --context | head -40
git-cliff --unreleased --context \
  --include-path '.github/workflows/**' --include-path 'actions/**' \
  --exclude-path '.github/workflows/ci.yml' \
  --exclude-path '.github/workflows/commit-messages.yml' \
  --exclude-path '.github/workflows/release.yml' \
  --exclude-path '.github/workflows/release-proposal.yml'
```

**Expected**, as observed: JSON with a per-commit `breaking` boolean — **absent, not `false`, on an
unconventional commit**, which is why the refusal reads `jq 'any(.[].commits[]; .breaking == true)'` — and
a filtered second pass that keeps only commits touching the consumer surface.

Then the workflows:

| What | How | Expected |
| --- | --- | --- |
| `release.yml` refuses and renders without tagging | dispatch on this branch with `dry-run: true` | the notes in the step summary; **`git tag --list` unchanged** |
| `release.yml` refuses an empty range | dispatch `dry-run: true` from a commit whose range holds only a `bump` | an explicit error, no tag (FR-007) |
| `release-proposal.yml` end to end | dispatch on this branch | a `release-proposal` branch and a pull request appear, body = the rendered notes, diff = `pyproject.toml` + `uv.lock` only |
| The proposal's checks start | click *Approve and run* on that pull request | all three required contexts report; if they never appear at all, research.md's "Corrected while checking" premise is wrong and the App-token fallback applies |
| A reviewer's version survives a refresh | edit the version on that branch, then push any commit to the branch and re-dispatch | the body updates; **the edited version is untouched** (FR-009a) |
| A refresh recomputes a bot-owned version | re-dispatch without editing | version recomputed, notes re-rendered |

Then close the pull request and delete the branch.

**Do this before anything in this stage can pass**: turn on **Settings → Actions → General → "Allow
GitHub Actions to create and approve pull requests"**. It is currently **off**, and the proposal cannot
be opened until it is on — `POST /pulls` answers
`GitHub Actions is not permitted to create or approve pull requests` (403). Verified by probe;
research.md decision 10 has the detail and the alternative.

Readable and settable through the API rather than the UI, if preferred:

```sh
gh api repos/turboBasic/github-actions/actions/permissions/workflow            # read
# gh api -X PUT repos/turboBasic/github-actions/actions/permissions/workflow \
#   -F can_approve_pull_request_reviews=true -f default_workflow_permissions=read
```

## Stage 4 — after merge, the first real release

The two automatic triggers run for the first time here. This is the residual Principle VI gap in
plan.md, and it is deliberate.

1. Merge this branch. **Expected**: `release-proposal.yml` runs on the push and, because
   `[project].version` is still the tagged one and the range is non-empty, raises a proposal.
2. Read it — the version and the notes are the artifact under review (Story 2, FR-001).
3. Click *Approve and run*, let the three checks pass, and merge.
4. **Expected**: CI runs on the merge commit; when it reports green, `release.yml` starts by itself
   (FR-011), renders the notes again from the same rules (FR-009a), tags, publishes, and moves `vN`
   last (FR-013). No further human action (FR-009).
5. Confirm `mise run test-live` goes green — it is the check that says a release is owed, so it passing
   is the end-to-end proof that one was cut.

**If it fails after the version tag exists**: delete that tag, fix the cause, and re-dispatch. The
major tag moves last precisely so consumers stay on the previous release until the rest has succeeded.

## What none of this covers

- **A consumer exercising it.** Nothing here is callable, so `github-actions-test` has no part to play —
  the usual step 2 of *Verifying a workflow change* does not apply.
- **The `on: push` and `on: workflow_run` blocks themselves**, until stage 4. Every other line is
  exercised by stage 3.
