# Quickstart: Validating Layered AI Instructions

Everything here is offline. No task in this feature needs the network.

## Prerequisites

```sh
mise run setup
```

## The loop

```sh
mise run ci                      # lint, schema validation, typecheck, test
uv run pytest tests/test_instruction_layers.py -v
```

## Proving each outcome

### SC-001, SC-010 — every rule survives, in one place

The inventory is the evidence, and it is a task artefact rather than a shipped document. Build it
before editing anything: one row per rule currently in force, with the file and line it is stated
in. After the edits, rebuild it and reconcile. A rule present before and absent after, with no row
saying it was deliberately dropped, fails the feature.

```sh
uv run pytest tests/test_instruction_layers.py -k owned_fact -v
```

Sixteen rows, two assertions each — the anchor is present in its owner and absent everywhere else.

### SC-002 — no reference runs the wrong way

```sh
uv run pytest tests/test_instruction_layers.py -k direction -v
```

Passes only when the constitution names no artefact and the conventions name no layer-3 file. To
see it fail as intended, add a link to `docs/ai-instructions.md` in the constitution and rerun.

### SC-003, SC-004 — mechanism names stay in layer 3

```sh
uv run pytest tests/test_instruction_layers.py -k mechanism -v
```

Then prove the rename immunity, which is the point of the rule:

```sh
git grep -n 'test_no_mise_tool_version_floats' -- '*.md'    # expect no hits
git grep -n 'test_the_actionlint_ignore_is_still_needed' -- '*.md'
```

Both currently hit `docs/ai-instructions.md`. After the change, both are silent, and renaming
either test touches no prose.

### SC-005 — a rule change is a one-file diff

Three edits, three one-file diffs. Suggested set, one per layer:

| Rule | Expected diff |
| --- | --- |
| tighten a naming convention | `docs/ai-instructions.md` only |
| add a label to the set | `CONTRIBUTING.md` only, then `gh label create` |
| reword a principle's rationale | `.specify/memory/constitution.md` only |

```sh
git diff --name-only            # exactly one path each time
```

### SC-006 — each violation kind fails the standard run

Three deliberate breakages, one at a time, each reverted after:

1. Copy a principle's sentence into `docs/ai-instructions.md`.
2. Add a markdown link from the constitution to any layer-3 file.
3. Write a test function's name into `docs/ai-instructions.md`.

```sh
mise run ci                      # must fail, and name the file and the violation
git checkout -- .
```

A breakage that passes is a check that does not exist.

### SC-007 — the always-loaded set does not grow

```sh
wc -l CLAUDE.md docs/ai-instructions.md .specify/memory/constitution.md
```

Before: 1 + 292 + 0 loaded = 293 lines in context, with the constitution absent.
Target after: navigation plus roughly 190 lines of conventions plus 74 of invariants, so no more
than 293 with the invariants now present. Over that, something that was cut has crept back.

### SC-008 — one layer answers one question

Not scriptable. Take five rules at random — a naming rule, a permission rule, a Python rule, a
release rule, a spec rule — and for each, read only the layer the navigation file sends you to. If
you need a second file to be confident nothing contradicts what you read, the layer boundary is in
the wrong place.

### SC-009 — the pattern carries no local rules

The reusable write-up names layers and direction and nothing about workflows, actions, releases or
pinning.

```sh
grep -niE 'workflow|action|release|pin|major|consumer' <the pattern write-up>
```

Expect no hits outside an explicitly marked example.

## What cannot be validated here

Nothing in this feature is a workflow, so principle VI has no invocation to demand: there is no
reusable workflow to exercise from a real pull request and no consumer to exercise one at a pinned
ref. The equivalent obligation is SC-006 — a check nobody has watched fail is unverified — and it
is a task rather than a note.
