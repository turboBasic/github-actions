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

### 🧩 `python-ci`

One check over a **Python project**: its own lint, typecheck and test tasks, run by its own task
runner, after installing from its own lockfile.

```yaml
jobs:
  ci:
    permissions:
      contents: read
    uses: turboBasic/github-actions/.github/workflows/python-ci.yml@v0.1
```

Required context: `ci / python-ci` — your own job id, then the called job's name.

Reach for it when the repository has a `pyproject.toml` and a current `uv.lock`. A repository without
a lockfile is out of scope rather than badly served: the lockfile check is not a stage that can be
switched off, because a verdict from a tree whose lockfile disagrees with its manifest is a verdict
about neither. The three stage switches are for a Python repository genuinely missing a stage, not a
route to using this without Python.

It needs, from `mise.toml` in the calling repository: the tasks it is asked to run, `uv`, and `prek`
if the changed-files lint is on. Those stay yours to pin — that is the only reason a local verdict and
this one agree — and a missing one fails the run naming the tool and where to declare it, rather than
with `command not found`.

Two things worth knowing before setting an input, and prose is the only place either fits:

- **The changed-files lint lets a pull request pass while the tree is broken.** It reads the pull
  request's own diff, so a finding in a file the pull request did not touch is never looked for.
  `prek-advisory` is what compensates — it lints the whole tree on the same pull request and reports
  in a comment rather than a check.
- **A repository holding its slow hooks back for a later stage has to name that stage**, or the
  changed-files lint fires the default stage and those hooks silently stop running on pull requests.
  Pass `prek-advisory` the same stage.

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

### 🧩 `pr-description`

Fills a pull request's body from the commits in its range, into your own template: the subjects as a
summary, the full messages as a change list with each body indented under its subject.

```yaml
name: describe-pr

on:
  pull_request:
    types: [opened]

jobs:
  describe:
    permissions:
      contents: read
      pull-requests: write
    uses: turboBasic/github-actions/.github/workflows/pr-description.yml@v0.1
```

Required context: `describe / pr-description`.

**You identify nothing.** No token, no pull request number, no repository, no commit range — the
capability owns its own full-history checkout and reads all of it from the run. That is not a
convenience: every one of those as an input is a value a call site can get wrong, and the one that
used to bite was checkout depth, which silently truncated the range. A test asserts none of them can
come back.

Your template needs two substitution points, each on a line of its own:

```markdown
## What changed

<!-- pr-description:summary -->

## Commits

<!-- pr-description:changes -->
```

They are HTML comments, so a template carrying them reads normally whether or not this ever runs. The
first becomes one line per commit subject; the second becomes one list item per commit with its body's
paragraphs indented underneath, paragraph breaks intact. Git trailers are dropped — a co-author line is
provenance, not a description of the change — while a `BREAKING CHANGE:` paragraph is kept. An empty
range leaves a comment rather than an empty heading, because a section with nothing under it reads as
one somebody forgot to write.

**It renders into the body, not over it.** GitHub pre-fills a new pull request's body from your
template, so on `opened` the markers are already in the body along with anything the author typed before
submitting — and rendering into the body is what keeps their prose. Three cases, so nothing a person
wrote is ever discarded:

| The body | What happens |
| --- | --- |
| carries both markers | rendered into, and everything else in it survives |
| has content but no markers | left alone, with a notice saying so — a person wrote it |
| is empty | the template is rendered and becomes the body |

Only that last case reads `template-path` at all, and only then does a template missing either marker
fail the run, naming which one and where to put it.

**The trigger is `opened` and nothing else.** Adding `synchronize` would rewrite the body on every
push, discarding whatever a human typed into it since — and the body is where they explain *why*, which
no renderer can reconstruct from commits.

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
    uses: turboBasic/github-actions/.github/workflows/python-ci.yml@v0.1

  release:
    needs: verify
    permissions:
      contents: write
    uses: turboBasic/github-actions/.github/workflows/release.yml@v0.1
    with:
      dry-run: ${{ github.event_name == 'workflow_dispatch' && inputs.dry-run }}
```

Required context: `release / tag-and-publish`.

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
then reachable from no event a fork can raise.

```yaml
name: propose-on-merge

on:
  push:
    branches: [main]

jobs:
  proposal:
    permissions:
      contents: read
    uses: turboBasic/github-actions/.github/workflows/release-proposal.yml@v0.1
    secrets:
      app-client-id: ${{ secrets.RELEASE_APP_CLIENT_ID }}
      app-private-key: ${{ secrets.RELEASE_APP_PRIVATE_KEY }}
```

Context composed: `proposal / propose`. There is nothing here for a ruleset to require — it runs on a
push, and it writes rather than judges.

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

### 🧩 `prek-advisory`

Lints the whole tree and reports it as one pull request comment, edited in place on later pushes rather
than duplicated, plus a job summary and a warning annotation. It is what compensates for `python-ci`'s
`lint-changed-only`: that reads the diff, this reads everything.

```yaml
name: advisory

on:
  pull_request:

jobs:
  advisory:
    permissions:
      contents: read
      pull-requests: write
    uses: turboBasic/github-actions/.github/workflows/prek-advisory.yml@v0.1
```

Context composed: `advisory / prek-advisory`. **Do not require it in a ruleset** — see below.

**A green check means the lint ran, not that it passed.** Only the lint's verdict is advisory. The
capability's own setup still fails the check: a missing tool, or a lockfile disagreeing with its
manifest, reddens it, because a tree that cannot be set up has not been linted. The findings themselves
never fail anything — they go in the comment.

That is also why requiring this context is a mistake rather than caution: it is green either way, so as
a required gate it would pass without judging anything, and a green check is the one nobody
investigates.

**`pull-requests: write` is not optional, and omitting it is the worst failure mode here.** The run
fails at startup before any job exists — no log, no annotation, nothing to read, and no condition can
skip past it. That write is the entire reason this is a separate capability from `python-ci`: a workflow
demanding it anywhere forces every caller to grant it, so keeping the two apart is what lets you take
CI without handing write access to your pull requests.

**Pass the same `hook-stage` you pass to `python-ci`.** Different stages mean the two runs disagree
about which checks apply, and the comment then reports on a set of hooks the blocking check never ran.

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
