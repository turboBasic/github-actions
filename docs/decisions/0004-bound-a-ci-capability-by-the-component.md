---
id: 0004
status: accepted
date: 2026-09-15
scope: identity
---

# ADR 0004 — Bound a CI capability by the component, not by the language

## Decision

One capability judges one component, whatever it is written in. It knows no language: it checks the tree
out, installs what the caller's `mise.toml` pins, and invokes a fixed set of task names the caller
implements. A language, a framework or a runtime never appears in a capability's name, its inputs or its
steps, and never earns a capability of its own. A repository splits its calls where a component deserves
an independent verdict, not where it changes language.

## Context

`python-ci` at `@v0.2` runs eight steps, of which two name Python: a `uv` pre-flight and a lockfile
install. The other six say nothing about any language, and a capability for a second stack re-authors all
six to reach a `run:` line the consumer already owns.

What constrains the answer is that consumers describe how their code is checked in `mise.toml` already.
A capability naming a language therefore does not add a policy, it forks one, and the copy here is the
one nobody consuming it can edit. A polyglot component has no language for such a capability to select at
all.

## Options

### One capability, a fixed task interface (SELECTED)

- Adopted because: the language lives only where the consumer's own local run already put it.
- Adopted because: a polyglot component and a single-language one call the same thing.
- Adopted because: adding a stack becomes a consumer's commit, not a release of this library.
- Adopted despite: retiring `python-ci` is a break, so every consumer edits a required context by hand.
- Adopted despite: a component with no `build` target has to say so at the call site.

### One capability per language

- Rejected because: it duplicates every non-language step per stack, and the copies drift silently.
- Rejected because: it makes this repository the owner of a policy the consumer is better placed to hold.
- Rejected because: a polyglot component has to be split by language to be checked at all.
- Rejected despite: it can pre-flight and prepare a language's dependencies without being asked.

### One capability with a `language:` selector

- Rejected because: the duplication moves inside the file and the release cadence stays this library's.
- Rejected because: a selector value is a name for something the caller's task already names.
- Rejected despite: it retires no published contract and so breaks nothing.

### `project-ci` beside a retained `python-ci`

- Rejected because: two live answers to how a Python repository is checked, which principle I forbids.
- Rejected because: the migration never finishes while the old path still works.
- Rejected despite: it defers the ruleset edit every consumer now has to make.

## Consequences

A capability may not name a language, a framework or a runtime, and may not install, lock or verify
anything on a task's behalf; `tests/test_workflow_properties.py` holds the second half. Dependency
integrity becomes a `depends` of the task that cannot judge without it, in the consumer's configuration.

Every future request for a stack-specific workflow is answered with a task name and this record. What
this repository can still ship for a language is a capability judging something no task can — a surface,
a dependency graph, a published artifact.

Reopened if a stack cannot express a stage as a task, or if a verdict needs a step that must precede
every task and cannot be a task's dependency.

## Links

[Issue #61](https://github.com/turboBasic/github-actions/issues/61) holds the evidence. Sits beside
[ADR 0003](0003-judge-compatibility-from-the-surface.md), which rules how retiring `python-ci` is judged
as a break.
