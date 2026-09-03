# AI Instructions

Source of truth for all AI coding tools (Claude Code, GitHub Copilot) working in this repo.
`CLAUDE.md` and `.github/copilot-instructions.md` both point here.

Scope: reusable GitHub Actions workflows and composite actions consumed by other
`turboBasic` repositories. This repo ships no application code — the Python here exists to test
the YAML.

Committed configuration is authoritative for settings it already declares — read `mise.toml`,
`pyproject.toml`, `.pre-commit-config.yaml` (prek reads this same file), and `.cspell.config.yaml`
rather than assuming. Extend
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

### Specs

Each `/speckit-*` skill documents its own step and `.specify/templates/` holds what they produce.
Read those, not a summary here.

`.specify/memory/constitution.md` is ours to edit — it states the non-negotiables above as gates a
spec fails against. Everything else under `.specify/` and `.claude/skills/speckit-*/` is vendored
and version-locked to the `pipx:specify-cli` pin in `mise.toml`: bump the pin and run
`mise run spec-kit-upgrade`, never `specify self upgrade`, which replaces the binary outside mise
and leaves `.specify/integrations/*.manifest.json` describing a version nothing here pins.

A spec is not the default path. Size decides:

| Change | Path |
| --- | --- |
| A README fix, a pin bump, a one-line workflow edit | issue → PR |
| A new input, a new workflow, a behaviour change consumers can see | `/speckit-specify` → `/speckit-plan` → `/speckit-tasks` → PR |
| Versioning, permissions policy, the pinning rule itself | decision record first, then a spec |

Specs, plans and task lists live only where Spec Kit puts them. Scratch — notes, throwaway drafts,
anything not meant to be reviewed — goes in `tmp/`, which is gitignored. `docs/` is for documentation
that ships.

A completed feature directory stays under `specs/` permanently and is never edited again — Spec Kit
calls this *flow-forward*, one of the three persistence models it names and declines to choose
between. A changed requirement gets a new numbered directory that cross-links the one it supersedes,
rather than a revision of a shipped one. So `specs/` is a record of how this repository got here, not
documentation: nothing in it is authoritative for current behaviour, which is `README.md`, `docs/`,
and the workflows themselves. Read a ticked `tasks.md` or a passed checklist as a work log of the
change that shipped it.

## Environment

### Tooling hierarchy

1. **Project task** — a `mise.toml` task (`lint`, `test`, `typecheck`, `fmt`). Never bypass it.
2. **prek** — `mise exec -- prek run`.
3. **`uv run <tool>`** — project-local Python tools.
4. **`mise exec -- <tool>`** — system tools mise manages (`actionlint`, `zizmor`, `shellcheck`).

Never `pip install`. Never activate a venv by hand. Nothing is installed globally: a new runtime or
CLI is pinned in `mise.toml`, which owns every version in its `[tools]` table — Python tool versions
are `pyproject.toml`'s.

**No `[tools]` entry is `latest`.** Each names a version, so two machines on one commit resolve the
same linters. `.github/renovate.json` enables the `mise` manager that bumps them, and
`tests/test_action_pins.py::test_no_mise_tool_version_floats` is what stops a new tool arriving
unpinned.

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
| `.github/workflows/*.yml` with `workflow_call` | reusable workflows | `turboBasic/github-actions/.github/workflows/<name>.yml@vN` |
| `.github/workflows/{ci,commit-messages,release}.yml` | this repo's own CI and its release | not referenced |
| `actions/<name>/action.yml` | composite actions | `turboBasic/github-actions/actions/<name>@vN` |

`vN` is the current major tag. `README.md`'s Versioning section declares which one that is, and is
the only place a major is written literally.

Composite actions live in `actions/`, not `.github/actions/`. The latter is the convention for
*repo-local* actions and would read as private-by-convention here.

- **Pin every third-party action to a full 40-character commit SHA**, with the version as a
  trailing `# vX.Y.Z` comment. A tag can be retroactively repointed at malicious code — this is
  not hypothetical: CVE-2025-30066 did exactly that to `tj-actions/changed-files`. Enforced by
  `tests/test_action_pins.py`.
- **First-party references use the moving major tag** (`@vN`), never a SHA. See **Versioning**.
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

- prek is the linting entry point. Never call `ruff` directly.
- `actionlint` covers `.github/workflows`; it does not look in `actions/`. `.github/actionlint.yaml`
  owns its ignores. `zizmor` covers both and is the security linter — a finding it raises is
  addressed, not silenced.
- `.yamllint.yaml` owns yamllint's rules and exempt paths.
- A new GitHub config file gets a `check-jsonschema` hook and a matching line in the `lint` task.
  Prefer `--builtin-schema` to `--schemafile <url>`: a vendored schema needs no network and cannot be
  repointed. `.github/zizmor.yml` gets none — its only published schema is served off a floating
  `main` ref, and zizmor rejects an unknown field in its own config anyway. `.github/actionlint.yaml`
  does get one, because actionlint accepts an unknown key there silently.
- pyright strict. Never a blanket `# type: ignore` or a loosened mode to clear an error.
- pytest. Never `unittest.TestCase`. `tests/` asserts properties of the YAML, since there is no
  application to test.
- **The suite is offline; `mise run ci` must never need the network.** The exceptions are marked
  `@pytest.mark.drift` and deselected by default, run by `mise run test-drift` from its own `ci.yml`
  job where a token exists. Reach for one only where the thing being asserted is repository state no
  file can express: the required status checks on the `main` ruleset, this repository still being
  public, which is what lets a private consumer resolve these workflows at all, and whether the major
  tag still predates a change consumers resolve.
- **Lint does not verify a workflow. Run it.** Exercise every changed workflow before tagging: a
  reusable one from a real PR, anything else from a dispatch. Every linter here passes on a workflow
  that fails on its first run, because the file is correct and its environment is not: the caller
  cannot know to grant a permission, an input resolves to nothing, or a CLI needs a context the
  runner lacks — `gh release create` reads the repository from a git remote and `release.yml` clones
  nothing, so the first dispatch died on that line with every gate green. A relative self-call
  exercises a reusable workflow (principle VI). Where behaviour turns on caller-side
  configuration — `python-ci.yml`'s `hook-stage`, `run-typecheck`, a consumer with no mise config —
  it does not, so a consumer exercises it at the ref it pins.
- **Pre-flight the line out of the file, never a retyping of it.** Retype it and you test your
  typing: that pre-flight typed the missing `--repo` and passed.
- **The allowed commit types are declared once**, as `conventional-commits.yml`'s `types` default,
  and asserted equal to commitizen's built-in set by `tests/test_action_pins.py`. Both the title and
  the commit-message check read it from there. It may not fall back to a tool's own default:
  commitizen's set and the action's differ, `bump` being the one that does.

## Shipping

### Versioning

Consumers pin a moving major tag rather than a SHA. This is a deliberate exception to the
SHA-pinning rule above, and the distinction matters: that rule exists because a *third party* can
repoint a tag. This repo shares its owner with every consumer, and SHA-pinning first-party
workflows would mean one Dependabot PR per consumer for every one-line fix.

A change to a workflow's input contract that would break an existing call site is a major bump — a
new major tag, with the old one left where it is — not a move of the current one.

**The version describes the consumer-facing surface, not this repository's commit history.** Judge a
bump by what changed under `.github/workflows/` and `actions/`; a `feat:` touching only our own
linting or editor config is a patch. So the number is a human decision recorded as a one-line diff to
`pyproject.toml`'s `[project].version`, merged like any other change, and never computed unattended.

`release-proposal.yml` proposes that diff, and **proposing is not deciding**: a reviewer may change the
number, and a version a human has edited survives every refresh. The release refuses if the tag already
exists, so it cannot disagree with the reviewed decision. Notes are rendered before any tag is created,
from commit types in `.cliff.toml` — never from a pull request label. `CONTRIBUTING.md`'s Releasing
section is the procedure.

Which major is current and which tags are immutable live in `README.md`'s
Versioning section. Read the value from there; never restate it here, or it goes stale at the next
bump and this file is what every AI tool loads.

### Git

- Conventional Commits, commitizen's default types. The PR title is held to the same format.
- Commit or push only when asked. Branch first if on the default branch.
- Never commit a secret.
- **Labels are on issues, never on a pull request.** A PR's kind is its Conventional Commit title and
  a second copy of that on a label is a second source of truth. Nothing automated reads a label —
  `CONTRIBUTING.md`'s Labels section owns the axes and what each one is for.

### CI

`mise run ci` reproduces CI locally.

**A self-call must use the self-repository form** — `$/.github/workflows/<name>.yml`, with no
`{owner}/{repo}` and no `@{ref}`. It resolves at the caller's own commit, so a change to the called
workflow is validated by the version under review; the `turboBasic/github-actions/...@vN` form
resolves at the tag and would validate it against the last good release. `commit-messages.yml` calls
`conventional-commits.yml` this way, and `ci.yml` calls `python-ci.yml` this way.
`tests/test_action_pins.py` enforces it, because every other gate accepts the tagged form too.

**Never write the older `./.github/workflows/<name>.yml`.** It resolves at the same commit, but
reaches the file through the runner's filesystem, so a step running earlier can substitute what gets
called; zizmor's `self-repository` audit rejects it. `$/` is unavailable on GitHub Enterprise Server —
nothing here targets it, and that is not a reason to reach for `./`.

actionlint 1.7.12 has not learned `$/` yet (rhysd/actionlint#711) and reports it as a malformed
call, so `.github/actionlint.yaml` ignores that one message — anchored on the `$/` prefix, so a
genuinely malformed ref still fails. This is the one silenced rule in the repo, and it silences a
false positive rather than a finding. It cannot outlive the bug: `test_the_actionlint_ignore_is_still_needed`
asserts actionlint still rejects `$/`, so the day #711 ships the suite says to delete the file. Do not
treat it as precedent — a second ignore needs the same two things, a false positive and an expiry.
