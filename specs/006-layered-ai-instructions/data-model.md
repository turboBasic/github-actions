# Phase 1 Data Model: Layered AI Instructions

There is no runtime data here. The model is the layer assignment: which artefact sits where, what
it owns, and what it may name. Everything the check reads is derived from this table or declared
alongside it.

## Layers

Ordered from most abstract and most stable to most concrete and most volatile. "May name" is the
reference direction; anything not listed is forbidden.

| # | Layer | Artefact | Owns | May name | Loaded |
| --- | --- | --- | --- | --- | --- |
| 0 | User defaults | `~/.claude/CLAUDE.md` | cross-project habits of this developer | nothing in this repository | always, outside this repository's control |
| 1 | Invariants | `.specify/memory/constitution.md` | what may never be true here, as gates a spec fails against | domain vocabulary only | always, by import from layer 4 |
| 2 | Conventions | `docs/ai-instructions.md` | how to work here: naming, placement, style, process, and which layer 0 rules this repository overrides | layer 1 by principle name or number | always, by import from layer 4 |
| 3 | Mechanics | `README.md`, `CONTRIBUTING.md`, `docs/technical-debt.md`, `docs/instruction-layers.md`, `tests/`, the tool configs | values, procedures, enforcement, and the reasoning behind a specific gate | layers 1 and 2 by section, and each other | on demand, when a reader follows a pointer |
| 4 | Navigation | `CLAUDE.md`, `.github/copilot-instructions.md` | which artefact answers which kind of question | every artefact, by path | always |

Two properties of that table carry the whole design.

**Navigation is not a rule layer.** Layer 4 names every file and states no rule. Separating
navigation from rules is what makes the one-way direction achievable at all: without it, an
abstract layer has to name a concrete file to say where a fact lives, which is the violation. The
software analogue is a composition root — it knows every module, and no module knows it.

**A concrete layer announces itself; an abstract layer does not delegate downward.** Layer 2 does
not say "the label set lives in `CONTRIBUTING.md`". It states the rule — a label set is declared
once, as a table, and the check reads that table — and `CONTRIBUTING.md` says "this is that table".
Inverting the delegation is what survives a file being renamed.

## Entities

### Layer

- **Position**: an integer, 0 to 4, fixed by the table above.
- **Artefacts**: the paths belonging to it. A path belongs to exactly one layer.
- **May name**: the set of layers it may reference. Empty for layer 1 except domain vocabulary.
- **Stability**: what kind of change to it is expected. Layer 1 changes by amendment and a
  recorded decision; layer 2 changes by request; layer 3 changes with the code.

### Rule

- **Statement**: the imperative sentence a reader acts on.
- **Owning layer**: exactly one.
- **Enforcement**: whether a gate holds it. Recorded as a fact ("enforced by test"), never as the
  gate's name.
- A rule may **span** layers where the prohibition and the mechanics genuinely differ — layer 1
  states that a breaking change needs a new major tag, layer 2 enumerates which changes break a
  caller, layer 3 holds the frozen table. Each states only its own part.

### Citation

- **From** an artefact, **to** a section of another.
- Legal only when the target's layer number is lower than the source's, or when the source is
  layer 4.
- A citation carries no copy of what it points at. "See X" is a citation; "X says Y" is a
  restatement wearing a citation's clothes.

### Owned fact

The unit the check freezes. One row per fact that has more than one plausible home.

- **Fact**: what is owned, in a few words.
- **Owner**: the single artefact allowed to state it.
- **Forbidden pattern**: what may not appear anywhere else, as a literal or a regular expression.
- **Reason**: why a second copy is a defect rather than a convenience.

Existing rows, inherited from what the suite already asserts: the current major version, owned by
`README.md`; the label set, owned by `CONTRIBUTING.md`. New rows come from the duplication found in
Phase 0. `contracts/owned-facts.md` is the table.

### Mechanism identifier

A name belonging to layer 3's internals. Forbidden above it, and derivable rather than listed:

- test function names, parsed from `tests/*.py`
- module-level constant names in the test package
- `[tools]` and `[tasks]` keys from `mise.toml`
- upstream issue references matching `owner/repo#N`
- REST paths and HTTP status codes

Distinguished from **domain vocabulary** — `permissions`, `workflow_call`, `pull_request_target`,
`env` — which is the language the subject is written in and is legal at every layer. The line is
ownership: this repository chose its linters and named its tests, so those are internals; GitHub
chose `pull_request_target`, so that is vocabulary.

### Exemption

- **Path**: a file or glob the structural checks skip.
- **Reason**: why, in one line.
- Declared, never inferred. Current members: vendored Spec Kit machinery and its skills, which are
  rewritten wholesale on refresh, and completed directories under `specs/`, which are frozen work
  logs that legitimately restate rules as of their date.

## Validation rules

Derived from the table, and each one is a check in `tests/test_instruction_layers.py`:

1. Every artefact under the instruction set belongs to exactly one layer, and no path is
   unassigned.
2. No artefact names an artefact from a higher-numbered layer, unless it is layer 4.
3. No artefact above layer 3 contains a mechanism identifier.
4. For every owned fact, its forbidden pattern appears only in its owner.
5. No cycle exists in the citation graph.
6. Layer 1 and layer 2 are reachable from layer 4 by import, so their rules are in context.
7. Exempt paths are skipped, and every exemption carries a reason.
