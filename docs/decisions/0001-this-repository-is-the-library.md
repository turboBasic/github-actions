---
id: 0001
status: accepted
date: 2026-09-13
scope: identity
---

# ADR 0001 — This repository is the library

## Decision

`turboBasic/github-actions` is the one repository the library ships from. There is no second name for
it, and no ref resolves under it that this tree did not publish.

## Context

One library, one name. Two names for one library leaves consumers with two answers to which ref to pin,
and nothing in either tree saying which is current.

## Consequences

A consumer reaches every capability at `turboBasic/github-actions`, and the lowest ref it resolves is
`0.1.0`.

Anything of this repository's own is reached with `$/` rather than by naming the repository, so nothing
here has to be edited if the name ever moves again.

Reopened only if the library is split: the part that leaves takes a new repository and its own line.

## Links

No issue — ruled in conversation. Sits beside [ADR 0002](0002-start-the-line-at-0-1-0.md), which rules
the number this line starts on.
