# Consumers

The blast-radius list. A change to a workflow affects every repository named here, so keep this
current in the same change that alters an input contract.

**A pin is not insulation here**, which is why the list exists at all. Consumers pin `@v4`, a tag every
release force-moves — the trade is in README's Versioning section. So a change merged here is running
in every repository below on its next push, with no pull request and no review on their side, and the
list is how you know who that is before the merge rather than after.

Two things no ref carries, even to a consumer frozen on an old major: a required status-check context
lives in that repository's ruleset, and a permission grant lives in its caller workflow. Each needs a
human to edit that repository, so the change has to know which ones. And several paths run in exactly
one place — `prek-advisory`, `release`, `cache-prek` — which makes a row here sometimes the only
evidence a workflow works anywhere.

`repo-factory` is out of scope for the workflow migration — it calls one composite action and no
workflow. `opus-magnum` is the only migration still intended.

| Repository | Visibility | Pinned at | Calls | Notable inputs |
| --- | --- | --- | --- | --- |
| `github-actions` (this one) | public | self-calls | `python-ci`, `conventional-commits`, `dependency-review`, `release`, all **as self-calls** | defaults throughout |
| `github-actions-test` | public | `@v4` | everything: `python-ci` twice, `conventional-commits`, `prek-advisory`, `release`, `populate-pr-description` | one call at defaults, one with `lint-changed-only: true`, `hook-stage: pre-push`, `run-typecheck: false`, `cache-prek: true` — the only caller of that input anywhere, and `python-ci.yml` gates its cache step on `cache-prek && lint-changed-only`, so that step runs there and nowhere else. Also the only repository declaring a `[tool.turbobasic-release]` surface besides this one |
| `python-app-baseline` | public | `@v4` | `python-ci`, `conventional-commits` | defaults throughout |
| `repo-factory` | public | `@v2` | `populate-pr-description` action only | — |
| `opus-magnum` | private, **resolves nothing here yet** | — | `python-ci`, `prek-advisory`, `conventional-commits` | `lint-changed-only: true`, `hook-stage: pre-push` on both, `run-typecheck: false`, `run-tests: false`, `mise-version` pinned |

`v3` renamed `precommit-advisory.yml` to `prek-advisory.yml` and `actions/precommit-advisory-pr` to
`actions/prek-advisory-pr`, so anything still on `@v2` changes those paths when it moves — a call left
on the old path fails at workflow-parse time, with no job and no check to re-run. `v2` and `v3` are
frozen where they are and still resolve the names of their day, so nothing breaks until a repository
repins.

`v4` renamed every check name these workflows compose, so a repin has to carry the consumer's own
required status checks with it — no ref can edit a ruleset. The contexts and why a stale one blocks
everything are below, under the paragraph about call sites changing check names.

**The `v4` rollout, in the order it ran, because the next major's will want the same shape.**
`github-actions-test` went first: it is the only caller of `prek-advisory` and `release`, so it is the
only place `advisory / prek-advisory` and `release / tag-and-publish` report at all, and until it was
green those two renames were unverified anywhere. `python-app-baseline` followed, `v2` straight to
`v4` in one hop — it never pinned `v3`, and the `prek-*` path rename never reached it, since it calls
`python-ci` and `conventional-commits` only, both at defaults. Its `main` ruleset requires one
approving review where the other two require none, so its repin was the one that could not be merged
unattended; budget for that. `repo-factory` needed nothing, and still resolves `@v2`: a composite
action reports no check of its own, so nothing it uses changed.

Two orderings that are not interchangeable. A consumer's ruleset flips *after* its repin branch has
reported the new names, never before — a required context that has never reported blocks every open
pull request in that repository, not just the one doing the repin. And between the flip and the merge,
that repository's `main` still resolves the old major, so any *other* pull request opened in that
window reports the retired names and blocks. Keep the window short.

**`github-actions-test` is deliberately at `0.x`**, and is kept there. `is_ahead` compares across every
major, so a repository that has released `1.0.0` can never publish a 0.x version again — which makes this the
only place the 0.x compatibility line can be exercised: the `v0.1`/`v0.2` moving refs, and the refusal that
allows `0.2.0` to carry a break while `0.1.2` may not. Its releases and tags were reset for that
(turboBasic/github-actions#107). Do not graduate it to `1.0.0` without standing up a replacement first.

`github-actions-test` exists to run these at `@v4` rather than to do work of its own. It is the only
caller of `opus-magnum`'s input combination, so it is where those inputs are known to work before
`opus-magnum` migrates onto them. Break a workflow and it goes red there, on a repository nobody
depends on.

`repo-factory` keeps its own workflows and calls only the `populate-pr-description` composite action.
It and `github-actions-test` are that action's only callers, so a change to its inputs reaches two.

`release-decisions` has **no** external caller and is not meant to gain one: it holds the decisions
`release.yml` and `release-proposal.yml` used to make in shell, so their blast radius is its blast
radius. `release-proposal.yml` invokes it by in-repo path rather than through `uses:`, having no
`workflow_call` trigger and so no way to run anywhere else.

**Every `release.yml` caller declares its own consumer surface** in its own `pyproject.toml`, under
`[tool.turbobasic-release]`. `release.yml` checks out the caller's tree, so that file is the caller's —
which is why the surface is configuration there rather than an input here, and why there is no input at
all: a default would be this repository's layout, right for anyone else only by coincidence. A caller
declaring nothing gets an unfiltered range and a notice, so the breaking-change refusal over-refuses
rather than under-refuses. `github-actions-test` is the only caller and so the only place this is
exercised; ours lives beside `[tool.commitizen]`, and its exclusions are `OWN_CI` as workflow paths, held
equal to it by `tests/test_release_decisions.py`.

`opus-magnum` defines no `typecheck` or `test` mise task — its `[tasks.*]` are all `make` wrappers —
so it needs `run-typecheck: false` and `run-tests: false` alongside the lint inputs.

`opus-magnum` needs `hook-stage: pre-push`: it reserves mypy for that stage, and without the input
those hooks silently stop running on PRs. Once it migrates it will be the second repository calling
`prek-advisory.yml` — today `github-actions-test` is the only one, and so the only one granting
`pull-requests: write`. Pass `hook-stage` to both its calls, or the blocking run and the advisory run
check different hooks. No other consumer needs `write` on anything. Callers of
`conventional-commits.yml` all grant `pull-requests: read` — see the README for why it is not
optional.

`conventional-commits.yml` installs `uv` directly rather than through `mise-action` so that a repo
with no mise config can still have its commit messages checked.

`opus-magnum` is private, and will be able to call these workflows when it migrates only because this
repository is public. Were this one ever made private, every consumer would need
Settings → Actions → General → Access → "Accessible from repositories owned by 'turboBasic'".

That policy cannot be guarded directly: `GET /repos/{owner}/{repo}/actions/permissions/access`
answers `422 Access policy only applies to internal and private repositories` while this repository
is public, so there is nothing to read and nothing to need. What a test can guard is the
precondition, and `test_this_repository_is_still_public` in `tests/test_action_pins.py` does — a private
repository fails it, with the setting above as the failure message. Set the policy and delete the
test, in that order.

A call site changes the names of the repo's status checks to `<caller job> / <called job>`, so a
required check named after the old job stops reporting and blocks every merge. Update the required
checks in the same change. `v4` renamed the called half of all three, so they are now
`ci / python-ci`, `commits / pr-title` and `commits / commit-messages` — a repin that
leaves the old contexts required blocks every pull request on a check nothing will ever report.
The caller half has moved before too, in this repository: its required check was named `CI` until
`ci.yml` stopped running its checks inline and began calling `python-ci.yml` (`2596188`), which
prefixed it with the calling job's id.

`REQUIRED_CHECKS` in `tests/test_action_pins.py` is the single statement of these contexts, checked
against both the workflows and the live ruleset. A consumer wanting the same guard needs its own
copy — the URL is repo-specific.

Call `conventional-commits.yml` from `pull_request`, never `pull_request_target`: both its jobs are
gated on `github.event_name == 'pull_request'`, so under `pull_request_target` they are skipped
without failing, and the commit job's checkout would resolve the base ref instead of the commits
under review.
