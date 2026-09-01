# Contributing

This repo holds the CI that other `turboBasic` repositories run. A change here executes in every
consumer listed in [`docs/consumers.md`][consumers] — read that list before starting.
Forking to suit your own conventions is an expected use; the [MIT licence][license] asks nothing
beyond keeping the notice.

Taking part means following the [Code of Conduct][coc]. Report anything exploitable
privately instead of opening an issue — see the [security policy][security].

## Read this first

[`docs/ai-instructions.md`][ai-instructions] is the source of truth and binds humans and AI
tools alike. This file does not repeat it.

Start with [Changes to these rules][ai-instructions-changes]: it marks which
rules are non-negotiable and what to do when a change would trade one away. The rest covers
[tooling][ai-instructions-tooling],
[workflows and actions][ai-instructions-workflows],
[quality gates][ai-instructions-quality], and
[versioning][ai-instructions-versioning].

## Setup

```sh
mise run setup
```

One command; it wires up the `pre-commit` and `commit-msg` hooks together.

## The loop

```sh
mise run ci      # lint, schema validation, typecheck, test — exactly what CI runs
```

## Specs

Most changes are an issue and a PR. A new input, a new workflow, or any behaviour a consumer can see
gets a spec first — `/speckit-specify`, then `/speckit-plan`, then `/speckit-tasks`. Which changes
need one is settled in [ai-instructions][ai-instructions-specs]; the gates a spec is read against
are in [the constitution][constitution].

A spec lands in `specs/NNN-slug/` on your branch and merges with the code it describes. Until that
merge it is a proposal — the PR review is what makes it an artifact, so put it up for review before
building against it.

## Verifying a workflow change

Lint is necessary and not sufficient. **A reusable workflow that has never been called is
unverified** — YAML that parses can still fail on a missing input, a permission it was not granted,
or an expression that evaluates to the wrong branch.

Before a change to a reusable workflow is done:

1. Push the branch and open a PR here, so this repo's own CI runs.
2. Call the changed workflow at `@<your-branch>` from a throwaway repository, and exercise both
   outcomes — the passing path and the failing one. A check that cannot fail is not a check.
3. Delete the throwaway repo afterwards.

The major tag is only moved once that has happened.

## Pull requests

Branch first. Title the PR as a Conventional Commit — a squash merge takes its subject from there.
Both workflows must pass.

Say which consumers a change affects and what you ran to verify it, and update
[`docs/consumers.md`][consumers] and the [README][readme] in the same change when an
input contract moves. Agent-written code is welcome; you are still the author of it.

## Releasing

Merging changes nothing for consumers. They pin the major tag — see [Versioning][readme-versioning] —
and it only moves when a release is cut, which is two steps:

1. **Bump `[project].version` in `pyproject.toml`** and re-run `uv lock` so the lockfile agrees, then
   merge that as a normal pull request. `uv run cz bump --version-files-only` makes the edit and will
   offer an increment computed from the commit range; the number is still yours. Judge it by the surface
   consumers resolve — `.github/workflows/` and `actions/` — not by this repo's commit history. A
   `feat:` that only touched our own linting is a patch.
2. **Run the [Release workflow][release-workflow]** against `main`. It tags that commit `vX.Y.Z`,
   publishes the release with notes generated from `.github/release.yml` covering everything since the
   previous version tag, and force-moves `vX` last, once the rest has succeeded.

Nothing is built and nothing is uploaded. A consumer resolves this repository's tree at a ref, so
the tag *is* the artifact — which is also why the version in `pyproject.toml` is the only place the
number is decided, and why deciding it in a reviewed pull request is the whole point.

The workflow refuses to tag when the version is already tagged, when `ci / CI` has not passed on the
commit, or when it is dispatched from anywhere but `main`. If it fails after the version tag exists,
delete that tag and re-run once the cause is fixed.

A major bump is a new tag rather than a move: the old major stays where it is, and the
[README][readme]'s Versioning section is updated to name the new one in the same pull request as the
version bump.

Neither step existed until now, which is how the major tag came to sit 29 commits behind `main` for 19
days with four consumer-facing changes stranded. `mise run test-live` fails while a reusable workflow
or a composite action is newer than the major tag — `ci.yml`, `commit-messages.yml` and `release.yml`
are excluded, since nothing outside resolves those — so the next pull request says a release is owed
rather than someone noticing by accident.

<!-- Links -->

[consumers]: docs/consumers.md
[license]: LICENSE
[coc]: CODE_OF_CONDUCT.md
[security]: SECURITY.md
[ai-instructions]: docs/ai-instructions.md
[ai-instructions-changes]: docs/ai-instructions.md#changes-to-these-rules
[ai-instructions-specs]: docs/ai-instructions.md#specs
[constitution]: .specify/memory/constitution.md
[ai-instructions-tooling]: docs/ai-instructions.md#tooling-hierarchy
[ai-instructions-workflows]: docs/ai-instructions.md#workflows-and-actions
[ai-instructions-quality]: docs/ai-instructions.md#quality-gates
[ai-instructions-versioning]: docs/ai-instructions.md#versioning
[readme]: README.md
[readme-versioning]: README.md#versioning
[release-workflow]: https://github.com/turboBasic/github-actions/actions/workflows/release.yml
