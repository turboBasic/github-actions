# Implementation Plan: Tested Release Scripts

**Branch**: `003-tested-release-scripts` | **Date**: 2026-09-06 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/003-tested-release-scripts/spec.md`

## Summary

Move the decidable logic out of `release.yml` and `release-proposal.yml` into standard-library-only Python that
the offline suite can import and test, leaving the plumbing — `git-cliff`, `gh api`, `uv version`,
`GITHUB_OUTPUT` — as shell.

The spec's proposed home, `scripts/` at the repository root, **does not work for `release.yml`** and the
plan does not use it. `release.yml` is called cross-repo by `github-actions-test`, and inside a reusable
workflow `github.repository` resolves to the *calling* repository — which is why `release.yml` reads the
caller's `pyproject.toml` and releases the caller. A file in this repository's tree is simply absent
from that job. The logic therefore lives in a **composite action**, whose repository Actions downloads
independently of the workspace, reachable through `${GITHUB_ACTION_PATH}` exactly as
`actions/populate-pr-description` already reaches `populate.py`.

## Technical Context

**Language/Version**: Python 3.14, standard library only for everything extracted

**Primary Dependencies**: none at runtime. `tomllib`, `json`, `re`, `os` are in the standard library. Dev-side:
pytest, pyright, ruff, already present

**Storage**: N/A

**Testing**: pytest, offline, no marker — these tests belong to the default suite, not to `drift`

**Target Platform**: GitHub Actions `ubuntu-latest`; the Python is also imported by the local suite on
macOS

**Project Type**: reusable GitHub Actions workflows and composite actions. No application

**Performance Goals**: N/A. Every extracted function is a pure comparison over a handful of strings

**Constraints**: `mise run ci` must stay offline (FR-014); pyright strict with no suppression (FR-013);
no change to any `workflow_call` input, output, permission or job name (FR-009, FR-009a)

**Scale/Scope**: two workflows, ~301 lines of block-scalar shell today, of which ~191 are code rather
than comment or blank

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Verdict | How the design satisfies it |
| --- | --- | --- |
| **I. Consumer Contract Stability** | **PASS** — and this is the gate that shaped the design | The naive `scripts/` extraction would have broken `github-actions-test`'s call site. A composite action keeps both call sites byte-identical. No input, output, permission or job name moves; `tag-and-publish` and `propose` are pinned by test. |
| **II. Supply-Chain Pinning** | PASS | No new third-party action. The one new first-party reference from `release.yml` uses the moving major tag, matching `prek-advisory.yml:70` — and is never pinned to a branch, which is what forces the two-stage delivery ([research.md D9](./research.md#d9)). |
| **III. Least Privilege** | PASS | The action declares no permissions of its own; it runs inside the job that already holds them. Nothing is widened. |
| **IV. Untrusted Input Is Data** | PASS, and strengthened | Every argument arrives as an `action.yml` input mapped to `env`. Commit subjects continue to reach nothing but a file read by `--notes-file`. Extraction removes shell-quoting sites rather than adding them. |
| **V. Secrets Never Persist** | PASS | The extracted logic touches no token. `GH_TOKEN` stays in the shell steps that call `gh`. |
| **VI. Verification By Real Invocation** | PASS, with a route that must be followed in order | Ladder in [quickstart.md](./quickstart.md), split across the two stages: offline tests, then `release-proposal.yml` exercising the module for real in stage 1, then a dry-run dispatch and a real release in `github-actions-test` repointed at the stage-2 branch — **before** this repository's `main` cuts a tag with the new `release.yml`. Our version tags are immutable; its are disposable. |
| **VII. Gates Are Never Loosened** | PASS, and it is the binding constraint | pyright strict unchanged; `extraPaths`/`pythonpath` are additions, not relaxations. No new ignore, and the existing `actionlint` ignore is untouched. Critically, `test_first_party_actions_use_the_major_tag` is **not** relaxed to admit a branch pin — that gate is why the work is two releases instead of one. FR-017 also requires the four gates this change breaks to be rewritten or retired deliberately, never left to fail unnoticed. |

**Post-Phase-1 re-check**: no violations introduced. Two things surfaced after the first pass and are
recorded rather than smoothed over: the two-stage delivery that Principles II and VII force
([research.md D9](./research.md#d9)), and the four existing gates this change breaks
([contracts/decisions.md](./contracts/decisions.md#existing-tests-this-change-breaks)). One convention
tension is flagged and *not* resolved unilaterally — `.github/actions/` in
[research.md D5](./research.md#d5).

## Project Structure

### Documentation (this feature)

```text
specs/003-tested-release-scripts/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   ├── action.md        # the composite action's input/output contract
│   └── decisions.md     # the Python module's public functions
├── checklists/
│   └── requirements.md  # from /speckit-specify
└── tasks.md             # /speckit-tasks output — NOT created here
```

### Source Code (repository root)

```text
actions/release-decisions/
├── action.yml            # composite; maps inputs to env, runs the script
└── decisions.py          # the pure logic plus a thin __main__, standard library only

.github/workflows/
├── release.yml           # two `uses:` of the action at @v4, plumbing shell around them
└── release-proposal.yml  # invokes the same file by in-repo path; it never runs elsewhere

tests/
├── test_release_decisions.py  # new: the pure functions, offline
├── test_release_notes.py      # amended: surface list held to OWN_CI by import, not YAML text
└── test_action_pins.py        # amended: job names pinned; new action gets the usual gates

pyproject.toml            # + pytest pythonpath, + pyright extraPaths. That is all: `[tool.ruff].src`
                          # and `[tool.pyright].include` already list `actions`

```

**Structure Decision**: the logic lives in **one** composite action, `actions/release-decisions/`,
because that is the only home reachable from `release.yml`'s cross-repo caller. `release-proposal.yml`
has no `workflow_call` trigger and only ever runs in this repository, so it invokes the same file by
path rather than through `uses:` — one copy of the code, two ways in, which is what keeps the surface
path list from splitting across two languages.

`actions/` rather than `.github/actions/` follows the written convention, though the convention's own
stated rationale argues the other way for an action only `release.yml` calls. Flagged, not resolved
unilaterally: [research.md D5](./research.md#d5).

### Delivery stages

Two pull requests, two releases. Forced by Principles II and VII, not chosen — see
[research.md D9](./research.md#d9).

| Stage | Ships | Adds a `uses:`? |
| --- | --- | --- |
| **1** | the complete action — module, `__main__`, all three decisions, `action.yml` — plus `release-proposal.yml` rewired to invoke it by in-repo path, plus the surface constant and every test | **No.** Nothing resolves `@v4`, so nothing can deadlock |
| **2** | `release.yml` rewired to `uses: …@v4`, now that stage 1's release put the action in that tree | Yes, and it resolves |

Stage 1 ships the action **complete**, including the `verify-version` and `check-notes` decisions only
`release.yml` will call, so that stage 2's branch and `@v4` hold identical action code and stage 2's
verification means something.

## Complexity Tracking

> Filled because the design adds a public artifact the spec did not anticipate.

| Violation | Why Needed | Simpler Alternative Rejected Because |
| --- | --- | --- |
| A new composite action, i.e. new public surface, where the spec assumed a private `scripts/` directory | `release.yml` is called cross-repo by `github-actions-test`; its own checkout is the *caller's* tree, so nothing in this repository's tree is on disk. An action's repository is downloaded independently, which is the only mechanism that reaches it without new workflow inputs. | `scripts/` alone breaks the external call site (Principle I). A `scripts-ref` input plus a second checkout adds contract surface consumers must keep in sync with their own pin. Extracting only `release-proposal.yml` leaves the refusal ladder untested *and* splits the surface path list across Python and shell — worse than the two identical shell copies `#90` created deliberately. |
| The action carries a `decision` discriminator input rather than being one cohesive verb | `release.yml` asks two different questions (may this be released; are these notes publishable), and the issue's own comment requires they stay two calls with different arguments. | Two separate actions read better as contracts but double the new public surface for something only `release.yml` calls. One action, one new name. |
| Two releases instead of one, doubling the review and release overhead | `release.yml`'s `uses: …@v4` cannot resolve until a release exists whose tree holds the action, and a branch pin fails `test_first_party_actions_use_the_major_tag`. | One release with a temporary branch pin turns the suite red and still deadlocks at merge. Relaxing that gate is Principle VII. Invoking the module by in-repo path from `release.yml` works only for the self-call and breaks `github-actions-test`. |
