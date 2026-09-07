# Implementation Plan: The 0.x Compatibility Line

**Branch**: `005-zero-x-compatibility-line` | **Date**: 2026-09-07 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/005-zero-x-compatibility-line/spec.md`

## Summary

One idea carries the whole change: the **compatibility line** a moving ref may span — `(major)` from
`1.0.0` up, `(major, minor)` below it. Three decisions then fall out of it with no 0.x branch of their own:

| Decision | Today | After |
| --- | --- | --- |
| the refusal | `version.major == highest_major` | the release's line equals the highest release's line |
| the increment | breaking → next major | breaking → next line; otherwise advance within the line |
| the moving tag | `v${VERSION%%.*}` in shell | `v` + the line, decided in the module |

Because all three read one function, the 0.x rule cannot end up stated three times and drift. That is the
design, and `test_the_line_is_the_only_place_the_split_lives` is what holds it.

Two things shaped the plan beyond the issue:

1. **`next_version` is in scope.** It returns `(1, 0, 0)` from `(0, 1, 0)` on a break, verified by running
   it, so fixing only the refusal would leave the new `0.2.0` allowance unreachable — every 0.x break would
   arrive as a `1.0.0` proposal. [research.md D2](./research.md#d2).
2. **The 0.x path cannot be verified in any existing consumer.** `is_ahead` spans every major and
   `github-actions-test` is at `2.0.0`, so it can never publish 0.x again. A throwaway repository is stood
   up for it; [quickstart.md](./quickstart.md) is the route. This is the plan's largest cost and it buys the
   only real invocation available.

## Technical Context

**Language/Version**: Python 3.14 locally; standard library only, and no syntax newer than the oldest
maintained interpreter parses, because the runner resolves `python3` for the action

**Primary Dependencies**: none new. Dev-side: pytest, pyright, ruff, actionlint, zizmor, all present

**Storage**: N/A

**Testing**: pytest, offline, no marker

**Target Platform**: GitHub Actions `ubuntu-latest`; the module is also imported by the local suite on macOS

**Project Type**: reusable GitHub Actions workflows and composite actions. No application

**Performance Goals**: N/A. Tuple comparisons over three integers

**Constraints**: nothing at or above `1.0.0` may change (FR-007, SC-001); no `workflow_call` interface
change (FR-008); the moving-ref shape must stay outside `.cliff.toml`'s `tag_pattern` (FR-009);
`mise run ci` stays offline (FR-011); pyright strict, no suppression

**Scale/Scope**: one module, one workflow's tag step, two test files, two documents. Two consumers, neither
of which can reach the changed path

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Verdict | How the design satisfies it |
| --- | --- | --- |
| **I. Consumer Contract Stability** | **PASS**, trivially and deliberately | No `workflow_call` interface changes, and no behaviour at or above `1.0.0` moves. Both consumers are `1.x`+, so neither can observe this at all. FR-007 makes the no-change-above-0.x property a requirement with its own assertions rather than a hope. |
| **II. Supply-Chain Pinning** | PASS | No new action reference. |
| **III. Least Privilege** | PASS | No permission changes; the same step publishes the same kind of ref under a different name. |
| **IV. Untrusted Input Is Data, Never Code** | PASS, and slightly improved | The moving tag stops being built by shell expansion of an interpolated version and arrives as a step output through `env`, so one more string leaves the shell's hands. |
| **V. Secrets Never Persist** | PASS | Touches no token. |
| **VI. Verification By Real Invocation** | **PASS only with the throwaway repository**, and this is the gate that shaped the plan | Offline tests cover every decision, but creating and force-moving `v0.1` is API behaviour they cannot reach — and no existing consumer can host it, because `is_ahead` spans every major and `github-actions-test` is at `2.0.0`. Shipping the tag-move half on offline evidence alone is exactly what this principle forbids. [quickstart.md](./quickstart.md) rungs 4–6. |
| **VII. Gates Are Never Loosened** | PASS | No suppression, no relaxed mode. `test_tag_pattern_excludes_the_moving_major_tags` is *extended* to cover `v0.1`, the new moving shape — the same assertion over a larger set. The `immutable release tags` ruleset needs no edit: `refs/tags/v*.*.*` requires two literal dots, so `v0.1` stays movable and `v0.1.0` stays immutable. |

**Post-Phase-1 re-check**: no violations, nothing for Complexity Tracking. The one thing re-examined after
the first pass is recorded rather than smoothed over: a 0.x `feat` and a 0.x `fix` propose the *same*
version, because within a 0.x line there is only one component left to advance
([research.md D3](./research.md#d3)).

## Project Structure

### Documentation (this feature)

```text
specs/005-zero-x-compatibility-line/
├── plan.md              # This file
├── research.md          # Phase 0: the decisions, with what was rejected
├── quickstart.md        # Phase 1: the verification route, including the consumer reset
├── contracts/
│   └── decisions.md     # the compatibility line, the functions reading it, and the action's interface
│                        # (no data-model.md: the entity is one tuple, and the spec's Key Entities has it)
├── checklists/
│   └── requirements.md  # spec quality gate
└── tasks.md             # /speckit-tasks output
```

### Source Code (repository root)

```text
actions/release-decisions/
├── decisions.py              # + compatibility_line, moving_tag; refusal and increment read them
└── action.yml                # highest-major → highest-version; + moving-tag output

.github/workflows/
├── release.yml               # the tag step takes the moving tag as an input, not ${VERSION%%.*}
└── release-proposal.yml      # unchanged — it reads next_version through the same module

tests/
├── test_release_decisions.py # the line, both defects, and the above-1.0.0 no-change assertions
└── test_release_notes.py     # tag_pattern extended to reject v0.1

README.md                     # Versioning: what a 0.x consumer pins
CONTRIBUTING.md               # Releasing: the 0.x increment
docs/consumers.md             # unchanged — no consumer's row moves
```

**Structure Decision**: `release-proposal.yml` and `docs/consumers.md` are listed because their absence
from the diff is a property worth stating — the first because it picks the fix up through the module with
no edit, the second because no consumer is affected. `action.yml` does change, and it is the only interface
that does; that it is internal is recorded in `docs/consumers.md` already.

## Complexity Tracking

No constitution violations, so nothing to justify.
