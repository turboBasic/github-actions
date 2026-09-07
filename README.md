# github-actions

Reusable GitHub Actions workflows and composite actions shared across `turboBasic` repositories.

[![CI][ci-badge]][ci-workflow]
[![Drift][drift-badge]][drift-workflow]
[![License: MIT][license-badge]][license]

Conventions live in [`docs/ai-instructions.md`][ai-instructions]; how to send a change is
in [`CONTRIBUTING.md`][contributing].

## Reusable workflows

### `python-ci.yml`

Lint, typecheck, and test a Python project through its `mise` tasks, so CI and `mise run ci` cannot
drift apart.

```yaml
on:
  push:
    branches: [main]
  pull_request:

permissions:
  contents: read

concurrency:
  group: ${{ github.workflow }}-${{ github.head_ref || github.run_id }}
  cancel-in-progress: true

jobs:
  ci:
    uses: turboBasic/github-actions/.github/workflows/python-ci.yml@v4
    permissions:
      contents: read
```

`concurrency` has to be set here: a reusable workflow cannot set its caller's group.

| Input | Default | Purpose |
| --- | --- | --- |
| `mise-version` | `""` | Pin the mise release; empty uses the action's default. |
| `run-lint` / `run-typecheck` / `run-tests` | `true` | Skip a stage a repo does not have. |
| `lint-task` / `typecheck-task` / `test-task` | `lint` / `typecheck` / `test` | Override a differently-named `mise` task. |
| `lint-changed-only` | `false` | Lint changed files via prek instead of the lint task. |
| `hook-stage` | `""` | prek hook stage for the changed-files run; empty is the default stage. |
| `cache-prek` | `true` | Cache `~/.cache/prek`, keyed on the config hash. |
| `timeout-minutes` | `20` | Job timeout. |

`contents: read` is all this workflow needs, and all you should grant it.

`lint-changed-only` is faster on a large tree but lets a PR pass while the tree is broken. Pair it
with [`prek-advisory.yml`][prek-advisory-heading], which is the compensating control.

Set `hook-stage: pre-push` if the repo reserves its slow hooks for that stage — without it those
hooks silently stop running on PRs. Pass the same value to `prek-advisory.yml` if you call it,
or the two runs disagree about which hooks apply.

Requires a `mise.toml` with the tasks being run, and a `uv.lock` — the workflow runs
`uv sync --locked`, so any lockfile drift fails it, including a project version bumped without
re-running `uv lock`.

### `prek-advisory.yml`

Runs prek over every file, non-blocking, and reports the result as a single PR comment that is
updated in place on each push. The compensating control for `lint-changed-only`.

Non-blocking covers prek's verdict, not the job: a lint finding becomes a comment, while this
workflow's own setup still fails it. It runs `uv sync --locked` first, so lockfile drift reddens this
check as well as `python-ci.yml`'s. That is deliberate — a broken lockfile is not a lint opinion to
report and move past — but it means a green check here means prek ran, not that prek passed.

```yaml
on:
  pull_request:

permissions:
  contents: read
  pull-requests: write

jobs:
  advisory:
    uses: turboBasic/github-actions/.github/workflows/prek-advisory.yml@v4
    permissions:
      contents: read
      pull-requests: write
```

| Input | Default | Purpose |
| --- | --- | --- |
| `mise-version` | `""` | Pin the mise release; empty uses the action's default. |
| `hook-stage` | `""` | prek hook stage; match what `python-ci.yml` is given. |
| `cache-prek` | `true` | Cache `~/.cache/prek`, keyed on the config hash. |
| `timeout-minutes` | `20` | Job timeout. |

Trigger on `pull_request`: the job is gated on that event name and silently skips under any other,
`pull_request_target` included.

**`pull-requests: write` is required at the call site.** A called workflow's job permissions are
validated when the run starts, before any `if:` can skip the job, so omitting it fails the whole run
as `startup_failure` — no job, no log, no diagnostic. It is a separate workflow so that only the
repositories wanting the comment grant write access.

### `conventional-commits.yml`

Validates the PR title (what a squash merge uses) and every commit message in the range (what a
rebase merge puts on the default branch).

```yaml
on:
  pull_request:
    types: [opened, edited, reopened, synchronize]

permissions:
  contents: read
  pull-requests: read

jobs:
  commits:
    uses: turboBasic/github-actions/.github/workflows/conventional-commits.yml@v4
    permissions:
      contents: read
      pull-requests: read
```

**Spell out `types` and include `edited`.** A bare `pull_request:` subscribes to the default activity
types, which do not include it — so a rejected title stays rejected until something is pushed, and
correcting a title is an edit, not a push. Keep it in its own workflow, or every title edit re-runs
your whole suite.

**`pull-requests: read` is required at the call site**, at both levels shown above, and for the same
reason `prek-advisory.yml` needs `write`: permissions are validated before any job exists, so a
caller granting less fails the run as `startup_failure`.

| Input | Default | Purpose |
| --- | --- | --- |
| `check-title` | `true` | Validate the PR title. |
| `check-commits` | `true` | Validate commit messages via `cz check`. |
| `types` | commitizen's set | Newline-separated allowed types, authoritative for both checks. |
| `timeout-minutes` | `5` | Job timeout. |

**Trigger on `pull_request`, never `pull_request_target`.** Both jobs are gated on
`github.event_name == 'pull_request'`, and a skipped job
[reports success][job-conditions],
so under `pull_request_target` this becomes a required check that passes without validating anything.
The commit job's checkout would also resolve the base ref rather than the commits under review.
Adding `push` alongside `pull_request` is fine: both jobs skip, which is what you want on a push.
The same holds for `check-title: false` and `check-commits: false`, which gate the same conditions:
drop a check and remove its context from your required status checks in the same change, or the
branch protection page keeps showing a gate that is no longer there.

Commit checking uses commitizen rather than commitlint, because the same tool enforces this in the
local `commit-msg` hook — local and CI verdicts cannot disagree.

`types` governs both jobs: it is compiled into a throwaway commitizen schema rather than read from
the consumer's `[tool.commitizen]`, so the title check and the commit check cannot disagree about
what is valid. The default is commitizen's own set, including `bump` as `cz bump` emits it, so a
commit the local `commit-msg` hook accepts cannot fail here. Types must be bare words
(`[a-zA-Z0-9_-]`).

This workflow needs no `mise.toml` — it installs `uv` directly, so a repo with no mise config can
still have its commit messages checked.

### `dependency-review.yml`

Reads the PR's dependency-graph diff against GitHub's advisory database and license policy. Renovate
proposes upgrades for dependencies it already knows about, on its own schedule — this instead gates
the PR that introduces a new one.

```yaml
on:
  pull_request:

permissions:
  contents: read

jobs:
  deps:
    uses: turboBasic/github-actions/.github/workflows/dependency-review.yml@v4
    permissions:
      contents: read
```

| Input | Default | Purpose |
| --- | --- | --- |
| `fail-on-severity` | `""` | Minimum advisory severity that fails the check; empty uses the action's own default. |
| `timeout-minutes` | `10` | Job timeout. |

`contents: read` is all this needs. Pass `comment-summary-in-pr` yourself in a fork of this workflow
if you want the summary posted as a PR comment too — that needs `pull-requests: write`, which this
workflow does not request, for the same reason `python-ci.yml` does not: a caller wanting write
access should have to ask for it in a workflow that says so.

### `release.yml`

Cuts this repository's own releases, and callable so that a consumer can cut its own the same way.
Refuses unless `[project].version` is ahead of every existing release, the notes render something, and
a range that breaks the consumer surface carries a new major; renders the notes before creating any
ref, so a failure leaves no tag behind. The version tag is annotated, the release is published from
those notes, and the major tag moves last.

**Declare your consumer surface** so that last refusal is measured against your layout. It goes in the
`pyproject.toml` of the repository being released — the same file whose `[project].version` decides which
version that is — and both keys are optional:

```toml
[tool.turbobasic-release]
surface-include = ["src/**"]
surface-exclude = ["src/**/_generated/**"]
```

Entries are `git-cliff` path globs. They narrow only the breaking-change refusal: the notes always
describe the whole range, and the other two refusals never looked at paths.

| Your `pyproject.toml` | The refusal considers | The run says |
| --- | --- | --- |
| no `[tool.turbobasic-release]` table | every path in the range | a notice naming the omission |
| a table declaring paths | only what you declared | nothing |
| a table with both lists empty | every path in the range | nothing — you decided |

Declaring nothing is safe in the direction that matters: the refusal fires more often, never less, so it
cannot let a breaking change through under a patch. The cost is a release refused over a change nothing of
yours resolves. There is deliberately **no input** to override this — an input would have to default to
something, and one repository's layout is right for another only by coincidence.

A path is rejected, before any tag exists, if it is empty, holds whitespace, or begins with `-`: the flags
reach the renderer as one whitespace-split line, so such a path would be split in two or read as a flag.
So is a key other than those two — a misspelled `surface_include` would otherwise read as an absent key,
leaving you with the unfiltered range and nothing said about it.

```yaml
# .github/workflows/release-on-merge.yml
on:
  push:
    branches: [main]
  workflow_dispatch:
    inputs:
      dry-run:
        description: Run every refusal and render the real notes, then stop before creating any tag.
        type: boolean
        default: false

permissions: {}

jobs:
  verify:
    uses: turboBasic/github-actions/.github/workflows/python-ci.yml@v4
    permissions:
      contents: read

  release:
    needs: [verify]
    uses: turboBasic/github-actions/.github/workflows/release.yml@v4
    with:
      # `inputs` does not exist on the push path, so `|| false` is what makes this the boolean the
      # input's type demands.
      dry-run: ${{ inputs.dry-run || false }}
    permissions:
      contents: write # creates the version tag, publishes the release, moves the major tag
```

| Input | Default | Purpose |
| --- | --- | --- |
| `dry-run` | `false` | Run every refusal and render the real notes, then stop before creating any tag. |

**Give the release its own workflow rather than a job in your CI one.** A refused or failed release
then reddens the release, and your CI badge keeps answering for the code alone.

**`needs: [verify]` is the CI verdict**, and gating on a job rather than on a `workflow_run` trigger is
deliberate: the release cannot start unless CI passed on this exact commit, so there is no check run to
query and no race to lose. Point `needs:` at whichever job reports your required context. Verifying in
this workflow means running CI twice on the merge commit — that is the price of a separate run, since a
`needs:` edge is the only verdict structurally true on the commit being tagged.

This workflow has **no trigger of its own** — `workflow_call` only — so that edge is the only gate and
nothing can reach the tagging step around it. A manual release therefore goes through your caller, which
is what the `workflow_dispatch` above is for.

Requires a `.cliff.toml` — the notes come from commit types, never from a pull request label — and a
`pyproject.toml` declaring `[project].version`, which is what decides the version being cut. Also a
checkout with full history and tags, which the workflow does itself.

On an ordinary merge, where the declared version is already tagged, it says so with a notice and
stops rather than failing, so it does not redden `main` for doing nothing wrong.

## Composite actions

### `actions/prek-advisory-pr`

Runs prek over every file, non-blocking, and reports failures as a job summary plus a single
PR comment that is *updated* rather than duplicated on later pushes.

```yaml
- uses: turboBasic/github-actions/actions/prek-advisory-pr@v4
  with:
    github-token: ${{ github.token }}
    hook-stage: pre-push # optional
```

Requires `pull-requests: write` and a `mise`-provisioned prek.

### `actions/populate-pr-description`

Renders the repo's PR template as a Jinja2 template, substituting `{{ description }}` with commit
subjects and `{{ changes }}` with full commit messages, then patches the PR body.

```yaml
- uses: turboBasic/github-actions/actions/populate-pr-description@v4
  with:
    github-token: ${{ github.token }}
    pr-number: ${{ github.event.pull_request.number }}
    repo: ${{ github.repository }}
    base-sha: ${{ github.event.pull_request.base.sha }}
    head-sha: ${{ github.event.pull_request.head.sha }}
```

Needs `pull-requests: write` and a full-history checkout (`fetch-depth: 0`) — commit subjects come
from the range, so a shallow clone renders an empty body. It installs `uv` itself; the caller needs no
Python or `uv` setup. `template-path` overrides the default `.github/PULL_REQUEST_TEMPLATE.md`.

### `actions/release-decisions`

Answers one release question — `verify-version`, `check-notes`, `next-version`, `declared-version` or
`surface-args` — from files and environment variables, writing its answers to `GITHUB_OUTPUT` and its
verdicts as `::notice::` / `::error::`. It exits non-zero to say the caller should not proceed.
`surface-args` reads `[tool.turbobasic-release]` from the `pyproject` it is given, which is the released
repository's — see `release.yml` above.

```yaml
- uses: turboBasic/github-actions/actions/release-decisions@v4
  with:
    decision: verify-version
    tag-refs: ${{ steps.tags.outputs.refs }}
```

`release.yml` and `release-proposal.yml` are its only callers, and nothing outside this repository has
a reason to be one — it exists so their decisions can be tested offline rather than asserted as text.
It does no network I/O and declares no permissions: `gh api` and `git-cliff` stay in the calling
workflow, and their results arrive as an input path or a string. Needs `python3` in the job, which
`mise-action` provides.

## Versioning

Pin `@v4`. `v4.x.y` tags are immutable; `v4` is force-moved to each release, so fixes arrive on the
next run without a PR in every consumer. Anything a consumer cannot absorb by resolving the new ref
alone — a broken call site, a retired status-check context, a permission it must grant — gets a new
major tag instead.

**If your own project is at `0.x`, `release.yml` publishes a two-part moving ref and you pin that.** Under
[SemVer §4](https://semver.org/#spec-item-4) a `0.y.z` carries no stability guarantee and the component
signalling a break is the minor, so the minor is what a moving ref may not cross:

| Your release | Immutable | Moving |
| --- | --- | --- |
| `0.1.0`, then `0.1.1` | `v0.1.0`, `v0.1.1` | `v0.1`, moved to each |
| `0.2.0` | `v0.2.0` | `v0.2` is created; `v0.1` stays at `0.1.1` |
| `1.0.0` | `v1.0.0` | `v1` |

So pin `v0.1` and you get fixes and features and never a break — the same deal `v4` gives, one component
down. **No `v0` is ever published**, because it would have to span every 0.x break. A breaking change may
ship as `0.2.0` rather than being forced to `1.0.0`, and a `feat` under `0.x` advances the patch, since a
minor bump would leave the line you are pinned to.

`v3` is frozen where it is, and so is `v2` before it. Both resolve check names that no longer
exist on `main`: `v4` renamed every job whose name composes one, so the three required contexts
became `ci / python-ci`, `commits / pr-title` and `commits / commit-messages`. A required
check that stops reporting blocks every pull request, so **update your required status checks in the
same change as the ref** — nothing else about the call sites moved. `v3` also renamed
`precommit-advisory.yml` to `prek-advisory.yml` and `actions/precommit-advisory-pr` to
`actions/prek-advisory-pr`, so a consumer coming from `v2` changes those two paths as well.

`v4` moves when a release is cut, and cutting one is approving a pull request: after a merge to
`main` a bot opens a proposal carrying the next version and the exact notes it would publish, and
merging that proposal tags and releases once CI passes on it. Nothing is built or published from
here, so the tag itself is the artifact. The procedure, and what decides the next version, are in
[CONTRIBUTING][contributing-releasing].

One exception to that immutability: `prek-advisory.yml` references
`actions/prek-advisory-pr@v4`, because a reusable workflow cannot interpolate its own ref into
a `uses:`. A consumer pinned to `@v4.0.1` therefore still gets the *current* `v4` composite action
in that one job. Pin the action directly in your own workflow if you need it frozen.

This is a deliberate exception to the rule that actions are pinned to a full SHA. That rule exists
because a third party can retroactively repoint a tag. This repo shares its owner with every
consumer, so the threat model differs, and SHA-pinning it would mean one dependency PR per consumer
for every one-line fix.

Third-party actions *inside* this repo are pinned to full SHAs with no exception, enforced by
`tests/test_action_pins.py`.

## Local development

```sh
mise run setup     # uv sync --locked, then prek install
mise run ci        # lint, typecheck, test — offline
mise run test-drift # check GitHub's own state against the tree: the main ruleset, this repo's
                    # public visibility, and whether the major tag is behind a change consumers
                    # resolve
```

`actionlint` does not look outside `.github/workflows`, which is where none of the composite actions
live — `zizmor` covers both trees and is the security linter. `yamllint` covers all YAML, including
the config files under `.github/` that neither of the other two reads, and `check-jsonschema`
validates those against their published JSON schemas.

<!-- Links -->

[ci-badge]: https://github.com/turboBasic/github-actions/actions/workflows/ci.yml/badge.svg?branch=main
[ci-workflow]: https://github.com/turboBasic/github-actions/actions/workflows/ci.yml?query=branch%3Amain
[drift-badge]: https://github.com/turboBasic/github-actions/actions/workflows/drift.yml/badge.svg?branch=main
[drift-workflow]: https://github.com/turboBasic/github-actions/actions/workflows/drift.yml?query=branch%3Amain
[license-badge]: https://img.shields.io/badge/licence-MIT-blue.svg
[license]: LICENSE
[ai-instructions]: docs/ai-instructions.md
[contributing]: CONTRIBUTING.md
[contributing-releasing]: CONTRIBUTING.md#releasing
[prek-advisory-heading]: #prek-advisoryyml
[job-conditions]: https://docs.github.com/en/actions/using-jobs/using-conditions-to-control-job-execution
