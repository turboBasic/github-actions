# Contributing

This repo holds the CI that other `turboBasic` repositories run. A change here executes in every
consumer listed in [`docs/consumers.md`](docs/consumers.md) — read that list before starting.
Forking to suit your own conventions is an expected use; the [MIT licence](LICENSE) asks nothing
beyond keeping the notice.

Taking part means following the [Code of Conduct](CODE_OF_CONDUCT.md). Report anything exploitable
privately instead of opening an issue — see the [security policy](SECURITY.md).

## Read this first

[`docs/ai-instructions.md`](docs/ai-instructions.md) is the source of truth and binds humans and AI
tools alike. This file does not repeat it.

Start with [Changes to these rules](docs/ai-instructions.md#changes-to-these-rules): it marks which
rules are non-negotiable and what to do when a change would trade one away. The rest covers
[tooling](docs/ai-instructions.md#tooling-hierarchy),
[workflows and actions](docs/ai-instructions.md#workflows-and-actions),
[quality gates](docs/ai-instructions.md#quality-gates), and
[versioning](docs/ai-instructions.md#versioning).

## Setup

```sh
mise run setup   # uv sync --locked, then pre-commit install
```

One command; it wires up the `pre-commit` and `commit-msg` hooks together.

## The loop

```sh
mise run ci      # lint, typecheck, test — exactly what CI runs
```

`mise run lint`, `typecheck`, `test`, and `fmt` run the pieces while iterating. Lint means
`actionlint` over `.github/workflows`, `zizmor` over that *and* `actions/`, and `ruff` over the
Python.

## Verifying a workflow change

Lint is necessary and not sufficient. **A reusable workflow that has never been called is
unverified** — YAML that parses can still fail on a missing input, a permission it was not granted,
or an expression that evaluates to the wrong branch.

Before a change to a reusable workflow is done:

1. Push the branch and open a PR here, so this repo's own CI runs.
2. Call the changed workflow at `@<your-branch>` from a throwaway repository, and exercise both
   outcomes — the passing path and the failing one. A check that cannot fail is not a check.
3. Delete the throwaway repo afterwards.

`v1` is only moved once that has happened.

## Pull requests

Branch first. Title the PR as a Conventional Commit — a squash merge takes its subject from there.
Both workflows must pass.

Say which consumers a change affects and what you ran to verify it, and update
[`docs/consumers.md`](docs/consumers.md) and the [README](README.md) in the same change when an
input contract moves. Agent-written code is welcome; you are still the author of it.
