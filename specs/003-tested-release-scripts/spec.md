# Feature Specification: Tested Release Scripts

**Feature Branch**: `003-tested-release-scripts`

**Created**: 2026-09-06

**Status**: Draft

**Input**: Issue [#61](https://github.com/turboBasic/github-actions/issues/61) — "chore: move the release
workflows' wall of shell into tested Python scripts", plus its comment on the surface-path list.

**Supersedes / relates to**: [`002-commit-driven-releases`](../002-commit-driven-releases/spec.md) built
the release path this specification makes testable. Nothing about the shape it chose changes here.

## Why this has a spec at all

By `docs/ai-instructions.md`'s size table this is issue → PR: no observable behaviour changes. It is
specified anyway because it rewrites the path that moves the major tag, and because `release.yml` is a
`workflow_call` workflow with a real external call site — which puts it under the constitution's
**Cross-Repository Impact** gate. That gate is answered below, and its answer is "one consumer, no
interface delta", which is the claim most worth writing down and holding a reviewer to.

That call site is the fact the gate turns on. `docs/consumers.md` records `github-actions-test` pinning
`@v4` and calling `release`, and being *the only place* the `release / tag-and-publish` check context
reports at all. So there are two call sites, one of them external, and a job rename here would retire a
required context in another repository. The blast radius is small but it is not empty, and the
requirements below are written against it.

Making the surface-path list a `workflow_call` input — raised in #61's comment — is **out of scope**. It
is a new input on a reusable workflow, so it is consumer-facing contract surface and owns its own
specification. This one changes nothing a caller can see.

## User Scenarios & Testing *(mandatory)*

The actor throughout is a **maintainer of this repository**. There is no external user: the release path
is plumbing, and its only consumer is the person who has to trust it.

### User Story 1 - Prove a release decision offline (Priority: P1)

A maintainer changes how the next version is chosen, or how "these notes are empty" is decided, and wants
to know it is right before it runs on `main`. Today the only way to find out is to dispatch a dry run, or
to merge and watch the tag move. Every decision the release path makes is spelled in shell inside a YAML
block scalar, and the offline suite can only assert that certain text is present in the file.

**Why this priority**: This is the whole point of the change, and it is the story that both real defects
in #61 came from. `gh: Argument list too long` and the empty-notes refusal testing size instead of content
each passed every linter and each shipped. Neither could have survived a unit test, and neither had one
available to write.

**Independent Test**: Land the decisions as tested pure functions and nothing else — no workflow is
rewired. `mise run ci` proves every one of them offline, and both workflows keep their shell and keep
working. Value delivered: the rules most often argued about become decidable without GitHub, and the
release path is untouched, so this ships on its own.

**Acceptance Scenarios**:

1. **Given** a current version and the verdicts "breaking: yes", **When** the next version is computed,
   **Then** the result is the next major with minor and patch zeroed, and a test asserts it offline.
2. **Given** a current version and the verdicts "breaking: no, feature: yes", **When** the next version is
   computed, **Then** the result is the next minor with patch zeroed.
3. **Given** a current version and neither verdict, **When** the next version is computed, **Then** the
   result is the next patch.
4. **Given** a rendered notes body holding only whitespace — including the single trailing newline
   git-cliff emits for an empty range — **When** emptiness is decided, **Then** it is reported empty, and
   a test covers the one-byte case by name.
5. **Given** a `--context` payload whose commits carry no `breaking` key at all, **When** the breaking
   verdict is read, **Then** it is `false` rather than an error or a true-ish null.

---

### User Story 2 - See the decisions in the path (Priority: P2)

A maintainer reviewing a change to `release.yml` or `release-proposal.yml` needs to see what the workflow
decides. Today shell quoting, `${{ }}` interpolation and YAML block-scalar rules stack in the same lines,
across roughly 154 and 147 lines of shell, and the reviewer has to hold all three grammars at once to
answer "would this refuse the right release".

**Why this priority**: Real, but it follows P1 rather than standing beside it. Readability without tests
is taste; tests without readability still catch defects.

**Independent Test**: After the extraction, each workflow step that used to carry a wall of shell reads as
a named invocation with its arguments arriving through `env`. A reviewer can name every decision the step
makes from the step alone.

**Acceptance Scenarios**:

1. **Given** the extracted release path, **When** a maintainer opens `release.yml`, **Then** every
   remaining `run:` block is plumbing — an invocation, an API call, a write to `GITHUB_OUTPUT` — and no
   `run:` block contains a comparison, an arithmetic increment, or a version parse.
2. **Given** a decision that refuses a release, **When** it refuses, **Then** the message a maintainer
   reads in the run log says the same thing it says today.

---

### User Story 3 - One definition of the consumer surface (Priority: P3)

The include/exclude path list that defines "what a consumer resolves" is currently written out in both
`release.yml` and `release-proposal.yml`, identically. The two halves disagreeing about what "breaking"
means once deadlocked a release ([#62](https://github.com/turboBasic/github-actions/issues/62)), which is
why [#90](https://github.com/turboBasic/github-actions/pull/90) put the same list in both places. A test
holds both copies to `OWN_CI` so they cannot drift, but the copies are still copies.

**Why this priority**: The drift is already fenced by a test, so this is tidying rather than repair. It
rides along because the extraction touches exactly these lines anyway.

**Independent Test**: The list has one definition. Deleting a workflow from `OWN_CI` and running the
offline suite fails, as it does today.

**Acceptance Scenarios**:

1. **Given** the extracted surface definition, **When** a maintainer searches the two workflows for an
   `--include-path` or `--exclude-path` flag, **Then** neither workflow spells the list.
2. **Given** the surface definition and `OWN_CI`, **When** the offline suite runs, **Then** a disagreement
   between them fails a test, and the failure names both lists.
3. **Given** `release.yml`'s two range reads, **When** the notes are rendered, **Then** the range is
   unfiltered; **and when** the breaking verdict is taken, **Then** the range is surface-filtered. The two
   reads stay distinct.

---

### Edge Cases

- **An empty render is one byte, not zero.** git-cliff emits a trailing newline for a range holding
  nothing and for a range holding only a `bump:`, and exits 0 in both cases. Emptiness is a content
  question. A size test and an exit-code test are both wrong, and each has already been wrong here.
- **`--context` omits `breaking` on a non-Conventional commit.** The key is absent, not `false`. A
  truthiness test on the absent value answers wrongly.
- **No version tags exist at all.** The "ahead of the highest release" comparison has nothing to compare
  against and must permit the release rather than refuse it or fail.
- **The declared version is not a plain `N.N.N`.** Refused, before anything is tagged.
- **The declared version equals or trails the highest release.** Three different verdicts for one
  condition, keyed on who asked: a notice-and-stop on a push to `main`, a reported-but-continue under a
  dry run, an error under a real dispatch. The distinction survives the extraction intact.
- **A range breaks the consumer surface under a non-major version.** Refused, before anything is tagged,
  and only when a highest major exists to be moved onto.
- **A blob's base64 exceeds Linux's 128 KiB single-argument cap.** `uv.lock` does. The code path that
  works around this is plumbing and stays as it is; it is named here so the extraction does not
  accidentally route it back through an argument.
- **A reviewer has edited the proposed version.** Authorship on the proposal branch decides, and a
  human's number outranks a computed one through every later refresh. Unchanged.

## Requirements *(mandatory)*

### Functional Requirements

**What moves out of shell.** Each of these is a decision with one right answer for given inputs, and each
gets tests:

- **FR-001**: The next version MUST be derived from a current version plus a breaking verdict and a feature
  verdict, as one testable decision, together with the reason string a maintainer reads.
- **FR-002**: Whether a rendered notes body is empty MUST be decided on content — any non-whitespace
  character — never on file size and never on an exit code.
- **FR-003**: The declared version MUST be read from `pyproject.toml` as TOML, keyed by table, never by
  matching the first `version =` line.
- **FR-004**: The refusal ladder's comparisons MUST each be a separately testable decision, with its own
  function and its own tests: (a) that a version is a plain three-part semantic version; (b) that it is
  strictly ahead of the highest existing release; (c) that a breaking range is not being published under a
  non-major bump, which is `False` when no highest major exists to be moved onto.
- **FR-005**: The breaking and feature verdicts MUST be derived from a rendered `--context` payload as a
  testable decision, replacing the inline `jq` filters, and MUST treat an absent `breaking` key as false.
- **FR-006**: The consumer-surface path list MUST have exactly one definition, read by both
  surface-filtered range reads — `release.yml`'s breaking check and `release-proposal.yml`'s increment.
  `release.yml`'s notes render stays deliberately unfiltered and reads no list at all.

**What stays as shell.** Named as requirements because the boundary is the scope:

- **FR-007**: Plumbing already one line per call MUST stay in the workflow: `git-cliff` invocations, `gh`
  and `gh api` calls, `uv version`, and writes to `GITHUB_OUTPUT` and `GITHUB_STEP_SUMMARY`.
- **FR-008**: `conventional-commits.yml`, `python-ci.yml`, `actions/populate-pr-description` and
  `actions/prek-advisory-pr` MUST NOT be touched. Inline shell up to about a screen is fine, and the two
  workflows are consumer-facing besides.

**What must not change:**

- **FR-009**: No `workflow_call` input, output, secret or permission of either workflow may change. All
  three routes into `release.yml` — `ci.yml`'s self-call, `github-actions-test`'s call at `@v4`, and the
  dispatch route — MUST work untouched.
- **FR-009a**: The job name `tag-and-publish` MUST NOT change, and neither may `propose`. Renaming
  `tag-and-publish` retires the `release / tag-and-publish` context that `github-actions-test` reports,
  and a required context that stops reporting blocks every pull request in that repository until its own
  ruleset is edited — which no ref can do for it. A rename here would be a major bump, which this change
  is not.
- **FR-010**: Every refusal MUST refuse the same cases it refuses today, and MUST report them with a
  message of the same meaning.
- **FR-011**: An extracted script MUST receive its arguments from the environment, declared alongside the
  step. No `${{ }}` interpolation may reach a script's argument list or a shell line, so that a commit
  subject — which is a merged pull request title, and attacker-influenceable — stays data.

**How the extraction is delivered:**

- **FR-012**: Extracted logic MUST be importable by the offline test suite with no path manipulation
  inside a test file.
- **FR-013**: Extracted logic MUST resolve statically under the project's existing strict type checking,
  with no loosened mode and no blanket suppression.
- **FR-014**: Extracted logic MUST be standard-library-only. A third-party dependency would have to be
  declared twice — once for the script's own execution, once for the suite that imports it — and would put
  the offline suite on the network.
- **FR-015**: `[project].dependencies` MUST stay empty. Nothing is published from this repository.
- **FR-016**: `docs/ai-instructions.md`'s statement that the Python here exists only to test the YAML
  MUST be corrected in the same change, along with any other documentation the change falsifies.
- **FR-017**: Every existing gate that asserts the text of the removed shell MUST be rewritten against the
  new form or retired with its reason stated, in the stage that breaks it. Four are known —
  `test_the_surface_filter_agrees_with_own_ci`,
  `test_only_a_breaking_change_to_the_surface_refuses_a_release`,
  `test_the_release_refuses_notes_with_no_content` and the `_surface_flags` helper. A gate that vanishes
  because nobody noticed it fail is what Principle VII forbids.
- **FR-018**: No reference may be pinned to a branch and no gate may be relaxed to deliver this. That
  forces two releases: `release.yml`'s `uses: …@v4` cannot be introduced before a release exists whose tree
  contains the action, or `v4` resolves to a tree without it and the release job cannot start.

### Key Entities

- **Declared version** — the `[project].version` in the tree being released. The single input to the
  patch-vs-minor-vs-major decision that a human writes by hand.
- **Highest release** — the greatest plain three-part version among existing tags, across all majors,
  because a frozen major is never backported. Absent when nothing has been released.
- **Release range** — the commits between the newest version tag and the commit being released. Read twice
  and differently: whole, for the notes; surface-filtered, for the breaking verdict.
- **Consumer surface** — the paths a consumer resolves: every reusable workflow and composite action, minus
  this repository's own plumbing. Currently two identical lists; becomes one.
- **Verdicts** — the breaking and feature booleans taken from the surface-filtered range. The only inputs
  to the increment besides the declared version.
- **Rendered notes** — the body a release or proposal publishes. Emptiness is a property of its content.

## Cross-Repository Impact *(constitution gate)*

`release.yml` is a `workflow_call` workflow with an external call site, so this section is mandatory.

- **Affected consumers**: **`github-actions-test`**, which pins `@v4` and calls `release`. It is the only
  external caller, and the only place the `release / tag-and-publish` context reports. `release.yml` is
  also self-called by this repository's `ci.yml`. `release-proposal.yml` has no callers at all — it is
  `push`- and `dispatch`-triggered only, with no `workflow_call` trigger. Both files are in `OWN_CI`, which
  is why neither counts as consumer *surface* for the version increment; that is a different question from
  whether anything calls them, and #61 conflated the two.
- **Interface delta**: none on either workflow. `release.yml` keeps its single `dry-run` boolean input on
  both `workflow_call` and `workflow_dispatch`, its `contents: write` job permission, its `concurrency`
  group, and its `tag-and-publish` job name. No output, secret or permission changes. A reusable
  workflow's steps run in its own job, so what language they are written in is invisible to a caller.
  One artifact **is** added — the composite action the logic lives in, which the plan settles and
  [`contracts/action.md`](./contracts/action.md) specifies. Nothing outside `release.yml` calls it.
- **Compatibility**: both call sites keep working untouched, and `ci.yml`'s call block is byte-identical
  before and after. `github-actions-test` needs no edit — it passes no input and requires no context this
  change moves. No major bump is warranted; by the rule that the version describes the consumer-facing
  surface, and with both files in `OWN_CI`, this is a patch.
- **Rollout and rollback**: no consumer migrates. Rollback is a revert of one pull request — and because
  `github-actions-test` resolves `@v4`, a revert reaches it the moment the major tag moves back, with
  nothing to do on its side. Rollback of a *bad release* is the standing rule and is unchanged: bump to the
  next patch and merge, never re-run, because a version tag already created cannot be deleted by anyone.

**The trap is not hypothetical, and it decides the design.** `actions/checkout` inside a reusable
workflow checks out the **caller's** repository, so a file living in this repository is not on disk. This
paragraph originally recorded that as a cost for whoever *later* widened the change to a consumer-facing
workflow. It applies now: `release.yml` already has a cross-repo caller, which is why it reads
`github-actions-test`'s `pyproject.toml` and releases that repository. A `scripts/` directory here would
therefore break that call site outright — Principle I. The logic lives in a composite action instead,
whose repository Actions downloads independently of the workspace; the reasoning and the four rejected
alternatives are [`research.md` D1](./research.md#d1).

**This ships as two releases, and that is a constraint rather than a preference.** `release.yml`'s
`uses: …@v4` cannot be introduced in the release that introduces the action: at the merge commit `v4` still
points at a tree without it, so the job fails to start, so `v4` never moves — a deadlock, not a retry.
Pinning the branch instead fails `test_first_party_actions_use_the_major_tag`, and relaxing that gate is
Principle VII. So stage 1 ships the complete action plus `release-proposal.yml`, which needs no `uses:`
because it invokes the module by in-repo path and only ever runs here; stage 2 rewires `release.yml` once
`v4` resolves. [`research.md` D9](./research.md#d9).

**The verification order follows from it.** `ci.yml`'s `$/` self-call resolves at the merge commit, so each
merge cuts this repository's own release with the new code — against tags a ruleset makes undeletable.
`github-actions-test`'s cost nothing, so it is repointed at the stage-2 branch and spends a disposable tag
first. [`research.md` D7](./research.md#d7) and [`quickstart.md`](./quickstart.md) hold the ladder.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every decision named in FR-001 through FR-006 has at least one test that fails if the
  decision is inverted, and those tests run with no network access.
- **SC-002**: The empty-render case is covered by a test that asserts a body of exactly one newline is
  empty, and the absent-`breaking`-key case by a test that asserts the verdict is false. Both are the
  defects that shipped; both fail if the old form is restored.
- **SC-003**: Neither `release.yml` nor `release-proposal.yml` contains a `run:` block holding a
  comparison, an arithmetic increment, a version parse, or a `jq` filter over commit data. Each file's
  total shell drops to plumbing only — from roughly 154 and 147 lines to a small fraction of that.
- **SC-004**: The include/exclude surface list appears once in the tree outside `OWN_CI`,
  `CONTRIBUTING.md` and the test that holds them together — down from a copy in each of the two
  workflows.
- **SC-005**: `mise run ci` passes offline, with strict type checking clean and no rule disabled or
  suppression added to get there.
- **SC-006**: A dry-run dispatch of `release.yml` from a branch renders the same notes and reports the
  same refusals as the same dispatch does before the change.
- **SC-007**: A real release cut in `github-actions-test` publishes a release, moves the major tag, and
  leaves no tag behind on a failure — verified by invocation, not by lint. It is met by repointing that
  repository at the **stage-2** branch and cutting a release there before this repository's `main` does.
  Not met by lint, and not by the self-call alone.
- **SC-008**: `release / tag-and-publish` still reports in `github-actions-test` after the change, under
  that exact name.
- **SC-009**: A maintainer can state, from a single workflow step, every decision that step makes.
- **SC-010**: Delivered without a branch-pinned reference and without a relaxed gate. At every commit on
  both branches, `test_first_party_actions_use_the_major_tag` passes unmodified.
- **SC-011**: Each of FR-017's four gates either asserts the new form or is gone with its reason recorded.
  None is left failing, and none is deleted silently.

## Assumptions

- **The actor is a maintainer of this repository.** There is no end user in this feature; "user value" is
  a maintainer's ability to change the release path without fear.
- **Behaviour is meant to be identical.** Any behaviour difference discovered during the work is a defect
  in this change, not an improvement, unless it is one of the two defects #61 names — where today's
  behaviour is the defect.
- **The surface-path list stays hardcoded to this repository's layout.** Making it an input is
  consumer-facing contract surface and belongs to its own specification. Until then `README.md`'s
  `release.yml` section documents what writing them in costs a caller.
- **`release.yml`'s two range reads stay two reads.** One definition of the surface, called twice with
  different arguments — not one call, and not one range.
- **`OWN_CI` remains the authority on which workflows are this repository's own plumbing.** The surface
  definition is held to it, not the other way round.
- **`github-actions-test` remains available** as the repository where a real release can be cut for
  nothing, and remains the only external caller of `release.yml`. Without it, SC-007 and SC-008 have no
  route. If `docs/consumers.md` gains another caller of `release` before this lands, the blast radius above
  is recomputed rather than assumed.
- **The project's existing offline-suite constraint holds.** `mise run ci` must never need the network,
  which is what makes FR-014's standard-library-only rule load-bearing rather than stylistic.
- **The delivery shape is settled, and it is not the one #61 proposed.** `scripts/` at the repository root
  cannot work for `release.yml`, per the trap above. The logic lives in a composite action under
  `actions/`, invoked by `release.yml` through `uses:` and by `release-proposal.yml` by in-repo path, since
  that workflow only ever runs here. FR-012 through FR-015 still state what the shape must satisfy, and it
  does: measured, `pythonpath` and `extraPaths` are both required and sufficient, and `python3` suffices at
  runtime because the logic is standard-library-only. [`research.md`](./research.md) D1 through D4.
