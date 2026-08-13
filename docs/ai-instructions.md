# AI Instructions

Source of truth for all AI coding tools (Claude Code, GitHub Copilot) working in this repo.
`CLAUDE.md` and `.github/copilot-instructions.md` both point here.

Scope: reusable GitHub Actions workflows and composite actions consumed by other
`turboBasic` repositories. This repo ships no application code — the Python here exists to test
the YAML.

Committed configuration is authoritative for settings it already declares — read `mise.toml`,
`pyproject.toml`, `.pre-commit-config.yaml`, and `cspell.config.yaml` rather than assuming. Extend
those files; never regenerate them.

## Working style

- Read the file, run the tool, check the config rather than guessing at structure or conventions.
- Ask when genuinely ambiguous; take the sensible default otherwise and say so.
- Match existing patterns over personal preference.
- Scope to the request. No refactoring adjacent code or improving what was not asked about.

### Changes to these rules

A rule is **non-negotiable** when breaking it is irreversible, weakens security, or silently
breaks a consumer: a third-party action on a floating ref, a breaking change to a workflow's input
contract shipped under the same major tag, `pull_request_target` combined with a checkout of the
head ref, a secret written anywhere, a blanket `# type: ignore` or a loosened tool mode.
Everything else here is a convention: follow it, but a request to change it is just a request.

Treat a change to a non-negotiable as a design change, not a task. Before implementing one, in a
short paragraph: name the rule, state concretely what breaks without it, and offer the smallest
alternative that still meets the underlying need. Then stop and wait.

- **Report the conflict even when it is incidental.** A change that erodes one of these as a side
  effect gets the same treatment as a request to drop it outright.
- **Once the objection is heard and the request restated, implement it fully.** Do not relitigate
  or leave the old path in place as a safety net.
- **Never weaken one silently** to make a task easier.
- Do not object over conventions: naming, file placement, or how a test is organised.

## Environment

### Tooling hierarchy

1. **Project task** — a `mise.toml` task (`lint`, `test`, `typecheck`, `fmt`). Never bypass it.
2. **Pre-commit** — `mise exec -- pre-commit run`.
3. **`uv run <tool>`** — project-local Python tools.
4. **`mise exec -- <tool>`** — system tools mise manages (`actionlint`, `zizmor`, `shellcheck`).

Never `pip install`. Never activate a venv by hand. Nothing is installed globally: a new runtime or
CLI is pinned in `mise.toml`.

### Dependencies

- Dev deps in `[dependency-groups].dev`. `[project].dependencies` stays empty — nothing is
  published from here.
- Run `uv lock` after editing dependencies and commit the result in the same change.
- Introducing a new file type updates `.editorconfig`, `.gitattributes`, and `.gitignore` in the
  same change.

## Code

### Workflows and actions

The repository layout is load-bearing:

| Path | Contents | Referenced as |
| --- | --- | --- |
| `.github/workflows/*.yml` with `workflow_call` | reusable workflows | `turboBasic/github-actions/.github/workflows/<name>.yml@v1` |
| `.github/workflows/{ci,semantic-pull-request}.yml` | this repo's own CI | not referenced |
| `actions/<name>/action.yml` | composite actions | `turboBasic/github-actions/actions/<name>@v1` |

Composite actions live in `actions/`, not `.github/actions/`. The latter is the convention for
*repo-local* actions and would read as private-by-convention here.

- **Pin every third-party action to a full 40-character commit SHA**, with the version as a
  trailing `# vX.Y.Z` comment. A tag can be retroactively repointed at malicious code — this is
  not hypothetical: CVE-2025-30066 did exactly that to `tj-actions/changed-files`. Enforced by
  `tests/test_action_pins.py`.
- **First-party references use the moving major tag** (`@v1`), never a SHA. See **Versioning**.
- **Every input needs a `description` and an explicit `default`** unless genuinely required. A
  consumer reads the input list as the contract.
- **Declare the narrowest `permissions`** the workflow needs. Permissions can only be reduced down
  a call chain, never elevated, so a reusable workflow that asks for too much cannot be constrained
  by its caller.
- **`env` does not propagate from caller to called workflow.** Anything a reusable workflow needs
  must arrive as an `input`.
- **Interpolate untrusted values through `env`, not directly into `run:`.** A PR title or branch
  name inlined as `${{ }}` in a shell line is a script-injection vector.
- **`concurrency` belongs to the caller**, `timeout-minutes` to the callee. A reusable workflow
  cannot set its caller's concurrency group.

### Python

Python 3.14. The only Python here supports the actions and their tests.

- `X | None`, not `typing.Optional`. Built-in `dict`/`list`, not `typing.Dict`.
- No `from __future__ import annotations`.
- Full type hints on every signature, tests included.
- A script invoked by a composite action reads its arguments from the environment, declared in
  `action.yml`. It never parses `${{ }}` interpolations inline.

### Comments and docs

- No docstrings. No multi-line comment blocks.
- Comments only where the WHY is non-obvious, never restating what the code does.
- `README.md` is the consumer-facing contract: what each workflow does, its inputs, and a call site
  that can be copied as-is. A new input or a changed default updates it in the same change.
- `docs/consumers.md` records which repository calls what. Keep it current — it is the blast-radius
  list for any change to a workflow.
- Every change ends by checking the documentation it affects and correcting it in the same change.
  Stale framing is a defect, not a follow-up.

## Quality gates

- Pre-commit is the linting entry point. Never call `ruff` directly.
- `actionlint` covers `.github/workflows`; it does not look in `actions/`. `zizmor` covers both and
  is the security linter — a finding it raises is addressed, not silenced.
- pyright strict. Never a blanket `# type: ignore` or a loosened mode to clear an error.
- pytest. Never `unittest.TestCase`. `tests/` asserts properties of the YAML, since there is no
  application to test.
- A workflow change is not verified by lint alone. A reusable workflow that has never been called
  is unverified: exercise it from a real PR before tagging. Every linter here passes on a workflow
  that no caller can run — a permission the caller cannot know to grant, an input that resolves to
  nothing — because nothing is wrong with the file in isolation.
- **The allowed commit types are written out in two workflows** — `conventional-commits.yml`'s
  `types` default and `semantic-pull-request.yml`'s `types` input — and both are asserted equal to
  commitizen's built-in set by `tests/test_action_pins.py`. Neither may be edited alone, and neither
  may fall back to a tool's own default: commitizen's set and the actions' sets differ.

## Shipping

### Versioning

Consumers pin `@v1`; `v1.x.y` tags are immutable and `v1` is force-moved to each release. This is
a deliberate exception to the SHA-pinning rule above, and the distinction matters: that rule exists
because a *third party* can repoint a tag. This repo shares its owner with every consumer, and
SHA-pinning first-party workflows would mean one Dependabot PR per consumer for every one-line fix.

A change to a workflow's input contract that would break an existing call site is a major bump —
a new `v2` tag, with `v1` left where it is — not a `v1` move.

### Git

- Conventional Commits, commitizen's default types. The PR title is held to the same format.
- Commit or push only when asked. Branch first if on the default branch.
- Never commit a secret.

### CI

`mise run ci` reproduces CI locally. This repo's own CI runs the checks inline rather than calling
its own reusable workflows: a `workflow_call` reference resolves at the called ref, so a broken
change would be validated by the last good tag and pass.
