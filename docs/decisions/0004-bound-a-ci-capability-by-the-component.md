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

`python-ci` shipped in `0.1.0`. Writing the second one showed what a third would have cost: stripped of
comments, `go-ci` differed from it in six hunks, and only two of them named anything Go — the module
integrity step and the pre-flight tool list. The rest was a stage renamed. Every stack after that would
have re-authored the same checkout, the same task-runner install, the same cache and the same stage
switches to reach a `run:` line the consumer already owned.

What constrains the answer is that consumers describe how their code is checked in `mise.toml` already.
A capability naming a language therefore does not add a policy — it forks one, and the copy in this
repository is the one nobody consuming it can edit. A polyglot component made that visible: it has no
language to select, and composing its checks per language would split a single verdict for a reason its
maintainer does not have.

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
anything on a task's behalf — `tests/test_workflow_properties.py` holds the second half by asserting
`project-ci` runs its stages and nothing else. Dependency integrity is a `depends` of the task that
cannot judge without it, in the consumer's own configuration.

Every future request for a stack-specific workflow is answered with a task name and this record. What
this repository can still ship for a language is a capability judging something no task can — a surface,
a dependency graph, a published artifact — and that is not this shape.

Reopened if a stack cannot express a stage as a task at all, or if a component's verdict genuinely needs
a step that must run before any task and cannot be a task's dependency.

## Links

[Issue #61](https://github.com/turboBasic/github-actions/issues/61) holds the evidence; #60 is the
`go-ci` it supersedes. Sits beside [ADR 0003](0003-judge-compatibility-from-the-surface.md), which rules
how the retirement of `python-ci` is judged as a break.
