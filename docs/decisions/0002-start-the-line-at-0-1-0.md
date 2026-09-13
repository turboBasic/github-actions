---
id: 0002
status: accepted
date: 2026-09-13
scope: release
---

# ADR 0002 — The line starts at `0.1.0`, and `1.0.0` waits for consumers

## Decision

The first release is `0.1.0` and consumers pin `@v0.1`. `1.0.0` is published once consumers have
exercised the surface, not once the tree feels finished.

Below `1.0.0` a break is signalled by the minor, so the moving ref spans a patch range only — `v0.1`,
`v0.2` — and `v0` is never published.

## Context

`1.0.0` promises that a break arrives only in a major, and that promise cannot be withdrawn once a
consumer has resolved it. `0.x` says accurately that the surface may still move.

## Consequences

A consumer repins on a minor bump, so the README's versioning table is the live rule rather than a
transitional one.

From `0.1.0` on, no published release tag is deleted or moved. The `immutable-release-tags` ruleset in
`.github/rulesets/` is where that is held, and this ruling is why it may not be dropped.

## Links

No issue — ruled in conversation. Sits beside [ADR 0001](0001-this-repository-is-the-library.md) and
[ADR 0003](0003-judge-compatibility-from-the-surface.md), which rules how a break is recognised.
