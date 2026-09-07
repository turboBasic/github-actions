# Feature Specification: Layered AI Instructions

**Feature Branch**: `006-layered-ai-instructions`

**Created**: 2026-09-07

**Status**: Draft

**Input**: User description: "rewrite ai layer instructions similar to interfaces and
implementation layers in well-architected software. I want my ai layer instructions to be well
layered similar to interfaces and implementation layers in well-architected software, so that
dependency arrow direction is consistent and implementation details are contained and not leaking.
Use Claude Code architecture guidances for establishing these rules. ask questions"

## Context

The instructions an AI tool reads in this repository are spread across a set of files that grew
one rule at a time. They work, but they are not layered: the same rule is stated in two places, the
most abstract file names the least abstract one, and the top of the stack reaches down into the
test suite's internals.

Concrete instances as of this spec:

- The invariants file points down at the conventions file, and the conventions file points back up
  at the invariants file. The reference is a cycle, so neither is readable first.
- Six rules are stated in full in both files — pinning, least privilege, untrusted input, secrets,
  verification by real invocation, and gates never loosened.
- The conventions file names individual test functions, a lint rule id, and an upstream issue
  number. Rename any of them and the prose is silently wrong, with nothing to catch it.
- Which facts are owned elsewhere is stated inconsistently: one rule correctly says "read the value
  from the consumer-facing document, never restate it here", while others restate freely.

This feature restructures those files so that the dependency direction is one-way and stable, and
so that mechanics stay in the layer that owns them. It changes no workflow and no composite action.

**Constitution note**: the Cross-Repository Impact section does not apply. Nothing under
`.github/workflows/` or `actions/` changes, so there is no interface delta, no compatibility
question, and no rollout order. No version bump is owed.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - An agent gets one answer, not two (Priority: P1)

An AI tool starts work in this repository, loads the instruction set, and reads a rule. Every rule
it reads is stated once, by the file that owns it. Where another file needs that rule, it cites the
owner instead of restating it, so the agent never has to decide which of two phrasings is current.

**Why this priority**: this is the whole point. Two statements of one rule is two sources of truth,
and an agent reconciling them is an agent guessing. Nothing else in this feature matters if a rule
still has two owners.

**Independent Test**: pick every rule currently in force, and confirm each appears in exactly one
layer, with citations where it is needed elsewhere. Delivers a non-contradictory instruction set
on its own, before any structural change or new check.

**Acceptance Scenarios**:

1. **Given** a rule currently written out in both the invariants layer and the conventions layer,
   **When** an agent reads the instruction set, **Then** it finds one statement of that rule and,
   at most, a citation from the other layer.
2. **Given** a rule whose abstract prohibition and concrete format genuinely belong to different
   layers, **When** the rule is placed, **Then** each layer states only its own part and neither
   restates the other's.
3. **Given** a fact already owned by a human-facing document, **When** the AI layer needs it,
   **Then** the AI layer cites the document rather than copying the value.

---

### User Story 2 - A maintainer edits one file (Priority: P1)

A maintainer changes a rule. The edit lands in exactly one file. Nothing else in the repository
goes stale as a result, and no second file has to be found and kept in step.

**Why this priority**: single ownership is only real if editing is cheap. The current duplication
means a rule change is a search-and-replace across files, which is how the two copies drifted in
the first place.

**Independent Test**: take three rules of different kinds — an invariant, a naming convention, and
a fact owned by a human-facing document — change each, and confirm each change is a one-file diff.

**Acceptance Scenarios**:

1. **Given** a test function is renamed, **When** the rename lands, **Then** no instruction file
   needs editing, because no instruction file named the test.
2. **Given** a convention is tightened, **When** the edit lands, **Then** the invariants layer is
   untouched, because it never restated the convention.
3. **Given** a new rule is added, **When** the author looks for where it goes, **Then** the
   instruction set states which layer owns rules of that kind.

---

### User Story 3 - The structure cannot silently rot (Priority: P2)

A change that duplicates a rule, points a reference the wrong way, or names a mechanism above its
layer fails the repository's own offline checks, locally and in CI, before review.

**Why this priority**: the layering is prose, and prose decays under edits nobody checks. This is
also how the repository already holds its other structural rules — a property asserted by test
rather than remembered. It comes second only because the restructure has to exist before it can be
guarded.

**Independent Test**: introduce each violation kind deliberately, one at a time, and confirm the
standard offline run fails and names the offending file and rule.

**Acceptance Scenarios**:

1. **Given** a reference added from a more abstract layer to a more concrete one, **When** the
   offline checks run, **Then** they fail and name both files and the direction violated.
2. **Given** a rule copied into a second layer, **When** the offline checks run, **Then** they fail
   and name both locations.
3. **Given** a test function name written into a layer that does not own mechanics, **When** the
   offline checks run, **Then** they fail and name the identifier.
4. **Given** vendored files and completed spec directories, **When** the offline checks run,
   **Then** those are exempt and do not produce findings.
5. **Given** the checks run, **When** they run, **Then** they need no network.

---

### User Story 4 - Another repository can adopt the shape (Priority: P3)

A maintainer setting up a second `turboBasic` repository reads a description of the layering — what
the layers are, which way references run, what belongs in each — and applies it without inheriting
any rule specific to reusable workflows.

**Why this priority**: the value beyond this repository, and the reason the pattern is written down
rather than left implicit in the file set. Last because this repository has to work first.

**Independent Test**: read the pattern description alone and confirm it contains no rule about
workflows, actions, releases or pinning — only the layering itself.

**Acceptance Scenarios**:

1. **Given** the pattern description, **When** a maintainer reads it, **Then** it names the layers
   and the reference direction without depending on this repository's subject matter.
2. **Given** a repository with a different domain, **When** the pattern is applied, **Then** no
   rule from this repository has to be carried across for the structure to hold.

---

### Edge Cases

- **A rule that is both an invariant and a convention.** Pinning is a prohibition at the invariant
  level and a comment format at the convention level. The layering must allow one subject to span
  layers while forbidding either layer from restating the other's part.
- **A rule that only exists in the outer, unowned layer.** The user-level instructions outside this
  repository are read-only here. A rule stated only there, which this repository depends on, needs
  an owner inside the repository or an explicit statement that the outer layer owns it.
- **The outer layer contradicts this repository.** Precedence has to be stated somewhere, in a
  layer that is allowed to know both exist.
- **Vendored instruction content.** The Spec Kit machinery and its skills are version-locked and
  rewritten on refresh; the invariants file within it is ours. The boundary between what may be
  restructured and what may not must be explicit, and the checks must respect it.
- **Completed spec directories.** They are frozen work logs that legitimately restate rules as of
  their date. They cannot be held to single ownership.
- **A false positive in a prose check.** A legitimate mention that trips a check needs a route that
  does not amount to loosening the gate: a narrow, reasoned exemption rather than a disabled rule.
- **A rule that no layer wants.** Restructuring surfaces rules that fit nowhere. Dropping one
  silently is a regression; the feature has to make that visible rather than convenient.
- **An AI tool that cannot follow a pointer.** Per-tool entry points exist because each tool reads
  its own path. A tool that will not follow a reference would force a copy, which the layering
  forbids.

## Requirements *(mandatory)*

### Functional Requirements

#### The layers

- **FR-001**: The instruction set MUST declare a named, ordered set of layers, and state what
  belongs in each one.
- **FR-002**: Each layer MUST state its own purpose and how stable it is — what kind of change to
  it is expected, and what kind is a design decision.
- **FR-003**: An agent MUST be able to tell, from the entry point alone, which layer answers a
  given question, without reading every layer to be sure no other one contradicts it.
- **FR-004**: The most abstract layer MUST be actionable standalone: reading it requires no forward
  reference into a more concrete layer.

#### One owner per rule

- **FR-005**: Every rule in the instruction set MUST be stated in exactly one layer, which owns it.
- **FR-006**: A layer that needs a rule it does not own MUST cite the owner rather than restate the
  rule.
- **FR-007**: A subject MAY span layers where the abstract prohibition and the concrete mechanics
  genuinely differ, provided each layer states only its own part.
- **FR-008**: Human-facing documentation is the concrete layer for consumer-facing and procedural
  facts. The AI layer MUST cite it and MUST NOT copy values it owns.

#### Direction

- **FR-009**: References MUST run one direction only: a more concrete layer may name a more
  abstract one; the reverse MUST NOT appear. No cycle between layers MUST exist.
- **FR-010**: No layer other than the concrete layer MUST name a mechanism identifier — a test
  function, a path inside the test suite, a lint rule id, an upstream issue reference, or a tool's
  internal symbol.
- **FR-011**: A rule enforced by a check MUST say that it is enforced without naming the check.
  The check names the rule it enforces, which is the direction that survives a rename.
- **FR-012**: Per-tool entry points MUST stay thin pointers carrying no rules of their own, so
  adding a third AI tool adds a pointer rather than a copy.

#### The rule about the rules

- **FR-013**: The layering rule itself MUST be stated in the layer that owns rules about rules, and
  MUST satisfy its own direction and ownership requirements.
- **FR-014**: The restructure MUST preserve every rule currently in force by relocation rather than
  deletion. A rule deliberately dropped MUST be recorded as dropped, so removal is a decision and
  not an accident.

#### Enforcement

- **FR-015**: Offline automated checks MUST fail on a rule stated in two layers, a reference against
  the direction, and a mechanism identifier above the concrete layer.
- **FR-016**: A failure MUST name the file and the specific violation, so it can be fixed without
  re-deriving the rule.
- **FR-017**: The checks MUST NOT require the network, and MUST run in the repository's standard
  offline verification.
- **FR-018**: The checks MUST exempt vendored instruction content and completed spec directories,
  and the exemption list MUST be declared rather than implied.

#### Reuse

- **FR-019**: The layering MUST be described in a form another repository can adopt, containing no
  rule specific to this repository's subject matter.
- **FR-020**: The description MUST cover what the layers are, which way references run, what
  belongs in each layer, and how a violation is caught.

### Key Entities

- **Layer**: a named tier of the instruction set with a purpose, a stability expectation, and a
  position in the order. Holds rules; does not hold another layer's rules.
- **Rule**: a single statement an agent or maintainer must follow. Has exactly one owning layer.
- **Citation**: a reference from one layer to a rule owned by another. Legal in one direction only.
- **Entry point**: a per-tool file an AI tool loads by convention. Carries pointers, not rules.
- **Mechanism identifier**: the name of a test, a lint rule, a config symbol, or an upstream issue.
  Belongs to the concrete layer, and to nothing above it. The test for membership is silent rot: a
  renamed test leaves prose that is wrong with nothing to say so, which is what makes it a
  mechanism. A term whose owner is outside this repository is vocabulary rather than a mechanism and
  is legal at every layer, as is the name of a tool a rule tells a reader to run — that name is the
  rule's content, and renaming it fails loudly at the first invocation.
- **Exemption**: a declared file or path the structural checks do not apply to, with a reason.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every rule in force before the change is in force after it, in exactly one layer. The
  count of statements duplicated across layers is zero, down from nine today — six principles
  restated in full, two governance sentences, and one clause of the first principle.
- **SC-002**: The count of references running against the declared direction is zero, and no cycle
  exists between layers — down from one cycle today.
- **SC-003**: The count of mechanism identifiers appearing above the concrete layer is zero.
- **SC-004**: Renaming any test function or lint rule requires no edit to any layer above the
  concrete one, demonstrated on at least two renames.
- **SC-005**: Changing one rule is a one-file diff, demonstrated on three rules of different kinds.
- **SC-006**: Each violation kind, introduced deliberately, fails the repository's standard offline
  run and names the offending file — three kinds, three failures.
- **SC-007**: The always-loaded instruction text is no larger than before the change, so the
  structure is not bought with context.
- **SC-008**: A reader answering a question about any single rule reads one layer, with no second
  file needed to confirm nothing contradicts it.
- **SC-009**: The reusable description contains zero rules specific to this repository's subject
  matter.
- **SC-010**: No rule is lost: the before-and-after rule inventory reconciles, with every removal
  named and reasoned.

## Assumptions

- **The file topology is a plan-level decision, not a spec-level one.** The requirements above are
  satisfiable by keeping the current file set and fixing ownership and direction, by splitting the
  conventions layer into self-contained topic modules, or by moving mechanics into instructions
  loaded on demand. The plan chooses, with the smallest change that can state one owner per rule
  preferred, and a split justified only where a single owner cannot otherwise be named.
- **Scope is this repository plus a written-up pattern.** No other repository is edited by this
  feature.
- **The user-level instruction file outside this repository is read-only here.** This repository may
  override it and must say where it does, but does not restructure it.
- **Vendored Spec Kit content and its skills are out of scope for restructuring.** The invariants
  file inside that tree is ours and is in scope.
- **Completed spec directories are frozen.** They are work logs, exempt from every requirement here.
- **No consumer-facing file changes**, so no version bump and no consumer migration.
- **"Claude Code architecture guidance" means its documented memory hierarchy, its file-import
  mechanism, and its progressive disclosure of instructions loaded on demand.** The plan verifies
  the current documented behaviour rather than assuming it, and the requirements above are written
  so that no requirement depends on a mechanism that turns out not to exist.
- **The offline checks analyse prose**, so they trade precision for coverage. The plan states how a
  legitimate mention is exempted without disabling a rule.
