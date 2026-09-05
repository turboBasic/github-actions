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

Lint is necessary and not sufficient. **Run every workflow you change.** YAML that parses still
fails on a missing input, a permission nobody granted, an expression that picks the wrong branch, or
a CLI that wants a context the runner lacks.

Before a change to a reusable workflow is done:

1. Push the branch and open a PR here, so this repo's own CI runs.
2. Open a branch in [`github-actions-test`][test-consumer], point its call site at `@<your-branch>`,
   and exercise both outcomes — the passing path and the failing one. A check that cannot fail is not
   a check.
3. Leave that branch. Nothing there needs deleting, and a scenario worth running once is worth
   keeping: `tests/scenario-*/README.md` says what each existing branch covers and what it asserts in
   the log, so start from the nearest one.

Move the major tag only after that.

A workflow only this repo runs — `ci.yml`, `commit-messages.yml`, `dependabot-automerge.yml`,
`release.yml`, `release-proposal.yml` — has no consumer to call it. Dispatch it, or open a PR that
triggers it, and read the run. A brand-new one cannot be dispatched at all: GitHub offers `workflow_dispatch` only for a workflow file already on the default branch, so exercising one before
merge means a temporary trigger scoped to your branch, removed in the same pull request.

## Labels

Labels are on **issues only**, and nothing automated reads them — release notes come from commit
types via `.cliff.toml`. A PR's kind already lives in its Conventional Commit title, so labelling one
would be a second source of truth about what kind of change it is. The exception is `deps`, which
Renovate applies to its own PRs and dashboard so a report can exclude bot traffic.

Two required axes and four flags:

| Axis | Labels | Rule |
| --- | --- | --- |
| kind | `kind:bug` `kind:feat` `kind:chore` `kind:docs` | exactly one |
| area | `area:workflows` `area:actions` `area:release` `area:tooling` | one or more |
| flags | `breaking` `blocked` `needs-spec` `deps` | as they apply |

**This table is the label set.** Adding a label means adding it here and running
`gh label create`; `tests/test_action_pins.py` reads the second column and fails when GitHub and this
table disagree.

Colour is by axis, not by label — `kind:` blue, `area:` purple, a flag red or amber, `deps` grey so
bot traffic recedes. Darkest first down each axis. Nothing asserts a colour: it carries no data anyone
groups by, and a rule regenerates it without a table of hex codes to keep current.

`area:workflows` and `area:actions` are the consumer-facing surface; `area:release` and
`area:tooling` are not. That split is the one the version bump turns on — a change confined to the
second pair is a patch however it is titled. `breaking` means shipping it needs a new major tag, and
those issues go in the `v3.0` milestone.

Do not label a closure. GitHub's own close reason — *not planned*, *duplicate* — already records it
and is queryable.

```sh
gh issue list --state open --json labels --jq '[.[].labels[].name]|group_by(.)|map({(.[0]):length})'
```

## Pull requests

Branch first. Title the PR as a Conventional Commit — a squash merge takes its subject from there.
Both workflows must pass.

Say which consumers a change affects and what you ran to verify it, and update
[`docs/consumers.md`][consumers] and the [README][readme] in the same change when an
input contract moves. Agent-written code is welcome; you are still the author of it.

## Releasing

Merging changes nothing for consumers. They pin the major tag — see [Versioning][readme-versioning] —
and it only moves when a release is cut, which is now **one step: approve a proposal.**

After any merge to `main` that leaves something worth describing, the [Release
proposal][release-proposal-workflow] workflow opens a pull request titled `bump: release vX.Y.Z`. Its
body is the exact notes that release will publish, and its diff is `pyproject.toml`'s
`[project].version` and `uv.lock`'s matching line, nothing else. Read the notes, and:

- **Agree with the version?** Merge it. `ci.yml` runs on the merge commit and, when `ci / CI` passes,
  calls the release: it renders the notes again from the same rules, tags `vX.Y.Z`, publishes the
  release with those notes, and force-moves `vX` last. No further human action.
- **Disagree with the version?** Change it on the proposal branch before merging. The released version
  is the one you approved, and every later refresh leaves it alone — a commit on that branch authored
  by anyone but the bot is how the workflow knows a human has decided.

The proposal proposes; it does not decide. The increment it offers is computed from the commits that
touch the surface consumers resolve — `.github/workflows/` and `actions/`, minus this repo's own
CI — so a `feat:` that only touched our own linting comes out a patch, which is the rule the number
has always followed. `pyproject.toml` remains the only place the version is decided.

Nothing is built and nothing is uploaded. A consumer resolves this repository's tree at a ref, so the
tag *is* the artifact — which is why deciding the number in a reviewed pull request is the whole point.

A major bump is a new tag rather than a move: the old major stays where it is, and the
[README][readme]'s Versioning section is updated to name the new one in the same pull request.

### What refuses, and why

The release renders the notes *before* it creates any ref, so a failure leaves no tag behind. It
refuses when the version is not ahead of every existing release, when the notes render nothing, and
when the range holds a breaking change under a version that is not a new major — publishing that would
move the existing major tag onto a broken contract.

On an ordinary merge, where the declared version is already tagged, it says so with a notice and stops.
It does not redden `main` for doing nothing wrong.

`mise run release-notes` renders the notes locally, offline, creating nothing.
[Dispatching the Release workflow][release-workflow] with `dry-run` runs every refusal and prints the
notes it would publish, without creating a tag. If a release fails *after* the version tag exists,
delete that tag and re-dispatch once the cause is fixed — the major tag moves last precisely so
consumers stay on the previous release until the rest has succeeded.

### The App behind the proposal

The proposal is opened by a GitHub App, `turbobasic-release-proposal`, installed on this repository
with `Contents` and `Pull requests` write and nothing else. Its id and private key live in the
`RELEASE_APP_ID` and `RELEASE_APP_PRIVATE_KEY` Actions secrets, and the token each run mints is
narrowed to those two permissions and expires in an hour.

`GITHUB_TOKEN` cannot do this job: opening a pull request from Actions requires *Allow GitHub Actions
to create and approve pull requests*, which is off here and stays off, because it grants approving as
well as opening. An App is not "GitHub Actions", so it is not subject to that setting — and its pull
requests trigger the required checks with no click.

**If that key is rotated or the installation removed, no proposal is raised and nothing says so.** The
backstop is `mise run test-drift`, which fails while a reusable workflow or composite action is newer
than the major tag — the repo-local workflows named under [Verifying a workflow
change](#verifying-a-workflow-change) are excluded, since nothing outside resolves those — so the next
pull request says a release is owed rather than someone noticing by accident. That check is why the major tag can no longer sit 29 commits behind
`main` for 19 days with four consumer-facing changes stranded, as it once did.

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
[test-consumer]: https://github.com/turboBasic/github-actions-test
[readme-versioning]: README.md#versioning
[release-proposal-workflow]: https://github.com/turboBasic/github-actions/actions/workflows/release-proposal.yml
[release-workflow]: https://github.com/turboBasic/github-actions/actions/workflows/release.yml
