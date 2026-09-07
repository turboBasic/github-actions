# Specification Quality Checklist: The 0.x Compatibility Line

**Purpose**: Validate specification completeness and quality before planning
**Created**: 2026-09-07
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
- [x] Success criteria are technology-agnostic
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

- [x] **Cross-Repository Impact** answered: consumers, interface delta, compatibility, rollout and rollback
- [x] **I. Consumer Contract Stability**: no `workflow_call` interface change, and FR-007 makes "nothing above
      0.x moves" a requirement with its own assertions rather than an expectation. Both consumers are `1.x`+,
      so neither can observe this
- [x] **III. Least Privilege**: no permission changes
- [x] **VI. Verification By Real Invocation**: the spec states plainly that no *existing* consumer can reach
      the changed path, and what is done about it — `github-actions-test` reset to an unreleased 0.x state
- [x] **VII. Gates Are Never Loosened**: `test_tag_pattern_excludes_the_moving_major_tags` is extended, not
      rewritten; and D5 exists precisely to stop the refusal being silently disabled for one release

## Scope beyond the source issue

- [x] `next_version` is included though #107 does not mention it. Verified by running the current code:
      `next_version((0,1,0), breaking=True)` is `(1,0,0)`. Without it the new allowance is unreachable by the
      automated path. Argued at [research.md D2](../research.md#d2).
- [x] The 0.x/1.x split is unified behind one function rather than fixed in each of the three places that
      need it. [research.md D4](../research.md#d4), and T002 asserts the split appears once.

## Findings recorded rather than smoothed over

- [x] **A 0.x `feat` and `fix` propose the same version.** The line consumes two components, leaving only the
      patch. Deliberate, and pinned by a test so it cannot be "fixed" by accident
      ([research.md D3](../research.md#d3)).
- [x] **Dropping `highest-major` would disable the refusal for one release.** `release.yml` resolves as `$/`
      while the action resolves at `@v4`, so one run pairs the new workflow with the old module. The issue
      proposed an additive change and was right, for a reason it did not state
      ([research.md D5](../research.md#d5)).
- [x] **A `-obsolete` tag suffix would not have worked.** `.cliff.toml`'s `tag_pattern` is applied unanchored,
      so `v1.0.0-obsolete` still matches and would bound a range, while `highest_version`'s anchored pattern
      would ignore it. Moot now that the tags are deleted outright, but recorded because the asymmetry between
      those two patterns is a trap either way.

## Notes

Same two deliberate deviations from the template as `003` and `004`: the spec names files, because a workflow
contract's user-facing nouns *are* paths; and success criteria are verification-shaped rather than
metric-shaped, because the actor is a maintainer and there is no volume or latency to measure.

The requirements deliberately avoid naming `compatibility_line`, `moving_tag` or the table key — those are
[contracts/decisions.md](../contracts/decisions.md). FR-001 and FR-002 state the *rule*, which is what has to
hold however it is spelled.
