# Specification Quality Checklist: Declared Consumer Surface

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
      rollback — all four, before any plan
- [x] **I. Consumer Contract Stability**: the interface delta is empty, so no call site changes and no major
      is owed. The behaviour that does move is named, and its increment argued (minor, not patch)
- [x] **III. Least Privilege**: no permission changes
- [x] **IV. Untrusted Input Is Data**: caller-controlled paths reach the renderer through a parsed file, not
      inline `${{ }}`; FR-006 closes the leading-`-` route
- [x] **VI. Verification By Real Invocation**: behaviour turns entirely on the released repository's own
      file, so the spec names the consumer that must exercise it and SC-003 requires the undeclared state be
      seen on a real run before it is removed
- [x] **VII. Gates Are Never Loosened**: FR-008 requires the `OWN_CI` equality to move intact; FR-010
      forbids any override mechanism, which is what makes the old bypass hazard structural rather than tested

## Deviation from the source issue

- [x] #110 proposes a `workflow_call` input; this spec adds none. The deviation is stated in the spec's
      header, argued under *Why not the input*, and reasoned in full at
      [research.md D1](../research.md#d1). It is a smaller change with no interface delta, so the issue's
      shape is superseded rather than implemented — and #110 is owed a comment recording that.

## Notes

Two deliberate deviations from the template's "no implementation details" guidance, both matching
`003-tested-release-scripts`:

- The spec names files (`release.yml`, `pyproject.toml`, `OWN_CI`). The product here *is* a workflow
  contract, so a path is the user-facing noun rather than an implementation leak. The requirements still
  avoid naming the table, its keys, or any function — those are
  [contracts/config.md](../contracts/config.md).
- Success criteria are verification-shaped rather than metric-shaped: the users are two maintainers, and
  there is no volume or latency to measure.

One limit is recorded rather than sold as a feature: an undeclared surface and a declared-empty one produce
the *same* filter, differing only in whether a notice is printed. Stated in the spec's Key Entities and in
[data-model.md](../data-model.md#declaration-state).

The question #110 left open — what an empty list means — is answered by the mechanism rather than by
assumption. Structured data distinguishes absent from empty, so no reading had to be chosen for a blank
string, which is what made the earlier draft's "blank means use ours" necessary and unpalatable.
