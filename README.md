# turboBasic/github-actions

[![ci](https://github.com/turboBasic/github-actions/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/turboBasic/github-actions/actions/workflows/ci.yml?query=branch%3Amain)

Reusable GitHub Actions workflows for `turboBasic` repositories. Every published capability is a
callable workflow: none is offered as a composite action a consumer places in a job it already owns.

## Capabilities

One section each, carrying a call site to copy, what the capability is for, and when not to reach for
it.

**A capability's inputs, its defaults, the permissions a caller must grant and the check names it
composes are declared in its own workflow file, and are deliberately not restated here.** Two
statements of one default drift apart, and afterwards nothing in the tree says which of them was ever
authoritative — so the file being called is the only place any of it is written. Open it for the full
list.

Two things a call site cannot show, and which apply to every capability below:

- **Concurrency grouping stays the caller's.** A called workflow cannot set its caller's group.
- **A permission a caller does not grant fails the whole run before any job exists**, with no log, no
  annotation, and no condition able to skip past it. That is why each capability's demand is part of
  what it publishes rather than something a first run teaches you.

Every call site below pins the moving ref. It resolves, but a capability merged since the last release
is not on it until a release moves it there — and a break starts a new line instead, leaving the old
ref where it is. Versioning says which ref to pin.

### 🧩 `project-ci`

One check over **one component**, in whatever language it is written: its own `lint`, `build`,
`typecheck` and `test` tasks, run by its own task runner. Those four names are the whole interface. This
capability checks the tree out, installs what your `mise.toml` pins, and runs them — it knows no
language, and there is no selector to tell it one.

```yaml
jobs:
  api:
    permissions:
      contents: read
    uses: turboBasic/github-actions/.github/workflows/project-ci.yml@v0.3
```

Required context: `api / project-ci` — your own job id, then the called job's name.

**Name the job after the component, not after the workflow it sits in.** One capability judges every
component, so the called half of every context is the same word and your job id is the only thing telling
one component's check from another's — a `ci` job in a `ci` workflow reads `ci / project-ci` and has spent
that word on nothing. This repository's own call site is `python`.

**The four task names are a port, and what runs behind each is yours.** A Python component and a Go one
call the same workflow and differ only in a file neither this repository nor a reviewer of it ever needs
to read:

```toml
[tools]
go = "1.27.1"
prek = "0.5.3"

[tasks.deps]
run = "go mod download && go mod verify && go mod tidy -diff"

[tasks.lint]
depends = ["deps"]
run = "prek run --all-files --show-diff-on-failure"

[tasks.build]
depends = ["deps"]
run = "go build ./..."

[tasks.typecheck]
depends = ["deps"]
run = "go vet ./..."

[tasks.test]
depends = ["deps"]
run = "go test ./..."
```

**Every task must be runnable from a clean checkout, and each owns the preparation it needs.** No stage
here installs anything, locks anything or verifies anything on a task's behalf: a lockfile install, a
module download, a checksum check is a `depends` of the task that cannot judge without it — as above.
That is also the only reason your own `mise run test` and this check reach the same verdict.

Four things that follow from the shape, and prose is the only place any of them fits:

- **A stage you do not have is switched off at the call site**, through the inputs declared in the
  workflow file. All four default on, so an absent task fails the run naming itself; `run-build: false`
  in your `with:` block is the answer, and it is visible in review where a `build` task existing only to
  exit zero would not be. A call with all four off is refused outright — a check that judges nothing
  must not report success. A switch is for a genuinely absent stage, never a way to quiet a failing one.
- **Prek is reached through `lint` and nowhere else.** This capability owns no linter and invokes no hook
  runner: the verdict is the one your own `mise run lint` gives, over whatever your task covers. A task
  reading only part of the tree yields a check that passed over the rest, and that is yours to fix.
- **A monorepo calls this once per component**, each with its own job id and so its own required context,
  and each passing `working-directory:` — the stages run there, so the task runner reads that
  component's own `mise.toml`. Split only where a component deserves an independent verdict, not per
  language: a single polyglot component's four tasks already cover several. Two things follow from how
  task configuration nests. Tools are installed from the root, before any stage, so a component's
  toolchain is pinned in the `[tools]` table the repository root holds. And a component **defines all
  four task names itself** — one it leaves out is inherited from the root, and a stage judging the root
  while the check name says otherwise is the one failure mode nobody reads a green check for.
- **The checkout is shallow.** No stage reads history beyond the head commit, so a task of yours that
  wants a range or a tag will not find one, and no input here changes that.

**`python-ci` was retired for this.** Its contract stands unchanged on `@v0.1` and `@v0.2`, which is
where a consumer that has not migrated stays. Migrating means renaming
your task if it was not called `typecheck` or `test`, moving `uv sync --locked` into a task of your own,
and editing the required context in your ruleset to whatever your call site now composes — that last one
blocks every pull request in your repository until it is done, so do it in the same sitting. Renaming the
job to the component's name while you are there costs the same edit.

### 🧩 `conventional-commits`

One grammar over both the pull request title and every commit message in the range, judged by the same
tool the local commit hook uses, against one list of types — so the two checks cannot reach different
verdicts about the same word. It provisions its own tooling, so a repository with no task-runner
configuration at all can call it.

```yaml
name: commits

on:
  pull_request:
    types: [opened, edited, reopened, synchronize]

jobs:
  commits:
    permissions:
      contents: read
      pull-requests: read
    uses: turboBasic/github-actions/.github/workflows/conventional-commits.yml@v0.1
```

Required contexts: `commits / pr-title` and `commits / commit-messages` — two jobs, so two checks you
require, switch off and retire independently.

Three things that call site is doing on purpose:

- **The activity types are spelled out, `edited` among them.** GitHub's default set for
  `pull_request` omits it, and a corrected title is an edit rather than a push — leave it out and
  fixing the title leaves the old red verdict standing with nothing to re-run it.
- **The event is `pull_request`, never `pull_request_target`.** That one runs with your repository's
  own token while the title and the commit messages are whatever a fork wrote. Both jobs pin the event
  and skip under every other, so `pull_request_target` would reach nothing here anyway — and a
  required context that never reports blocks every pull request.
- **The type list is never read from your own commit-tool configuration.** Reading it from two places
  is exactly what would let the title check and the commit check disagree, so pass `types` to change
  it. A malformed list — comma-separated, quoted, anything but bare words one per line — fails the run
  naming what it read, rather than compiling into a grammar that matches nothing.

**Switching a check off means retiring its context in the same change.** `check-title: false` skips
the `pr-title` job, and a skipped job reports success — so a ruleset still requiring
`commits / pr-title` afterwards names a gate that no longer reports, and blocks every pull request in
the repository until someone edits the ruleset by hand.

### 🧩 `release`

Tags the version your manifest already declares, publishes the release from notes rendered out of the
commit range, and moves the compatibility ref last. It never decides a version and never writes one:
what gets released is what a merged change put in `pyproject.toml`.

It has **no trigger of its own**. A caller's dependency edge is the only route to it, which is what
keeps anything from reaching the tagging step around a verdict.

```yaml
name: release-on-merge

on:
  push:
    branches: [main]
  workflow_dispatch:
    inputs:
      dry-run:
        type: boolean
        default: true

jobs:
  verify:
    permissions:
      contents: read
    uses: turboBasic/github-actions/.github/workflows/project-ci.yml@v0.3

  release:
    needs: verify
    permissions:
      contents: write
    uses: turboBasic/github-actions/.github/workflows/release.yml@v0.1
    with:
      dry-run: ${{ github.event_name == 'workflow_dispatch' && inputs.dry-run }}

  proposal:
    needs: release
    if: github.event_name == 'push'
    permissions:
      contents: read
    uses: turboBasic/github-actions/.github/workflows/release-proposal.yml@v0.1
    secrets:
      app-client-id: ${{ secrets.RELEASE_APP_CLIENT_ID }}
      app-private-key: ${{ secrets.RELEASE_APP_PRIVATE_KEY }}
```

Required context: `release / tag-and-publish`.

**`proposal` is ordered behind `release`, in the same workflow, not beside it in one of its own.**
`release-proposal` reads the tag list at checkout, and a push that releases has to have finished
tagging before it reads that list, or it computes its own next version's range against a tag that does
not exist yet — the wrong side of that race is always the one with less work to do, so `proposal`
running unordered beside `release` loses it on every release merge, not occasionally. `needs: release`
is what makes the tag visible first; `if: github.event_name == 'push'` keeps it off the dispatch path,
which promises nothing is created and would otherwise gain a write. See `release-proposal` below for
what a caller that cannot offer this ordering still gets.

**Dry-run it before you trust it with a tag.** Every refusal runs, the real notes render, and nothing
is created. This is the only safe way to exercise the capability, because a version tag is immutable
once published — a wrong one cannot be deleted, only lived with.

It refuses, always before any ref exists, when the run is not on your repository's own default branch;
when the declared version is not a plain `N.N.N`; when that version is not ahead of the highest release
across *every* compatibility line; when the range renders no notes; or when the range breaks your
consumer surface while the version stays on a line that already has a release.

**Nothing is released until the version says so.** A repository with no releases is measured against
`0.0.0`, so a manifest sitting there is not ahead of anything and every merge declines. That is the hold
for initial development: stay at `0.0.0` for as long as it takes, then bump when there is something worth
publishing. Nothing else to remember, and nothing to switch off afterwards.

**A routine merge never reddens your default branch.** While the version has not been bumped past the
highest release it is provisional, so nothing else about it can be judged yet — the run declines with a
notice and releases nothing, whatever the range contains. Releasing is therefore what merging a version
bump does, not something every merge attempts.

The one thing that does redden it is a version that *has* been bumped and is wrong for its range: a
break while the new version stays on a line that already has a release, which would force a ref your
consumers pin across that break. That is asserted rather than provisional, so it fails however the run
was reached.

Prerequisites in the calling repository: `git-cliff` pinned in `mise.toml`, a `cliff.toml` mapping
commit types to sections, a `[project].version` in `pyproject.toml`, and the surface declaration below.
Notes come from commit types, never from a label on a pull request: a label is applied after the fact by
whoever is looking, and two people label differently.

Declare what a consumer of *you* actually resolves, so your release is judged against your own layout
rather than a default that fits somebody else's:

```toml
[tool.turbobasic-release]
include = [".github/workflows", "actions"]
exclude = [".github/workflows/ci.yml"]
```

Omit it and every changed path counts towards a break — refusing more often rather than less, and said
out loud in the log. A misspelled key is refused rather than read as an absent one, because silently
widening the surface while looking configured is the failure nobody would notice.

### 🧩 `release-proposal`

Works out the next version from the commit range, writes it into `pyproject.toml` on a branch of its
own, and opens a pull request whose body is the exact notes that release will publish. Merging that pull
request is what releases: `release` only tags what the manifest already declares, and this is what puts
the number there — so nobody types one.

Like `release` it has **no trigger of its own**, and for a second reason: the App credentials below are
then reachable from no event a fork can raise. Its call site is the `proposal` job shown under
`release` above, in the same `release-on-merge.yml` — not a workflow of its own — so that it can be
ordered behind the release it must not race.

Context composed: `proposal / propose`. There is nothing here for a ruleset to require — it runs on a
push, and it writes rather than judges.

**It also declines on its own when the commit it would propose from already carries a release tag**,
whatever called it and however that call is ordered — nothing since a release already published is
proposed again. This is a backstop, not the ordering: it cannot make a run wait for a tag that does not
exist yet, so a caller racing this against its own release job can still lose that race on the first
push, the same way `release-on-merge`'s own two jobs would without `needs:`. What it does close is every
other way the same wrong proposal could recur once the tag exists — a delayed run, a retry, a caller
whose release job happens to finish first without any explicit ordering at all. A caller that cannot
offer `needs:` — two workflows that cannot see each other — is not safe by construction on the first
race, but is not stuck rediscovering it either: the standing self-heal (below) plus this backstop is what
it gets instead.

**It needs a GitHub App, and the run's own token cannot stand in.** Opening a pull request with
`GITHUB_TOKEN` requires *Allow GitHub Actions to create and approve pull requests*, which grants
approving along with opening. Install an App with `Contents` and `Pull requests` write and nothing else,
keep its client id and private key in Actions secrets, and pass them by name as above — never
`secrets: inherit`, which would hand this every secret your repository holds. The token each run mints is
narrowed to those two scopes and expires in an hour. A secret you do not pass refuses the run before any
job exists — no job, no log, no annotation — exactly as a permission you do not grant does.

**If that key is rotated or the installation removed, no proposal is raised and nothing says so.** No
check reddens, because nothing failed — the run cannot mint a token.

**The proposal branch is `release/next`, and a version you put there wins.** Every merge refreshes the
branch and leaves a hand-edited version alone: the workflow records what it computed in a trailer on its
own commit, so a version disagreeing with that trailer is one a person decided.

**An empty range closes a standing proposal** rather than leaving one pending against a range the last
release already covers.

Prerequisites in the calling repository, on top of everything `release` needs: `uv` pinned in
`mise.toml` alongside `git-cliff`, and a `uv.lock`. The version is written to the manifest and the
lockfile in one commit, so a proposal never leaves the two disagreeing.

### 🧩 `dependency-review`

Reads the dependency-graph difference between a pull request's base and its head, and reddens on an
advisory at or above a severity floor. It is the only capability here judging what a change starts
depending on rather than what it says.

```yaml
jobs:
  guard:
    permissions:
      contents: read
    uses: turboBasic/github-actions/.github/workflows/dependency-review.yml@v0.1
```

Required context: `guard / dependency-review` — your own job id, then the called job's name. It may be
required only under `pull_request`: requiring it under any other event gives a check that reports
success without reading anything, because there is no base and no head to difference.

What reddens the check: an advisory at or above the severity floor. What only appears in the run's
output and never fails anything: a finding below the floor, an OpenSSF Scorecard warning, and an
unlicensed dependency — with no licence policy configured, a licence is reported and never refused;
refusing a named licence is a second input this capability does not take.

**Your repository's own dependency graph has to be switched on.** This capability cannot switch it on
for you: with the setting off, the run fails naming it and the `settings/security_analysis` path to
change it, and says it cannot make that change on your behalf.

## Versioning

The line is `0.x`. `1.0.0` waits for consumers to have exercised the surface, so the table below is the
live rule rather than a transitional one.

Pin the moving ref. It is force-moved to each release, last, after the release exists:

| While the version is | Pin | Because |
| --- | --- | --- |
| below `1.0.0` | `v0.1`, `v0.2`, … | below `1.0.0` a break is signalled by the minor, so a ref spanning the minor is the one that never crosses one |
| `1.0.0` and above | `v1`, `v2`, … | above it a break is signalled by the major |

`v0` is never published. It would span every pre-1.0 break at once, which is the one thing a moving ref
exists to prevent. Exact release tags are immutable, so pin one of those instead if you want no
movement at all.

Which component the boundary falls on is decided in exactly one function in the release decision unit,
and a test asserts nothing else decides it. Reading it off the major number alone is wrong below
`1.0.0`, and wrong in the permissive direction.

### Pinning

Third-party actions are pinned to a full commit SHA, with no exceptions and no mechanism for one — a
test asserts it over every `uses:` in the tree. Anything of this repository's own is reached with `$/`,
which GitHub resolves from the repository owning the file rather than from the workspace. That holds even
inside a reusable workflow running against your checkout, so nothing here needs to name a ref to reach
its own code, and there is nothing for you to bootstrap.

## Working in this repository

`AGENTS.md` is the map — it names every artefact and what that artefact answers. Start there.

`CONTRIBUTING.md` has the setup, the loop, how a change to a capability is verified, and how a release is
cut. Anything exploitable goes to `SECURITY.md`'s private report rather than an issue.
