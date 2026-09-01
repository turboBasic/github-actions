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
