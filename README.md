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
    uses: turboBasic/github-actions/.github/workflows/python-ci.yml@v1
    permissions:
      contents: read
```

| Input | Default | Purpose |
| --- | --- | --- |
| `mise-version` | `""` | Pin the mise release; empty uses the action's default. |
| `run-lint` / `run-typecheck` / `run-tests` | `true` | Skip a stage a repo does not have. |
| `lint-task` / `typecheck-task` / `test-task` | `lint` / `typecheck` / `test` | Override a differently-named `mise` task. |
| `lint-changed-only` | `false` | Lint changed files via pre-commit instead of the lint task. |
| `advisory-all-files` | `false` | Non-blocking all-files lint reported as a PR comment. |
| `hook-stage` | `""` | pre-commit hook stage for the two runs above; empty is the default stage. |
| `cache-pre-commit` | `true` | Cache `~/.cache/pre-commit`, keyed on the config hash. |
| `timeout-minutes` | `20` | Job timeout. |

`lint-changed-only` is faster on a large tree but lets a PR pass while the tree is broken. Pair it
with `advisory-all-files: true`, which needs `pull-requests: write` at the call site.

Set `hook-stage: pre-push` if the repo reserves its slow hooks for that stage — both pre-commit runs
here honour it, and without it those hooks silently stop running on PRs.

Requires a `mise.toml` with the tasks being run, and a `uv.lock` (the workflow runs
`uv sync --locked` and fails on lockfile drift).

### `conventional-commits.yml`

Validates the PR title (what a squash merge uses) and every commit message in the range (what a
rebase merge puts on the default branch).

```yaml
jobs:
  commits:
    uses: turboBasic/github-actions/.github/workflows/conventional-commits.yml@v1
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
what is valid. The default is byte-equivalent to commitizen's built-in pattern. Types must be bare
words (`[a-zA-Z0-9_-]`).

This workflow needs no `mise.toml` — it installs `uv` directly, so a repo with no mise config can
still have its commit messages checked.

## Composite actions

### `actions/precommit-advisory-pr`

Runs pre-commit over every file, non-blocking, and reports failures as a job summary plus a single
PR comment that is *updated* rather than duplicated on later pushes.

```yaml
- uses: turboBasic/github-actions/actions/precommit-advisory-pr@v1
  with:
    github-token: ${{ github.token }}
    hook-stage: pre-push # optional
```

Requires `pull-requests: write` and a `mise`-provisioned pre-commit.

### `actions/populate-pr-description`

Renders the repo's PR template as a Jinja2 template, substituting `{{ description }}` with commit
subjects and `{{ changes }}` with full commit messages, then patches the PR body.

```yaml
- uses: turboBasic/github-actions/actions/populate-pr-description@v1
  with:
    github-token: ${{ github.token }}
    pr-number: ${{ github.event.pull_request.number }}
    repo: ${{ github.repository }}
    base-sha: ${{ github.event.pull_request.base.sha }}
    head-sha: ${{ github.event.pull_request.head.sha }}
```

Needs `pull-requests: write` and a full-history checkout (`fetch-depth: 0`).

## Versioning

Pin `@v1`. `v1.x.y` tags are immutable; `v1` is force-moved to each release, so fixes arrive on the
next run without a PR in every consumer. A change that breaks an existing call site gets a new
major tag instead.

One exception to that immutability: `python-ci.yml`'s advisory job references
`actions/precommit-advisory-pr@v1`, because a reusable workflow cannot interpolate its own ref into
a `uses:`. A consumer pinned to `@v1.2.3` therefore still gets the *current* `v1` composite action
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
