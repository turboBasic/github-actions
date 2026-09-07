# Feature Specification: The 0.x Compatibility Line

**Feature Branch**: `005-zero-x-compatibility-line`

**Created**: 2026-09-07

**Status**: Draft

**Input**: Issue [#107](https://github.com/turboBasic/github-actions/issues/107) — "fix: release.yml
refuses the one increment SemVer reserves for a breaking 0.x change".

**Relates to**: [`004-declared-consumer-surface`](../004-declared-consumer-surface/spec.md) changed *what*
the breaking-change refusal measures. This changes *when* that refusal is right. Independent; neither
depends on the other.

## Why this has a spec at all

Two things a consumer can see change: which increments a release refuses, and which ref a release
publishes. `docs/ai-instructions.md`'s size table puts a behaviour change consumers can see on the spec
path, and `release.yml`'s live external call site puts it under the constitution's **Cross-Repository
Impact** gate.

## The defect

Under [SemVer §4](https://semver.org/#spec-item-4) a `0.y.z` version carries no stability guarantee, and
the component that signals a breaking change is the **minor**. The refusal compares majors only:

```python
return breaking and highest_major is not None and version[0] == highest_major
```

Verified against the current code, from `0.1.0` with a breaking range:

| Increment | Today | Should be |
| --- | --- | --- |
| `0.1.1` | refused | refused — a patch may not break |
| `0.2.0` | **refused** | **allowed** — this is SemVer's signal for a 0.x break |
| `1.0.0` | allowed | allowed |

So of the three increments available, the refusal gets one wrong — and it is the one the spec reserves for
exactly this case, leaving a 0.x caller two exits: jump to `1.0.0`, or rewrite the commit.

**A second defect, not in the issue.** `next_version((0, 1, 0), breaking=True)` returns `(1, 0, 0)`,
verified by running it. So `release-proposal.yml` proposes graduating to stable on any 0.x break. Fixing
only the refusal would leave the new `0.2.0` allowance unreachable by the automated path: every 0.x break
would arrive as a `1.0.0` proposal, and reaching `0.2.0` would need a human to edit the number down. Both
halves are in scope, because the proposal and the refusal have to agree on what 0.x means.

## The decision this drags in

`release.yml` moves one ref per release, named `v${VERSION%%.*}` in shell. For `0.2.0` that is `v0` — so
allowing the release would force-move `v0` onto the very break the refusal exists to catch. Under 0.x the
compatibility boundary is the minor, so the moving ref has to be too.

**Decided: the moving ref tracks the minor line under 0.x, and no `v0` is ever published.**

| Release | Immutable | Moving |
| --- | --- | --- |
| `0.1.0` | `v0.1.0` | `v0.1` → `0.1.0` |
| `0.1.1` | `v0.1.1` | `v0.1` → `0.1.1` |
| `0.2.0` | `v0.2.0` | `v0.2` → `0.2.0`, and `v0.1` is left where it is |
| `1.0.0` | `v1.0.0` | `v1` → `1.0.0` |

This keeps one story rather than two: **pin the moving ref for your line and you get fixes and features,
never a break.** Under `1.x`+ the line is the major; under `0.x` it is the minor. That is SemVer's own
compatibility rule applied consistently, not a special case.

Rejected: moving `v0` anyway — coherent, since `v0` promises nothing, but it leaves a 0.x consumer with no
ref that receives fixes without breaks, which is the promise the rest of this repository's pinning story
rests on. Rejected: moving nothing under 0.x — least code, but a 0.x consumer could then only pin exact
versions, and `release.yml` would grow a branch that skips its tag move.

Two conveniences already hold and need no change: `.cliff.toml`'s `tag_pattern` requires three components,
so `v0.1` cannot become a range's lower bound, and `test_tag_pattern_excludes_the_moving_major_tags`
already asserts `v2.0` does not match. The `immutable release tags` ruleset covers `refs/tags/v*.*.*`,
which needs two literal dots — `v0.1` falls outside it and stays movable, `v0.1.0` inside it and stays
immutable.

## Cross-Repository Impact *(constitution gate)*

**Affected consumers.** From [`docs/consumers.md`](../../docs/consumers.md), `release.yml` has two call
sites: `ci.yml` here, and `github-actions-test` at `@v4`. Both are `1.x`+ or above — this repository is
`4.1.x` and `github-actions-test` is `2.0.0` — so **neither takes the 0.x branch at all**.
`actions/release-decisions` has no external caller and is not meant to gain one.

**Interface delta.** No `workflow_call` input, output, permission or job name changes on any workflow.
Inside `actions/release-decisions`, the `highest-major` input and output are replaced by
`highest-version` carrying the full `N.N.N`, and a `moving-tag` output is added — the refusal needs the
whole version to compare minors, and the tag name becomes a decision in the module rather than a shell
expansion. Both are internal: that action's only callers are the two release workflows.

**Compatibility.** Every existing call site keeps working untouched and **no major bump is owed**. No
release from `1.0.0` upward changes behaviour in any way: the refusal, the increment and the moving tag
are all identical above `0.x`, which is what SC-001 asserts. What changes is a path no current caller can
reach.

**Rollout and rollback.** Nothing to roll out — no consumer has to do anything, and none can observe the
change. Rollback is a revert. The 0.x path is inert until a repository at `0.x` calls `release.yml`.

**Verification needs `github-actions-test` reset to an unreleased state.** `is_ahead` compares across every
major, so at `2.0.0` that repository can never publish a 0.x version again — and it is the only external
caller. The pure functions are fully testable offline, but creating and force-moving a `v0.1` ref is API
behaviour no offline test reaches, and it is the half most likely to fail at runtime.

It has **no tag ruleset**, only a branch one, so its tags are freely deletable: the reset is to delete every
release, archive each `vX.Y.Z` as `obsolete-X.Y.Z`, drop the moving tags, and set `[project].version` back
to a 0.x number. That repository exists to be broken, and nothing resolves it.

The archive name may not contain a `vN.N.N` substring. `v1.0.0-obsolete` would still be matched by
`.cliff.toml`'s `tag_pattern`, which is applied unanchored, so it would become a range's lower bound and the
notes would render nearly nothing — while `highest_version`'s anchored pattern would ignore it, so the
release would be allowed. `obsolete-1.0.0` cannot match either pattern under any anchoring.

## User Scenarios & Testing *(mandatory)*

The actor is a **maintainer of a 0.x repository** that cuts its releases with `release.yml`. No such
repository exists yet, which is why this is a latent defect rather than an outage.

### User Story 1 - Ship a breaking change under 0.x (Priority: P1)

A maintainer at `0.1.0` lands a commit marked `!`, decides the project is not ready to promise stability,
and bumps to `0.2.0` — the increment SemVer reserves for exactly this. Today the release is refused, and
the message tells them the version is "not a new major", which is true and unhelpful: the only advice it
implies is to jump to `1.0.0`.

**Why this priority**: it is the defect. Everything else here exists to make this correct rather than
merely permitted.

**Independent Test**: with `0.1.0` released, a breaking range and a declared `0.2.0`, the release
proceeds; with `0.1.1` declared it is still refused.

**Acceptance Scenarios**:

1. **Given** `0.1.0` is the highest release and the range carries a breaking change, **When** `0.2.0` is
   released, **Then** it proceeds.
2. **Given** the same, **When** `0.1.1` is released, **Then** it is refused — a patch may not carry a break.
3. **Given** the same, **When** `1.0.0` is released, **Then** it proceeds, as it does today.
4. **Given** `0.2.0` is the highest release and the range carries a breaking change, **When** `0.2.1` is
   released, **Then** it is refused — the line being moved is `0.2`, not the major.

---

### User Story 2 - Be proposed the increment that keeps you in 0.x (Priority: P1)

The same maintainer merges the breaking change and reads the proposal. It should offer `0.2.0`. Today it
offers `1.0.0`, which decides on their behalf that the project is now stable.

**Why this priority**: P1 alongside Story 1, because without it Story 1's allowance is unreachable by the
automated path — the proposal would never produce a version the new refusal treats differently.

**Independent Test**: from `0.1.0` with a breaking range, the proposed version is `0.2.0`.

**Acceptance Scenarios**:

1. **Given** `0.1.0` and a breaking range, **When** the increment is proposed, **Then** it is `0.2.0`.
2. **Given** `0.1.0` and a range with a `feat` and no break, **When** the increment is proposed, **Then**
   it is `0.1.1` — a feature may not touch the minor under 0.x, because a consumer pinned to `v0.1` has to
   be able to receive it without crossing into `v0.2`.
3. **Given** `1.0.0` and any range, **When** the increment is proposed, **Then** it is exactly what is
   proposed today.
4. **Given** a 0.x range carrying both a `feat` and a break, **When** the increment is proposed, **Then**
   the break wins, as it does above 0.x.

---

### User Story 3 - Pin a 0.x line and receive fixes without breaks (Priority: P2)

A consumer of a 0.x repository wants the same deal every consumer of this repository gets: pin one ref,
receive fixes and features, never receive a break. Under 0.x that ref is `v0.1`.

**Why this priority**: it follows the two P1s because it is the *consequence* of the decision above rather
than a defect of its own — but without it the fix would allow `0.2.0` and then move `v0` onto it, which is
worse than refusing.

**Independent Test**: releasing `0.1.1` moves `v0.1`; releasing `0.2.0` creates `v0.2` and leaves `v0.1`
alone; no `v0` is ever created.

**Acceptance Scenarios**:

1. **Given** a release of `0.1.1`, **When** the moving ref is published, **Then** it is `v0.1` and no `v0`
   exists.
2. **Given** a release of `0.2.0` while `v0.1` exists, **When** the moving ref is published, **Then**
   `v0.2` is created and `v0.1` still resolves to `0.1.1`.
3. **Given** a release of `1.0.0`, **When** the moving ref is published, **Then** it is `v1`, exactly as
   today.
4. **Given** any release, **When** the moving tag's name is decided, **Then** it is decided in the module
   beside the other release decisions and not by a shell expansion.

---

### Edge Cases

- **`0.0.z`.** The line is `0.0`, so `0.0.1 → 0.0.2` with a break is refused and `0.0.1 → 0.1.0` is
  allowed. Falls out of the rule with no special case.
- **Crossing out of 0.x.** From `0.9.0` to `1.0.0` the line changes from `0.9` to `1`, so it is allowed
  whatever the range carries — correct, and the same reason a new major is always allowed.
- **Nothing released yet.** No ref exists to move onto a break, so nothing is refused. Unchanged.
- **A 0.x release when the highest release is `1.x`+.** Cannot arise: the version must be ahead of the
  highest across every major.
- **A feature and a fix propose the same version under 0.x.** Both advance the patch, so within a 0.x line
  the two are indistinguishable by increment. The reason reported to the maintainer still distinguishes
  them.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The breaking-change refusal MUST fire when, and only when, the moving ref this release would
  publish already exists and points at a different contract — that is, when the release's compatibility
  line equals the highest existing release's.
- **FR-002**: The compatibility line MUST be the major from `1.0.0` upward and the major and minor below
  it, so that `0.2.0` may carry a break over `0.1.0` while `0.1.1` may not.
- **FR-003**: The proposed increment MUST start a new line for a breaking range — the next minor under 0.x,
  the next major above it — and MUST otherwise advance within the current line.
- **FR-004**: A feature MUST NOT advance the minor under 0.x, so that a consumer pinned to a 0.x line
  receives features without crossing into the next line.
- **FR-005**: A release MUST publish a moving ref naming its compatibility line: `v0.1` under 0.x, `v1`
  above it. No `v0` may be published.
- **FR-006**: The moving ref's name MUST be decided in `actions/release-decisions` alongside the other
  release decisions, not composed by a shell expansion in a workflow.
- **FR-007**: No behaviour at or above `1.0.0` may change — same refusals, same increments, same moving
  ref, asserted rather than assumed.
- **FR-008**: No `workflow_call` input, output, permission or job name may change on any workflow.
- **FR-009**: The version-tag pattern that bounds a release range MUST continue to exclude every moving
  ref shape, `v0.1` included, so a moving ref can never become a range's lower bound.
- **FR-010**: `README.md`'s Versioning section MUST document what a 0.x consumer pins and why it differs,
  without naming a concrete major outside the one sentence that owns that value. `CONTRIBUTING.md`'s
  Releasing section MUST describe the 0.x increment.
- **FR-011**: Every decision MUST be testable offline, with `mise run ci` needing no network.

### Key Entities

- **Compatibility line**: the set of versions a single moving ref may span. `(major)` from `1.0.0` up,
  `(major, minor)` below. Every requirement here is a statement about this one idea, which is why the
  0.x/1.x split needs no branch outside its definition.
- **Moving ref**: the tag a consumer pins, named for the line. Force-moved on each release within the line,
  created on the first release of a new one, and left where it is once the line is superseded.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every refusal, increment and moving-ref name at or above `1.0.0` is unchanged, asserted
  offline against the values produced today.
- **SC-002**: All four rows of the 0.x refusal table hold, including the `0.2.1`-over-`0.2.0` case that is
  not in the issue.
- **SC-003**: A breaking 0.x range is proposed as the next minor, and a 0.x feature as the next patch.
- **SC-004**: A 0.x release publishes `v0.<minor>` and never `v0`.
- **SC-005**: No workflow spells a moving tag; the name comes from the module, asserted by test.
- **SC-006**: A 0.x maintainer can read `README.md` and know which ref to pin without reading any module.
- **SC-007**: The 0.x tag-publishing path is exercised by a real release, not only offline — see
  Assumptions for how, given no existing consumer can reach it.

## Assumptions

- **Under 0.x the minor is the compatibility boundary.** SemVer §4 says only that `0.y.z` is unstable; the
  convention that the minor signals a break is de facto rather than spelled in the spec, and it is what
  #107 asserts and what Cargo implements. Adopted deliberately.
- **A 0.x feature advances the patch.** This follows from the moving ref rather than from the spec: if a
  feature advanced the minor, a consumer pinned to `v0.1` could not receive it, and the analogy with `v4`
  carrying minors would break. It is the one place this specification chooses consistency with our own
  pinning story over the letter of common practice.
- **`actions/release-decisions` may change its inputs and outputs freely.** `docs/consumers.md` records
  that it has no external caller and is not meant to gain one, so replacing `highest-major` with
  `highest-version` costs nobody a change.
- **`github-actions-test` is reset to an unreleased 0.x state for the verification.** It is the only
  external caller, and at `2.0.0` it can never publish 0.x again. It has no tag ruleset, so the reset is
  cheap; it exists to be broken and nothing resolves it, so losing its release history costs nothing that
  is not archived. The alternative — a new throwaway repository — was rejected as more setup for the same
  evidence, and shipping the tag-move half on offline evidence alone is what principle VI forbids.
- **Its archived tags are named `obsolete-X.Y.Z`**, with no `v`, so they match neither `.cliff.toml`'s
  unanchored `tag_pattern` nor `highest_version`'s anchored one. A `-obsolete` *suffix* would satisfy the
  second and fail the first.
- **No consumer is at 0.x today**, so nothing is blocked and the rollout is empty. This is a latent defect
  being fixed before it costs someone a confusing refusal, not an incident.

## Out of Scope

- **Any change to behaviour at or above `1.0.0`.** FR-007 makes that a requirement rather than an
  expectation.
- **Graduating this repository or any consumer to a different versioning scheme.** `README.md`'s Versioning
  section keeps naming `v4` as the current major; nothing here touches which major is current.
- **A guard on the `immutable release tags` ruleset.** `v0.1` falls outside `refs/tags/v*.*.*` and stays
  movable, which is what this change needs. That the ruleset could be edited to cover the moving refs and
  silently break every release is a real gap, and a pre-existing one — it belongs to its own issue rather
  than riding along here.
- **What a 0.x consumer's own required status checks should be**, or any other consumer-side policy.
