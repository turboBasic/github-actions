# Research: The 0.x Compatibility Line

Phase 0. The decisions, with what was rejected.

## D1

**Which ref a 0.x release moves: `v<major>.<minor>`, and no `v0` is ever published.**

**Decision**: the moving ref names the compatibility line — `v0.1` under 0.x, `v1` from `1.0.0` up.

**Rationale**: the refusal exists because force-moving a ref onto a broken contract silently breaks whoever
pinned it. Allowing `0.2.0` while still moving `v0` would not fix that, it would trigger it. Under 0.x the
compatibility boundary is the minor, so the ref has to be too.

The result is one story rather than two: **pin the moving ref for your line, receive fixes and features,
never receive a break.** Above 0.x the line is the major; below it, the minor. Nothing about the promise
changes, only which component names it.

Two conveniences already hold and needed no work, both verified rather than assumed:

- `.cliff.toml`'s `tag_pattern` is `v[0-9]+\.[0-9]+\.[0-9]+` — three components, so a two-component moving
  ref cannot become a release range's lower bound. `test_tag_pattern_excludes_the_moving_major_tags`
  already asserts `v2.0` does not match; it is extended to `v0.1` rather than rewritten.
- The `immutable release tags` ruleset covers `refs/tags/v*.*.*` with no bypass actors. That pattern needs
  two literal dots, so `v0.1` falls outside it and stays force-movable while `v0.1.0` falls inside and
  stays immutable. Exactly the split this needs, with no ruleset edit.

**Alternatives considered**:

- *Move `v0` anyway.* Zero change to `release.yml`, and coherent on its own terms: SemVer §4 says `0.y.z`
  carries no stability guarantee, so `v0` promises nothing and moving it across a break violates no
  contract — which is itself an argument that the refusal should not fire. Rejected because it leaves a 0.x
  consumer with **no** ref that receives fixes without breaks, and that promise is the entire justification
  for this repository asking consumers to pin a moving tag rather than a SHA.
- *Move nothing under 0.x.* Least code in the module, and defensible — a version with no stability
  guarantee arguably has no meaningful moving ref. Rejected on two counts: a 0.x consumer could then only
  pin exact versions, and `release.yml` would grow a branch that skips its tag move, which costs more than
  the naming change and takes the "the moving tag moves last, so a failure leaves consumers on the previous
  release" story's subject away.

## D2

**`next_version` is in scope, though the issue does not mention it.**

**Decision**: a breaking range starts a new line — the next minor under 0.x, the next major above it.

**Rationale**: verified by running the current code, `next_version((0, 1, 0), breaking=True)` returns
`(1, 0, 0)`. So `release-proposal.yml` proposes graduating to stable on any 0.x break, deciding on the
maintainer's behalf that the project is now stable.

Fixing only the refusal would make its own allowance unreachable: every 0.x break would arrive as a
`1.0.0` proposal, which the new refusal allows, so `0.2.0` would only ever be reached by a human editing
the proposal branch. The two halves have to agree on what 0.x means or neither is right.

Proposing the smaller claim is also the better default independently — a reviewer can raise `0.2.0` to
`1.0.0` on the proposal branch, and every later refresh leaves a human-decided number alone. Proposing
`1.0.0` cannot be walked back the same way, because it is already the larger claim.

**Alternatives considered**: keeping strictly to the issue's stated scope and filing the proposal half
separately. Rejected: it ships a fix whose effect is unreachable through the automated path, and the
follow-up issue would have to be opened in the same breath.

## D3

**A 0.x `feat` advances the patch, not the minor — and so a `feat` and a `fix` propose the same version.**

**Decision**: under 0.x only a breaking range advances the minor. A feature advances the patch, as a fix
does.

**Rationale**: this follows from D1 rather than from SemVer. If a 0.x feature advanced the minor, it would
start a new line, and a consumer pinned to `v0.1` could not receive it — while a consumer pinned to `v4`
receives every minor. Keeping features inside the line is what makes the two cases the same promise.

The consequence is recorded rather than hidden: **within a 0.x line a feature and a fix are
indistinguishable by version**, because the line consumes two components and only the patch is left to
advance. `increment_reason` still tells the maintainer which it was, so the notice they read distinguishes
what the number cannot.

This is the one place the specification chooses consistency with our own pinning story over the letter of
common practice, where a 0.x feature often does bump the minor. Stated in the spec's Assumptions.

**Alternatives considered**: a 0.x feature advancing the minor, matching the looser common convention.
Rejected because it makes `v0.1` a ref that receives nothing but fixes, which is not the deal `v4` offers
and would leave the pinning story with two different meanings.

## D4

**One function owns the 0.x split.**

**Decision**: `compatibility_line(version)` returns `(major,)` or `(major, minor)`, and the refusal, the
increment and the tag name all read it. No other function tests `major == 0`.

**Rationale**: the alternative is the same rule spelled three times, in three functions that must agree
forever. A test asserts the split appears once, so a fourth reader cannot reintroduce it by hand.

It also makes the refusal simpler than it was rather than more complicated. The rule stops being "is this a
new major" and becomes **"does the ref this release would move already exist"** — one comparison, with the
0.x difference entirely inside the line's definition. Every row of the spec's table, including the
`0.2.1`-over-`0.2.0` case the issue does not mention, falls out of it.

## D5

**`highest-version` is added, and `highest-major` is kept for exactly one release — because dropping it
would switch the refusal off for that release.**

**Decision**: add a `highest-version` input and output carrying the full `N.N.N`, add a `moving-tag` output,
and **keep `highest-major` declared and passed** until the release that ships this has moved `v4`. The new
module reads only `HIGHEST_VERSION`. A follow-up removes the old pair.

**Rationale**: the refusal needs the highest release's minor, so `highest-major` has no remaining correct
use and replacing it outright looked obviously right. It is not, and the reason is the `@v4` indirection
that [`004`'s quickstart rung 3](../004-declared-consumer-surface/quickstart.md) recorded.

`release.yml` calls the action as `uses: …/actions/release-decisions@v4`, while `ci.yml` calls
`release.yml` itself as `$/`. So between merging this and cutting the release there is one run with **new
`release.yml` and the old action**:

| | during the interim | after the release |
| --- | --- | --- |
| `release.yml` | new, from `$/` | new |
| `decisions.py` | **old**, from `@v4` | new |

A new `release.yml` that passed only `highest-version` would give the old action nothing it declares.
`HIGHEST_MAJOR` would be empty, so `breaks_under_non_major` would return `False` for any range, and the
breaking-surface refusal would be **silently off for that release** — the one thing principle VII rules
out. Passing both closes it: the old action reads `highest-major`, the new one reads `highest-version`,
and neither needs to know about the other.

Note the asymmetry with `004`, which had the same interim and accepted it: there the old and new code
rendered the identical filter, so the interim was merely stale. Here it would be a missing gate.

`github-actions-test` is unaffected either way — it resolves `release.yml` *and* the action at `@v4`, so it
never sees a mixed pair.

**Alternatives considered**:

- *Replace outright and accept the one-release window*, since the release's own range is knowable in advance
  and can be checked offline with `mise run release-notes` before cutting. Rejected: it trades a gate for
  three lines and leaves the check depending on somebody remembering to run it.
- *Keep `highest-major` permanently.* Rejected — two values describing one fact, one of which is wrong under
  0.x, is exactly the drift the single-definition rule exists to stop. It goes in a follow-up once the tag
  has moved, which is a task in [tasks.md](./tasks.md) rather than a hope.
