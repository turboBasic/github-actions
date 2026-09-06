# Feature Specification: Declared Consumer Surface

**Feature Branch**: `004-declared-consumer-surface`

**Created**: 2026-09-06

**Status**: Draft

**Input**: Issue [#110](https://github.com/turboBasic/github-actions/issues/110) — "feat: make
release.yml's consumer-surface path list an input".

**Supersedes / relates to**: [`003-tested-release-scripts`](../003-tested-release-scripts/spec.md) moved
the surface-path list out of shell into `actions/release-decisions` and named this change as out of scope.
Nothing 003 decided changes here.

**Deviation from the issue, decided before planning**: #110 proposes a `workflow_call` **input**. This
specification does not add one. The reason is in [research.md D1](./research.md#d1) and summarised under
*Why not the input* below; the outcome is a smaller change with no interface delta at all, so the issue's
shape is superseded rather than implemented. #110 gets a comment recording this.

## Why this has a spec at all

`release.yml` is a `workflow_call` workflow with a live external call site, which puts any change to what
it decides under the constitution's **Cross-Repository Impact** gate. That gate is answered below.

By `docs/ai-instructions.md`'s size table the trigger was "a new input on a workflow consumers resolve".
There is no new input now, but there **is** a behaviour change consumers can see, which the same row
covers. The spec stays.

## Why not the input

The list has two readers inside this repository. `release-proposal.yml` runs only here and calls the
module by in-repo path. `release.yml` called from `ci.yml` has to reach the same list through whatever
interface an external caller uses. So a **mandatory** input forces `ci.yml` to produce our list, giving
the surface a second definition in YAML where the `OWN_CI` comparison cannot see it — and an **optional**
input has to default to something, which for any caller but us is our layout by coincidence. That
coincidence is the defect #110 is about; defaulting to it would have made the defect the documented
behaviour.

Both horns come from the list living somewhere only *we* can reach. It does not have to:
`release.yml` already reads the **caller's** `pyproject.toml`, because `[project].version` there is the
version being released. A table in that file is per-repository by construction, travels with the caller
for free, and is read by our two workflows through the identical code path — one definition each, and no
input to bypass.

## Cross-Repository Impact *(constitution gate)*

**Affected consumers.** From [`docs/consumers.md`](../../docs/consumers.md), `release.yml` has two call
sites: `ci.yml` here as a self-call, and `github-actions-test` at `@v4` — the only external caller, and
the only place the `release / tag-and-publish` check reports at all. `python-app-baseline`,
`repo-factory` and `opus-magnum` do not call it, so they are untouched.
`actions/release-decisions` has no external caller and is not meant to gain one.

**Interface delta.** **None.** No input, output, secret, permission or job name changes anywhere. The
existing `pyproject` input already carries the file the table lives in. What changes is what the release
*decides* when a caller has not declared a surface.

**Compatibility.** Every call site keeps working untouched, so **no major bump is owed** — by
`README.md`'s own test, nothing here breaks a call site, retires a check context, or changes a permission
a caller must grant. Behaviour does move for a caller with no table: it stops inheriting our filter and
gets an unfiltered range, which refuses *more* often, never less. That is consumer-visible, so this ships
as a **minor**.

**Rollout and rollback.** Our own table lands in the same change, so this repository's behaviour is
unchanged — omitting it would silently put our release on the unfiltered path and refuse over changes to
`ci.yml`, which is what 003 fixed. Order: land here with our table, cut the minor, then declare
`github-actions-test`'s surface and exercise both directions there at the ref it pins. Rollback is a
revert here; a consumer needs to do nothing, because a table it has already written is harmless to a
version that ignores it.

## User Scenarios & Testing *(mandatory)*

Two actors who want opposite things. A **consumer maintainer** cutting releases with this workflow wants
the refusal measured against their layout. A **maintainer of this repository** wants the change not to
have loosened the gate that keeps our own list honest.

### User Story 1 - Refuse on the caller's own surface (Priority: P1)

A consumer maintainer declares their surface and lands a commit marked `!` that breaks their package's
public API under `src/`. They expect the release to be refused unless the version carries a new major,
because that is the refusal the workflow advertises. Today it is not refused: the range is filtered to
`.github/workflows/**` and `actions/**`, neither of which their break touched, so the check passes over a
range that broke their consumers.

**Why this priority**: It is the false negative, and it is the direction that publishes a broken contract
under a moving tag. The false positive in Story 2 is loud and costs an argument; this one is silent.

**Independent Test**: Declare a surface naming the caller's own source, land a breaking commit inside it
under a version that is not a new major, and confirm the release is refused. Delivers the whole point of
the feature on its own.

**Acceptance Scenarios**:

1. **Given** a caller declaring `src/**` as its surface and a breaking commit touching `src/`,
   **When** a version that is not a new major is released, **Then** the release is refused before any tag
   is created.
2. **Given** the same caller and a breaking commit touching only `docs/`, **When** a patch version is
   released, **Then** it proceeds, because nothing on the declared surface changed.
3. **Given** a caller declaring a surface, **When** the notes are rendered, **Then** they still describe
   the *unfiltered* range — the filter belongs to the refusal, not to the notes.

---

### User Story 2 - Stop refusing over files nobody resolves (Priority: P2)

The same consumer maintainer keeps its own CI under `.github/workflows/`. A breaking change to one of
those workflows is refused under a patch today, because our include list counts every workflow as
surface — unless the file happens to be named `ci.yml` or `release.yml`, which our exclusions name, in
which case it is silently dropped. Which of the caller's plumbing files count has no relationship to the
caller's layout.

**Why this priority**: Real and already observed — during #61 stage 2's verification, two of the four
workflow files in `github-actions-test`'s breaking range were excluded by name coincidence and two were
not. It follows P1 because its failure mode is a refusal a maintainer can read and work around, not a
release that should not have shipped.

**Independent Test**: Declare a surface that omits `.github/workflows/**`, land a breaking change to one
of the caller's own workflows under a patch, and confirm it proceeds.

**Acceptance Scenarios**:

1. **Given** a caller whose declared surface omits `.github/workflows/**` and a breaking commit touching
   one of its workflows, **When** a patch version is released, **Then** it proceeds.
2. **Given** a caller that declares a surface, **When** the filter is built, **Then** it is composed only
   of what that caller declared — no path of ours is added to it, so no exclusion of ours can drop one of
   its files by name coincidence.

---

### User Story 3 - Never guess a caller's surface (Priority: P1)

A consumer maintainer calls `release.yml` having never heard of any of this. The workflow cannot know
their layout, and the previous behaviour — assume ours — is wrong in both directions and says nothing.
They should get the conservative answer and be told they got it.

**Why this priority**: P1 because it is the whole reason the input was rejected. A default that is right
by coincidence is a trap whether it arrives as an input default or a constant.

**Independent Test**: Run a release in a repository with no table and confirm the range is unfiltered and
the run says so in as many words.

**Acceptance Scenarios**:

1. **Given** a caller whose `pyproject.toml` declares no surface, **When** the filter is built, **Then**
   nothing is filtered, so the refusal considers every path in the range.
2. **Given** the same caller, **When** the filter is built, **Then** the run states that no surface was
   declared and where to declare one, rather than proceeding silently.
3. **Given** a caller that declares a deliberately empty surface, **When** the filter is built, **Then**
   the range is likewise unfiltered but no notice is printed — having decided is different from never
   having been asked.

---

### User Story 4 - Keep our own list held to one definition (Priority: P1)

A maintainer of this repository changes which workflows are its own CI. The gate that catches a
half-finished change compares the surface exclusions against `OWN_CI`. Moving the list from the module
into a data file must move that gate with it, not lose it.

**Why this priority**: P1 alongside Story 1. This is principle VII in this feature's terms: the gate is
*relocated*, and a relocation that quietly stops asserting the same equality is a loosening.

**Independent Test**: Assert offline that our declared exclusions equal `OWN_CI`, reading the file that
now holds them, and confirm the assertion fails when either side is edited alone.

**Acceptance Scenarios**:

1. **Given** the repository as committed, **When** the surface is read on our own release path, **Then**
   it is the list our `pyproject.toml` declares, and the exclusions equal `OWN_CI`.
2. **Given** a workflow added to or removed from `OWN_CI` without a matching edit to the table, **When**
   the suite runs, **Then** it fails and names both sides.
3. **Given** our table deleted entirely, **When** the suite runs, **Then** it fails — our own release
   silently going unfiltered is the failure mode this story exists to prevent.

---

### Edge Cases

- **No table at all.** Story 3. Unfiltered, with a notice.
- **A declared but empty surface.** Unfiltered, no notice. Deciding is different from not being asked.
- **A path holding whitespace.** The flags travel from the decision to the workflow as one line and are
  split on whitespace, so such a path would silently become two, each matching nothing. Refused by name.
- **A path beginning with `-`.** It would reach the notes renderer as a flag rather than a path. Refused
  by name. Not a privilege boundary — a caller editing its own repository could pass anything — but it is
  a typo with a confusing failure, and it costs one clause to catch.
- **A value of the wrong shape** — a bare string where a list belongs, or a list holding a number.
  Refused naming the key, never coerced.
- **A caller with no `pyproject.toml`.** Cannot arise: the release reads `[project].version` from it and
  already fails first without one.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The consumer surface MUST be read from the released repository's own `pyproject.toml`, so a
  caller's release is judged against the caller's layout.
- **FR-002**: A repository that declares no surface MUST get an unfiltered range — every path considered,
  so the refusal fires on any breaking change — and MUST NOT have any other repository's layout assumed
  for it.
- **FR-003**: A repository that declares no surface MUST be told so in the run, including where to declare
  one. A repository that declares an explicitly empty surface MUST get the same unfiltered range without
  the notice.
- **FR-004**: A declared surface MUST be used alone. No path from this repository may be added to it.
- **FR-005**: A declared value that is not a list of strings MUST be refused with a message naming the key,
  never coerced or partially used.
- **FR-006**: A path that cannot survive the single-line carrier the flags travel on, or that would be read
  as a flag rather than a path, MUST be refused with a message naming it — before the notes are rendered
  and before any ref is created. It MUST NOT be silently split, dropped, or passed through.
- **FR-007**: This repository MUST declare its own surface, so its release behaviour is unchanged by this
  feature.
- **FR-008**: The declared exclusions of *this* repository MUST remain held equal to `OWN_CI` by the suite.
  The gate moves to the file that now holds them and keeps asserting the same equality.
- **FR-009**: `release.yml` and `release-proposal.yml` MUST continue to resolve the surface through one
  code path, so the increment proposed and the refusal applied keep agreeing on what "breaking" means.
- **FR-010**: No `workflow_call` input, output, permission or job name may change. There is to be no
  mechanism by which a caller, or a dispatch of our own release, can supply a surface other than the one
  its repository declares.
- **FR-011**: The filter MUST continue to apply to the refusal only. The rendered notes stay unfiltered,
  because they describe everything that landed.
- **FR-012**: `README.md` MUST document how a caller declares its surface and what happens if it does not,
  replacing the paragraph that currently documents the miss in both directions as the workaround.
  `docs/consumers.md` MUST record the new obligation on `release.yml`'s callers.
- **FR-013**: Every decision MUST be testable offline, with `mise run ci` needing no network.

### Key Entities

- **Consumer surface**: the set of paths whose change a repository's consumers can observe, as an include
  list and an exclude list. Meaningful only relative to one repository's layout, which is why it belongs
  to the repository being released and not to the workflow releasing it.
- **Declaration state**: *undeclared*, *declared*, or *declared empty*. The first two differ in filter;
  the first and third differ only in whether the run says anything. Distinguishable at all only because
  the surface is now structured data rather than a string.
- **Surface filter**: the two lists rendered as the flags the notes renderer takes, carried from the
  decision to the workflow as one value.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: This repository's release produces a byte-identical surface filter to the one it produces
  today, asserted offline.
- **SC-002**: A caller that declares its own surface has the refusal fire on a breaking change inside that
  surface and not fire on one outside it — both demonstrated on a real run in a consumer, not only in the
  suite.
- **SC-003**: A repository with no declared surface produces an unfiltered range and a notice naming the
  omission, demonstrated on a real run before that repository declares one.
- **SC-004**: A rejected path or a mis-shaped value produces a named refusal in the run log, and no tag
  exists afterwards.
- **SC-005**: Editing `OWN_CI` alone, or our table alone, fails the suite with a message naming both.
- **SC-006**: There is exactly one place any repository's surface is written, and for this repository the
  suite proves it is the only one.
- **SC-007**: A consumer maintainer can read `README.md`'s `release.yml` section and declare a correct
  surface without reading `actions/release-decisions`.

## Assumptions

- **`pyproject.toml` is the right home**, not a new dedicated file. `release.yml` already reads it from the
  caller's tree for `[project].version`, the module already parses it with `tomllib`, and this repository
  already configures four tools there. A dedicated file would add a file and a parser to hold the same
  three lines — and YAML is not available to a standard-library-only module.
- **Absent and empty are worth distinguishing** even though they produce the same filter, because it lets
  a caller who genuinely wants an unfiltered range say so and stop being told about it.
- **Paths hold no spaces**, and refusing one is cheaper than changing what the flags travel on. The
  alternative — a multi-line carrier read back line by line — is the upgrade path if a caller ever
  genuinely needs one.
- **A caller's own `pyproject.toml` is as trusted as its own workflow file.** Both are its committed
  content, so the shape checks in FR-005 and FR-006 are there to catch mistakes, not to defend a
  privilege boundary. The values still reach the renderer through a file and an environment variable,
  never through inline `${{ }}`.
- **`github-actions-test` is the verification site**, as it was for `v4`. It is the only external caller of
  `release.yml`, so it is the only place caller-side behaviour can be exercised at all — and its version
  tags are disposable where ours are immutable.

## Out of Scope

- **Any way to override a repository's declared surface per call.** Deliberately absent: it would
  reintroduce the bypass that rejecting the input removed, and nothing has asked for two surfaces in one
  repository.
- **Switching the refusal off.** A caller wanting no refusal declares a surface nothing matches, visibly,
  in its own file. A dedicated opt-out is its own issue with its own argument.
- **The 0.x branch of the same refusal.** [#107](https://github.com/turboBasic/github-actions/issues/107)
  owns it — under `0.y.z` the component signalling a break is the minor, and which ref moves for a 0.x
  release is a decision of its own. Independent; neither blocks the other.
- **Deriving this repository's surface from the tree** instead of declaring it. It is computable — every
  workflow declaring `workflow_call`, plus every composite action — but it generalises to no consumer, so
  it would mean two mechanisms for one question. Noted in [research.md D6](./research.md#d6).
- **Any change to how "breaking" is read** from a commit, to the notes, or to the increment
  `release-proposal.yml` proposes.
