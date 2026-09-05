# Consumers

The blast-radius list. A change to a workflow affects every repository named here, so keep this
current in the same change that alters an input contract.

`repo-factory` and `python-cli-app-template` are out of scope for the workflow migration; only
`opus-magnum` is still intended.

| Repository | Visibility | Calls | Notable inputs |
| --- | --- | --- | --- |
| `github-actions` (this one) | public | `python-ci`, `conventional-commits`, `dependency-review`, all **as self-calls** | defaults throughout |
| `github-actions-test` | public | everything: `python-ci` twice, `conventional-commits`, `precommit-advisory`, `populate-pr-description` | one call at defaults, one with `lint-changed-only: true`, `hook-stage: pre-push`, `run-typecheck: false` |
| `python-app-baseline` | public | `python-ci`, `conventional-commits` | defaults throughout |
| `repo-factory` | public | `populate-pr-description` action only | — |
| `opus-magnum` | private, **not yet migrated** | `python-ci`, `precommit-advisory`, `conventional-commits` | `lint-changed-only: true`, `hook-stage: pre-push` on both, `run-typecheck: false`, `run-tests: false`, `mise-version` pinned |

`github-actions-test` exists to run these at `@v2` rather than to do work of its own. It is the only
caller of `opus-magnum`'s input combination, so it is where those inputs are known to work before
`opus-magnum` migrates onto them. Break a workflow and it goes red there, on a repository nobody
depends on.

`repo-factory` keeps its own workflows and calls only the `populate-pr-description` composite action.
It and `github-actions-test` are that action's only callers, so a change to its inputs reaches two.

`opus-magnum` defines no `typecheck` or `test` mise task — its `[tasks.*]` are all `make` wrappers —
so it needs `run-typecheck: false` and `run-tests: false` alongside the lint inputs.

`opus-magnum` needs `hook-stage: pre-push`: it reserves mypy for that stage, and without the input
those hooks silently stop running on PRs. It and `github-actions-test` are the only repos calling
`precommit-advisory.yml`, so the only two granting `pull-requests: write` — pass `hook-stage` to both
calls, or the blocking run and the advisory run check different hooks. No other consumer needs
`write` on anything. Callers of
`conventional-commits.yml` all grant `pull-requests: read` — see the README for why it is not
optional.

`conventional-commits.yml` installs `uv` directly rather than through `mise-action` so that a repo
with no mise config can still have its commit messages checked.

`opus-magnum` is private and can still call these workflows because this repository is public. Were
it ever made private, every consumer would need
Settings → Actions → General → Access → "Accessible from repositories owned by 'turboBasic'".

That policy cannot be guarded directly: `GET /repos/{owner}/{repo}/actions/permissions/access`
answers `422 Access policy only applies to internal and private repositories` while this repository
is public, so there is nothing to read and nothing to need. What a test can guard is the
precondition, and `test_this_repository_is_still_public` in `tests/test_action_pins.py` does — a private
repository fails it, with the setting above as the failure message. Set the policy and delete the
test, in that order.

A call site changes the names of the repo's status checks to `<caller job> / <called job>`, so a
required check named after the old job stops reporting and blocks every merge. Update the required
checks in the same change — for `python-app-baseline` they became `ci / CI`, `commits / PR title` and
`commits / Commit messages`. This repository hit the same rename when `ci.yml` stopped running its
checks inline and began calling `python-ci.yml`: its required `CI` became `ci / CI`.

`REQUIRED_CHECKS` in `tests/test_action_pins.py` is the single statement of these contexts, checked
against both the workflows and the live ruleset. A consumer wanting the same guard needs its own
copy — the URL is repo-specific.

Call `conventional-commits.yml` from `pull_request`, never `pull_request_target`: both its jobs are
gated on `github.event_name == 'pull_request'`, so under `pull_request_target` they are skipped
without failing, and the commit job's checkout would resolve the base ref instead of the commits
under review.
