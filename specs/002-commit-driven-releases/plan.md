# Implementation Plan: Commit-driven releases

**Branch**: `002-commit-driven-releases` | **Date**: 2026-09-02 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/002-commit-driven-releases/spec.md`

## Summary

`git-cliff` renders the seven sections from the commits in a range, configured by one `.cliff.toml`,
and three callers share it: the workflow that raises the release proposal, the workflow that
publishes the release, and a `mise` task a maintainer types. The proposal is a pull request that
bumps `[project].version` and carries the rendered notes as its body; merging it is the approval, and
the release fires from a job in `ci.yml` that `needs: [ci]`, so it starts only once `ci / CI` is
green on the merge commit. The proposal is opened by a GitHub App installation token, because `GITHUB_TOKEN` cannot open a pull request here without granting Actions
the power to approve one.

Nothing consumers resolve changes. What changes is how the notes are categorised (commit type, not
pull request label), where the version decision is recorded (a bot-raised pull request instead of a
hand-written one), and what triggers the release (a green CI verdict on an approved commit instead of
a manual dispatch).

The second half of the existing `release.yml` survives untouched — the annotated version tag,
`gh release create`, and the atomic `PATCH refs/tags/vN --force`. `evidence/release-managers.md`
established that no candidate tool moves a major tag, so that code was never up for replacement.

## Technical Context

**Language/Version**: no application language. `git-cliff` 2.13.1 owns the rendering, bash owns the
workflow steps. No Python is added — the existing suite gains assertions about `.cliff.toml`, not a
parser to test.

**Primary Dependencies**: `git-cliff = "2.13.1"` newly pinned in `mise.toml`
(`aqua:orhun/git-cliff`, the registry short name, so Renovate's mise manager bumps it). `gh`,
pre-installed on the runner, for every API call. `actions/checkout` and `jdx/mise-action` at the SHAs
this repo already pins, plus one new action —
`actions/create-github-app-token@bcd2ba49218906704ab6c1aa796996da409d3eb1 # v3.2.0` — which mints the
short-lived installation token every write uses (research.md decision 11). commitizen stays a dev dependency for what it already does — the commit-msg
hook and `test_allowed_types_match_the_commitizen_builtin_set` — and is not involved in rendering or
in computing the version.

**Storage**: N/A. The state is git refs and GitHub's own objects: tags, one long-lived proposal
branch, one open pull request. Nothing is persisted in the tree.

**Testing**: pytest asserts `.cliff.toml`'s mapping offline — that all twelve allowed types are placed,
that the seven titles and their order are intact, and that the consumer-surface path filter agrees
with `OWN_CI`. Rendering itself is verified by the spikes in `evidence/changelog.md` and re-verified
once against real history by `quickstart.md`. actionlint, zizmor `--pedantic`, yamllint and the
timeout schema cover the new workflow as they cover every other.

**Target Platform**: `ubuntu-latest` runners, and a local checkout on macOS or Linux for Story 3.

**Project Type**: reusable-workflow repository. This feature is entirely repo-local plumbing — it adds
nothing a consumer resolves.

**Performance Goals**: N/A. The release path runs a few times a month over tens of commits.

**Constraints**: the rendering reaches no network (FR-015) — git-cliff's `--remote.github`
integration stays off, which is also what keeps `mise run ci` offline. No credential is written where
a later step could read it (FR-014, Principle V), so every checkout sets `persist-credentials: false`
and every write goes through `gh` with the token in `env`. The notes exist before any tag does
(FR-006).

**Scale/Scope**: one repository, eight workflows after this change, release ranges of tens of commits
and twelve allowed commit types.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Re-evaluated after Phase 1 — the verdicts below are the post-design ones.

| Principle | Verdict | Why |
| --- | --- | --- |
| **I. Consumer Contract Stability** | Pass | Every file touched is repo-local. `release.yml` does declare `workflow_call`, but its only caller is `ci.yml` in this repository — it is not listed in `README.md` and `OWN_CI` excludes it, so no consumer resolves it and there is no call site to break. `release-proposal.yml` is not callable at all. `docs/consumers.md` needs no edit. |
| **II. Supply-Chain Pinning** | Pass | One new action, `actions/create-github-app-token`, pinned to a full SHA with its `# v3.2.0` comment — and it is GitHub's own org, not a third party. `git-cliff` is a **mise tool pin**, the sanctioned route for a CLI, covered by `test_no_mise_tool_version_floats` the moment it lands; 2.13.1 is the version the spike ran and what the aqua registry serves. |
| **III. Least Privilege** | Pass, and improved | `GITHUB_TOKEN` in `release-proposal.yml` needs only `contents: read`, for the checkout — every write uses the App installation token instead, scoped to this repository, expiring in an hour, granting `Contents` and `Pull requests` write and nothing else. No `issues: write`, because it applies no labels. `release.yml` keeps `contents: write` and gains nothing. |
| **IV. Untrusted Input Is Data** | Pass, and load-bearing here | This feature's entire input is attacker-influenceable text: a commit subject is a merged pull request title. No commit text passes through `${{ }}` into a `run:` block — git-cliff reads git and writes a file, and `gh release create --notes-file` reads that file. See research.md decision 3 for the second sink, markdown inside a breaking-change footer. |
| **V. Secrets Never Persist** | Pass | Two secrets, an App id and private key, live in Actions secrets — the sanctioned place — and neither they nor the minted token are written to a file, a log, an artifact or this repository. The installation token reaches each step through `env` and expires in an hour. Every checkout sets `persist-credentials: false`, so zizmor's `artipacked` audit stays clean and no `.git/config` carries a credential for a later step. Branch writes go through `gh api`, so nothing is pushed from a working tree. |
| **VI. Verification By Real Invocation** | **Partial — see Complexity Tracking** | `release.yml` is exercised by a `dry-run` dispatch, and `release-proposal.yml` by a temporary `push` trigger on this branch, since a new workflow is invisible to `workflow_dispatch`. What stays unexercised until merge is `ci.yml`'s `release` job, which runs only on a push to `main`. |
| **VII. Gates Are Never Loosened** | Pass | Nothing is silenced. One prek hook and one `mise run lint` line are *deleted*, together with the config file they validate (FR-017). The actionlint ignore is untouched. |

**Cross-Repository Impact**: the spec argues this section does not apply, and the design bears that
out — no reusable workflow or composite action is touched, so there is no interface delta, no consumer
to migrate and no rollout order. Rollback is reverting one commit: `.github/release.yml` and the
previous release step come back together, and no consumer was ever involved.

## Project Structure

### Documentation (this feature)

```text
specs/002-commit-driven-releases/
├── plan.md              # This file
├── research.md          # Phase 0: the four tool axes, then the wiring decisions on top
├── data-model.md        # Phase 1: the entities the rendering works in
├── quickstart.md        # Phase 1: how to validate this end to end
├── contracts/
│   ├── release-notes.md       # the rendering contract: sections, invocation, the facts it yields
│   └── workflow-triggers.md   # triggers, permissions and refusals of both workflows
├── checklists/          # pre-existing
├── evidence/            # pre-existing tool evaluations; Phase 0 defers to these
└── tasks.md             # Phase 2 (/speckit-tasks — not created here)
```

### Source Code (repository root)

```text
.cliff.toml                      # NEW: the whole shaping rule — parsers, seven groups, ordering

.github/workflows/
├── release-proposal.yml        # NEW: raises and refreshes the proposal on every push to main
└── release.yml                 # CHANGED: workflow_run trigger, renders its own notes, two new refusals

.github/
└── release.yml                 # DELETED: the label-driven config (FR-017)

tests/
├── test_release_notes.py       # NEW: .cliff.toml maps all twelve types onto the seven titles, in order
└── test_action_pins.py         # CHANGED: OWN_CI gains the new workflow; new gates for the above

mise.toml                       # CHANGED: git-cliff pin, `release-notes` task, drop the dead schema line
.pre-commit-config.yaml         # CHANGED: drop the `check-release-config` hook
CONTRIBUTING.md                 # CHANGED: Releasing becomes approve-a-proposal — and the repo-local
                                #   workflow list at :66 and :106, which is the same list as OWN_CI
README.md                       # CHANGED: Versioning no longer says "a dispatch of the Release workflow"
docs/ai-instructions.md         # CHANGED: the Versioning paragraph's description of the release path
```

**Structure Decision**: `.cliff.toml` at the repository root — the dotted name, which git-cliff's
discovery finds without a `--config` flag in any of the three call sites. Three things were verified
against 2.13.1 rather than assumed, because a config file nothing loads and nothing lints is the
failure mode here:

| Question | Answer |
| --- | --- |
| Does git-cliff find `.cliff.toml` with no flag? | Yes — it logs `Using configuration from parent directory: …/.cliff.toml` and renders from it. `--config`'s *default* is the bare `cliff.toml`, but discovery covers both names. |
| Does `taplo fmt` still collect a dotfile? | Yes — it appears in taplo's `found files` list and is reported when it is not properly formatted. `taplo.toml` excludes only `.venv`. |
| Does prek's `check-toml` accept it? | Yes. |
| Could the config live in `pyproject.toml` under `[tool.git_cliff]` instead, adding no file at all? | **No** — 2.13.1 warns `"cliff.toml" is not found, using the default configuration` and ignores the table. That is a `Cargo.toml`-only feature. |

It needs no other registration, and Renovate's `mise` manager owns the version pin. It gets **no**
`check-jsonschema` hook, unlike every GitHub config file here: it is not a GitHub config, and git-cliff
publishes no schema for it — the compensating control is `tests/test_release_notes.py`, which asserts
the mapping a schema could not have checked anyway.

No `scripts/` directory and no new Python. Choosing git-cliff over a hand-written parser is what
removed it (research.md decision 1).

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
| --- | --- | --- |
| **Principle VI, partially unmet**: `ci.yml`'s `release` job and `release-proposal.yml`'s `push: main` trigger cannot be exercised at the ref under review | GitHub runs a `push` workflow and resolves `workflow_run` from the default branch only. There is no ref at which a feature branch's copy of either trigger fires. FR-009 and FR-011 require both. | Polling for the CI verdict from a `push`-triggered job would be exercisable no more than `workflow_run` is — same trigger problem, plus runner minutes. A consumer cannot help, since nothing here is callable. Mitigation instead: `release.yml` gains a `dry-run` dispatch input that runs every refusal and renders the real notes but stops before the tag, and `release-proposal.yml` is exercised through a **temporary `push` trigger on this feature branch**, removed before merge. **Not a dispatch** — an earlier draft of this row said dispatch, and that is impossible: GitHub offers `workflow_dispatch` only for a workflow already on the default branch, which is the constraint research.md decision 10 hit while probing. `release.yml` can be dispatched because it is already on `main`; a new workflow cannot. What stays unverified until merge is the two trigger blocks themselves — the same residual `release.yml` carries today. |
| **A GitHub App must be registered and installed**, holding two secrets, and that setup cannot live in this repository | The proposal has to be opened by an identity whose pull requests trigger the required checks. `GITHUB_TOKEN` cannot: `Allow GitHub Actions to create and approve pull requests` is off in both repositories — probed, not assumed (research.md decision 10) — and `POST /pulls` answers `GitHub Actions is not permitted to create or approve pull requests` (403). | Enabling that setting was the cheaper-looking route and is rejected on what it grants: it lets Actions *approve* pull requests, not merely create them, so every workflow in the repository would gain the power to satisfy the review gate the ruleset exists to enforce. A PAT avoids the setting by introducing a long-lived human-owned credential into a release path built so no credential reaches a workspace. The App token is scoped to this repository, expires in an hour, and removes the unverified *Approve and run* click as well. Decision 11 has the full reckoning. |
| ~~A pre-flight is owed on three git-cliff flags~~ — **done**, see contracts/release-notes.md | `--context`, `--include-path` and `--exclude-path` carry the two facts the refusals need and the path scoping the version proposal needs. | Resolved rather than justified: all three were exercised against 2.13.1 with a throwaway harness in gitignored `tmp/`; the validated configuration is preserved in contracts/release-notes.md, and no fallback is needed. Two findings changed the design — an empty range exits 0 with zero bytes (so FR-007 is a file-size check), and `breaking` is absent rather than `false` on an unconventional commit (so the jq test compares against `true`). Kept in this table because it is the row a reviewer would otherwise ask about. |
