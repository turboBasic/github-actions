# Tasks: Commit-driven releases

**Input**: Design documents from `/specs/002-commit-driven-releases/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md),
[data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md)

**Tests**: included. `tests/test_release_notes.py` is named in plan.md's structure and its assertions
are specified in [contracts/release-notes.md](contracts/release-notes.md) — it is part of the
deliverable, not an optional TDD extra.

**Organization**: by user story, so each ships and is verified on its own. US1 delivers commit-driven
notes under the existing manual dispatch; US2 replaces the trigger with a proposal; US3 adds the local
preview.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependencies)
- **[Story]**: US1, US2, US3
- Exact file paths in every description

## Path Conventions

Repository root. No `src/`, no new Python package — `.cliff.toml` at the root, workflows under
`.github/workflows/`, tests in `tests/`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: the tool pin and the out-of-band credential, both of which have lead time.

- [x] T001 Add `git-cliff = "2.13.1"` to `mise.toml`'s `[tools]` table, alphabetically after
      `actionlint`. The bare registry short name, which resolves to `aqua:orhun/git-cliff`, so
      Renovate's `mise` manager tracks it. Not `latest` —
      `tests/test_action_pins.py::test_no_mise_tool_version_floats` rejects it.
- [x] T002 Run `mise install` and confirm `git-cliff --version` prints 2.13.1 — every behaviour the
      contracts record was observed against that binary, and `mise` resolves 2.13.1 even though
      2.14.1 is published (research.md, "Corrected while checking").
- [x] T003 [P] Add the words this feature introduces to `.cspell/project.txt` — `cliff`, `Tera`,
      `postprocessors`, `revspec`, `unreleased` and any others `cspell lint --no-progress .` reports
      once the files below exist. Re-run it rather than guessing the list.
- [x] T004 [P] **Out of band, one-off, not expressible in this repository**: register a **new** private
      GitHub App under the `turboBasic` account — `turbobasic-release-proposal` — with
      `Contents: Read and write` and `Pull requests: Read and write` and nothing else, no webhook,
      installed on `turboBasic/github-actions` alone. Store its id and private key as Actions secrets
      named **`RELEASE_APP_ID`** and **`RELEASE_APP_PRIVATE_KEY`** — the names T032 reads, and a typo
      in either yields an empty token and no proposal, silently. Delete the downloaded `.pem` once the
      secret is set; a private key on disk is a secret persisting (Principle V).
      **Do not reuse either app that already exists.** `turboBasic` owns two:
      `turbobasic-repo-automation` (public, installed on the `cargonautica` org) holds
      `administration`, `organization_administration`, `members` and `workflows` write, so its key
      could rewrite the `main` ruleset and every workflow here; `popcircles-agent` (private, installed
      for `PopulationCircles2026`) is close on permissions but is a comment-triggered coding agent, and
      one app means one key — adding this repository to its installation would give that agent write
      access to the CI every consumer resolves, and make this repository's secret a key to
      `PopulationCircles2026`. `create-github-app-token` can narrow the *token*; nothing narrows the
      key. A dedicated app is the only option that keeps Principle III's claim true.
      Leave *Settings → Actions → General → "Allow GitHub Actions to create and approve pull
      requests"* **off** (research.md decision 11); `gh api
      repos/turboBasic/github-actions/actions/permissions/workflow` confirms it, and read
      `can_approve_pull_request_reviews: false`. **There is no API check for the installation itself**
      — `gh api repos/{owner}/{repo}/installation` answers `401 A JSON web token could not be decoded`
      to a user token, since it authenticates as the app. Read
      <https://github.com/settings/installations> instead; the real proof is
      `create-github-app-token` succeeding in T047. Blocks Phase 4 only — Phase 3 needs none of it.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: `.cliff.toml`, the one shaping rule all three stories read. Nothing below it works
without it.

**⚠️ CRITICAL**: no user story work can begin until this phase is complete.

- [x] T005 Create `.cliff.toml` at the repository root by **copying** the verified configuration from
      [contracts/release-notes.md](contracts/release-notes.md)'s appendix verbatim. Do not retype it —
      every behaviour the contract asserts was observed from exactly those bytes, and this repo's own
      rule is that a retyping tests the typing.
- [x] T006 Add a header comment to `.cliff.toml` naming the file and warning that `git-cliff --init`
      writes the non-dotted `cliff.toml`, which would win on name and become a rival config
      (research.md decision 1). No `--config` flag is used anywhere, so discovery is what finds this
      file.
- [x] T007 In `.cliff.toml`'s `body` template, squeeze the double space that collapsing a paragraph
      break leaves in a long breaking-change footer (quickstart.md stage 2, and
      contracts/release-notes.md's "still owed" list). Keep the `'''` literal string — a basic string
      would make `pat="\n"` a TOML escape before Tera ever sees it (research.md decision 3).
      **Done as `split(pat="\n\n") | first`**, which also fixes what running it exposed: a
      `BREAKING CHANGE:` footer's value runs to the next footer-looking line, so every rationale
      paragraph after it lands in the bullet. v2.0.0's stopped early only because a body line began
      `advisory-all-files:` and the parser read that as a new footer. Taking the first paragraph yields
      the "what broke" sentence and leaves the reasoning in the commit, where it belongs.
- [x] T008 Run `taplo fmt` and `mise exec -- prek run --all-files`, and commit taplo's reformatting of
      `.cliff.toml` rather than fighting it. `check-toml` and `taplo-fmt` both collect the dotfile —
      verified in research.md decision 1.

**Checkpoint**: `git-cliff --unreleased` renders from `.cliff.toml` on a full clone. Both stories that
depend on the rendering can now proceed.

---

## Phase 3: US1 - A consumer can tell what changed, and what broke (P1) 🎯 MVP

**Goal**: the notes a release publishes are derived from commit types, with the breaking change in the
breaking section carrying its explanatory text — and rendered *before* any tag exists, so a failure
leaves nothing behind. The trigger stays today's manual dispatch.

**Independent Test**: render `v1.0.1..v2.0.0` and confirm the breaking change appears under 💥
Breaking changes with its footer text and again under 🚀 Features; walk every historical range and
confirm each commit appears once, `bump` commits zero times. Then dispatch `release.yml` with
`dry-run: true` and confirm the real notes render with `git tag --list` unchanged.

### Tests for User Story 1

- [x] T009 [US1] Create `tests/test_release_notes.py` asserting `.cliff.toml`'s mapping offline, by
      reading it with `tomllib` and never invoking git-cliff (so `mise run ci` still passes on a
      shallow clone). **Five** assertions, specified in
      [contracts/release-notes.md](contracts/release-notes.md)'s "The mapping, and what holds it":
      every one of the twelve allowed types placed in a group or explicitly skipped; the seven titles
      exactly [data-model.md](data-model.md)'s, in that order; `bump` the only skipped type; the
      catch-all parser last, since `commit_parsers` is first-match-wins; and `tag_pattern` still
      excluding two-component tags. Read the twelve types from `conventional-commits.yml`'s `types`
      default the way `test_allowed_types_match_the_commitizen_builtin_set` already does, not from a
      second literal list. The sixth assertion — the surface path filter against `OWN_CI` — is
      **T035a**, in Phase 4: that filter is a set of CLI flags in `release-proposal.yml`, so it has no
      subject until that file exists and it reads YAML rather than TOML.
- [x] T010 [US1] Add a gate to `tests/test_action_pins.py` asserting `release.yml` decides "the notes
      are empty" from the **file's size**, not from git-cliff's exit code. An empty range exits 0 with
      zero bytes and no warning, indistinguishably from a range holding only a `bump`
      (research.md decision 2), so a workflow trusting the exit code publishes an empty release body —
      exactly what FR-007 forbids and no linter would notice.

### Implementation for User Story 1

- [x] T011 [US1] In `.github/workflows/release.yml`, add the checkout the rendering needs:
      `actions/checkout` at the existing pinned SHA with `fetch-depth: 0` and
      `persist-credentials: false`, checking out the commit being released. Full history and tags,
      because git-cliff needs the range's lower bound; no credential, because nothing is pushed from
      the working tree and zizmor's `artipacked` audit must stay clean (FR-014, Principle V).
- [x] T012 [US1] In `.github/workflows/release.yml`, add `jdx/mise-action` at the SHA this repo already
      pins, so `git-cliff` comes from the `mise.toml` pin rather than a second install path.
- [x] T013 [US1] In `.github/workflows/release.yml`, render the notes to a file with
      `git-cliff --unreleased` **before** the first `gh api` call that creates a ref (FR-006). No
      `--config`, no `--tag`; a non-zero exit is a hard error — a bad range or a bad config — and is
      handled separately from the zero-exit empty case below (research.md decision 2).
- [x] T014 [US1] In `.github/workflows/release.yml`, refuse with an explicit error when the rendered
      notes file is zero bytes (FR-007), before any tag exists.
- [x] T015 [US1] In `.github/workflows/release.yml`, refuse when the range contains a breaking change
      and the version is not a new major (FR-012a), using
      `git-cliff --unreleased --context | jq 'any(.[].commits[]; .breaking == true)'`. `== true` and
      not truthiness: the key is **absent**, not `false`, on a commit matching no Conventional Commit,
      and a `null` in a boolean test is how this reaches production as a wrong answer
      (data-model.md, Commit). `jq` is pre-installed on `ubuntu-latest` and needs no pin.
- [x] T016 [US1] In `.github/workflows/release.yml`, replace `--generate-notes` with
      `--notes-file` reading the rendered file, and drop `--notes-start-tag` and the `notes_from`
      array — the range is git-cliff's concern now. No commit text is interpolated into a `run:` line;
      `gh` reads the file (Principle IV).
- [x] T017 [US1] In `.github/workflows/release.yml`, add the `workflow_dispatch` input
      `dry-run` (`type: boolean`, `default: false`) which runs every refusal and renders the real
      notes to `GITHUB_STEP_SUMMARY`, then exits 0 before the first ref is created. This is the
      Principle VI mitigation for everything above.
- [x] T018 [US1] In `.github/workflows/release.yml`, relax the `refs/heads/main` refusal so a
      `dry-run` dispatch from a feature branch is permitted while a real release from anywhere but
      `main` still refuses. Without this the dry run cannot execute at the ref under review, which is
      the whole point of T017. **The "not ahead of the highest release" refusal also had to become a
      notice under `dry-run`**, which the plan did not foresee: on a feature branch the declared
      version *is* the released one by definition, so erroring there stopped every dry run before it
      rendered anything. That refusal is unchanged code which has already run in earnest, so reporting
      it leaves nothing new unverified.
- [x] T019 [US1] Delete `.github/release.yml`, the label-driven notes configuration (FR-017). Nothing
      reads labels afterwards and nobody maintains a file with no effect.
- [x] T020 [US1] Remove the `check-release-config` hook from `.pre-commit-config.yaml` — its only
      target was the file T019 deletes.
- [x] T021 [US1] Remove the
      `check-jsonschema --schemafile https://www.schemastore.org/github-release-config.json` line from
      `mise.toml`'s `lint` task. That retires one of the task's two network fetches. Leave the
      `actionlint.json` schemafile line alone — it is load-bearing (actionlint ignores an unknown key
      silently).
- [x] T022 [US1] Rewrite the header comment of `.github/workflows/release.yml`: it currently says the
      release publishes "the release notes `.github/release.yml` shapes", that "Nothing is cloned",
      and closes on a "Not `.github/release.yml`" disambiguation — all three now false. State instead
      that notes are rendered from commits by `.cliff.toml` before any tag exists, and that the
      checkout carries no credential.
- [x] T023 [US1] Correct `CONTRIBUTING.md`'s Releasing step 2, which states the release "publishes the
      release with notes generated from `.github/release.yml`" (research.md, Constraints). The rest of
      that section is rewritten in Phase 4; this task fixes only the claim US1 falsifies.

### Verification for User Story 1

- [x] T024 [US1] **SC-002** — run `git-cliff v1.0.1..v2.0.0` on a full clone and confirm the breaking
      change appears under 💥 Breaking changes *with its footer text* and again under 🚀 Features.
      Note the previous tag is `v1.0.1`; there is no `v1.1.0`, and a nonexistent revspec exits 1.
      Expected output is recorded in quickstart.md stage 2.
- [x] T025 [US1] **SC-001 and SC-007** — run quickstart.md stage 2's loop over every historical
      version-tag pair and confirm the bullet and commit counts match, `v1.0.1..v2.0.0` being over by
      exactly one (FR-005 counting the breaking change twice). Skim the headings: every one must be
      one of the seven titles, none a raw commit type.
- [ ] T026 [US1] Dispatch `release.yml` from this branch with `dry-run: true` and confirm the rendered
      notes appear in the step summary and `git tag --list` is **unchanged**. Pre-flight the exact
      lines out of the file, never a retyping of them.
- [ ] T027 [US1] Dispatch `release.yml` with `dry-run: true` over a range holding only a `bump` and
      confirm an explicit error with no tag created (FR-007, SC-005).

**Checkpoint**: a manual dispatch now publishes commit-derived notes, and a failure while producing
them leaves no tag. The categorisation fix is complete and shippable on its own.

---

## Phase 4: User Story 2 - Release by approving, not by assembling (Priority: P2)

**Goal**: a proposal pull request carries the version and the notes it would publish; merging it is
the approval, and the release fires by itself once `ci / CI` reports green on the merge commit.

**Independent Test**: with T046a's temporary trigger in place, push to this branch — a
`release-proposal` branch and a pull request appear, body equal to the rendered notes, diff limited to
`pyproject.toml` and `uv.lock`. Edit the version on the proposal branch, push again, and confirm the
body refreshes while the edited version stands.

**Depends on**: Phase 3 (a proposal is only worth reviewing if the notes in it are correct) and T004.

### Tests for User Story 2

- [ ] T028 [US2] Add `"release-proposal.yml"` to `OWN_CI` in `tests/test_action_pins.py`. Without it
      `test_every_reusable_workflow_declares_workflow_call` fails the new workflow and
      `test_no_consumer_facing_change_is_waiting_for_a_release` demands a release for it
      (research.md, Constraints). T035a then holds the path filter to this same list.
- [ ] T029 [US2] Add a gate to `tests/test_action_pins.py` asserting `release.yml` takes the target
      commit from `github.event.workflow_run.head_sha` and not from `github.sha`. Under
      `workflow_run`, `GITHUB_SHA` is the default branch's tip, not the commit CI reported on
      (research.md decision 7), so getting this wrong releases a different tree than the one that
      passed — with every linter green.

### Implementation for User Story 2

- [ ] T030 [US2] Create `.github/workflows/release-proposal.yml` with the trigger block from
      [contracts/workflow-triggers.md](contracts/workflow-triggers.md): `push: branches: [main]` plus
      `workflow_dispatch` — for recovery and re-running a refresh by hand, **not** for pre-merge
      verification, which it cannot do (T046a) — top-level `permissions: {}`, and
      `concurrency: { group: release-proposal, cancel-in-progress: true }` — only the newest range
      matters. `timeout-minutes` on the job, which the `check-workflow-timeouts` hook requires.
- [ ] T031 [US2] In `release-proposal.yml`, give the job `contents: read` for `GITHUB_TOKEN` — it only
      checks out. No `pull-requests: write`, no `issues: write`; every write uses the App token
      (Principle III, research.md decision 11).
- [ ] T032 [US2] In `release-proposal.yml`, add
      `actions/create-github-app-token@bcd2ba49218906704ab6c1aa796996da409d3eb1 # v3.2.0` as the first
      step, fed `secrets.RELEASE_APP_ID` and `secrets.RELEASE_APP_PRIVATE_KEY` (T004), and pass its
      output token as `GH_TOKEN` through `env` to every later step. Never to a file, a log or an
      artifact (FR-014, Principle V).
- [ ] T033 [US2] In `release-proposal.yml`, add `actions/checkout` at `fetch-depth: 0` with
      `persist-credentials: false`, and deliberately **not** the app token — nothing is pushed from
      the working tree. Then `jdx/mise-action`, which supplies both `git-cliff` and `uv` from
      `mise.toml`.
- [ ] T034 [US2] In `release-proposal.yml`, implement the two skip conditions in order: exit 0 when the
      `[project].version` declared **on `main`'s tip** is not yet tagged (a release is already in flight
      or owed, and proposing on top would propose the version being cut); and when the rendered notes
      are empty, close any open proposal, delete the branch and exit 0 (FR-007). Read the version as
      TOML, not as the first line matching `version =`, the way `release.yml` already does. The ref is
      load-bearing: read it from the `release-proposal` branch instead and this finds its own bump,
      concludes a release is in flight, and stops refreshing the proposal it just wrote — FR-009a
      stalling silently.
- [ ] T035 [US2] In `release-proposal.yml`, compute the proposed version: highest existing release
      incremented by what the **consumer-facing** commits imply — breaking gives major, a `feat`
      touching `.github/workflows/**` or `actions/**` minus this repo's own CI gives minor, else
      patch. A second `git-cliff --unreleased --context` pass with the `--include-path` /
      `--exclude-path` flags exactly as quickstart.md stage 3 records them (research.md decision 5).
      The exclude list is the fourth copy of `OWN_CI` and T035a holds it to the first.
- [ ] T035a [US2] Add the sixth assertion to `tests/test_release_notes.py`: the `--include-path` /
      `--exclude-path` filter in `release-proposal.yml` agrees with `OWN_CI` and `CONSUMER_FACING` in
      `tests/test_action_pins.py`, so the two machine-readable copies of that list cannot drift
      (research.md decision 9). Reads the workflow as YAML, unlike the five in T009 — which is why it
      lands here and not with them.
- [ ] T036 [US2] In `release-proposal.yml`, keep a human's version: if the `release-proposal` branch
      exists and holds a commit whose author is **not** the fixed bot identity, use the version
      already on the branch and re-render only the body (FR-009a). Otherwise take T035's computed
      version.
- [ ] T037 [US2] In `release-proposal.yml`, write the branch through the Git Data API — blob, blob,
      tree on `main`'s tree, commit, force-update `refs/heads/release-proposal` — setting the commit
      `author` **explicitly** to one fixed identity. Load-bearing, not cosmetic: an App-token commit
      is otherwise attributed to `<app-name>[bot]`, so T036's comparison needs a value this workflow
      chooses rather than one the token implies (research.md decision 11). Nothing is pushed from the
      working tree.
- [ ] T038 [US2] In `release-proposal.yml`, produce the second blob by running `uv lock` after the
      `pyproject.toml` version edit. Plain `uv lock`, not `--offline`: the runner has a network and
      FR-015's offline constraint is on rendering the notes, not on this step. `uv.lock` carries the
      root package's version, so a bump without it fails `uv sync --locked` (research.md decision 4).
      The diff is those two files and nothing else.
- [ ] T039 [US2] In `release-proposal.yml`, create or update the pull request into `main` with title
      and commit subject both `bump: release vX.Y.Z` — a `bump` type, so the squash subject it becomes
      is excluded from the next range's notes (FR-004) — and the rendered notes verbatim as the body
      under a one-line preamble stating that merging publishes them.
- [ ] T040 [US2] In `.github/workflows/release.yml`, add the `workflow_run` trigger:
      `workflows: [CI]`, `types: [completed]`, `branches: [main]`, and require
      `github.event.workflow_run.event == 'push'` in the job so a CI run from a pull request cannot
      start a release. Two guards, not one — `branches:` filters the triggering run's branch only
      (research.md decision 7). Leave `concurrency: { group: release, cancel-in-progress: false }`
      untouched. **Add no guard on `github.event.workflow_run.conclusion`** — see T042.
- [ ] T041 [US2] In `.github/workflows/release.yml`, target `github.event.workflow_run.head_sha`
      throughout — the checkout, the version read, the check-runs query and every `gh api` call —
      falling back to the dispatch ref when dispatched. This is what T029 gates.
- [ ] T042 [US2] In `.github/workflows/release.yml`, keep the **existing `commits/{sha}/check-runs`
      query on `ci / CI` as the verdict on both paths**, and split only the severity: not `success`
      under `workflow_run` is a `::notice::` naming the conclusion found or `missing` and exit 0, while
      under dispatch it stays an **error** (FR-011). Likewise "the version is not ahead of the highest
      existing release" is a `::notice::` and exit 0 under `workflow_run` — it fires after every merge,
      most of which are not releases — but stays an error under dispatch, where doing nothing is not
      what was asked (research.md decision 7).
      **`github.event.workflow_run.conclusion` must not be the gate.** It is the *workflow-level*
      verdict and `ci.yml` holds two jobs: `ci`, which reports the required `ci / CI`, and `live`, which
      runs `test_no_consumer_facing_change_is_waiting_for_a_release` — red **precisely when a release is
      owed**. So a merged proposal's CI run concludes `failure` while `ci / CI` is green, and gating on
      `conclusion` would refuse every release the moment one was actually due. That is the same trap as
      consulting `ci / Live` directly, reached by a different route; `ci / Live` stays unconsulted, and
      must. No `conclusion` guard is needed at all — a cancelled or skipped run leaves the check run
      non-`success` too. `test_the_release_gates_on_a_required_context` keeps the check name honest.
- [ ] T043 [US2] Rewrite `CONTRIBUTING.md`'s Releasing section: the procedure is now approving a
      proposal, not bumping-then-dispatching. Record SC-004's one step, the GitHub App and its two
      secrets, and the symptom of a rotated key or removed installation — no proposal is raised,
      silently, and `test_no_consumer_facing_change_is_waiting_for_a_release` is the backstop that
      reddens the next pull request (research.md decision 11). Keep the recovery path: if a release
      fails after the version tag exists, delete that tag and re-dispatch.
- [ ] T044 [US2] Add `release-proposal.yml` to the two prose copies of the repository-local workflow
      list in `CONTRIBUTING.md` — the "A workflow only this repo runs" paragraph and the
      `mise run test-live` paragraph. Nothing keeps these in step with `OWN_CI`; that is accepted
      rather than tested, since a test asserting a line number in prose would be worse than the
      duplication (research.md decision 9).
- [ ] T045 [US2] Update `README.md`'s Versioning section, which says `v2` moves on "a dispatch of the
      `Release` workflow against `main`". It now moves when an approved proposal's CI goes green.
      Keep this the only place a concrete major is written literally.
- [ ] T046 [US2] Update the Versioning paragraph in `docs/ai-instructions.md`, which describes the
      release path as `release.yml` tagging what `[project].version` declares after a reviewed
      one-line diff. The version is still a human decision recorded in `pyproject.toml` — that does
      not change — but the diff is now proposed by a bot and approving it is the release. Write no
      concrete major here: `test_ai_instructions_names_no_concrete_major` forbids it.

### Verification for User Story 2

- [ ] T046a [US2] Add a **temporary** `push: branches: [002-commit-driven-releases]` trigger to
      `.github/workflows/release-proposal.yml`, solely to reach the steps below.
      `workflow_dispatch` cannot exercise this workflow: GitHub offers it only for a workflow file
      already on the **default branch**, so a brand-new one is unreachable at the ref under review —
      the constraint research.md decision 10 hit while probing, and the same workaround it used.
      `release.yml` needs none of this; it is already on `main`, which is why T026 can dispatch it.
- [ ] T047 [US2] Push to this branch and confirm `release-proposal.yml` runs: a `release-proposal`
      branch and a pull request appear, body equal to the rendered notes, diff limited to
      `pyproject.toml` and `uv.lock`.
- [ ] T048 [US2] Confirm the proposal commit's author is the fixed identity, not `<app-name>[bot]`:
      `gh api repos/turboBasic/github-actions/commits/<sha> --jq .commit.author.name`. If it is the
      app's own bot, T037 is not setting `author` and FR-009a's detection will misfire.
- [ ] T049 [US2] Watch the proposal's checks report **with no click** — the documented App-token
      behaviour, the reason for choosing it, and the one thing the probe could not observe
      (research.md decision 11). If a click is required, SC-004's "one step" is not quite one and that
      belongs in `CONTRIBUTING.md`.
- [ ] T050 [US2] Edit the version on the `release-proposal` branch, push again to this branch, and
      confirm the body updates while the edited version is **untouched** (FR-009a). Then push again
      without editing and confirm the version is recomputed and the notes re-rendered.
- [ ] T051 [US2] Close the pull request, delete the `release-proposal` branch, and **remove T046a's
      temporary `push` trigger**. Left in, it raises proposals on pushes to a branch that will not
      exist — dead config in the one workflow that writes to `main`. Its removal is visible in the pull
      request diff, which is the only thing holding it.

**Checkpoint**: US1 and US2 both work. Two of the three manual steps are gone; what stays unverified
until merge is the `on: push` and `on: workflow_run` blocks themselves, which is plan.md's recorded
Principle VI residual.

---

## Phase 5: User Story 3 - Preview the notes before proposing (Priority: P3)

**Goal**: the maintainer renders the notes locally, offline, creating nothing.

**Independent Test**: `mise run release-notes` on a full clone with networking disabled, and its
output matches what a release over the same range publishes.

- [ ] T052 [US3] Add `[tasks.release-notes]` to `mise.toml` running `git-cliff --unreleased`, with a
      description saying it renders the unreleased range and creates nothing. **Not** a dependency of
      `[tasks.ci]`: it needs a full clone with tags, and `mise run ci` must stay green on a shallow
      one (research.md decision 8).
- [ ] T053 [US3] Mention `mise run release-notes` in `CONTRIBUTING.md`'s Releasing section as the way
      to read the notes before a proposal exists, so the task is discoverable from the procedure that
      wants it.
- [ ] T054 [US3] **SC-006** — run quickstart.md stage 2's offline check: capture
      `mise run release-notes` once, disable networking, run it again and `diff`. Identical output, or
      `--remote.github` has been switched on somewhere (FR-015).

**Checkpoint**: all three stories independently functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [ ] T055 Run `mise run ci` and confirm green — lint, typecheck, test, all offline. `actionlint`,
      `zizmor --pedantic`, `yamllint --strict` and the timeout schema all cover
      `release-proposal.yml` as they cover every other workflow, and nothing is silenced to get there
      (Principle VII).
- [ ] T056 [P] Confirm `docs/consumers.md` needs no edit — the spec's Cross-Repository Impact section
      claims every file touched is repository-local, and that claim is worth checking against the diff
      rather than assumed.
- [ ] T057 [P] Re-read `specs/002-commit-driven-releases/checklists/requirements.md` against what
      shipped and tick what now holds.
- [ ] T058 **After merge** — quickstart.md stage 4, the first real release and the only exercise the
      two automatic triggers get. `release-proposal.yml` runs on the push and raises a proposal; read
      the version and the notes; let the three checks report and merge; `release.yml` starts by itself
      when CI reports green, renders, tags, publishes and moves `vN` last. Then confirm
      `mise run test-live` goes green — the check that says a release is owed passing is the
      end-to-end proof one was cut. If it fails after the version tag exists, delete that tag, fix the
      cause and re-dispatch.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies. T004 is out-of-band and has lead time — start it first.
- **Foundational (Phase 2)**: depends on T001–T002. **Blocks all three stories.**
- **US1 (Phase 3)**: depends on Phase 2.
- **US2 (Phase 4)**: depends on Phase 3 *and* T004. Phase 3 is not merely sequencing — a proposal is
  only worth reviewing if its notes are correct, and US2's `release.yml` edits sit on top of US1's.
- **US3 (Phase 5)**: depends on Phase 2 only. Could run alongside Phase 3.
- **Polish (Phase 6)**: T055–T057 after the stories being shipped; T058 only after merge.

### Within User Story 1

T009–T010 (tests) before or alongside T011–T018, which all touch `release.yml` and are therefore
strictly serial. T019–T021 (deleting the label config and its two gates) must land **with or after**
T016 — deleting `.github/release.yml` while `--generate-notes` is still in place would silently fall
back to GitHub's default categorisation. T024–T027 last.

### Within User Story 2

T030–T039 are one new file, serial. T035a is `tests/test_release_notes.py` and needs T035's flags to
exist first. T040–T042 are `release.yml`, serial, and independent of the new file. T043–T046 are four
separate documents, all independent. T046a–T051 last, in order: the temporary trigger goes on, the five
checks run, and T051 takes it off again.

### Parallel Opportunities

- T003 and T004 with each other and with T001–T002.
- T009 (`tests/test_release_notes.py`, new file) and T010 (`tests/test_action_pins.py`) in parallel.
- T019, T020, T021 touch three different files — parallel once T016 has landed.
- T028 and T029 both edit `tests/test_action_pins.py`: same file, so serial.
- The `release-proposal.yml` chain (T030–T039) and the `release.yml` chain (T040–T042) are different
  files and can proceed in parallel. T035a joins the first chain, since it reads what T035 writes.
- T043, T044, T045, T046 in parallel — four documents. T043 and T044 both edit `CONTRIBUTING.md`, so
  those two are serial with each other.
- T056 and T057 in parallel.

---

## Parallel Example: User Story 1

```bash
# The two test files, together:
Task: "Create tests/test_release_notes.py with the five mapping assertions"
Task: "Add the notes-file-size gate to tests/test_action_pins.py"

# Once T016 has replaced --generate-notes, the three retirements together:
Task: "Delete .github/release.yml"
Task: "Remove the check-release-config hook from .pre-commit-config.yaml"
Task: "Remove the github-release-config schemafile line from mise.toml's lint task"
```

---

## Implementation Strategy

### MVP First (User Story 1)

1. Phase 1 (T001–T003; start T004 in the background)
2. Phase 2 — `.cliff.toml`
3. Phase 3 — commit-driven notes under the existing dispatch
4. **STOP and VALIDATE**: T024–T027. SC-001, SC-002, SC-005 and SC-007 are all measurable here.
5. Shippable: the categorisation failure this feature exists to fix is fixed, and a release still
   requires the same three manual steps it does today.

### Incremental Delivery

1. Setup and Foundational → the rendering exists
2. Add US1 → notes derive from commits, no tag survives a failure (**MVP**)
3. Add US2 → three manual steps become one; SC-003 and SC-004 land
4. Add US3 → the shaping rules become debuggable offline; SC-006 lands

US3 could equally ship first — it depends only on Phase 2 and is three tasks. It is last because the
feature is useful without it.

### Notes

- Every workflow change is verified by running it, not by linting it. `release.yml` from a `dry-run`
  dispatch — it is already on `main`, so a feature branch's copy runs — and `release-proposal.yml` from
  a temporary `push` trigger, because `workflow_dispatch` is offered only for a workflow already on the
  default branch and cannot reach a new one at all.
- Pre-flight the exact line out of the file, never a retyping of it.
- The `on: push` and `on: workflow_run` blocks cannot be exercised before merge. That is the recorded
  Principle VI residual, not an oversight, and T058 is where they first run.
- Commit after each task or logical group. Conventional Commits; a `feat:` touching only our own
  plumbing is still a patch when the version is decided.
