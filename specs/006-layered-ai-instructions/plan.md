# Implementation Plan: Layered AI Instructions

**Branch**: `006-layered-ai-instructions` | **Date**: 2026-09-07 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/006-layered-ai-instructions/spec.md`

## Summary

The conventions layer already forbids what it does. `docs/ai-instructions.md` says "State the rule,
not the incident that taught it. No war stories, no version archaeology, no reasoning left in prose
where a test can hold it" — and then names six test functions, an upstream issue number, a REST
endpoint with its status code, two internal test symbols, and restates six of the seven
constitutional principles with their rationales, in places word for word. This feature makes that
rule true and puts a gate behind it.

Four layers, one direction, one owner per fact. Invariants name nothing; conventions cite invariants
by principle; mechanics cite both; a navigation layer names every file and states no rule.
Separating navigation from rules is what makes the direction achievable — without it an abstract
layer has to name a concrete file to say where a fact lives, which is the violation.

The root cause of the duplication is mechanical, not editorial: **nothing imports the constitution**,
so restating it was the only way to get it into context. Imports are eager, so importing it fixes
that at a known cost. Removing the restatements and adding the import are one change, not two.

Shape chosen: fix ownership and direction in the files that exist. No new instruction file, one new
test module, and one shipped document describing the pattern. Three richer shapes — topic modules,
on-demand skills, path-scoped rules under `.claude/rules/` — were weighed and rejected in
[research.md](research.md); each fragments the canonical text into something only Claude Code can
read, leaving the second documented tool with no way to reach it. That tool keeps working here only
because its pointer is widened to name both rule layers — a link it can carry, unlike an import.

## Technical Context

**Language/Version**: Python 3.14 for the check; Markdown is the subject matter.

**Primary Dependencies**: pytest. The check is standard library only — `ast`, `re`, `tomllib`,
`pathlib`. No new dependency, so `uv.lock` does not move.

**Storage**: N/A.

**Testing**: pytest, offline, in `tests/test_instruction_layers.py`. Runs under `mise run test` and
therefore `mise run ci`. Carries no `drift` marker: every fact it reads is in the tree.

**Target Platform**: the repository tree. The instruction consumers are Claude Code, which loads
memory files eagerly and concatenates them with no override mechanism, and GitHub Copilot, which
reads one file and has no verified include mechanism.

**Project Type**: documentation architecture plus a structural test. No application code.

**Performance Goals**: the check parses five Markdown files and four Python files, so it adds
milliseconds. The real budget is context: the always-loaded instruction text must not exceed today's
293 lines while now carrying the invariants too.

**Constraints**: offline; standard library only; no vendored file edited; the canonical text of each
layer stays a single file so a pointer-only tool can reach it; `.specify/memory/constitution.md`
is ours to edit while everything around it is not.

**Scale/Scope**: five instruction artefacts across four layers, sixteen owned facts, roughly 100
lines of restatement and archaeology relocated out of a 292-line file.

## Constitution Check

*GATE: passed before Phase 0, re-checked after Phase 1.*

| Principle | Bearing | Verdict |
| --- | --- | --- |
| I Consumer Contract Stability | Nothing under `.github/workflows/` or `actions/` changes. No input, output, secret, permission or job name moves. | Pass, not engaged |
| II Supply-Chain Pinning | No `uses:` line changes. The rule's *statement* moves layers; its content does not weaken. | Pass |
| III Least Privilege | No workflow permissions change. | Pass, not engaged |
| IV Untrusted Input Is Data | No `run:` block changes. | Pass, not engaged |
| V Secrets Never Persist | Nothing written. | Pass, not engaged |
| VI Verification By Real Invocation | No workflow to invoke, so the principle has no call site here. Its analogue binds instead: a check nobody has watched fail is unverified, which is SC-006 and a task rather than a note. | Pass, by analogue |
| VII Gates Are Never Loosened | **The principle at risk.** Two ways this feature could erode it: deleting a sentence that was the only statement of a rule, and letting the new check's exemption list become a dial. | Pass, with the mitigations below |

**Principle VII, stated plainly.** Nothing here disables a rule, relaxes a tool mode, or silences a
finding. Two guards:

- Every deletion is accounted for by a before-and-after rule inventory that must reconcile. A rule
  that disappears with no row saying it was deliberately dropped fails the feature. This is SC-010
  and a task, not an intention.
- The exemption list is a literal in the test with a reason beside each entry, and an entry without a
  reason fails. Exemptions cover vendored trees and frozen spec directories only — content this
  repository does not author.

**Editing the constitution is editing the governance layer, and that is reported here even though it
is incidental.** The planned edits remove its two downward pointers at lines 6–8 and 72, and add a
line in Governance stating that it names no artefact. No principle's substance changes, nothing it
forbids becomes permitted, and its version and ratification dates move as an amendment. If a
reviewer reads that as a change to a principle rather than an editorial one, this feature stops and
waits.

**Cross-Repository Impact does not apply.** That section binds a spec for a change to a reusable
workflow or composite action. Neither changes. There is no interface delta, no compatibility
question, and no rollout order. No version bump is owed either: `[tool.turbobasic-release]` scopes
the surface to `.github/workflows/**` and `actions/**`, and every path this feature touches is
outside it.

## Project Structure

### Documentation (this feature)

```text
specs/006-layered-ai-instructions/
├── plan.md                      # This file
├── spec.md                      # Requirements, shape-agnostic
├── research.md                  # Phase 0: loading behaviour, duplication inventory, shape decision
├── data-model.md                # Phase 1: the layer model and its entities
├── quickstart.md                # Phase 1: how each success criterion is proven
├── contracts/
│   ├── layer-contract.md        # Layer assignment, direction matrix, derived vocabulary
│   └── owned-facts.md           # The sixteen owned facts and their anchors
├── checklists/
│   └── requirements.md
└── tasks.md                     # Phase 2, by /speckit-tasks
```

### Repository paths this feature touches

```text
CLAUDE.md                        # 1 line -> the navigation layer: imports both rule layers,
                                 #   declares the four layers with purpose and stability, names
                                 #   every artefact and what it answers, states no rule
.specify/memory/constitution.md  # layer 1: drop the two downward pointers; substance unchanged
docs/ai-instructions.md          # layer 2: drop six restated principles, two governance
                                 #   sentences, every mechanism identifier and the archaeology;
                                 #   add the paragraph overriding the user-level layer, and the
                                 #   layering rule itself — rules about rules are this layer's
docs/instruction-layers.md       # NEW, layer 3: the pattern explained, adoptable with no local
                                 #   rules; not where this repository's copy of the rule lives
.github/copilot-instructions.md  # layer 4: points at both rule layers instead of one. Copilot
                                 #   cannot import, so after the deletions the single file it
                                 #   reads would otherwise no longer carry the invariants
README.md                        # layer 3: unchanged
CONTRIBUTING.md                  # layer 3: absorbs the release and verification mechanics that
                                 #   layer 2 was restating, where it does not already hold them
tests/test_instruction_layers.py # NEW: the layer contract and the owned-facts table
tests/test_action_pins.py        # gains the comments that leave prose; PROSE_DOCS unchanged
```

**Structure Decision**: no new directory and no new instruction layer. The four layers map onto
files that already exist, in the places Claude Code and Copilot already look, so nothing about
discovery changes. The single addition is `docs/instruction-layers.md`, which is the reusable
pattern the scope asked for and is reference material rather than a rule — it sits at layer 3 and is
named by the navigation layer like any other document.

The one existing test module is extended rather than replaced. `tests/test_action_pins.py` already
holds the precedent this feature generalises — `PROSE_DOCS` with
`test_no_prose_document_names_a_concrete_major`, which asserts that README alone may name the
current major and every other document must cite it. That fact stays where it is, and the new module
holds the general table so the two do not compete for ownership of the same assertion.

## Complexity Tracking

No Constitution Check violation to justify. The one cost taken deliberately is recorded in
[research.md](research.md) rather than here: importing the constitution puts 74 lines into every
session that were previously absent, bought by removing roughly 100 lines of restatement and
archaeology from the file that is already imported.
