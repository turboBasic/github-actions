---

description: "Task list for Layered AI Instructions"
---

# Tasks: Layered AI Instructions

**Input**: Design documents from `/specs/006-layered-ai-instructions/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Tests are part of the deliverable here, not an optional addition — User Story 3 *is* the
check that the layering cannot rot. They land after the restructure so that every checkpoint leaves
`mise run ci` green, and their ability to fail is proven by the deliberate breakages in the final
phase rather than by writing them first.

**Organization**: Tasks are grouped by user story. Stories 1 and 2 both edit
`docs/ai-instructions.md`, so they are sequential increments rather than parallel ones.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

Documentation architecture, no application code. Instruction artefacts are at the repository root,
in `docs/`, in `.github/` and in `.specify/memory/`. The check lives in `tests/`. Scratch goes in
`tmp/`, which is gitignored.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: capture the before state, and de-risk the check's precision before any prose moves

- [X] T001 Build the before inventory in `tmp/rule-inventory-before.md`: one row per rule currently in force across `.specify/memory/constitution.md`, `docs/ai-instructions.md`, `README.md`, `CONTRIBUTING.md` and `docs/technical-debt.md`, each with its file and line. This is the artefact SC-010 reconciles against, so a rule missed here is a rule that can be lost silently.
- [X] T002 [P] Spike the derived vocabulary in `tmp/derived-vocabulary.py`: parse `tests/*.py` with `ast` for `def test_*` names and module-level constants, and print the forbidden set alongside every occurrence of it in the instruction files. Tool and task names are deliberately **not** derived — see the reasoning in `specs/006-layered-ai-instructions/contracts/layer-contract.md`. Confirm the set contains no domain vocabulary (`permissions`, `workflow_call`, `env`) that would make the check unusable.
- [X] T003 [P] Record in `tmp/anchor-check.md` that each of the fourteen anchor phrases in `specs/006-layered-ai-instructions/contracts/owned-facts.md` currently appears in its declared owner, and list every other file it appears in today. The second column is the deletion list for Phase 3.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: get the invariants into context and the layer model declared, so removing a restatement neither loses the rule nor leaves the scheme unstated

**⚠️ CRITICAL**: T004 blocks all of User Story 1. Deleting a restatement before the original is loaded would lose the rule.

- [X] T004 Rewrite `CLAUDE.md` as the navigation layer: an `@` import of `.specify/memory/constitution.md`, an `@` import of `docs/ai-instructions.md`, then the layer declaration — the four layers named in order, each with its purpose, its stability (what kind of change to it is expected), and the artefacts belonging to it, including `README.md`, `CONTRIBUTING.md`, `docs/technical-debt.md`, `tests/` and the tool configs. Descriptive throughout: no imperative sentence anywhere in the file, and no import inside a code fence, because fenced imports are skipped.
- [X] T005 Confirm the imports load, mechanically: both paths in `CLAUDE.md` resolve relative to it, neither import line sits inside a code span or fence, and both files appear in the memory files Claude Code lists for this session. Record the three results in `tmp/import-smoke.md`. If either file is absent from that list, stop — every deletion in Phase 3 depends on it, and no prose assertion substitutes for seeing it loaded.

**Checkpoint**: the invariants are in context without being copied, and the layer model is declared. User Story 1 can begin.

---

## Phase 3: User Story 1 - An agent gets one answer, not two (Priority: P1) 🎯 MVP

**Goal**: every rule is stated once, by the layer that owns it. Where another layer needs it, it cites the owner.

**Independent Test**: for each of the fourteen anchor phrases, confirm it appears in its owner and nowhere else. Delivers a non-contradictory instruction set on its own, before any new check exists.

- [X] T006 [P] [US1] Remove the two downward pointers from `.specify/memory/constitution.md` — the preamble at lines 6–8 that names `docs/ai-instructions.md` as owner of the concrete rules, and the closing sentence at line 72 that names it again — replacing them with a statement that this file names no artefact and that navigation lives at the entry point. Bump `Last Amended` and the version to `1.1.2`: the change is editorial, no principle's substance moves.
- [X] T007 [US1] Delete the six restated principles from `docs/ai-instructions.md` — pinning, least privilege, untrusted input, secrets, verification by real invocation, and gates never loosened — replacing each with a citation by principle number and keeping only the part layer 2 owns, per the disposition table in `specs/006-layered-ai-instructions/contracts/owned-facts.md`.
- [X] T008 [US1] Delete the two duplicated governance sentences from `docs/ai-instructions.md`'s "Changes to these rules": the objection procedure and the conventions carve-out. What survives is the sentence that objecting over a convention is this layer's own business, plus a citation of Governance.
- [X] T009 [US1] Delete the tag-immutability clause from `docs/ai-instructions.md`'s Versioning section. Keep what the version number describes and which changes a consumer cannot absorb — those are layer 2's own — and cite principle I for the rest.
- [X] T010 [US1] Add the precedence paragraph to `docs/ai-instructions.md`'s Working style: this repository's rules win where they are stricter than the user-level file, naming the two live contradictions — a third-party action pinned to a tag rather than a full SHA, and `@main` for in-house references. Memory files concatenate with no override mechanism, so this paragraph is the only thing that resolves them.
- [X] T011 [US1] Move the release and verification mechanics that `docs/ai-instructions.md` restates into `CONTRIBUTING.md`, only where `CONTRIBUTING.md` does not already hold them, and delete them from layer 2. Most are already there; the task is the reconciliation, not the copy.
- [X] T012 [P] [US1] Rewrite `.github/copilot-instructions.md` to point at both rule layers rather than one. Copilot has no import mechanism, so after T007 the single file it reads no longer carries the invariants it used to find restated there. Still a thin pointer with no rule of its own, so it stays layer 4 — two links and a line each saying what is at the end of them.
- [X] T013 [US1] State the layering rule in `docs/ai-instructions.md`'s "Changes to these rules": each fact has one owning layer, a layer that needs a fact it does not own cites the owner, and references run from concrete to abstract only. Rules about rules are layer 2's business, so this is where the rule lives — `docs/instruction-layers.md` explains it for another repository, and layer 2 may not cite layer 3.
- [X] T014 [US1] Repair every anchor link into `docs/ai-instructions.md` that this phase broke, and verify by extracting each `docs/ai-instructions.md#…` fragment used anywhere in the repository and matching it against the file's surviving headings. `CONTRIBUTING.md`'s "Read this first" links five anchors and `README.md` links more; nothing here lints a cross-file anchor, so the extraction is the only proof.
- [X] T015 [US1] Rebuild the inventory as `tmp/rule-inventory-after.md` and reconcile against `tmp/rule-inventory-before.md`. Every rule present before is present after, in exactly one layer. Any deliberate drop gets a row naming it and the reason. An unexplained absence fails the story.

**Checkpoint**: no rule is stated twice, both tools reach both rule layers, and the layering rule is stated where it is owned. `mise run ci` passes. Nothing yet stops it regressing.

---

## Phase 4: User Story 2 - A maintainer edits one file (Priority: P1)

**Goal**: mechanism names live only in layer 3, so renaming a test touches no prose.

**Independent Test**: `git grep` for two test function names and an upstream issue reference across `*.md` and get no hits; then rename a test and confirm no document needs editing.

- [X] T016 [P] [US2] Merge the enforcement archaeology out of `docs/ai-instructions.md` into the comments in `tests/test_action_pins.py` that already carry it — the `$/` and upstream-issue explanation, the public-repository REST endpoint and its `422`, and the offline-marker rationale. Merge rather than append: most of this text exists in both places already, and the deliverable is one copy.
- [X] T017 [P] [US2] Replace every named test and test symbol in `docs/ai-instructions.md` with the bare fact that a gate holds the rule. `WORKFLOW_CONTRACTS`, `OWN_CI`, six `test_*` names and `@pytest.mark.drift` all go; "enforced by test" stays, because that a rule is checked is something an agent acts on. Tool and task names stay — `prek` and the lint task are the rule's content, not a mechanism behind it.
- [X] T018 [US2] Remove every layer 3 path from `docs/ai-instructions.md` — the tool-config filenames and the document names alike — and move the statements of which artefact owns which fact to `CLAUDE.md`'s navigation layer, where naming a path is the content rather than a violation. The tools themselves keep their names in layer 2, and so does every rule whose path was only a pointer: that a major is never written literally outside the artefact that declares it survives without naming that artefact. Seven document names are outstanding after Phase 3 — five `README.md` and two `CONTRIBUTING.md` — and the direction check in T024 fails on each one that remains. Naming a spec's own `tasks.md` is not one of them: `specs/**` is exempt and is assigned to no layer.
- [X] T019 [US2] Reverse the arrow in `tests/test_action_pins.py`: each test whose name was cited in prose gains a comment naming the rule it enforces and the layer that owns it. The test names the rule; the rule does not name the test.
- [X] T020 [US2] Verify with `git grep -n` across `'*.md'` that no `def test_*` name, no test-module constant and no `owner/repo#N` reference survives outside `tests/` and `CONTRIBUTING.md`.
- [X] T021 [US2] Prove SC-005 with the three one-file diffs from `specs/006-layered-ai-instructions/quickstart.md`: tighten a naming convention, add a label, reword a principle's rationale. `git diff --name-only` returns exactly one path each time. Revert all three.

**Checkpoint**: a rename in `tests/` is invisible to every document. Stories 1 and 2 are both complete and `mise run ci` is green.

---

## Phase 5: User Story 3 - The structure cannot silently rot (Priority: P2)

**Goal**: each violation kind fails the standard offline run, locally and in CI, before review.

**Independent Test**: introduce each of the three violation kinds one at a time and confirm `mise run ci` fails and names the file and the violation.

- [X] T022 [US3] Create `tests/test_instruction_layers.py` with the `LAYERS` assignment and the `EXEMPTIONS` table from `specs/006-layered-ai-instructions/contracts/layer-contract.md`, and a test asserting every instruction path in the tree is assigned to exactly one layer. An unassigned document fails, so a new one has to be placed deliberately.
- [X] T023 [US3] Add the derived-vocabulary helper to `tests/test_instruction_layers.py`, promoted from the T002 spike: `ast` over `tests/*.py` for test names and module constants. Standard library only — no new dependency, so `uv.lock` does not move.
- [X] T024 [US3] Add the direction check to `tests/test_instruction_layers.py`: no artefact names one from a higher-numbered layer, layer 4 exempted because navigation is its content, and no cycle in the citation graph. The failure message names both files and the direction violated.
- [X] T025 [US3] Add the mechanism-identifier check to `tests/test_instruction_layers.py`: nothing above layer 3 contains a derived identifier, an `owner/repo#N` reference, a REST path or a bare HTTP status code. The failure message names the identifier.
- [X] T026 [US3] Add the owned-facts table to `tests/test_instruction_layers.py` from `specs/006-layered-ai-instructions/contracts/owned-facts.md`, parametrised one case per **anchored** row, asserting the anchor appears in its owner **and** nowhere else. The first assertion is what stops a row rotting into a pattern that matches nothing. The two rows carrying no anchor are held by existing gates and get a comment saying which.
- [X] T027 [US3] Add the import-reachability and precedence checks to `tests/test_instruction_layers.py`: `CLAUDE.md` imports both rule layers outside any code fence, `.github/copilot-instructions.md` links both, and `docs/ai-instructions.md` still carries the precedence paragraph, asserted by anchor phrase.
- [X] T028 [US3] Add the layer-4 check to `tests/test_instruction_layers.py`: a navigation file carries imports, links, the layer declaration and a gloss per artefact, and no imperative sentence. This is the assertion FR-012 needs and the one the layer contract defers to "checked separately".
- [X] T029 [US3] Add the exemption check to `tests/test_instruction_layers.py`: every entry in `EXEMPTIONS` carries a reason, and an entry without one fails. This is what keeps the exemption list from becoming a dial on the gate.
- [X] T030 [US3] Confirm `tests/test_instruction_layers.py` carries no `drift` marker and that `mise run ci` passes with the network unavailable. Every fact it reads is in the tree.

**Checkpoint**: the layering is machine-checked. Its ability to fail is proven in Phase 7, not assumed here.

---

## Phase 6: User Story 4 - Another repository can adopt the shape (Priority: P3)

**Goal**: the pattern is written down in a form another repository can apply without inheriting a rule from this one.

**Independent Test**: read `docs/instruction-layers.md` alone and find no rule about workflows, actions, releases or pinning.

- [X] T031 [US4] Write `docs/instruction-layers.md`: the four layers, the reference direction, what belongs in each, the navigation-is-not-a-rule-layer principle, and how a violation is caught. Explanatory rather than normative — this repository's copy of the rule lives in layer 2 per T013 — so it sits at layer 3. Examples are allowed where marked as such. It must contain no literal major version, because every prose document except `README.md` is already scanned for one.
- [X] T032 [US4] Add `docs/instruction-layers.md` to the layer 3 list in `tests/test_instruction_layers.py`, so the new document is assigned rather than unassigned.
- [X] T033 [P] [US4] Name `docs/instruction-layers.md` from `CLAUDE.md`'s navigation layer with a one-line gloss.
- [X] T034 [US4] Prove SC-009: grep `docs/instruction-layers.md` for `workflow`, `action`, `release`, `pin`, `major` and `consumer` and confirm no hit outside a marked example.

**Checkpoint**: all four stories complete.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: prove the checks can fail, and close the documentation the change touched

- [X] T035 Reintroduce a copied principle sentence into `docs/ai-instructions.md`, confirm `mise run ci` fails and names the file and the anchor, then `git checkout -- docs/ai-instructions.md`.
- [X] T036 Reintroduce a markdown link from `.specify/memory/constitution.md` to a layer 3 file, confirm `mise run ci` fails and names the direction violated, then revert.
- [X] T037 Write a `def test_*` name from `tests/test_action_pins.py` into `docs/ai-instructions.md`, confirm `mise run ci` fails and names the identifier, then revert.
- [X] T038 Prove SC-004 by renaming two test functions in `tests/test_action_pins.py`, running `mise run ci`, and confirming no `*.md` file needs editing for it to pass. Revert both. Absence of a name today does not prove immunity tomorrow; this does.
- [X] T039 [P] Prove SC-007 with `wc -l CLAUDE.md docs/ai-instructions.md .specify/memory/constitution.md`: the always-loaded total is no more than the 293 lines loaded before the change, now with the invariants included. **Measured 383 against 293, and the deviation is accepted rather than closed.** 38 navigation + 268 conventions + 77 invariants, against 1 + 292 + 0 before. The invariants are +77 and were previously not in context at all, which is the change's point; the budget assumed the conventions layer would fall to ~190 and it fell to 268, because each deleted restatement left a citation behind and two new owned paragraphs — precedence and the layering rule — arrived. Cutting the remaining 90 would mean un-stating rules that T015 reconciled as surviving, so the criterion is recorded as missed rather than met by deletion.
- [X] T040 [P] Walk SC-008: pick a naming rule, a permission rule, a Python rule, a release rule and a spec rule, and for each read only the layer `CLAUDE.md` sends you to. Needing a second file to be sure nothing contradicts it means a boundary is in the wrong place.
- [X] T041 ~~Delete the scratch from `tmp/` once the inventory has reconciled and the PR body carries its conclusion.~~ **Dropped by decision.** The precondition never came about — the PR body is still the spec-only one — and `tmp/` is gitignored, so the deletion is unrecoverable. The scratch stays. Nothing there ships regardless: `tmp/` is exempt from the layer checks and excluded from markdownlint.
- [X] T042 Run `mise run ci` clean, and re-read `README.md`, `CONTRIBUTING.md` and `docs/technical-debt.md` for framing this change made stale — a section that describes the old two-copy arrangement is a defect in this change, not a follow-up.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies. T001 is the only one that must be complete and correct before anything is deleted.
- **Foundational (Phase 2)**: depends on Setup. **Blocks User Story 1** — T004 must land before any restatement is removed, or the rules leave context with them, and T005 must confirm it mechanically before T007 deletes anything.
- **User Story 1 (Phase 3)**: depends on Phase 2.
- **User Story 2 (Phase 4)**: depends on User Story 1, because both edit `docs/ai-instructions.md` and US1's deletions determine what is left for US2 to strip.
- **User Story 3 (Phase 5)**: depends on Stories 1 and 2. A check written against an uncleaned tree fails on work in progress; written against a cleaned one, it holds the cleaning in place.
- **User Story 4 (Phase 6)**: depends on Phase 5 only for T032, which edits the test module. T031 can be drafted at any point after T013 settles where the rule itself lives.
- **Polish (Phase 7)**: depends on Phase 5 for T035–T038, and on everything for T042.

### User Story Dependencies

- **US1 (P1)**: after Phase 2. Independently deliverable — a non-contradictory instruction set with no new gate.
- **US2 (P1)**: after US1. Same file, so not parallel. Independently deliverable.
- **US3 (P2)**: after US2. Independently deliverable as the guard on what US1 and US2 achieved.
- **US4 (P3)**: T031 and T034 are independent of every other story; T032 needs the test module to exist.

### Within Each User Story

- Phase 3: T006 edits the constitution and T012 the Copilot pointer, so both are parallel to the rest; T007, T008, T009, T010, T011 and T013 are sequential on `docs/ai-instructions.md`; T014 comes after every heading change; T015 is last, because it measures the rest.
- Phase 4: T016 and T017 are different files and parallel; T019 follows T016 on `tests/test_action_pins.py`; T018 follows T017 on `docs/ai-instructions.md`; T020 and T021 verify and come last.
- Phase 5: every task edits `tests/test_instruction_layers.py`, so all are sequential. T023 is a prerequisite of T025.
- Phase 6: T031, then T032 and T033 in parallel, T034 last.

### Parallel Opportunities

- T002 and T003 run alongside T001.
- T006 and T012 run alongside the `docs/ai-instructions.md` sequence.
- T016 runs alongside T017.
- T033 runs alongside T032.
- T039 and T040 run alongside each other and alongside T035–T038.
- Nothing else parallelises: this feature is four documents and one test module, and the two documents that carry the most work are edited by every story that touches them.

---

## Parallel Example: Phase 1

```bash
# Three independent reads of the current state, no shared file:
Task: "Build the before inventory in tmp/rule-inventory-before.md"
Task: "Spike the derived vocabulary in tmp/derived-vocabulary.py"
Task: "Record anchor phrase locations in tmp/anchor-check.md"
```

---

## Implementation Strategy

### MVP (User Story 1 only)

1. Phase 1 — capture the before state, or SC-010 cannot be answered later.
2. Phase 2 — import the invariants and declare the layers. **Do not skip; it is what makes deletion safe and what tells a reader the scheme exists.**
3. Phase 3 — one owner per rule.
4. **Stop and validate**: `mise run ci` green, inventory reconciled, anchors unique, both tools reaching both rule layers.
5. Shippable here. The instruction set no longer contradicts itself, with no new gate.

### Incremental delivery

1. Setup + Foundational → the invariants are in context and the layers are declared.
2. US1 → no rule stated twice → ship.
3. US2 → a rename touches no prose → ship.
4. US3 → the structure is guarded → ship.
5. US4 → the pattern is reusable → ship.

Each increment leaves `mise run ci` green, so any of them can be the stopping point.

### Sequencing note

This feature does not parallelise across people. Two of the four artefacts absorb most of the work,
and every story edits at least one of them. Run it as one sequence.

---

## Notes

- `[P]` means a different file and no dependency on incomplete work.
- Commit per task or per logical group. The Conventional Commit type is `docs:` for Phases 3, 4 and 6, `test:` for Phase 5, and `chore:` for Phase 7.
- No version bump is owed: every path touched is outside the release surface declared in `pyproject.toml`.
- Editing `.specify/memory/constitution.md` is editing the governance layer. T006 is editorial by design — if a reviewer reads it as a change to a principle, stop and wait rather than proceeding.
- Nothing here needs the network, at any task.
