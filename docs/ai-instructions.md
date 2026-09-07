# AI Instructions

The conventions layer: how work is done here, binding humans and AI coding tools (Claude Code, GitHub
Copilot) alike. The invariants are a layer above and are cited here by principle number; the entry
point says where every kind of instruction lives.

Scope: reusable GitHub Actions workflows and composite actions consumed by other
`turboBasic` repositories. This repo ships no application. Its Python is of two kinds: the test suite,
which asserts properties of the YAML, and the modules a composite action runs — where a
decision the YAML used to make in shell now lives, so that it can be tested at all.

Committed configuration is authoritative for settings it already declares: read it rather than
assuming, extend it, and never regenerate it. The entry point names which file holds what.

## Working style

- Read the file, run the tool, check the config rather than guessing at structure or conventions.
- Ask when genuinely ambiguous; take the sensible default otherwise and say so.
- Match existing patterns over personal preference.
- Scope to the request. No refactoring adjacent code or improving what was not asked about.

A user-level instruction file is concatenated into context ahead of this one with no override
mechanism, so a contradiction between the two has nowhere else to be resolved.
**This repository's rules win where they are stricter.** Two are live today. A user-level file that
permits a third-party action pinned to a tag rather than a full SHA does not permit one here, and one
that permits `@main` for an in-house reference does not permit it here.

### Changes to these rules

These rules are one layer of four. Each fact has exactly one owning layer; a layer needing a fact it
does not own cites the owner instead of restating it; and a citation runs from the concrete to the
abstract only. So this file cites a principle by number, and nothing more abstract than it cites
back. Which layer owns what is navigation, and the entry point answers it.

Everything in this file is a convention: follow it, but a request to change one is just a request,
and objecting over it is this layer exceeding its own standing. What may never be violated is not
stated here, and neither is what a request to erode one of those obliges — the invariants layer's
Governance section owns both.

- **Once the objection is heard and the request restated, implement it fully.** Do not relitigate
  or leave the old path in place as a safety net.
- **Never weaken an invariant silently** to make a task easier.

### Specs

Each `/speckit-*` skill documents its own step and `.specify/templates/` holds what they produce.
Read those, not a summary here.

`.specify/memory/constitution.md` is ours to edit — it states the invariants as gates a
spec fails against. Everything else under `.specify/` and `.claude/skills/speckit-*/` is vendored
and version-locked to the `pipx:specify-cli` pin mise holds: bump the pin and run
`mise run spec-kit-upgrade`, never `specify self upgrade`, which replaces the binary outside mise.

A spec is not the default path. Size decides:

| Change | Path |
| --- | --- |
| A README fix, a pin bump, a one-line workflow edit | issue → PR |
| A new input, a new workflow, a behaviour change consumers can see | `/speckit-specify` → `/speckit-plan` → `/speckit-tasks` → PR |
| Versioning, permissions policy, the pinning rule itself | decision record first, then a spec |

Specs, plans and task lists live only where Spec Kit puts them. Scratch — notes, throwaway drafts,
anything not meant to be reviewed — goes in `tmp/`, which is gitignored. `docs/` is for documentation
that ships.

A completed feature directory under `specs/` is never edited again; a changed requirement gets a new
numbered directory cross-linking the one it supersedes. Nothing there is authoritative for current
behaviour — the shipped documentation and the workflows are. Read a ticked `tasks.md` as a work log.

## Environment

### Tooling hierarchy

1. **Project task** — a mise task (`lint`, `test`, `typecheck`, `fmt`). Never bypass it.
2. **prek** — `mise exec -- prek run`.
3. **`uv run <tool>`** — project-local Python tools.
4. **`mise exec -- <tool>`** — system tools mise manages (`actionlint`, `zizmor`, `shellcheck`).

Never `pip install`. Never activate a venv by hand. Nothing is installed globally: a new runtime or
CLI is pinned with mise, which owns every version in its `[tools]` table — except Python tool
versions, which are declared alongside the Python dependencies.

**No `[tools]` entry is `latest`.** Each names a version, so two machines on one commit resolve the
same linters. Renovate's `mise` manager bumps them, and a gate stops a new tool arriving unpinned.

### Dependencies

- Dev deps in `[dependency-groups].dev`. `[project].dependencies` stays empty — nothing is
  published from here.
- Run `uv lock` after editing dependencies and commit the result in the same change.
- Renovate owns version updates; Dependabot is kept for security alerts, whose PRs wait for a human.
  Their own configs own that split and say why symmetry between the two is not a goal.
- Introducing a new file type updates `.editorconfig`, `.gitattributes`, and `.gitignore` in the
  same change.

## Code

### Workflows and actions

The repository layout is load-bearing:

| Path | Contents | Referenced as |
| --- | --- | --- |
| `.github/workflows/*.yml` with `workflow_call` | reusable workflows | `turboBasic/github-actions/.github/workflows/<name>.yml@vN` |
| `.github/workflows/{ci,commit-messages,release-on-merge}.yml` | this repo's own CI and its release | not referenced |
| `actions/<name>/action.yml` | composite actions | `turboBasic/github-actions/actions/<name>@vN` |

`vN` is the current major tag. Exactly one artefact declares which one that is, and it is the only
place a major is written literally.

Composite actions live in `actions/`, not `.github/actions/`. The latter is the convention for
*repo-local* actions and would read as private-by-convention here.

- **Pin every third-party action to a full 40-character commit SHA** (principle II), with the
  version as a trailing `# vX.Y.Z` comment. Enforced by test.
- **First-party references use the moving major tag** (`@vN`), never a SHA. See **Versioning**.
- **A workflow's own `name:` is an emoji, a space, then its filename stem** — 🧩 where `workflow_call`
  is the only trigger (`🧩 python-ci`), 🌜 where the workflow has triggers of its own (`🌜 ci`). The
  prefix answers what the Actions sidebar is there to answer: where a run history is. A 🧩 entry never
  has one, because a called workflow's jobs appear inside its caller's run — so a 🧩 labelled 🌜 sends
  a reader to an empty page. The sidebar sorts by name by code point, so both blocks sit below the
  entries GitHub injects and nobody can rename, and every entry that has runs is contiguous.
- **Whether a workflow is on the version surface does not decide the prefix.** That answers whether a
  change obliges a release, which is a different question with a different answer: `release.yml` is
  called by a consumer and is deliberately off the surface. Separate gates hold the two. No check
  context reads a workflow's name, so renaming one retires no context — but a consumer-facing file is
  still consumer-facing, so a release is owed for it like any other change.
- **A job's `name:` is lowercase-kebab-case, and a called job's name says what the job is rather
  than repeating its caller.** GitHub composes a check as `<caller job id> / <called job name>`, so
  the callee owns half of an identifier consumers type into their own rulesets. The name takes its
  workflow's name without the prefix — `python-ci`, `dependency-review` — unless the workflow has
  sibling jobs, where the deed distinguishes them (`pr-title`, `commit-messages`), or unless it
  would double a common caller id, where the deed wins again (`tag-and-publish`, not `release`).
  Never name it after behaviour a caller can switch off. A gate enforces the casing; the rest is
  judgement.
- **Renaming a job that composes a required context is a major bump**, because a required check that
  stops reporting blocks every pull request until each consumer edits its own ruleset, and no ref can
  do that for them.
- **Every input needs a `description` and an explicit `default`** unless genuinely required. A
  consumer reads the input list as the contract.
- **Declare the narrowest `permissions`** the workflow needs (principle III).
- **Both halves of that contract are frozen by a table in the suite** — every reusable workflow's
  inputs, and each job's effective permissions. Both are validated before any job exists, so either
  one moving breaks a caller with no job and no log, and is a major bump. Adding an input is
  backwards-compatible and updates the table in the same change. Defaults are not frozen there: a
  default is behaviour rather than call-site shape, and the consumer-facing reference carries it.
- **`env` does not propagate from caller to called workflow.** Anything a reusable workflow needs
  must arrive as an `input`.
- **Interpolate untrusted values through `env`, not directly into `run:`** (principle IV).
- **`concurrency` belongs to the caller**, `timeout-minutes` to the callee. A reusable workflow
  cannot set its caller's concurrency group.

### Python

Python 3.14. The only Python here supports the actions and their tests.

- `X | None`, not `typing.Optional`. Built-in `dict`/`list`, not `typing.Dict`.
- No `from __future__ import annotations`.
- Full type hints on every signature, tests included.
- A script invoked by a composite action reads its arguments from the environment, declared in
  `action.yml`. It never parses `${{ }}` interpolations inline.
- **A module a composite action runs is standard-library-only, and keeps to syntax older
  interpreters parse.** mise pins 3.14 here, but a caller whose own config pins no `python`
  falls back to the runner's, and `python3` is what runs the file — there is no resolution step to
  fail loudly. Its imports are asserted against `sys.stdlib_module_names` by test.
- **A module a composite action runs is importable by the suite**, through a `pythonpath` entry in the
  pytest config and a matching `extraPaths` for pyright. Both are needed; neither is a relaxation.

### Comments and docs

- No docstrings. No multi-line comment blocks.
- Comments only where the WHY is non-obvious, never restating what the code does.
- State the rule, not the incident that taught it. No war stories, no version archaeology, no
  reasoning left in prose where a test can hold it.
- The consumer-facing reference is a contract: what each workflow does, its inputs, and a call site
  that can be copied as-is. A new input or a changed default updates it in the same change.
- Every change ends by checking the documentation it affects and correcting it in the same change.
  Stale framing is a defect, not a follow-up.

## Quality gates

- prek is the linting entry point. Never call `ruff` directly.
- `actionlint` covers `.github/workflows`; it does not look in `actions/`. Its own config owns its
  ignores. `zizmor` covers both and is the security linter (principle VII).
- yamllint's own config owns its rules and exempt paths.
- A new GitHub config file gets a `check-jsonschema` hook and a matching line in the `lint` task.
  Prefer `--builtin-schema` to `--schemafile <url>`: a vendored schema needs no network and cannot be
  repointed. zizmor's config gets none — its only published schema is served off a floating `main`
  ref, and zizmor rejects an unknown field in its own config anyway. actionlint's does get one,
  because actionlint accepts an unknown key there silently.
- pyright strict (principle VII).
- pytest. Never `unittest.TestCase`. The suite asserts properties of the YAML where there is nothing
  to call, and calls the action modules where there is — the second is always the better test, and
  moving a decision out of a `run:` block so it can be called is the reason those modules exist.
- **The suite is offline; `mise run ci` must never need the network.** The few exceptions are marked
  and deselected by default, and `mise run test-drift` opts in. What earns the marker is stated where
  the marker is declared.
- **This repository stays public, or every consumer needs an access policy.** A private caller resolves
  these workflows only because this one is public; were it made private, each consumer would have to
  allow access to repositories this owner holds. The policy itself cannot be asserted, so a gate
  guards the visibility that makes it unnecessary and carries the setting as its failure message. Set
  the policy and delete the gate, in that order.
- **A relative self-call is what exercises a reusable workflow here** (principle VI). Which
  behaviour turns on caller-side configuration is concrete: `python-ci.yml`'s `hook-stage`,
  `run-typecheck`, and a consumer with no mise config — those want a real consumer at the ref it
  pins.
- **Pre-flight the line out of the file, never a retyping of it**, or you test your typing rather
  than the file.
- **The allowed commit types are declared once**, as `conventional-commits.yml`'s `types` default,
  and asserted equal to commitizen's built-in set by test. Both the title and the commit-message
  check read it from there. It may not fall back to a tool's own default: commitizen's set and the
  action's differ, `bump` being the one that does.

## Shipping

### Versioning

Consumers pin a moving major tag rather than a SHA, which principle II allows only for first-party
references. SHA-pinning them would mean one Dependabot PR per consumer for every one-line fix.

A major bump is owed by any change a consumer cannot absorb by resolving the new ref alone, and what
a bump does to the tags is principle I:

- **The call site stops working.** A removed or renamed input, a `uses:` path that no longer exists.
- **A status check the consumer requires stops reporting.** Renaming a job whose name composes a check
  context retires it, and a required context that never reports blocks every pull request — the
  consumer's ruleset has to be edited, which no ref can do for it.
- **A permission the caller must grant changes.** Job permissions are validated before any job exists,
  so a caller granting too little fails at startup with no job and no log.

**The version describes the consumer-facing surface, not this repository's commit history.** Judge a
bump by what changed under `.github/workflows/` and `actions/`; a `feat:` touching only our own
linting or editor config is a patch. The number is a human decision, never computed unattended, and
a proposal of it is not a decision.

Which major is current, and which tags are immutable, is declared in exactly one artefact and read
from there. Never restate it here.

### Git

- Conventional Commits, commitizen's default types. The PR title is held to the same format.
- Commit or push only when asked. Branch first if on the default branch.
- Never commit a secret (principle V).
- **Labels are on issues, never on a pull request.** A PR's kind is its Conventional Commit title and
  a second copy of that on a label is a second source of truth. Nothing automated reads a label, and
  the axes are documented once, for contributors.

### CI

`mise run ci` reproduces CI locally.

**A self-call must use the self-repository form** — `$/.github/workflows/<name>.yml`, with no
`{owner}/{repo}` and no `@{ref}`. It resolves at the caller's own commit, so a change to the called
workflow is validated by the version under review; the `turboBasic/github-actions/...@vN` form
resolves at the tag and would validate it against the last good release. `commit-messages.yml` calls
`conventional-commits.yml` this way, and `ci.yml` calls `python-ci.yml` this way.
A gate enforces it, because every other gate accepts the tagged form too.

**Never write the older `./.github/workflows/<name>.yml`.** It resolves at the same commit, but
reaches the file through the runner's filesystem, so a step running earlier can substitute what gets
called; zizmor's `self-repository` audit rejects it. `$/` is unavailable on GitHub Enterprise Server,
which nothing here targets.

actionlint has not learned `$/` yet and reports it as a malformed call, so its own config ignores
that one message. It is the one silenced rule in the repo, and it silences a false positive
rather than a finding — the config names the upstream bug, and a gate fails on the day that bug ships
so the ignore cannot outlive it. A second ignore needs the same two things, a false positive and an
expiry.
