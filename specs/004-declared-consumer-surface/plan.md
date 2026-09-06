# Implementation Plan: Declared Consumer Surface

**Branch**: `004-declared-consumer-surface` | **Date**: 2026-09-06 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/004-declared-consumer-surface/spec.md`

## Summary

The consumer surface moves from a constant in `actions/release-decisions/decisions.py` to a
`[tool.turbobasic-release]` table in the `pyproject.toml` of whichever repository is being released. A
repository that declares no surface gets an unfiltered range and a notice saying so, rather than inheriting
ours.

**#110 asked for a `workflow_call` input and this plan does not add one.** The reasoning is
[research.md D1](./research.md#d1); the consequence is that the change is far smaller than the issue
imagined, because `release.yml` already reads the caller's `pyproject.toml` — that is where
`[project].version`, the version being released, comes from.

Three facts checked before planning, each of which removed work:

1. **`PYPROJECT` already reaches the module** with `pyproject.toml` as its default (`action.yml:86`,
   `decisions.py:167`), and `action.yml` already declares the input. So **no workflow and no `action.yml`
   needs a functional change** — `release.yml`'s `surface-args` step and `release-proposal.yml`'s in-repo
   call both already pass everything required.
2. **Unfiltered falls out for free.** An empty flag list means `git-cliff` gets no `--include-path` at all,
   which is the unfiltered range. No branch in any workflow, no special value.
3. **The change is a net deletion in the module.** `OWN_WORKFLOWS` was a second copy of `OWN_CI` held equal
   by test; it stops existing ([research.md D4](./research.md#d4)).

So the diff is: `decisions.py`, our own `pyproject.toml`, two test files, `README.md`,
`docs/consumers.md`, and one stale comment in `release.yml` that currently promises this will be an input.

## Technical Context

**Language/Version**: Python 3.14 locally; the module runs under whatever `python3` the runner resolves, so
standard library only and no syntax newer than the oldest maintained interpreter parses

**Primary Dependencies**: none at runtime — `tomllib` is already imported for `[project].version`. Dev-side:
pytest, pyright, ruff, actionlint, zizmor, all already present

**Storage**: N/A. The declaration is committed configuration

**Testing**: pytest, offline, no marker. Nothing here needs the network, so nothing here is `drift`

**Target Platform**: GitHub Actions `ubuntu-latest`; the module is also imported by the local suite on macOS

**Project Type**: reusable GitHub Actions workflows and composite actions. No application

**Performance Goals**: N/A. One TOML parse that already happens, and two list comprehensions

**Constraints**: zero interface delta (FR-010); our own release byte-identical (FR-007, SC-001); the
`OWN_CI` equality relocated intact and never relaxed (FR-008); `mise run ci` stays offline (FR-013);
pyright strict, no suppression

**Scale/Scope**: one module, one config table, two test files, two documents. Two call sites exist; one of
them is the verification site

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Verdict | How the design satisfies it |
| --- | --- | --- |
| **I. Consumer Contract Stability** | **PASS**, and it is what rejected the input | The interface delta is empty — no input, output, secret, permission or job name moves. Nothing a consumer wrote has to change, so no major is owed. Behaviour moves only for an undeclared caller, in the stricter direction, which is a minor ([research.md D7](./research.md#d7)). |
| **II. Supply-Chain Pinning** | PASS | No new action reference of any kind, and the rejected alternatives include a third-party utility precisely because it would have added one for a data-location problem. |
| **III. Least Privilege** | PASS | No permission changes. The decision reads a file the job already reads and writes one string. |
| **IV. Untrusted Input Is Data, Never Code** | **PASS, and strengthened** | Caller-controlled paths become arguments to `git-cliff`, and they now reach the module through a file it parses rather than through `${{ }}` — one interpolation hop fewer than the input would have been. FR-006's rejection of a leading `-` closes the one way a path could still be read as a flag. |
| **V. Secrets Never Persist** | PASS | Touches no token. |
| **VI. Verification By Real Invocation** | PASS, with two rungs that cannot be skipped | Behaviour turns entirely on the released repository's own file, so the offline suite proves only the decisions. Two constraints found by running it rather than reasoning about it, both in [quickstart.md](./quickstart.md): **a dispatch of `release.yml` cannot exercise this module at all**, because it reaches the action through `@v4` and `${GITHUB_ACTION_PATH}` is the tagged download — `release-proposal.yml`, which calls it by in-repo path, is the pre-tag exerciser; and **a dry-run dispatch reaches the refusal without cutting a tag**, because `check-notes` runs whenever `verify.outputs.proceed` is true and a dry run makes it true, which is what makes the consumer rungs cheap. `github-actions-test` still has to exercise both directions and the undeclared case at the ref it pins, after `@v4` moves. |
| **VII. Gates Are Never Loosened** | **PASS, and it is the principle most at risk** | The hazard was never a suppression, it was a bypass. Rejecting the input removes it structurally: there is nothing for a dispatch form or a caller's `with:` to override. `test_the_surface_exclusions_are_own_ci_as_workflow_paths` is *relocated* — same equality, different left-hand side — and gains a third assertion for the failure the move creates (our table missing, which would put our own release on the unfiltered path). No test is deleted, no regex loosened; the rejected `needs` alternative was rejected partly because it would have loosened one. |

**Post-Phase-1 re-check**: no violations, nothing for Complexity Tracking. Two things surfaced after the
first pass and are recorded rather than smoothed over: that absent and declared-empty produce the *same*
filter and differ only in the notice ([research.md D2](./research.md#d2), stated as a limit rather than
sold as a feature), and that our own surface is derivable from the tree and deliberately is not derived
([research.md D6](./research.md#d6)).

## Project Structure

### Documentation (this feature)

```text
specs/004-declared-consumer-surface/
├── plan.md              # This file
├── research.md          # Phase 0: the decisions, with what was rejected
├── data-model.md        # Phase 1: the table, its states, its validation
├── quickstart.md        # Phase 1: the verification ladder, in order
├── contracts/
│   ├── config.md        # the [tool.turbobasic-release] table a caller writes
│   └── decisions.md     # the module's functions, and the tests that move
├── checklists/
│   └── requirements.md  # spec quality gate
└── tasks.md             # /speckit-tasks output, not created here
```

### Source Code (repository root)

```text
actions/release-decisions/
├── decisions.py              # constants deleted; surface read from the table; three pure functions
└── action.yml                # unchanged — `pyproject` already carries the file

.github/workflows/
├── release.yml               # comment only: it currently promises this will be an input
└── release-proposal.yml      # unchanged — already reads our pyproject.toml through the same path

pyproject.toml                # + [tool.turbobasic-release], this repository's own surface

tests/
├── test_release_decisions.py # the new decisions; the OWN_CI gate relocated and widened
└── test_action_pins.py       # unchanged — no input set moves, so the frozen-interface table stands

README.md                     # the release.yml section; how a caller declares its surface
docs/consumers.md             # the obligation this puts on release.yml's callers
```

**Structure Decision**: nothing new is created and nothing is moved between files. `action.yml`,
`release-proposal.yml` and `test_action_pins.py` are listed because their *absence* from the functional
diff is a requirement — FR-010 for the first two, and for the third the fact that
`test_the_release_interface_is_frozen` still asserts exactly `{dry-run}`, which under the rejected input
design would have had to be edited. That test standing unchanged is the cheapest proof the interface delta
is empty.

## Complexity Tracking

No constitution violations, so nothing to justify.
