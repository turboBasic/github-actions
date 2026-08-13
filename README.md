# github-actions

Reusable GitHub Actions workflows and composite actions shared across `turboBasic` repositories.

[![CI](https://github.com/turboBasic/github-actions/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/turboBasic/github-actions/actions/workflows/ci.yml?query=branch%3Amain)
[![License: MIT](https://img.shields.io/badge/licence-MIT-blue.svg)](LICENSE)

Conventions live in [`docs/ai-instructions.md`](docs/ai-instructions.md); how to send a change is
in [`CONTRIBUTING.md`](CONTRIBUTING.md). [`docs/consumers.md`](docs/consumers.md) lists which
repository calls what.

## Reusable workflows

### `python-ci.yml`

Lint, typecheck, and test a Python project through its `mise` tasks, so CI and `mise run ci` cannot
drift apart.

```yaml
jobs:
  ci:
    uses: turboBasic/github-actions/.github/workflows/python-ci.yml@v2
    permissions:
      contents: read
```

| Input | Default | Purpose |
| --- | --- | --- |
| `mise-version` | `""` | Pin the mise release; empty uses the action's default. |
| `run-lint` / `run-typecheck` / `run-tests` | `true` | Skip a stage a repo does not have. |
| `lint-task` / `typecheck-task` / `test-task` | `lint` / `typecheck` / `test` | Override a differently-named `mise` task. |
| `lint-changed-only` | `false` | Lint changed files via pre-commit instead of the lint task. |
| `hook-stage` | `""` | pre-commit hook stage for the changed-files run; empty is the default stage. |
| `cache-pre-commit` | `true` | Cache `~/.cache/pre-commit`, keyed on the config hash. |
| `timeout-minutes` | `20` | Job timeout. |

`contents: read` is all this workflow needs, and all you should grant it.

`lint-changed-only` is faster on a large tree but lets a PR pass while the tree is broken. Pair it
with [`precommit-advisory.yml`](#precommit-advisoryyml), which is the compensating control.

Set `hook-stage: pre-push` if the repo reserves its slow hooks for that stage — without it those
hooks silently stop running on PRs. Pass the same value to `precommit-advisory.yml` if you call it,
or the two runs disagree about which hooks apply.

Requires a `mise.toml` with the tasks being run, and a `uv.lock` (the workflow runs
`uv sync --locked` and fails on lockfile drift). Bumping the project version without re-running
`uv lock` is enough to fail it.

### `precommit-advisory.yml`

Runs pre-commit over every file, non-blocking, and reports the result as a single PR comment that is
updated in place on each push. The compensating control for `lint-changed-only`.

```yaml
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
| `hook-stage` | `""` | pre-commit hook stage; match what `python-ci.yml` is given. |
| `cache-pre-commit` | `true` | Cache `~/.cache/pre-commit`, keyed on the config hash. |
| `timeout-minutes` | `20` | Job timeout. |

**`pull-requests: write` is required at the call site.** A called workflow's job permissions are
validated when the run starts, before any `if:` can skip the job, so omitting it fails the whole run
as `startup_failure` — no job, no log, no diagnostic. That behaviour is why this is a separate
workflow: it used to be a job inside `python-ci.yml`, which forced *every* consumer to grant write
access whether or not it wanted the comment.

### `conventional-commits.yml`

Validates the PR title (what a squash merge uses) and every commit message in the range (what a
rebase merge puts on the default branch).

```yaml
jobs:
  commits:
    uses: turboBasic/github-actions/.github/workflows/conventional-commits.yml@v2
    permissions:
      contents: read
      pull-requests: read
```

| Input | Default | Purpose |
| --- | --- | --- |
| `check-title` | `true` | Validate the PR title. |
| `check-commits` | `true` | Validate commit messages via `cz check`. |
| `types` | commitizen's set | Newline-separated allowed types, authoritative for both checks. |
| `timeout-minutes` | `5` | Job timeout. |

Commit checking uses commitizen rather than commitlint, because the same tool enforces this in the
local `commit-msg` hook — local and CI verdicts cannot disagree.

`types` governs both jobs: it is compiled into a throwaway commitizen schema rather than read from
the consumer's `[tool.commitizen]`, so the title check and the commit check cannot disagree about
what is valid. The default matches commitizen's built-in set exactly — including `bump`, which
`cz bump` emits — so a commit the local `commit-msg` hook accepts cannot fail here. That equivalence
is asserted by `tests/test_action_pins.py`, not maintained by hand. Types must be bare words
(`[a-zA-Z0-9_-]`).

This workflow needs no `mise.toml` — it installs `uv` directly, so a repo with no mise config can
still have its commit messages checked.

## Composite actions

### `actions/precommit-advisory-pr`

Runs pre-commit over every file, non-blocking, and reports failures as a job summary plus a single
PR comment that is *updated* rather than duplicated on later pushes.

```yaml
- uses: turboBasic/github-actions/actions/precommit-advisory-pr@v2
  with:
    github-token: ${{ github.token }}
    hook-stage: pre-push # optional
```

Requires `pull-requests: write` and a `mise`-provisioned pre-commit.

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

Needs `pull-requests: write` and a full-history checkout (`fetch-depth: 0`).

## Versioning

Pin `@v2`. `v2.x.y` tags are immutable; `v2` is force-moved to each release, so fixes arrive on the
next run without a PR in every consumer. A change that breaks an existing call site gets a new
major tag instead.

`v1` is frozen at `v1.0.1` and is not maintained. It was never consumed: verifying it against a real
caller showed that `python-ci.yml` could not be called without granting `pull-requests: write`, and
splitting the advisory job out to fix that removed an input. That is a breaking contract change, so
it took a major tag rather than moving `v1`.

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
mise run setup   # uv sync --locked, then pre-commit install
mise run ci      # lint (actionlint + zizmor + ruff), typecheck, test
```

`actionlint` does not look outside `.github/workflows`, which is where none of the composite actions
live — `zizmor` covers both trees and is the security linter.
