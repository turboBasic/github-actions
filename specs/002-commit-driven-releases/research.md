# Research: Commit-driven releases

**Phase 0 output** for [spec.md](./spec.md). Per-axis detail in [`evidence/`](./evidence/) — one file
each for commit authoring, commit checking, changelog rendering and release management.

Every claim below is either verified by a command run against this repository on 2026-09-02 or marked
`[unverified]`. Four axes were searched because the toolchain question was posed broadly: what creates
a conventional commit, what checks it, what renders a changelog from it, and what manages a release.

**The broad search returns a narrow answer: add one tool, delete two things, keep commitizen.**

| Axis | Verdict | Evidence |
| --- | --- | --- |
| Commit authoring | **Adopt nothing** | `cz commit`'s prompt offers 9 types, omitting `bump`, `chore`, `revert` — and `chore` is the most-used type here (17 of 51 commits). Matching the twelve needs `cz_customize`, the second declaration `test_allowed_types_match_the_commitizen_builtin_set` exists to forbid. 24 co-author trailers across 21 of 51 commits: an agent writes most commits, so a terminal prompt is unreachable from the path that produces them. |
| Commit checking | **Keep commitizen** | Already the `commit-msg` hook and `cz check --rev-range`. No candidate improves on it without splitting the type list in two. `gitlint` is dead (last release 2023-03-10). `cog`'s `[commit_types]` only *adds* — declaring `feat` alone still admitted `chore`. `convco` silently discards its whole `types:` block to stock defaults on one malformed entry. Both caught by experiment, not by reading docs. |
| PR title checking | **Replace the third-party action with `cz check -m`** — *separate feature* | Verified from `/tmp`, outside any git repository: exit 0 for `feat:`, `bump:`, `chore(deps):`, `feat!:`; exit 14 for unknown type, missing colon, empty, and multi-line. Needs no checkout, no token, and would drop the `pull-requests: read` grant every consumer makes. `amannn/action-semantic-pull-request` is release-stale, v6.1.1 ~12 months old. |
| Changelog | **git-cliff** (runner-up `convco` 0.7.1) | Spiked twice independently. Custom section titles including emoji, explicit order, all twelve types mappable, `(#N)` preserved for GitHub to auto-link, `tag_pattern` excludes the moving `v1`/`v2` tags, and `--unreleased --tag` renders before the tag exists. `commit.breaking_description` renders the footer *text*, and a breaking commit appears in both the breaking section and its type's. |
| Release manager | **Adopt nothing new; commitizen already covers it** | `cz bump` 4.18.0 has a `MANUAL_VERSION` positional and `--files-only`, and `[tool.commitizen]` already declares `version_provider = "pep621"` and `tag_format = "v$version"`. Runner-up `npm:release-please` 17.11.2 as a pinned CLI, not the Action. |

## The finding that collapsed an axis

**No release manager can move a moving major tag.** release-please documents it as the adopter's own
step — and its own example embeds a token in a git remote and deletes the ref before recreating it,
which must not be copied. knope and cocogitto reach it only by shelling out. Consumers pin `@v2`, so
that step is not optional here: the second half of today's release path survives adoption of anything.
The moving-major-tag requirement therefore stops discriminating between candidates, and the axis
reduces to "what proposes the version" — which commitizen already does.

## Rejected, with the reason

- **Staying on GitHub's native generator.** Its categories match on **labels only** — verified against
  the docs: the allowed fields are `categories[].title`, `categories[].labels`,
  `categories[].exclude.labels`, `categories[].exclude.authors`, and root `exclude.labels` /
  `exclude.authors`. No title or commit-type matcher exists. So the label hop is forced by the format,
  and removing the hop means leaving the format.
- **Labelling pull requests from their commit type** so the native generator categorises correctly.
  This was the original request. It requires a workflow holding `pull-requests: write`, a hand-created
  label, a mapping that is a second source of truth about change kind, and it depends on two
  behaviours GitHub does not document — whether a pull request matching two categories appears once or
  twice, and whether removing an absent label is a no-op. The generator depends on neither.
- **commitizen for the notes.** It cannot be configured into this. `commit_parser` recognises only
  `feat|fix|refactor|perf|BREAKING CHANGE`, and it lives in `CzSettings` — the `customize` sub-table —
  so widening it means abandoning the conventional-commits plugin. Measured:
  `cz changelog --start-rev v2.0.2 --unreleased-version v2.0.3 --dry-run` printed a heading and nothing
  else, because all three commits since that tag are `docs:` and `chore:`.
- **cocogitto** as a single tool for all four axes: rejected on absence of evidence rather than a
  demonstrated failure. Its breaking-change and pre-tag behaviour is docs-only here, and its
  `[commit_types]` additive-only behaviour was a measured surprise.

## Corrected while checking

- **`GITHUB_TOKEN` does trigger runs on a pull request it opens.** The widely-repeated opposite is out
  of date. Per GitHub's docs: "when a workflow using `GITHUB_TOKEN` creates or updates a pull request,
  the resulting `pull_request` event creates workflow runs in an approval-required state." One click by
  a write-access user, no PAT and no App. `labeled`, `edited` and `closed` do **not** create runs.
  release-please's README still advises otherwise. This is what makes the release-proposal model viable
  without new credentials.
- **`bump:` is live, not theoretical.** `5bd235b bump: version 2.0.1 → 2.0.2` is the most recent version
  commit; the two before it were `chore: set version to …`. Unless `bump` is excluded, every release's
  notes carry its own version bump.
- **The version-channel lag is not one backend's fault.** git-cliff v2.14.1 published 2026-09-01,
  neither draft nor prerelease, while `aqua:`, `github:`, `npm:` and `cargo:` all resolve 2.13.1 — still
  after `mise cache clear`. Normal downstream propagation. Pin what mise resolves and let Renovate bump
  it, as with the other ten tools.
- **Absence from mise's registry is not a filter.** Every candidate installs with an explicit backend:
  `cargo:convco` 0.7.1, `cargo:knope` 0.23.0, `npm:@commitlint/cli` 21.2.2, `npm:semantic-release`
  25.0.9, `pipx:commitizen` 4.18.0. What differs is cost — `aqua:` is a prebuilt binary, `cargo:`
  compiles, `npm:` drags Node into a Python repository.

## Constraints the plan must honour

Measured facts about the current release path, which the plan has to work with rather than discover:

- **It clones nothing, deliberately** — "no credential is written to a workspace for a later step to
  pick up, and there is no working tree to push from." Rendering notes from commits needs history, so a
  checkout is required; `persist-credentials: false` preserves the property that comment protects.
- **Today's ordering creates the tag first**, then publishes with generated notes. So a notes failure
  leaves a tag with no release — a state the workflow's own comments explain how to recover from.
  Rendering before tagging removes that failure mode, and `--unreleased --tag <version>` is what makes
  it possible without the tag existing.
- **`.github/release.yml` is validated by a network-fetched schema** in the `lint` task
  (`--schemafile https://www.schemastore.org/github-release-config.json`). Deleting the config retires
  that line and one of the task's two network fetches.
- **`CONTRIBUTING.md:89` states the release "publishes the release with notes generated from
  `.github/release.yml`"**, which this feature makes false.
- **A new repository-local workflow must join `OWN_CI`** in `tests/test_action_pins.py`, or
  `test_every_reusable_workflow_declares_workflow_call` fails it and
  `test_no_consumer_facing_change_is_waiting_for_a_release` demands a release for it.
- **The same list of repository-local workflows is written three times** — `OWN_CI`,
  `CONTRIBUTING.md:66` and `CONTRIBUTING.md:106` — with nothing keeping them in step.
- **`README.md` says nothing about labels or release notes**; `.github/release.yml` is discussed only
  in `CONTRIBUTING.md`. So the documentation change lands there, not in the consumer-facing README.

## Open `[unverified]`

- Whether a ruleset `commit_message_pattern` applies to a squash merge's generated message, and whether
  that rule is available on a free public repository. Bears only on whether a native rule could ever
  replace the commit-message job; not on this feature's path.
- That release-please's recomputed increment contradicts this repository's "the version describes the
  consumer-facing surface" rule is a judgement, not a sourced claim — though it agrees with what
  `docs/ai-instructions.md` already states.

## Design decisions taken during planning

The axes above settle *which tools*. These settle *how they are wired*, and are the decisions
[plan.md](./plan.md) and [contracts/](./contracts/) are built on. Numbering is local to this section.

Two of them re-verify an axis above with a command rather than a doc, and one corrects the spike the
changelog axis relied on.

### 1. The rendering config is `.cliff.toml`, and the spike's template is recoverable

**Decision**: the dotted filename at the repository root, seeded from the changelog axis's spike
template — which survived at `/tmp/cliff.toml` and is preserved verbatim in
[contracts/release-notes.md](./contracts/release-notes.md)'s appendix — with four corrections.

**The correction that matters**: the spike groups `bump` **into CI and dependencies**
(`{ message = "^(ci|build|bump)", … }`), which FR-004 forbids outright. The axis summary above notes
`bump:` is live and must be excluded; the spike was measuring whether all twelve types *landed
somewhere*, so it never caught the conflict. Fixed by `{ message = '^bump(\([^)]*\))?!?:', skip = true }`
placed **first**, since `commit_parsers` is first-match-wins. Anchored on the full prefix so a subject
like `bumping the pin` is not silently swallowed.

**On the filename**, three things were run against 2.13.1 rather than assumed, because a config nothing
loads and nothing lints is the failure mode:

- git-cliff finds `.cliff.toml` with no flag — `--config`'s *default* is the bare `cliff.toml`, but
  discovery covers both names and logs `Using configuration from parent directory: …/.cliff.toml`.
- `taplo fmt` still collects it: it appears in taplo's `found files` and is reported when not properly
  formatted, so the `taplo-fmt` hook covers it like any other TOML here.
- prek's `check-toml` accepts it.

**Rejected**: `pyproject.toml` under `[tool.git_cliff]`, which would have added no file at all. 2.13.1
warns `"cliff.toml" is not found, using the default configuration` and ignores the table — embedded
config is a `Cargo.toml` feature.

**Residual**: `git-cliff --init` writes the non-dotted name, so anyone running it here creates a rival
config that wins on name. Not worth a gate; worth a header comment in the file.

**Also considered and rejected: writing our own renderer** in standard-library Python. It would have
cost no new pin and given hermetic fixture tests, against owning a Conventional Commit parser and every
edge case in it forever. The pin costs one line Renovate maintains. The changelog axis had already
spiked git-cliff against this repository, which is stronger evidence than a design argument.

### 2. What the four flags actually do

The changelog axis verified rendering. The refusals and the version proposal need four more behaviours,
exercised the same way — on a throwaway repository carrying one commit of every shape on
distinguishable paths. Two results changed the design rather than confirming it:

- **An empty range is `exit 0` with zero bytes and no warning** — for a range holding only a `bump` and
  for a range holding nothing, indistinguishably. So FR-007 is a **file-size check**, never an
  exit-code check.
- **A *broken* range is `exit 1`** (`SetCommitRangeError … "revspec 'v1.1.0' not found"`), so the two
  are distinguishable and must be handled apart. Conflating them either publishes an empty body or
  refuses a legitimate release because a tag lookup misfired.
- **`--context` omits `breaking` entirely on a commit matching no Conventional Commit**, rather than
  setting it `false`. Hence `jq 'any(.[].commits[]; .breaking == true)'`; the naive form returns
  `[false, false, false, true, null, false, false]`. The first attempt at this probe passed only because
  `any()` short-circuited on the `true` before reaching the `null`.
- **`--include-path` / `--exclude-path` filter commits as decision 5 needs**: given commits touching
  `python-ci.yml`, `ci.yml`, `README.md`, `actions/thing/action.yml`, `pyproject.toml` and an untyped
  subject, the filtered pass kept exactly the consumer-facing `feat` and the breaking `actions/` commit.
- **A detached HEAD renders identically**, which is how `release.yml` will run once it checks out the
  released SHA. No `--use-branch-tags` needed.

### 3. A breaking-change footer can inject a heading, and does

**Decision**: emit the footer inline after an em dash with its newlines collapsed, which requires the
`body` to be a TOML **literal** string (`'''`) so `pat="\n"` reaches Tera as an escape.

**Demonstrated, not predicted.** Principle IV's usual sink is a shell, and the design closes that one —
commit text never passes through `${{ }}`, and `gh release create --notes-file` reads a file. The second
sink is the markdown. A footer ending `## a heading that must not survive` rendered that line **flush
left in the release body**, indistinguishable from one of our own section headings. The spike's template
missed it because its two-space indent indents only the footer's *first* line. After the fix the only
lines starting with `#` are the seven section headings.

Switching to `'''` also stops a trailing `\` acting as a TOML line-continuation, so use Tera's own
whitespace control (`{%-` … `-%}`) instead. Nothing further: GitHub sanitises HTML in a release body, and
a commit subject is safe by construction since `%s` stops at the first newline.

### 4. The proposal is a pull request from one fixed branch

**Decision**: `release-proposal`, bumping `[project].version` and `uv.lock`'s matching line, with the
rendered notes as the body. Raised on the first push to `main` that needs one, rewritten on every push
after. Merging it is the approval.

**Rationale**: satisfies FR-008 literally, and keeps `pyproject.toml` as the one place the number is
decided — which the release-manager axis establishes commitizen already assumes
(`version_provider = "pep621"`). A pull request is also the only proposal shape that can carry an
editable version (FR-010) *and* still be refused after approval (FR-011, FR-012a), because a merge is a
commit and a commit can be gated. A fixed branch name means two proposals cannot be open at once.

`uv.lock` is not optional: it carries the root package's version, so a bump without it fails
`uv sync --locked`. Measured on a copy of this project — after a version-only edit, `uv lock` resolves
in ~200 ms and changes **exactly one line**, no dependency churn.

**Departs from the release-manager axis**, which recommends a `workflow_dispatch` snapshot PR and calls
the absence of refresh "arguably correct". FR-009a, added by clarification after that was written,
requires the refresh. Superseded rather than overridden.

**Rejected**: a draft GitHub Release approved by clicking Publish — publishing creates the tag
*immediately*, so nothing can stand between the click and the tag and FR-011/FR-012a could only delete
afterwards, never refuse. A GitHub Environment with required reviewers — a deployment approval cannot
alter an input, so FR-010 has nowhere to happen. `peter-evans/create-pull-request` — it force-pushes,
which is what FR-009a forbids over a reviewer-altered version.

### 5. The proposal's version is scoped by changed path

**Decision**: highest release, incremented by what the *consumer-facing* commits imply — breaking gives
major, a `feat` touching `.github/workflows/` (excluding this repo's own CI) or `actions/` gives minor,
else patch. Computed by a second git-cliff pass with `--include-path` / `--exclude-path`.

**Rationale**: this is the standing disagreement the release-manager axis names — every tool derives the
increment from commit history, while `docs/ai-instructions.md` requires the version to describe the
consumer-facing surface, and gives the failing case: a `feat:` touching only our own linting is a patch.
Filtering by path is what makes the proposal agree with the written policy instead of being overridden
routinely. Reusing git-cliff rather than parsing commits in shell keeps one commit-convention
implementation in the repo.

This proposes; it does not decide. The number still lands as a reviewed one-line diff.

### 6. A reviewer's version survives every refresh, detected by authorship

**Decision**: the bot sets the commit author explicitly to `github-actions[bot]` when writing the
proposal commit through the Git Data API. On refresh, any commit on the branch not authored by the bot
means the version is a human's and only the body is rewritten; otherwise the branch is rebuilt.

**Rationale**: FR-009a wants both halves — recomputed as the range grows, *and* a reviewer's version
surviving — so the cases must be distinguishable, and authorship is the only signal needing no stored
state.

**Rejected**: comparing the branch's version against the freshly computed one. It cannot tell "a human
chose 2.0.3" from "the bot chose 2.0.3 before a `feat` landed and moved the computation to 2.1.0", and
would start treating its own stale output as a human decision.

### 7. The release starts on `workflow_run`, and stays quiet on ordinary merges

**Decision**: `workflow_run` on `CI` completing for a `push` to `main`, guarded on
`conclusion == 'success'`, operating on `github.event.workflow_run.head_sha`. `workflow_dispatch` stays
for recovery and the dry run.

**Rationale**: FR-011 wants the release to begin *when* the verdict arrives for the commit approval
produced, not to fail because it had not arrived yet.

Two traps: `GITHUB_SHA` under `workflow_run` is the default branch tip, **not** the head SHA of the
triggering run, so the target commit comes from the event payload; and two guards are needed, since
`branches: [main]` filters the triggering run's branch while `workflow_run.event == 'push'` is what
excludes CI runs from pull requests.

**And it must not redden `main`.** `workflow_run` fires after every merge, most of which are not
releases, so "the declared version is already tagged" exits 0 with a `::notice::`. It stays an error
only under manual dispatch, where doing nothing is not what was asked. Today's "not ahead of the highest
release" message is an error precisely because a dispatch implied intent.

### 8. The mapping is tested, the rendering is not

**Decision**: `tests/test_release_notes.py` reads `.cliff.toml` as TOML and asserts the mapping —
twelve types placed or skipped, seven titles in order, `bump` the only exclusion, catch-all last,
`tag_pattern` still excluding two-component tags, and the surface path filter agreeing with `OWN_CI`.
Rendering is verified by the spikes and once against real history by [quickstart.md](./quickstart.md).

**Rationale**: choosing git-cliff moved what is worth testing. There is no parser of ours to unit-test;
what can silently rot is the *mapping* — a type added to `conventional-commits.yml` and not here would
vanish into Other changes, and a retitled group would break FR-002 with every linter green. Reading the
config asserts that offline, with no git-cliff invocation, so `mise run ci` still passes on a shallow
clone. A test walking the tag graph would need a full clone and would either fail or skip, and a
skipping gate asserts nothing.

**Measured against real history** with the corrected config, which is what makes SC-001 and SC-002
claims rather than hopes:

```text
v1.0.1   v1.0.0..v1.0.1     bullets=3  commits=3
v2.0.0   v1.0.1..v2.0.0     bullets=3  commits=2
v2.0.1   v2.0.0..v2.0.1     bullets=5  commits=5
v2.0.2   v2.0.1..v2.0.2     bullets=32 commits=32
```

Every range matches one-for-one except `v1.0.1..v2.0.0`, over by exactly one — the breaking change
counted a second time under its own type, which is FR-005 working. And v2.0.0's breaking change now
renders under 💥 Breaking changes *with its explanatory text*, where the published release has it under
"Other changes".

### 9. The three-times-written workflow list

The constraints section above records that the repository-local workflow list appears three times —
`OWN_CI`, `CONTRIBUTING.md:66` and `CONTRIBUTING.md:106` — with nothing keeping them in step. Adding
`release-proposal.yml` touches all three, and the path filter in decision 5 makes it a **fourth**
copy.

**Decision**: `tests/test_release_notes.py` asserts the path filter agrees with `OWN_CI`, so the two
machine-readable copies cannot drift. The two prose copies stay prose — a test asserting a line number
in `CONTRIBUTING.md` would be worse than the duplication. Noted here so the tasks phase updates all
four rather than the one that fails a test.

### 10. The `GITHUB_TOKEN` route has a prerequisite, and it is currently off

**Probed, not reasoned.** The token choice above rests on GitHub's documented behaviour for a
`GITHUB_TOKEN`-authored pull request, which was read from docs rather than observed. A disposable
workflow was pushed to a branch in `turboBasic/github-actions-test` — `on: push`, because
`workflow_dispatch` only fires for a workflow already on the default branch, which is the constraint
being worked around — and it tried to do exactly what `release-proposal.yml` will do. Branches deleted
afterwards; no pull request was created, because it could not be.

**Result 1 — creation is blocked, and the API field name misleads.**

```text
POST /repos/turboBasic/github-actions-test/pulls
{"message":"GitHub Actions is not permitted to create or approve pull requests.","status":"403"}
```

`GET /repos/{owner}/{repo}/actions/permissions/workflow` reads
`{"default_workflow_permissions":"read","can_approve_pull_request_reviews":false}` for **both**
`turboBasic/github-actions` and `turboBasic/github-actions-test`. The field is named for approval only,
but the single Settings → Actions → General checkbox it backs — *Allow GitHub Actions to create and
approve pull requests* — governs creation too, and the 403 above is what a maintainer sees while it is
off.

So this is not a "confirm the setting" step, as an earlier draft of the plan had it. **It is a
prerequisite that is currently unmet in both repositories, and nothing in the design works until it is
changed.** Deliberately left unchanged here: enabling it is a security-relevant repository setting and
the owner's call, not a planning step.

**Result 2 — an API-created commit is already attributed to the bot.** With no `author` field set at
all, `POST /git/commits` under `GITHUB_TOKEN` produced:

```text
commit.author.name:  github-actions[bot]
commit.author.email: 41898282+github-actions[bot]@users.noreply.github.com
author.login:        github-actions[bot]
```

So decision 6's instruction to set the author explicitly is belt-and-braces rather than load-bearing.
It stays — it costs one field and makes the intent legible — but the human-versus-bot detection it
enables works on the default attribution regardless. The risk it was written against was a *PAT*, which
attributes to its human owner; that risk left with the PAT.

**Result 3 — the original question is still open.** Whether the required checks then appear in an
approval-required state or do not appear at all cannot be observed until the setting is on, because the
pull request never exists. The probe narrowed the unknown rather than closing it.

**What this does to the token choice.** The trade-off has moved, and the tasks phase should not treat
`GITHUB_TOKEN` as settled:

| | `GITHUB_TOKEN` | GitHub App token |
| --- | --- | --- |
| Repository setting | **must be turned on** — currently off in both repos | not needed; an App is not "GitHub Actions" |
| Per-release human action | one *Approve and run* click, unverified | none |
| Secrets to hold | none | two, plus an app to register |
| New pinned action | none | `actions/create-github-app-token` |

The App token now avoids *two* costs rather than one, and needs no change to a security setting the
account has left off. `GITHUB_TOKEN` remains the choice on record, and the decision is worth re-taking
with this in hand.
