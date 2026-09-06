# Specification Quality Checklist: Tested Release Scripts

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-09-06
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic (no implementation details)
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Constitution Gates

- [x] **Cross-Repository Impact** answered: affected consumers, interface delta, compatibility, rollout and
      rollback — mandatory because `release.yml` is `workflow_call` with an external call site
- [x] **I. Consumer Contract Stability** — FR-009, FR-009a: no input/output/permission change, no job
      rename
- [x] **III. Least Privilege** — permissions unchanged; FR-009 forbids widening
- [x] **IV. Untrusted Input Is Data** — FR-011: arguments arrive through `env`, never `${{ }}`
- [x] **VI. Verification By Real Invocation** — SC-006, SC-007, SC-008; the `@v4` lag on the external
      route is named and handed to the plan
- [x] **VII. Gates Are Never Loosened** — FR-013, FR-014, SC-005: strict typing, no suppression, offline

## Notes

Two deviations from the template, both deliberate:

1. **Terminology.** The spec names `pyproject.toml`, `git-cliff`, `jq` and `--context`. These are not
   implementation choices being smuggled in — they are the existing system under description, and the
   spec would be unreadable without them. The choice this spec genuinely leaves open (PEP 723 scripts
   under `scripts/` versus a module in an existing package) is stated as an open decision in Assumptions
   and constrained only by FR-012 through FR-015.
2. **"Non-technical stakeholders" reads as "a maintainer who does not know this repository".** There is no
   business stakeholder for release plumbing; the Assumptions section says so.

**One correction to the source issue, now fixed at the source.** #61 originally stated that `ci.yml` is
`release.yml`'s only caller. `docs/consumers.md` records `github-actions-test` calling `release` at `@v4`,
and being the only place `release / tag-and-publish` reports. That moved the Cross-Repository Impact answer
from "no consumers" to "one, with no interface delta", and is what FR-009a and SC-008 exist for. The issue
description has since been rewritten to match, with the correction recorded in a comment there, so the two
no longer disagree.

**Scope decision on record.** Making the surface-path list a `workflow_call` input — #61's comment — is
excluded. It is a new input on a reusable workflow and owns its own spec.

**Amended after `/speckit-analyze`.** The cross-artifact pass found one CRITICAL and four HIGH issues, all
now resolved in the artifacts:

- **A branch pin was impossible, and the one-release plan deadlocked.** `test_first_party_actions_use_the_major_tag`
  forbids a `@branch` reference, and introducing `uses: …@v4` in the release that introduces the action
  makes `v4` resolve to a tree without it — no job, no release, no way for `v4` to move. Resolved by
  shipping in two stages ([research.md D9](../research.md#d9)); FR-018 and SC-010 now state the constraint.
- **FR-004 named three comparisons and only two had functions.** The breaking-under-a-non-major check had
  no function, no invariant and no task. Added as `breaks_under_non_major` with four invariants.
- **Four existing gates assert the shell being deleted.** None but one was accounted for. FR-017 and SC-011
  now require each to be rewritten or retired with its reason, in the stage that breaks it.
- **The check-runs query had no home.** FR-007 implied it stays shell; now stated, because
  `test_the_release_gates_on_a_required_context` asserts its literal is in `release.yml`.

Also corrected: US1's Independent Test now describes the phase that exists, SC-007 states its decision
instead of deferring it, FR-006 says "surface-filtered reads", the US2 title matches `tasks.md`, and
FR-014 gained the guard that keeps the suite offline.

**Amended after `/speckit-plan`.** Phase 0 found that the spec's assumed home for the logic, `scripts/` at
the repository root, breaks `github-actions-test`'s call site: `actions/checkout` inside a reusable
workflow checks out the *caller's* repository. The spec had recorded that trap as hypothetical. Its
Cross-Repository Impact, Assumptions and trap paragraphs were corrected, and the delivery shape is now a
composite action. The requirements themselves (FR-012 through FR-015) needed no change — they constrained
the shape without naming it, which is what let the plan pick a different one without reopening the spec.
