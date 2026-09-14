# Contributing

This repository holds the CI that other `turboBasic` repositories run. A change to a capability reaches
every consumer pinned to the moving ref on their next push, so the question a change answers is whether
a caller on that ref can absorb it — see [Versioning][readme-versioning].
Forking to suit your own conventions is an expected use; the [MIT licence][license] asks nothing beyond
keeping the notice.

Taking part means following the [Code of Conduct][coc]. Report anything exploitable privately instead of
opening an issue — see the [security policy][security].

## Read this first

Two files carry the rules and bind humans and AI tools alike: [the constitution][constitution] states
what may never be violated, and [`docs/ai-instructions.md`][ai-instructions] states how work is done
here. This file repeats neither.

Start with [Changes to these rules][ai-instructions-changes]: it says how the conventions relate to the
layers around them, and everything in that file is one. The constitution's Governance section owns what
a request to erode an invariant obliges. The rest covers
[tooling][ai-instructions-tooling],
[capabilities][ai-instructions-capabilities],
[quality gates][ai-instructions-quality], and
[versioning][ai-instructions-versioning].

## Setup

```sh
mise run setup
```

One command; it wires up the `pre-commit` and `commit-msg` hooks together.

## The loop

```sh
mise run ci             # lint, schema validation, typecheck, test — exactly what CI runs
mise run release-notes  # what a release would publish, rendered here, creating nothing
```

## Specs

Which changes need a spec first, and the sequence one goes through, is settled in
[ai-instructions][ai-instructions-specs]; the gates a spec is read against are in
[the constitution][constitution].

A spec lands in `specs/NNN-slug/` on your branch and merges with the code it describes. Until that merge
it is a proposal — the PR review is what makes it an artifact, so put it up for review before building
against it.

## Verifying a workflow change

Lint is necessary and not sufficient. **Run every workflow you change.** YAML that parses still fails on
a missing input, a permission nobody granted, an expression that picks the wrong branch, or a CLI that
wants a context the runner lacks.

Every capability is called by this repository itself, so opening a pull request here exercises each one
at the commit under review. That covers the code and not the caller: what turns on caller-side
configuration — `python-ci`'s stage switches and its task names, a consumer with no `mise.toml` — is
only exercised by a real consumer at the ref it pins.

Before a change to a capability is done:

1. Push the branch and open a PR here, so this repository's own CI runs.
2. Open a branch in [`github-actions-test`][test-consumer], point its call site at `@<your-branch>`, and
   exercise both outcomes — the passing path and the failing one. A check that cannot fail is not a
   check.
3. Leave that branch. Nothing there needs deleting, and a scenario worth running once is worth keeping:
   `tests/scenario-*/README.md` says what each existing branch covers and what it asserts in the log, so
   start from the nearest one.

Move the compatibility ref only after that.

A workflow no consumer calls — `ci.yml`, `commit-messages.yml`,
`dependency-guard.yml`, `release-on-merge.yml`, `propose-on-merge.yml`, `apply-ruleset.yml` — has no
caller but this repository. Dispatch it, or open a PR that triggers it, and read the run. `release.yml`
and `release-proposal.yml` have no trigger of their own: dispatch `release-on-merge.yml` to reach the
first, and merge to `main` to reach the second. A brand-new workflow cannot be
dispatched at all — GitHub offers `workflow_dispatch` only for a workflow file already on the default
branch — so exercising one before merge means a temporary trigger scoped to your branch, removed in the
same pull request.

## Labels

Labels are on **issues only**, and nothing automated reads them — release notes come from commit types
via `cliff.toml`. A PR's kind already lives in its Conventional Commit title, so labelling one would be a
second source of truth about what kind of change it is.

Two required axes and three flags:

| Axis | Labels | Rule |
| --- | --- | --- |
| kind | `kind:bug` `kind:feat` `kind:chore` `kind:docs` | exactly one |
| area | `area:workflows` `area:actions` `area:release` `area:tooling` | one or more |
| flags | `breaking` `blocked` `needs-spec` | as they apply |

**This table is the label set.** Adding a label means adding it here and running `gh label create`.
Nothing asserts it against the live repository: which paths are consumer-facing is already declared as
`[tool.turbobasic-release]` in `pyproject.toml`, and that declaration is what the release is judged
against — a label is a filing aid, not an input to anything.

Colour is by axis, not by label — `kind:` blue, `area:` purple, a flag red or amber. Darkest first down
each axis. Nothing asserts a colour: it carries no data anyone groups by, and a rule regenerates it
without a table of hex codes to keep current.

`breaking` means shipping it needs a new compatibility line rather than a move of the current ref — which
line that is depends on where the version stands, so a breaking issue waits for the milestone that cuts
it rather than naming one here.

Do not label a closure. GitHub's own close reason — *not planned*, *duplicate* — already records it and
is queryable.

```sh
gh issue list --state open --json labels --jq '[.[].labels[].name]|group_by(.)|map({(.[0]):length})'
```

## Pull requests

Branch first. Title the PR as a Conventional Commit — a squash merge takes its subject from there. Every
required check must pass; which ones those are is committed in `.github/rulesets/`.

Say whether a caller on the current ref can absorb the change and what you ran to verify it, and update
the [README][readme] in the same change when a capability's shape moves. Agent-written code is welcome;
you are still the author of it.

## Releasing

Merging changes nothing for consumers. They pin the moving ref — see [Versioning][readme-versioning] —
and it only moves when a release is cut, which is **one step: approve a proposal.**

After any merge to `main` that leaves something worth describing, [Propose on
merge][release-proposal-workflow] calls the `release-proposal` capability, which opens a pull request
titled `chore: release vX.Y.Z`. Its
body is the exact notes that release will publish, and its diff is `pyproject.toml`'s `[project].version`
and `uv.lock`'s matching line, nothing else. Read the notes, and:

- **Agree with the version?** Merge it. [Release on merge][release-workflow] runs on the merge commit
  and, once its `verify` job passes, cuts the release. No further human action. `ci.yml` runs on the same
  commit and answers for the code alone, so a refused or failed release never reddens it.
- **Disagree with the version?** Change it on the proposal branch before merging. The released version is
  the one you approved, and every later refresh leaves it alone — the branch disagreeing with what the
  workflow's own last commit there says it computed is how it knows a human has decided.

The proposal proposes; it does not decide. `pyproject.toml` is the only place the version is decided, and
what the number describes is [ai-instructions][ai-instructions-versioning]'s rule: the consumer-facing
surface, declared as `[tool.turbobasic-release]` in that same file.

What the release refuses, and what it does on a merge that releases nothing, is the
[README][readme-release]'s: it is the same capability a consumer calls. Two things are ours alone:

- [Dispatching Release on merge][release-workflow] with `dry-run` runs every refusal and renders the real
  notes on a runner, creating nothing — on a commit that is already tagged it stops at the empty-range
  refusal, which is that refusal working. It is the only safe way to exercise the release path.
- If a release fails *after* the version tag exists, recover by merging the next patch version. That tag
  cannot be deleted, and the compatibility ref moves last precisely so consumers stay on the previous
  release until the rest has succeeded.

### Repinning consumers onto a new line

Only a break needs this; nothing else asks a consumer to act. Repin
[`github-actions-test`][test-consumer] first — it is the one caller whose configuration is not ours, so a
rename is unverified for a consumer until that repository is green.

Then, per consumer, two orderings that are not interchangeable. Its ruleset flips **after** its repin
branch has reported the new check names, never before — a required context that has never reported blocks
every open pull request in that repository, not just the one doing the repin. And between the flip and the
merge, that repository's `main` still resolves the old ref, so any *other* pull request opened in that
window reports the retired names and blocks. Keep the window short, and expect a consumer whose ruleset
requires an approving review not to merge unattended.

### The App behind the proposal

The proposal is opened by a GitHub App, `turbobasic-release-proposal`, installed on this repository with
`Contents` and `Pull requests` write and nothing else. Its client id and private key live in the
`RELEASE_APP_CLIENT_ID` and `RELEASE_APP_PRIVATE_KEY` Actions secrets, which `propose-on-merge.yml`
passes into the capability by name, and the token each run mints is narrowed to those two permissions and
expires in an hour.

`GITHUB_TOKEN` cannot do this job: opening a pull request from Actions requires *Allow GitHub Actions to
create and approve pull requests*, which is off here and stays off, because it grants approving as well as
opening. An App is not "GitHub Actions", so it is not subject to that setting — and its pull requests
trigger the required checks with no click.

**If that key is rotated or the installation removed, no proposal is raised and nothing says so.** No
check reddens, because nothing failed: the workflow simply cannot mint a token. Reach for a dispatch of
[Release on merge][release-workflow] with `dry-run` to confirm the release path still works, and re-add the
secrets before expecting another proposal.

<!-- Links -->

[license]: LICENSE
[coc]: CODE_OF_CONDUCT.md
[security]: SECURITY.md
[ai-instructions]: docs/ai-instructions.md
[ai-instructions-changes]: docs/ai-instructions.md#changes-to-these-rules
[ai-instructions-specs]: docs/ai-instructions.md#specs
[constitution]: .specify/memory/constitution.md
[ai-instructions-tooling]: docs/ai-instructions.md#tooling-hierarchy
[ai-instructions-capabilities]: docs/ai-instructions.md#capabilities
[ai-instructions-quality]: docs/ai-instructions.md#quality-gates
[ai-instructions-versioning]: docs/ai-instructions.md#versioning
[readme]: README.md
[test-consumer]: https://github.com/turboBasic/github-actions-test
[readme-versioning]: README.md#versioning
[readme-release]: README.md#release
[release-proposal-workflow]: https://github.com/turboBasic/github-actions/actions/workflows/propose-on-merge.yml
[release-workflow]: https://github.com/turboBasic/github-actions/actions/workflows/release-on-merge.yml
