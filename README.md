# github-actions

Reusable GitHub Actions workflows and composite actions shared across `turboBasic` repositories.

[![CI][ci-badge]][ci-workflow]
[![License: MIT][license-badge]][license]

Conventions live in [`docs/ai-instructions.md`][ai-instructions]; how to send a change is
in [`CONTRIBUTING.md`][contributing]. [`docs/consumers.md`][consumers] lists which
repository calls what.

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
    uses: turboBasic/github-actions/.github/workflows/python-ci.yml@v2
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
| `cache-pre-commit` | `true` | Cache `~/.cache/prek`, keyed on the config hash. |
| `timeout-minutes` | `20` | Job timeout. |

`contents: read` is all this workflow needs, and all you should grant it.

`lint-changed-only` is faster on a large tree but lets a PR pass while the tree is broken. Pair it
with [`precommit-advisory.yml`][precommit-advisory-heading], which is the compensating control.

Set `hook-stage: pre-push` if the repo reserves its slow hooks for that stage — without it those
hooks silently stop running on PRs. Pass the same value to `precommit-advisory.yml` if you call it,
or the two runs disagree about which hooks apply.

Requires a `mise.toml` with the tasks being run, and a `uv.lock` — the workflow runs
`uv sync --locked`, so any lockfile drift fails it, including a project version bumped without
re-running `uv lock`.

### `precommit-advisory.yml`

Runs prek over every file, non-blocking, and reports the result as a single PR comment that is
updated in place on each push. The compensating control for `lint-changed-only`.

```yaml
on:
  pull_request:

permissions:
  contents: read
  pull-requests: write

jobs:
  advisory:
    uses: turboBasic/github-actions/.github/workflows/precommit-advisory.yml@v2
    permissions:
      contents: read
      pull-requests: write
```

| Input | Default | Purpose |
| --- | --- | --- |
| `mise-version` | `""` | Pin the mise release; empty uses the action's default. |
| `hook-stage` | `""` | prek hook stage; match what `python-ci.yml` is given. |
| `cache-pre-commit` | `true` | Cache `~/.cache/prek`, keyed on the config hash. |
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
    uses: turboBasic/github-actions/.github/workflows/conventional-commits.yml@v2
    permissions:
      contents: read
      pull-requests: read
```

**Spell out `types` and include `edited`.** A bare `pull_request:` subscribes to the default activity
types, which do not include it — so a rejected title stays rejected until something is pushed, and
correcting a title is an edit, not a push. Keep it in its own workflow, or every title edit re-runs
your whole suite.

**`pull-requests: read` is required at the call site**, at both levels shown above, and for the same
reason `precommit-advisory.yml` needs `write`: permissions are validated before any job exists, so a
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

## Composite actions

### `actions/precommit-advisory-pr`

Runs prek over every file, non-blocking, and reports failures as a job summary plus a single
PR comment that is *updated* rather than duplicated on later pushes.

```yaml
- uses: turboBasic/github-actions/actions/precommit-advisory-pr@v2
  with:
    github-token: ${{ github.token }}
    hook-stage: pre-push # optional
```

Requires `pull-requests: write` and a `mise`-provisioned prek.

### `actions/populate-pr-description`

Renders the repo's PR template as a Jinja2 template, substituting `{{ description }}` with commit
subjects and `{{ changes }}` with full commit messages, then patches the PR body.

```yaml
- uses: turboBasic/github-actions/actions/populate-pr-description@v2
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

## Versioning

Pin `@v2`. `v2.x.y` tags are immutable; `v2` is force-moved to each release, so fixes arrive on the
next run without a PR in every consumer. A change that breaks an existing call site gets a new
major tag instead.

`v1` is frozen and unmaintained.

One exception to that immutability: `precommit-advisory.yml` references
`actions/precommit-advisory-pr@v2`, because a reusable workflow cannot interpolate its own ref into
a `uses:`. A consumer pinned to `@v2.1.3` therefore still gets the *current* `v2` composite action
in that one job. Pin the action directly in your own workflow if you need it frozen.

This is a deliberate exception to the rule that actions are pinned to a full SHA. That rule exists
because a third party can retroactively repoint a tag — CVE-2025-30066 did precisely that to
`tj-actions/changed-files`. This repo shares its owner with every consumer, so the threat model
differs, and SHA-pinning it would mean one dependency PR per consumer for every one-line fix.

Third-party actions *inside* this repo are pinned to full SHAs with no exception, enforced by
`tests/test_action_pins.py`.

## Local development

```sh
mise run setup   # uv sync --locked, then prek install
mise run ci      # lint, schema validation, typecheck, test
```

`actionlint` does not look outside `.github/workflows`, which is where none of the composite actions
live — `zizmor` covers both trees and is the security linter. `yamllint` covers all YAML, including
the config files under `.github/` that neither of the other two reads, and `mise run lint-schemas`
validates those against their published JSON schemas.

<!-- Links -->

[ci-badge]: https://github.com/turboBasic/github-actions/actions/workflows/ci.yml/badge.svg?branch=main
[ci-workflow]: https://github.com/turboBasic/github-actions/actions/workflows/ci.yml?query=branch%3Amain
[license-badge]: https://img.shields.io/badge/licence-MIT-blue.svg
[license]: LICENSE
[ai-instructions]: docs/ai-instructions.md
[contributing]: CONTRIBUTING.md
[consumers]: docs/consumers.md
[precommit-advisory-heading]: #precommit-advisoryyml
[job-conditions]: https://docs.github.com/en/actions/using-jobs/using-conditions-to-control-job-execution
