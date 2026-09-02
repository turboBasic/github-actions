# Feature Specification: Commit-driven releases

**Feature Branch**: `002-commit-driven-releases`

**Created**: 2026-09-02

**Status**: Draft

**Input**: User description: "Release notes and the version proposal both derive from commit history instead of from PR labels and a hand-edited version file."

## Clarifications

### Session 2026-09-02

- Q: If more commits land on `main` after a release proposal is raised but before it is approved, what
  should the proposal do? → A: Refresh automatically on every new commit — version and notes
  recomputed, and publishing re-derives from the same rules.
- Q: When the release range contains nothing that would appear in the notes, what should happen? → A: No
  proposal is raised at all; a release attempted anyway fails loudly and creates no tag.
- Q: Which sections should `perf`, `revert` and `build` commits appear under? → A: `perf` and `revert`
  under Fixes, `build` under CI and dependencies; `chore`, `style`, `test` and `refactor` under
  Maintenance.
- Q: If the reviewer changes the proposed version and a new change then lands on `main`, does the refresh
  keep their version or recompute it? → A: Keeps theirs — the refresh updates only the notes — but
  publishing is refused when the range holds a breaking change and the version is not a new major.
- Q: When the proposal is approved, continuous integration has not yet finished on the commit that
  approval produced — what should the release do? → A: It starts when CI reports on that commit and
  proceeds only if it passed, so approval stays the only human step.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A consumer can tell what changed, and what broke (Priority: P1)

Someone who pins this repository's moving major tag opens a release and reads its notes to decide
whether to move and whether anything needs changing on their side. Every change in the release
appears under a heading that describes it, and a change that breaks an existing call site says in
words what broke, not merely that something did.

**Why this priority**: This is the failure being fixed. The notes are categorised today by a hand-
applied label, so a change is filed correctly only if someone remembered. Nine merged pull requests
carry no label at all, and the only breaking change this repository has ever shipped was published
under "Other changes" — the single item a consumer most needed to see, in the section that means
"we could not classify this".

**Independent Test**: Produce the notes for a range that has already been released and compare them
against the commit log for that range: every change accounted for, and the breaking change in the
breaking section carrying its explanatory text. This needs no change to how a release is triggered,
so it delivers the whole of the categorisation fix on its own.

**Acceptance Scenarios**:

1. **Given** a release range containing a commit whose type marks it breaking, **When** the notes for
   that range are produced, **Then** the change appears in the breaking section with the explanatory
   text from its message, and also under the heading for its own type.
2. **Given** a release range containing changes of several types, **When** the notes are produced,
   **Then** each change appears under the heading for its type, and the headings appear in a fixed
   order that does not vary between releases.
3. **Given** a pull request that carries no labels at all, **When** it is included in a release,
   **Then** its change is categorised from its commit alone and no heading of last resort is used.
4. **Given** a release range containing a version-bump commit, **When** the notes are produced,
   **Then** that commit does not appear anywhere in them.

---

### User Story 2 - Release by approving, not by assembling (Priority: P2)

The maintainer decides a release is due. Instead of editing a version by hand, merging that, and then
separately triggering a release, they are presented with a proposal: the version, and the notes that
release would publish. They read it, and approving it is what performs the release.

**Why this priority**: It removes two of the three manual steps and, more importantly, moves the notes
in front of a human *before* they are published rather than after. It depends on Story 1 — a proposal
is only worth reviewing if the notes in it are correct — which is why it is second.

**Independent Test**: Produce a release proposal, review it, approve it, and confirm a tag, a
published release and an updated major tag all result, with no other manual step in between.

**Acceptance Scenarios**:

1. **Given** the repository is ready to release, **When** a release is proposed, **Then** the proposal
   shows both the version to be released and the exact notes that will be published.
2. **Given** a release proposal under review, **When** it is approved, **Then** the version tag is
   created, the release is published with those notes, and the moving major tag points at the released
   commit.
3. **Given** a release proposal, **When** the reviewer disagrees with the version it proposes,
   **Then** they can change it before approving, and the released version is the one they approved.
4. **Given** the required continuous-integration verdict has not passed on the commit to be released,
   **When** a release is attempted, **Then** it does not proceed and says which verdict is missing.
5. **Given** the notes cannot be produced for any reason, **When** a release is attempted, **Then** no
   tag exists afterwards.
6. **Given** a proposal whose version the reviewer has already altered, **When** further changes land
   before it is approved, **Then** the notes update to describe them and the altered version stands.
7. **Given** a proposal has just been approved and the verdict for the resulting commit is still
   pending, **When** that verdict arrives green, **Then** the release proceeds with no further human
   action.

---

### User Story 3 - Preview the notes before proposing (Priority: P3)

Before proposing a release, or while changing how the notes are shaped, the maintainer renders them
locally and reads them, without reaching the network and without creating anything.

**Why this priority**: It makes the shaping rules debuggable and keeps a change to them reviewable —
but the feature is useful without it, so it ranks last.

**Independent Test**: Render notes for a chosen range on a local checkout with networking disabled,
and confirm the output matches what a release for the same range publishes.

**Acceptance Scenarios**:

1. **Given** a local checkout and no network access, **When** the maintainer renders the notes for a
   range, **Then** the output is produced and matches what a release over that range would publish.
2. **Given** a change to how sections are shaped, **When** the notes are re-rendered locally,
   **Then** the effect is visible without proposing or publishing a release.

---

### Edge Cases

- **A range whose every commit is excluded** (for example, only a version bump): the notes would be
  empty, which means either nothing shippable happened or the shaping rules are wrong. No proposal is
  raised, so nothing invites a release that has nothing to say; a release attempted regardless fails
  loudly rather than publishing an empty body.
- **A change marked breaking with no explanatory text**: the breaking section still lists it, falling
  back to the change's summary rather than showing nothing.
- **Two or more breaking changes in one release**: all appear, not just the first.
- **The first release of a new major**, where there is no previous version tag to measure from, and
  the major tag does not yet exist and must be created rather than moved.
- **A commit whose type is not one of the twelve allowed**: it must still surface somewhere rather
  than disappearing, even though both commit checks are required and should prevent it.
- **More changes landing after a release is proposed but before it is approved**: the proposal refreshes
  so the reviewer never reads a stale version or stale notes, and the published notes describe what is
  actually being released rather than what was true when the proposal was first raised.
- **Two release proposals open at once**, or one approved twice.
- **A version that is not ahead of every existing release**: releasing it would move the major tag
  onto something consumers read as older than what they already have.
- **A breaking change landing into a range whose proposed version is not a new major**, whether the
  version was proposed or set by hand: publishing it would move the existing major tag onto a broken
  contract, so the release refuses rather than shipping it.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The notes for a release MUST be derived from the commits in the range being released.
  No pull request label may affect them.
- **FR-002**: The notes MUST present the same seven sections the notes carry today — breaking changes,
  features, fixes, documentation, CI and dependencies, maintenance, and a section of last resort — in
  a fixed order.
- **FR-003**: Every one of the twelve allowed commit types MUST be accounted for by the shaping rules,
  and a type that is not MUST fall into the section of last resort rather than vanish. Features carries
  `feat`; fixes carries `fix`, `perf` and `revert`, since each is a change in behaviour a consumer feels;
  documentation carries `docs`; CI and dependencies carries `ci` and `build`; maintenance carries `chore`,
  `style`, `test` and `refactor`. `bump` is excluded per FR-004.
- **FR-004**: Version-bump commits MUST NOT appear in the notes.
- **FR-005**: A breaking change MUST appear in the breaking section carrying its explanatory text, and
  MUST also appear under the section for its own type.
- **FR-006**: The notes MUST be produced before any tag for the release exists, so that a failure to
  produce them leaves no tag behind.
- **FR-007**: A release MUST NOT publish empty notes. No release proposal may be raised for a range whose
  notes would be empty, and a release attempted over such a range MUST fail with an explicit error and
  create no tag.
- **FR-008**: The version being released MUST appear in a change that a human approves before it
  reaches a tag.
- **FR-009**: Approving the release proposal MUST be what creates the tag and publishes the release;
  no separate manual trigger may be required afterwards.
- **FR-009a**: An open release proposal MUST be refreshed whenever a new change lands on the default
  branch, so its notes always describe the current release range. The notes published MUST be derived at
  publication time from the same rules, not carried over from an earlier rendering. A version the reviewer
  has altered MUST survive every refresh — the refresh recomputes the notes, never a version a human has
  already decided.
- **FR-010**: The reviewer MUST be able to alter the proposed version before approving, and the
  released version MUST be the approved one.
- **FR-011**: A release MUST refuse to proceed unless the required continuous-integration verdict
  passed on the exact commit being released, and MUST name the missing verdict when it refuses. It MUST
  begin only once that verdict has been reported for the commit approval produced, so approval is never
  followed by a failure that only means the verdict had not arrived yet.
- **FR-012**: A release MUST refuse a version that is not ahead of every existing released version.
- **FR-012a**: A release MUST refuse a version that is not a new major when the range being released
  contains a breaking change, since publishing it would move the existing major tag onto a broken
  contract.
- **FR-013**: The moving major tag MUST point at the released commit once a release is published, and
  MUST be created if it does not yet exist.
- **FR-014**: The release path MUST NOT write a credential anywhere a later step could read it.
- **FR-015**: The notes MUST be reproducible from a local checkout with no network access.
- **FR-016**: Already-published releases MUST be left exactly as they are.
- **FR-017**: Once this ships, the label-driven notes configuration MUST no longer exist, so that
  nothing reads labels and no one maintains a file with no effect.

### Key Entities

- **Release range**: the commits between the previously released version and the one being released.
  What the notes describe.
- **Section**: one heading in the notes, fixed in title and position, into which changes are placed by
  the type of their commit.
- **Breaking explanation**: the text a change carries describing what it breaks, distinct from the
  change's one-line summary.
- **Release proposal**: the reviewable statement of a version and the notes that version would
  publish. Approving it is the release.
- **Moving major tag**: the reference consumers pin, repointed at each release.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For every historical release range, each commit in the range appears exactly once in the
  rendered notes, except version-bump commits, which appear zero times.
- **SC-002**: The breaking change shipped in v2.0.0 appears under the breaking section with its
  explanatory text. Today it appears under the section of last resort.
- **SC-003**: The count of pull request labels required for a correctly categorised release is zero.
  All nine historically unlabelled pull requests categorise correctly.
- **SC-004**: The number of manual steps to cut a release falls from three — edit a version, merge it,
  trigger a release — to one: approve a proposal.
- **SC-005**: A failure while producing the notes results in zero tags created. Today the same failure
  leaves one tag with no release attached.
- **SC-006**: The notes for any range can be produced on a local checkout with networking disabled,
  and match what a release over that range publishes.
- **SC-007**: No section heading in a published release reads as a raw commit type rather than one of
  the seven intended titles.

## Cross-Repository Impact

The constitution requires this section for a change to a reusable workflow or composite action.
**It does not apply here, and that is a claim this spec makes rather than an omission**: everything in
scope is repository-local. The release path is not callable — no consumer resolves it — and nothing
under the consumer-facing surface changes. `docs/consumers.md` needs no edit, no interface moves, every
existing call site keeps working untouched, and no consumer migrates in any order.

Rollback is deleting one configuration file and restoring the previous release step; no consumer is
involved either way.

The sibling change that *does* touch a reusable workflow — replacing the pull request title check — is
deliberately a separate feature for exactly this reason, and owes this section in full.

## Out of Scope

- **The pull request title check.** A sibling feature, separated because it changes a reusable workflow
  and reduces a permission every consumer grants — a different blast radius, owing the
  cross-repository section this one does not.
- **Replacing what validates commit messages**, either locally or in continuous integration. Only what
  *reads* the commits to shape notes is in scope.
- **Regenerating the notes of already-published releases**, covered by FR-016. Their notes are
  published as they are.
- **A changelog file kept in the repository.** The release body is the artifact; a committed file would
  be a second copy of the same facts to hold in step.
- **Changing which commit types are allowed**, or their meanings. The twelve are declared elsewhere and
  this feature consumes that declaration rather than editing it.
- **Changing the version numbering policy** — what makes a release a patch rather than a minor stays a
  human judgement about the consumer-facing surface. FR-012a adds a refusal, not a policy: it stops a
  breaking range shipping under a moved major tag without deciding any other increment.

## Assumptions

- **Squash merging stays the merge method**, so each commit on the default branch carries a validated
  Conventional Commit summary taken from its pull request title. The notes' quality rests on this.
- **Both commit checks stay required**, so a commit reaching the default branch has one of the twelve
  allowed types. The section of last resort is a safety net, not an expected path.
- **The seven section titles stay as they are today.** Changing them would change how every release
  reads and is a separate decision.
- **Version-bump commits are identifiable by their commit type.** The most recent one uses the `bump`
  type; the two before it did not, so historical ranges may still show a version commit under
  maintenance, and only ranges from here forward are fully clean.
- **What mechanism raises and refreshes the release proposal is a plan-phase decision**, not a
  requirement here. This spec constrains only that a proposal exists, shows the version and the notes,
  refreshes as the range changes (FR-009a), and that approving it releases.
- **Consumers keep pinning the moving major tag**, so repointing it remains part of publishing a
  release regardless of what produces the notes.
- **The audience for the notes is a maintainer of a consuming repository**, not an end user. One human
  and one bot have authored every change here, so authorship credit in the notes carries little value.
