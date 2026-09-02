# Phase 1: Data Model

Five of these are the spec's Key Entities; the sixth — the facts the workflows read back out of the
rendering — is here because the two new refusals depend on it.

Nothing is persisted. Every entity is derived from git refs or from the GitHub API on each run, which
is what lets FR-009a re-derive the notes at publication time with no state carried from the proposal.

## Commit

One commit in a release range, as git-cliff's template context sees it. Populated by
`conventional_commits = true` parsing the subject; this repo authors none of it.

| Field | Meaning here |
| --- | --- |
| `id` | The full SHA. Abbreviated in the bullet, where GitHub renders it as a link in a release body. |
| `group` | The section title, assigned by the first matching entry in `commit_parsers`. The `<!--N-->` ordering prefix is stripped by a `postprocessors` regex. |
| `message` | The subject with its `type(scope)!:` prefix removed. Single-line by construction. |
| `scope` | The parenthesised scope, if any. |
| `breaking` | True for `!` before the colon **or** a `BREAKING CHANGE:` / `BREAKING-CHANGE:` footer. In the `--context` JSON the key is **omitted entirely** for a commit that matched no Conventional Commit, so a consumer of that JSON must test for `== true` rather than for truthiness. |
| `breaking_description` | The footer's text. Verified present in 2.13.1 by the spike in `evidence/changelog.md`. Falls back to `message` when `breaking` came from `!` alone, which is the spec's edge case for a breaking change with no explanatory text. |

### Settings that matter, and why

- `filter_unconventional = false`. A commit whose subject matches no Conventional Commit still reaches
  the catch-all parser instead of being dropped — FR-003's requirement that such a commit surface
  rather than vanish.
- `commit_parsers` is **first-match-wins**, so the catch-all is last. Exactly the ordering constraint
  `.github/release.yml`'s trailing `labels: ['*']` category carries today.
- Merge commits are excluded. Squash merging is the assumed merge method, so a merge commit on `main`
  is not a change to describe.
- `commit_preprocessors` collapses newlines inside a breaking description (research.md, "Corrected while checking").

## Section

One heading in the notes: a `group` value in `.cliff.toml`. Fixed in title and position (FR-002); the
table *is* the mapping FR-003 requires, and `tests/test_release_notes.py` asserts the config against
it.

| Order | Title | Types | Membership |
| --- | --- | --- | --- |
| 1 | 💥 Breaking changes | — | every commit with `breaking` true, whatever its type |
| 2 | 🚀 Features | `feat` | by type |
| 3 | 🐛 Fixes | `fix`, `perf`, `revert` | by type |
| 4 | 📚 Documentation | `docs` | by type |
| 5 | 🚚 CI and dependencies | `ci`, `build` | by type |
| 6 | 🧹 Maintenance | `chore`, `style`, `test`, `refactor` | by type |
| 7 | Other changes | — | any commit whose type matched no parser above |

- Section 1 is not a `group`. It is a separate Tera block over
  `commits | filter(attribute="breaking", value=true)`, which is what lets one commit occupy two
  sections (FR-005). It is the only place `breaking_description` is shown.
- `bump` is matched by a `skip = true` parser and appears nowhere (FR-004). It is the only excluded
  type.
- An empty section is omitted from the output. Its position is fixed, not its presence.
- The twelve allowed types are `conventional-commits.yml`'s `types` default, asserted equal to
  commitizen's built-in set by `test_allowed_types_match_the_commitizen_builtin_set`. Eleven are placed
  above and the twelfth is `bump`. A type added there and not here lands in Other changes — the FR-003
  behaviour rather than a bug — and `tests/test_release_notes.py` fails, so it is noticed.

## Release range

The commits the notes describe: from the previous version tag to the commit being released.

- **Previous version tag** is the highest tag matching `v<major>.<minor>.<patch>`, across *all* majors,
  sorted by version. Across all majors because a frozen major is never backported, only left where it
  is — the rule `release.yml` already applies.
- `tag_pattern = "v[0-9]+\\.[0-9]+\\.[0-9]+"` is what excludes the moving `v1` / `v2` tags. Both sit on
  `main`'s tip, so a default pattern finds one there and renders an empty range silently
  (research.md decision 1, and the changelog axis's `tag_pattern` finding).
- When no matching tag exists, the range is every commit reachable from the target. Only the repository's
  first release hits this; the first release of a new *major* still has the previous major's highest tag
  beneath it.
- Both callers derive it the same way, from tags rather than from published releases. The two differ
  whenever a tag carries no release, and that difference has already burned this repo once.

## Facts read back from the rendering

The two new refusals and the version proposal need answers, not prose. All three come from git-cliff
rather than from a second parser, so one commit-convention implementation stays in the repo.

| Fact | Source | Used by |
| --- | --- | --- |
| The notes are empty | the rendered file holds no non-whitespace character | FR-007: no proposal is raised; a release refuses and creates no tag |
| The range contains a breaking change | `--context`, then `jq 'any(.[].commits[]; .breaking == true)'` | FR-012a: a release refuses unless the version is a new major |
| A `feat` touched the consumer surface | `--context` on a second pass filtered by `--include-path` / `--exclude-path` | the version the proposal proposes |

All three were exercised against 2.13.1; `contracts/release-notes.md` records what came back. Two results
shape the code rather than merely confirming it: an empty range exits **0**, so FR-007 can be no
exit-code check; and `breaking` is **absent** on an unconventional commit rather than `false`, so the jq
test compares against `true` instead of relying on truthiness. A third correction came later, from
running it: the empty render is a lone newline rather than zero bytes, so FR-007 is a check for content
and a file-size test passes on it.

The consumer surface is `.github/workflows/**` and `actions/**`, minus this repo's own CI —
`ci.yml`, `commit-messages.yml`, `release.yml`, `release-proposal.yml`. That list is `OWN_CI` in
`tests/test_action_pins.py`, and a test asserts the two agree rather than letting them drift.

## Release proposal

One pull request from the fixed branch `release-proposal` into `main`. Fixed name, so two cannot be open
at once — the spec's edge case is closed by construction rather than by a check.

| Part | Value |
| --- | --- |
| Branch | `release-proposal`, rebuilt from `main`'s tip, one commit ahead |
| Commit / PR title | `bump: release vX.Y.Z` — a `bump` type, so the squash subject it becomes is excluded from the next range's notes (FR-004) |
| Commit author | one fixed bot identity, set **explicitly** in the API payload; this is what distinguishes a refresh from a reviewer's edit. Explicit because an App token would otherwise attribute the commit to `<app-name>[bot]` (research.md decision 11) |
| Diff | `pyproject.toml`'s `[project].version` and `uv.lock`'s matching line, nothing else |
| Body | the rendered notes verbatim, under a short preamble stating that merging publishes them |

**Version ownership**: bot-owned while every commit on the branch carries that fixed author; human-owned
from the moment the reviewer pushes an edit, and then never rewritten (FR-009a).

### State transitions

| From | Event | To |
| --- | --- | --- |
| absent | push to `main`, range non-empty, declared version already tagged | open |
| absent | push to `main`, range empty | absent — no proposal for empty notes (FR-007) |
| absent | push to `main`, declared version *not* yet tagged | absent — a release is already in flight or owed |
| open, bot-owned | push to `main` | open, branch rebuilt: version recomputed, notes re-rendered |
| open, human-owned | push to `main` | open, body re-rendered only; version untouched |
| open | range becomes empty | closed, branch deleted |
| open | merged | approved — the release is now pending a CI verdict |
| approved | `ci / CI` green on the merge commit | released |
| approved | `ci / CI` red, or a refusal fires | no tag; the proposal is already merged, so recovery is a new pull request |
| released | next push to `main` | absent — the declared version is now tagged and the range is empty |

The proposal is opened by a GitHub App installation token, so its checks report without any click — the
reason for choosing that token over `GITHUB_TOKEN`, which cannot open a pull request here at all
(research.md decisions 10 and 11).

## Moving major tag

`v<major>` of the version being released. Repointed at the released commit once the release exists, and
created when it does not exist yet (FR-013).

- Moved **last**, after the version tag and the release. It is the only ref consumers resolve, so a
  failure earlier leaves them on the previous release rather than half-way into this one.
- Annotated, like every other tag here: `PATCH` on the ref for a move, `POST` for the first release of a
  new major. Atomic — never `git tag -d` then re-push, which would leave a window where `@vN` resolves
  nothing.
- Which major is current is stated only in `README.md`'s Versioning section.
