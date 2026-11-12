---
id: 0005
status: accepted
date: 2026-11-12
scope: identity
---

# ADR 0005 — Cache component dependencies in the component capability

## Decision

`project-ci` restores and saves caches for supported package ecosystems detected in the checked-out
repository. Cache preparation may name those ecosystems, but it does not install, lock, or verify
dependencies on behalf of a task. The capability remains one check for one component.

## Context

Consumers cannot add steps inside the reusable job, so dependency and compiled-output caches cannot be
placed around the component's own tasks from the caller. [Issue #114](https://github.com/turboBasic/github-actions/issues/114)
records a Go race step dropping from 25s to 2s on a warm cache and PopCircles repeatedly recompiling
Cargo output in about 40s. ADR 0004's ban on language-specific inputs and steps prevented `project-ci`
from restoring those caches.

The one-component boundary still holds: the caller's tasks remain responsible for dependency
resolution and verification, and no extra required check is added.

## Options

### Detect and cache supported ecosystems in `project-ci` (SELECTED)

- Adopted because: consumers gain reusable caches inside the job they already call.
- Adopted because: repository manifests determine which caches apply, including in polyglot components.
- Adopted despite: cache paths and ecosystem rules become a published workflow surface.
- Adopted despite: cache storage and key maintenance add cost to the shared workflow.

### Leave caching to consumer tasks

- Rejected because: consumers cannot insert a cache step into the called job.
- Rejected despite: this keeps `project-ci` unaware of ecosystem-specific locations.

### Add a separate capability per language

- Rejected because: a component with multiple languages would need multiple verdicts or duplicated jobs.
- Rejected despite: each capability could prepare a single-language component's dependencies.

## Consequences

`project-ci` may name supported ecosystems in its cache steps and inputs. It must preserve one component,
one check name, and task-owned dependency resolution. Tests pin cache selection, keys, secret-free paths,
and the unchanged check contract. Reopen this decision if callers cannot express their cache needs through
the supported cache locations and overrides.

## Links

[Issue #114](https://github.com/turboBasic/github-actions/issues/114) holds the requirements and evidence.
This supersedes [ADR 0004](0004-bound-a-ci-capability-by-the-component.md).
