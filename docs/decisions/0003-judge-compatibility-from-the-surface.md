---
id: 0003
status: accepted
date: 2026-09-13
scope: release
---

# ADR 0003 — Compatibility is judged from the published surface

## Decision

Whether a change breaks a consumer is read from the published surface and its fixture in
`tests/published_surface.toml`. The consumer set is indefinite and is not recorded, so which repositories
are known to call what is not an input to the judgement.

## Context

A published ref may be resolved by anyone who can read this repository, and that set cannot be
enumerated. A count of known callers is therefore not an argument about the interface: an input, a check
name, a required permission and a call site are promises to whoever holds the ref, not to a list.

## Consequences

A renamed check, a moved call site, a renamed input or a newly demanded permission is a break whatever
the caller count, and starts a new compatibility line.

The fixture is the surface's one declaration, so a change to the surface that leaves it untouched is the
change the gate exists to catch.

## Links

No issue — ruled in conversation. Supplies the constraint
[ADR 0002](0002-start-the-line-at-0-1-0.md) turns on.
