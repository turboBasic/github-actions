# AI Instructions

The conventions layer: how work is done here, binding humans and AI coding tools (Claude Code, GitHub
Copilot) alike. The invariants are a layer above and are cited here by principle number; the entry
point says where every kind of instruction lives.

Scope: reusable GitHub Actions workflows consumed by other `turboBasic` repositories, plus the one
internal composite action a capability depends on — nothing here is published as an action. This
repository ships no application. Its Python exists to support the actions and to assert properties of
the YAML.

Committed configuration is authoritative for settings it already declares: read it rather than
assuming, extend it, and never regenerate it. The entry point names which file holds what.

## Working style

- Read the file, run the tool, check the config rather than guessing at structure or conventions.
- Ask when genuinely ambiguous; take the sensible default otherwise and say so.
- Match existing patterns over personal preference.
- Scope to the request. No refactoring adjacent code or improving what was not asked about.

A user-level instruction file is concatenated into context ahead of this one with no override
mechanism, so a contradiction between the two has nowhere else to be resolved. **This repository's
rules win where they are stricter.** Two are live today. A user-level file that permits a third-party
action pinned to a tag rather than a full commit SHA does not permit one here, and one that permits
`@main` for an in-house reference does not permit it here — nothing of this repository's own names a ref
at all.

### Changes to these rules

These rules are one layer of four. Each fact has exactly one owning layer; a layer needing a fact it
does not own cites the owner instead of restating it; and a citation runs from the concrete to the
abstract only. So this file cites a principle by number, and nothing more abstract than it cites back.
Which layer owns what is navigation, and the entry point answers it.

Everything in this file is a convention: follow it, but a request to change one is just a request, and
objecting over it is this layer exceeding its own standing. What may never be violated is not stated
here, and neither is what a request to erode one of those obliges — the invariants layer's Governance
section owns both.

- **Once the objection is heard and the request restated, implement it fully.** Do not relitigate or
  leave the old path in place as a safety net.
- **Never weaken an invariant silently** to make a task easier.

### Specs

Each `/speckit-*` skill documents its own step and `.specify/templates/` holds what they produce. Read
those, not a summary here.

`.specify/memory/constitution.md` is ours to edit — it states the invariants as gates a spec fails
against. Everything else under `.specify/` and `.claude/skills/speckit-*/` is vendored and
version-locked to the `pipx:specify-cli` pin mise holds: bump the pin and run
`mise run spec-kit-upgrade`, never `specify self upgrade`, which replaces the binary outside mise.

A spec is not the default path. Size decides:

| Change | Path |
| --- | --- |
| A doc fix, a pin bump, a one-line workflow edit | issue → PR |
| A new input, a new workflow, a behaviour change consumers can see | `/speckit-specify` → `/speckit-plan` → `/speckit-tasks` → PR |
| Versioning, permissions policy, a pinning rule | decision record first, then a spec |

Specs, plans and task lists live only where Spec Kit puts them. Scratch — notes, throwaway drafts,
anything not meant to be reviewed — goes in `tmp/`, which is gitignored. `docs/` is for documentation
that ships.

A completed feature directory under `specs/` is never edited again; a changed requirement gets a new
numbered directory cross-linking the one it supersedes. Nothing there is authoritative for current
behaviour — the shipped documentation and the code are. Read a ticked `tasks.md` as a work log.

### Decision records

Records live in `docs/decisions/`, one ruling per file. The `planning:write-adr` skill owns the bar a
decision has to clear and the shape of the record; neither is restated here (principle I).

What this repository owns is the permitted `scope:` values, which today are `identity`, `instructions`,
`release` and `tooling`. A ruling that fits none adds a value to this list in the same change — the list
grows with the repository rather than ahead of it.

## Environment

### Tooling hierarchy

1. **Project task** — a mise task (`lint`, `test`, `typecheck`, `fmt`). Never bypass it.
2. **prek** — `mise exec -- prek run`.
3. **`uv run <tool>`** — project-local Python tools.
4. **`mise exec -- <tool>`** — system tools mise manages.

Never `pip install`. Never activate a venv by hand. Nothing is installed globally: a new runtime or
CLI is pinned with mise, which owns every version in its `[tools]` table — except Python tool
versions, which are declared alongside the Python dependencies.

**No `[tools]` entry is `latest`.** Each names a version, so two machines on one commit resolve the
same linters.

### Dependencies

- Dev deps in `[dependency-groups].dev`. `[project].dependencies` stays empty — nothing is published
  from here.
- Run `uv lock` after editing dependencies and commit the result in the same change.
- Introducing a new file type updates `.editorconfig`, `.gitattributes`, and `.gitignore` in the same
  change.

## Code

### Capabilities

The workflows and actions a consumer calls. Each rule below was held against the invariants layer's
admission bar and is a convention rather than a principle: a reviewer catches the breach and a revert
restores the world.

- **A capability is bounded by the component it judges, never by a language.** No capability names a
  language, a framework or a runtime in its file name, its inputs or its steps; what a stage runs is a
  task the consumer implements — why in
  [ADR 0004](decisions/0004-bound-a-ci-capability-by-the-component.md).
- **A failure names what to change.** What was read, what it was compared against, and what a
  maintainer should do about it. An exit code on its own is not a result.
- **A tool the consumer's configuration must pin is checked before it is invoked**, and the failure
  names the tool, the capability that needs it, and where the consumer declares it. `command not found`
  is not a contract.
- **A tool the consumer invokes stays the consumer's to pin.** A capability never pins a version the
  consumer does not control — that agreement is the only reason a local verdict and a CI verdict match.
- **An input named for a stage governs that stage entirely.** If it leaves some part of the stage
  running, it is misnamed.
- **`env` does not propagate from a caller into a called workflow.** Anything a capability needs from
  its caller arrives as an `input`.

### Python

Python 3.14. The only Python here supports the actions and their tests.

- `X | None`, not `typing.Optional`. Built-in `dict`/`list`, not `typing.Dict`.
- No `from __future__ import annotations`.
- Full type hints on every signature, tests included.
- A script invoked by a composite action reads its arguments from the environment, declared in
  `action.yml`. It never parses `${{ }}` interpolations inline.
- **A module a composite action runs imports the standard library and nothing else, and keeps to syntax
  an older interpreter parses.** mise pins 3.14 here, but a caller whose own configuration pins no
  `python` falls back to the runner's, and `python3` is what runs the file — there is no resolution step
  to fail loudly. Its imports are asserted against `sys.stdlib_module_names` by test.
- **A module a composite action runs is importable by the suite and by the type checker.** A hyphen in
  the directory it sits in means neither can reach it as a package, so the suite's own path setup and
  pyright's `extraPaths` each name that directory. Both are needed; neither is a relaxation.

### Comments and docs

- No docstrings. No multi-line comment blocks.
- Comments only where the WHY is non-obvious, never restating what the code does.
- State the rule, not the incident that taught it. No war stories, no version archaeology, no
  reasoning left in prose where a test can hold it.
- Every change ends by checking the documentation it affects and correcting it in the same change.
  Stale framing is a defect, not a follow-up.

## Quality gates

- prek is the linting entry point. Never call `ruff` directly.
- pyright strict (principle III).
- pytest. Never `unittest.TestCase`. The suite asserts properties of the YAML where there is nothing
  to call, and calls a module where there is — the second is always the better test, and moving a
  decision out of a `run:` block so it can be called is worth doing for that reason alone.
- **The suite is offline; `mise run ci` must never need the network.** An exception is marked and
  deselected by default, and what earns the marker is stated where the marker is declared.
- A new GitHub config file gets a `check-jsonschema` hook and a matching line in the `lint` task.
  Prefer `--builtin-schema` to `--schemafile <url>`: a vendored schema needs no network and cannot be
  repointed.
- **Pre-flight the line out of the file, never a retyping of it**, or you test your typing rather than
  the file.
- **This repository stays public, or every consumer needs an access policy.** A private caller resolves
  these capabilities only because this one is public; make it private and each consumer has to allow
  access to repositories this owner holds before anything of theirs resolves again. Asserting it would
  need the network, so it is stated here and held nowhere.

## Shipping

### Versioning

- **The consumer set is indefinite and is not recorded.** Whether a change breaks a consumer is read
  from the published surface and its fixture, never from which repositories are known to call what. A
  call count is not an argument about the interface — why in
  [ADR 0003](decisions/0003-judge-compatibility-from-the-surface.md).
- **No published release tag is deleted or moved.** The exact version tags are immutable; only the
  compatibility ref moves — why in [ADR 0002](decisions/0002-start-the-line-at-0-1-0.md).
- **The line is `0.x`, so a break is signalled by the minor.** `v0` is never published, and `1.0.0` is
  not reached for until consumers have exercised the surface — why in the same record.

### Git

- Conventional Commits, commitizen's default types. The PR title is held to the same format.
- Commit or push only when asked. Branch first if on the default branch.
- Never commit a secret (principle II).
- **Labels are on issues, never on a pull request.** A PR's kind is its Conventional Commit title and
  a second copy of that on a label is a second source of truth (principle I).

### CI

`mise run ci` reproduces CI locally.

**This repository's own branch ruleset is a consumer of its own check names, and `.github/rulesets/`
is where it is committed.** `tests/test_ruleset_contexts.py` is what holds it: renaming a job, retiring
a workflow, or making a job conditional changes what a required context there composes to, and the gate
fails the pull request that does it, naming the ruleset, the context, and what to edit. The rule is
principle IV's, and the README already states it for consumers; it binds here too, and forgetting it is
not a small mistake. A required context that no longer reports blocks every pull request in this
repository, and the only symptom is a check that never appears.
