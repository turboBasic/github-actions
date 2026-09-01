# Release managers for a conventional-commit repo, judged for `turboBasic/github-actions`

Scratch research. Not documentation, not authoritative for anything.

**Method.** All figures read live on **2026-09-01/02 UTC** via `gh api`, `mise latest` /
`mise registry`, and `WebFetch` against each tool's own docs. No web search was available, so there
are **no adoption, popularity or trend claims here beyond raw `stargazers_count`**. Anything not
established by one of those three tools is tagged `[unverified]`.

## The finding that reorders everything

**No candidate moves a major tag.** Not one. release-please documents it as *your* extra step;
knope and cocogitto can do it only because they can shell out; changesets, semantic-release,
release-plz and commitizen have nothing. So requirement 1 does not discriminate between
candidates — it just means the **second half of the existing `release.yml` survives adoption of any
of them**, unchanged: the annotated version tag, `gh release create`, and the
`PATCH refs/tags/vN --force` move.

What is actually up for replacement is only the *first* half: the human's edit to
`[project].version`. Every candidate is therefore competing for a ~20-line slice of one workflow, and
should be priced accordingly.

Also worth pricing in: the repo's own rule that **"the version describes the consumer-facing surface,
not this repository's commit history"** (`docs/ai-instructions.md`). Every tool here derives the
increment from commit history. That is a standing, structural disagreement with the repo's written
policy, not a configuration detail — and it decides the recommendation below.

## Comparison table

Maintenance columns: stars / `pushed_at` / latest stable release + its date, all read 2026-09-01.

| Tool | Stars | Pushed | Latest stable | Release-PR? | Moves major tag? | `pyproject` `[project].version`? | Can be told the version? | mise-pinnable |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **commitizen** (`cz bump`) | 3,499 | 2026-08-25 | `v4.18.0` 2026-08-19 | no — you write the 3 lines | no | **yes, already configured** | **yes**, `MANUAL_VERSION` positional | **already a dev dep** |
| **release-please** (CLI) | 7,433 | 2026-08-24 | `v17.11.2` 2026-08-24 | **yes, native** | no — documented as your extra step | **yes** (`release-type: python`, or `extra-files` toml+jsonpath) | **yes**, `release-as` / `Release-As:` footer | `npm:release-please` → 17.11.2 |
| **release-please-action** | 2,512 | 2026-08-28 | `v5.0.0` 2026-04-22 | as above | as above | as above | as above, plus a `release-as` input | new SHA-pinned Action |
| **knope** | 187 | 2026-09-01 | `knope/v0.23.0` 2026-05-24 | **yes**, `CreatePullRequest` step | via `Command` step w/ `shell = true` | **yes** | **yes**, `--override-version` | **awkward** — not in registry |
| **cocogitto** (`cog bump`) | 1,180 | **2026-04-22** | `7.0.0` **2026-03-04** | no | via `post_bump_hooks` | not built in | **yes**, `--version 3.2.1` | `aqua:cocogitto/cocogitto` → 7.0.0 |
| **python-semantic-release** | 1,055 | 2026-09-01 | `v10.6.2` 2026-08-28 | **no** — commits + tags directly | no | yes `[unverified]` syntax | partly `[unverified]` | `pipx:` → 10.6.2 |
| **semantic-release** | 24,011 | 2026-08-29 | `v26.0.0-beta.1` 2026-08-07 (pre) | **no** | no | **no** — version lives only in git tags | no first-party way `[unverified]` | `npm:semantic-release` → 25.0.9 |
| **changesets** | 12,350 | 2026-08-31 | (per-pkg, 2026-08-19) | **yes**, canonical | no | **no** — `package.json` only | no | `npm:@changesets/cli` → 3.0.1 |
| **release-plz** | 1,469 | 2026-08-31 | `v0.3.160` 2026-07-14 | yes | no | **no** — Cargo only | n/a | `aqua:` → 0.3.160 |
| release-it | 9,040 | 2026-08-09 | `21.0.2` 2026-08-09 | no (interactive-first) | no | no | yes | `npm:release-it` → 21.0.2 |
| git-cliff | 12,194 | 2026-09-01 | `2.13.1` | n/a — changelog only | n/a | n/a | n/a | `aqua:orhun/git-cliff` |
| goreleaser / jreleaser | 16,013 / 1,238 | 2026-09-01 / 08-31 | — | no | no | no | — | yes |

## The `GITHUB_TOKEN` question — the folklore is now out of date

This matters for **every** release-PR candidate, so it is settled once here.

Two GitHub docs pages agree, read 2026-09-01:

> "When you use the repository's `GITHUB_TOKEN` to perform tasks, events triggered by the
> `GITHUB_TOKEN` will not create a new workflow run, with the following exceptions: [...]
> `workflow_dispatch` and `repository_dispatch` events always create workflow runs."
>
> "When a pull request is created or updated by a workflow using `GITHUB_TOKEN`, `pull_request`
> events with the `opened`, `synchronize`, or `reopened` activity types create workflow runs that
> **require approval**." — and "a user with write access to the repository can approve these runs
> from the pull request page."

So the classic "GITHUB_TOKEN-opened PRs get no CI at all" is **no longer accurate**. The runs are
created; they sit in an approval-required state until a write-access user clicks *Approve and run*.

Consequence for this repo specifically: `release.yml` gates on `ci / CI` being `success` on the
commit. With a `GITHUB_TOKEN`-opened release PR, that check does not start on its own — the human who
reviews the version diff must first approve the run. That is one extra click on a path a human is
already standing on, so it is **friction, not a blocker**, and it needs **no PAT and no GitHub App**.

Note `release-please-action`'s README still advises otherwise, and its stated reason is the outdated
half of the rule:

> "you will need to specify a `token` for your workflows to run on Release Please's releases and
> PRs" — because "events triggered by the `GITHUB_TOKEN` will not create a new workflow run."

If the approval click is ever judged unacceptable, the escape hatch is
`actions/create-github-app-token` (`actions` org, 879 stars, `v3.2.0` 2026-05-12) — an App
installation token triggers runs normally. A PAT would also work and is strictly worse: a
long-lived, broadly-scoped, human-owned credential.

**Permissions, identical for every release-PR candidate:**

- On the PR-opening job: `contents: write` (push the branch) + `pull-requests: write` (open/update
  the PR). Nothing else. No `issues: write` unless labels are used — release-please's README asks
  for it because it labels its PRs; `skip-labeling: true` drops the need.
- The repo/org setting **"Allow GitHub Actions to create and approve pull requests"** must be on.
  (Quoted from `changesets/action`'s README, but it is a GitHub-wide gate on any
  `GITHUB_TOKEN`-opened PR, not a changesets quirk.)
- The bot must **push a branch and open a PR, never push `main`** — `main`'s ruleset bypasses only
  for the Repository admin role, which `GITHUB_TOKEN` does not hold. Every release-PR tool here
  already works that way; every *direct-commit* tool (semantic-release, python-semantic-release,
  `cog bump` in its documented form) collides with it head-on.
- The existing tagging job keeps `contents: write` alone.

## Per-candidate notes

### commitizen — `cz bump` (recommended)

Already pinned in `[dependency-groups].dev` as `commitizen>=4.17`, resolved locally to **4.18.0**.
Already configured for exactly this job:

```toml
[tool.commitizen]
tag_format = "v$version"
version_scheme = "semver"
version_provider = "pep621"
```

`version_provider = "pep621"` *is* "`pyproject.toml` `[project].version` is the source of truth" —
requirement 4 is already satisfied and already in the repo. And `cz bump --help`, run locally against
4.18.0, has a positional argument:

```text
positional arguments:
  MANUAL_VERSION        Bump to the given version (e.g., 1.5.3).
```

plus `--files-only` (write the version, do not commit or tag), `--get-next` (print the computed next
version, change nothing), `--changelog`, and `--annotated-tag`. That is requirement 5 satisfied
first-class, and it is the only candidate where a human typing the number is the *primary* interface
rather than an override.

It is also already load-bearing here for something else: `tests/test_action_pins.py` asserts the
allowed commit types equal commitizen's built-in set. Adopting a second conventional-commit
implementation for versioning would mean two tools with two type tables, which is the exact failure
that test exists to prevent.

What a release PR costs, in full: a `workflow_dispatch` with an optional `version` input, then
`cz bump --files-only --changelog [$version]`, a commit onto `release/vX.Y.Z`, and `gh pr create`.
No new pinned binary. No new Action. No new config file.

What it does not do: nothing computes or force-pushes an updated proposal as more commits land — the
PR is a snapshot. For a repo that releases on a human's decision anyway, that is arguably correct
rather than a gap.

### release-please (runner-up)

The strongest *product*, and the one whose behaviour is easiest to verify:

- **Release PR is native and configurable.** The config schema (`schemas/config.json`) carries
  `pull-request-title-pattern`, `pull-request-header`, `pull-request-footer`, `changelog-sections`,
  `skip-changelog`, `versioning-strategy`, `release-as`, `extra-files`, `tag-separator`,
  `include-v-in-tag`.
- **`pyproject.toml` `[project].version` — confirmed from source**, not from docs.
  `src/strategies/python.ts` resolves
  `const pyProject = parsedPyProject?.project || parsedPyProject?.tool?.poetry;` and pushes a
  `PyProjectToml` updater. Its `setup.cfg` / `setup.py` updates are `createIfMissing: false`, so
  their absence here is harmless. The alternative, avoiding the Python strategy's assumptions
  entirely, is `release-type: simple` plus
  `extra-files: [{ "type": "toml", "path": "pyproject.toml", "jsonpath": "$.project.version" }]`.
- **Requirement 5 is first-class:** `release-as` in config, per-package, or as a `Release-As:` commit
  footer, or as an action input.
- **Requirement 1 is explicitly *not* its job.** README §"Creating major/minor tags":

  > "you will likely want to tag a major and minor tag during a release, i.e., if you are releasing
  > `v2.8.3`, you will also want to update tags `v2` and `v2.8`."

  The example that follows does `git remote add gh-token "https://${{ secrets.GITHUB_TOKEN }}@github.com/..."`
  then `git tag -d` / `git push origin :v${major}` / re-tag / push. **Do not copy it** — it writes a
  credential into a remote URL in the workspace, which is the precise thing the current `release.yml`
  was built to avoid, and it deletes the major ref before recreating it, leaving a window where
  consumers pinned to `@v2` resolve nothing. Keep the existing atomic
  `PATCH .../git/refs/tags/v2 -F force=true`.
- **Supply chain, and a genuinely good option here:** it can be adopted with **no new Action at
  all** — `mise latest npm:release-please` → **17.11.2**, so it pins like `npm:cspell` already does
  and Renovate's mise manager bumps it. If the Action is preferred instead, `v5.0.0` dereferences to
  `45996ed1f6d02564a971a2fa1b5860e934307cf7` (lightweight tag, so the tag SHA is the commit SHA).
  Pinning the CLI is the better trade: one pinned npm package instead of one pinned Action plus its
  whole bundled `node_modules`.

Why it is the runner-up and not the pick:

1. **It recomputes the version on every push to `main`.** The repo's rule is that a `feat:` touching
   only linting is a *patch*. release-please will call it a minor. The fix is a `Release-As:` footer
   or a config edit per occurrence — i.e. the human is overriding the tool routinely, which inverts
   the intended relationship and makes the tool's proposal noise.
2. **It brings a `CHANGELOG.md`** (`createIfMissing: true`). New file → `markdownlint-cli2 "**/*.md"`
   and `cspell lint .` both start linting generated prose, and its heading style will collide with
   default rules. Manageable (`skip-changelog: true`, or an ignore) but it is real work for a repo
   whose release notes are already generated by `.github/release.yml`.
3. **It needs two committed config files** (`release-please-config.json` +
   `.release-please-manifest.json`), and per the repo's own gate each new GitHub-adjacent config file
   wants a `check-jsonschema` hook and a `lint` task line.

### knope

Technically the best fit on paper and the worst on supply chain.

- `CreatePullRequest`: "Create a pull request on every configured forge from the current branch to a
  specified branch"; existing PRs are updated rather than duplicated; title and body are templated
  (`chore: Release {version}`).
- `pyproject.toml` is a first-class versioned file: "For Python projects using PEP-621 or Poetry.
  Must contain either a `[project.version]` or `[tool.poetry.version]` value."
- `--override-version 1.0.0` covers requirement 5.
- Requirement 1: the `Release` step "tags the current commit with the new version" as `v{version}`
  and says nothing about moving an existing tag — but the `Command` step exists to "cover the
  infinite things you might want to do that Knope doesn't yet know how to do itself", with
  `shell = true` and `{version}` substitution. So the major-tag move is expressible, just as a shelled
  `gh api` call.

**Disqualifying in practice: it will not pin cleanly.** `mise registry` has no `knope` entry.
`mise latest github:knope-dev/knope` returns **0.16.1** while the actual current CLI release is
**`knope/v0.23.0`** (2026-05-24) — the backend cannot read the monorepo's per-package tag scheme, so
it silently resolves something seven minors stale. `cargo:knope` does return 0.23.0, but that is a
from-source Rust build in CI. The alternative, `knope-dev/action`, has **1 star** and its last
release is `v2.1.2` (2026-02-13). At **187 stars** overall, this is a lot of bus-factor for a 20-line
slice of one workflow.

### cocogitto

`cog bump --version 3.2.1` gives requirement 5, and `post_bump_hooks` run arbitrary shell — the docs'
own examples are `git push` and `git push origin {{version}}` — so the major tag is reachable. But:

- **No release-PR model at all.** Hooks push to the branch. That collides with `main`'s
  pull-request-required ruleset, which `GITHUB_TOKEN` cannot bypass. Requirement 3 fails.
- **No documented `pyproject.toml` updater.** You would hand-roll the write in a `pre_bump_hook`.
- **Least active of the serious candidates:** `pushed_at` **2026-04-22**, latest release `7.0.0` on
  **2026-03-04** — a ~4-month and ~6-month gap respectively as of the read date. Not abandoned, but
  the only candidate here where that is even a question.

### python-semantic-release / semantic-release

Both are the unattended model this repo has already rejected. python-semantic-release's own
GitHub-Actions doc describes its sequence as "(1) determine the next version number, (2) stamp the
version number, ... (5) commit the changes, (6) tag the commit, (7) publish the commit & tag" — no PR
anywhere. semantic-release: "For each new commit added to one of the release branches ... a CI build
is triggered and runs the `semantic-release` command to make a release", and it stores no version in
any file, only in git tags — so it cannot honour `[project].version` as the source of truth even in
principle.

Both also want to push to `main`, which the ruleset forbids to `GITHUB_TOKEN`; python-semantic-release
acknowledges this and recommends "storing an administrator's Personal Access Token" — a long-lived
admin credential in a repo whose entire release path was designed so no credential reaches a
workspace. That is the wrong direction.

### changesets

The canonical release-PR implementation, and the model the owner has approved is essentially
changesets' idea. But it is bound to npm: `changesets/action/version` "Version packages and create or
update a pull request with the changes", `changesets/action/publish` "Publish packages to npm", and
the version lives in `package.json`. There is no `pyproject.toml` path. Adding a `package.json` purely
to hold a version this repo already declares elsewhere would create two sources of truth for
requirement 3's one number.

Its README is still the best citation for the repo-setting requirement:

> "In your repository settings, in `Actions > General`, also ensure the `Allow GitHub Actions to
> create and approve pull requests` option is enabled"

### Reference points, not candidates

- **release-plz** — "Releasing Rust packages is tedious and error-prone"; "release-plz creates a
  release Pull Request from CI". Right model, wrong ecosystem: versions come from `Cargo.toml` and the
  publish step is `cargo publish`. There is no `Cargo.toml` here.
- **goreleaser / jreleaser** — artifact builders. Requirement 2 removes their entire reason to exist
  here; nothing is built and nothing is published.
- **git-cliff** (12,194 stars, `2.13.1`, `aqua:orhun/git-cliff`) — changelog generation only, no
  versioning, no PR, no release. Worth knowing about *only* if a hand-written `CHANGELOG.md` is ever
  wanted; `.github/release.yml` + `--generate-notes` already covers the equivalent ground.
- **release-drafter** (3,931 stars) — drafts *release notes* as PRs merge. Not a version manager; no
  version file; overlaps what `.github/release.yml` already does.
- **`actions/publish-action`** — GitHub's own tool that does exactly requirement 1 ("Update a major
  tag (v1, for example) to point to the latest release"). Ruled out by its own README: "**this action
  is for internal usage only, issues are disabled and contributing PRs will not be reviewed. We also
  do not recommend this action for public or production usage while it is still in development.**"
  Status: "Alpha." 58 stars. The existing hand-rolled `PATCH` is strictly better.

## Recommendation

**Adopt the release-PR model on top of commitizen, which is already here.** Add a
`workflow_dispatch`-triggered job that runs `cz bump --files-only --changelog` (with an optional
`version` input passed as `MANUAL_VERSION`), commits to `release/vX.Y.Z`, and opens the PR with
`gh pr create`. Leave `release.yml` exactly as it is — its version-ahead check, its `ci / CI` gate,
its API-only tagging and its major-tag move all remain correct and all remain necessary.

Cost: ~20 lines of YAML, `contents: write` + `pull-requests: write`, one repo setting, one
*Approve and run* click per release PR. **Zero new pinned binaries, zero new pinned Actions, zero new
config files, zero new lint-task lines, one commit-convention implementation instead of two.**

**Runner-up: release-please, adopted as the pinned `npm:release-please` CLI rather than the Action.**
Take it if the changelog and a continuously-updated proposal are wanted for their own sake, and accept
that its computed increment will be overridden by `Release-As:` whenever the repo's
consumer-facing-surface rule and conventional-commit arithmetic disagree — which, for a repo where
most commits touch linting rather than workflows, will be often.

Either way, requirement 1 is satisfied by code this repo already owns.

## Disqualified, keyed to the numbered requirements

| Tool | Fails | Why |
| --- | --- | --- |
| **changesets** | **4** | Version lives in `package.json`; no `pyproject.toml` path. Also (2) its publish half is npm-only. |
| **release-plz** | **4**, 2 | Reads `Cargo.toml`, publishes with `cargo publish`. No Rust here. |
| **semantic-release** | **3**, **4** | Releases unattended on every push to the release branch; stores the version only in git tags, so `[project].version` cannot be the source of truth. |
| **python-semantic-release** | **3**, 5 | Commits and tags directly, no PR model; recommends an admin PAT to get past branch protection. |
| **cocogitto** | **3**, 4 | No release-PR model — hooks push to the branch, which `main`'s ruleset forbids to `GITHUB_TOKEN`. No built-in `pyproject.toml` updater. |
| **knope** | **4 (supply chain)** | Not in `mise registry`; `github:` backend resolves 0.16.1 against an actual 0.23.0; `cargo:` means a from-source build; its Action has 1 star. Everything else about it fits. |
| **release-it** | **3** | Interactive-first, no release-PR model, no `pyproject.toml`. |
| **goreleaser / jreleaser** | **2** | Artifact builders; nothing is built or published here. |
| **git-cliff / release-drafter** | — | Not release managers. Changelog and release-notes generators respectively; neither versions anything. |
| **`actions/publish-action`** | **4 (supply chain)** | Vendor says "internal usage only", "do not recommend for public or production usage", "Alpha". |

## `[unverified]` — read these as gaps, not as facts

1. **python-semantic-release's `pyproject.toml` syntax.** Believed to be
   `version_toml = ["pyproject.toml:project.version"]`; not confirmed against its docs, because the
   tool failed requirement 3 first and the question stopped mattering.
2. **Whether semantic-release can be told an exact version.** No first-party mechanism was found.
   Whether a community plugin provides one is unknown.
3. **Whether cocogitto has any `version_files`-style file updater.** Its `bump` guide does not mention
   one; absence from that page is weak evidence of absence from the tool.
4. **Whether `@semantic-release/exec` could move the major tag.** Plausible, unexamined — the tool is
   out on requirement 3 regardless.
5. **Whether release-please's `release-type: simple` + toml `extra-files` combination avoids the
   `CHANGELOG.md` creation** as cleanly as `skip-changelog: true` does. Both options exist in the
   schema; their interaction was not tested.
6. **Everything about relative popularity or momentum.** `stargazers_count` and `pushed_at` are the
   only quantities here, and they measure neither. There is no download, dependent-repo or trend
   figure in this document, deliberately — no web search was available to source one.
7. **Whether the *Approve and run* click can be avoided without an App or PAT.** Both docs pages read
   describe the approval-required state as unconditional for `GITHUB_TOKEN`-authored PRs; no
   repository setting that waives it was found, but the search was not exhaustive.
