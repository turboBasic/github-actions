# Consumers

The blast-radius list. A change to a workflow affects every repository named here, so keep this
current in the same change that alters an input contract.

`repo-factory` and `python-cli-app-template` are out of scope for the workflow migration; only
`opus-magnum` is still intended.

| Repository | Visibility | Calls | Notable inputs |
| --- | --- | --- | --- |
| `github-actions` (this one) | public | `python-ci`, `conventional-commits`, `dependency-review`, `release`, all **as self-calls** | defaults throughout |
| `github-actions-test` | public | everything: `python-ci` twice, `conventional-commits`, `prek-advisory`, `release`, `populate-pr-description` | one call at defaults, one with `lint-changed-only: true`, `hook-stage: pre-push`, `run-typecheck: false` |
| `python-app-baseline` | public | `python-ci`, `conventional-commits` | defaults throughout |
| `repo-factory` | public | `populate-pr-description` action only | — |
| `opus-magnum` | private, **not yet migrated** | `python-ci`, `prek-advisory`, `conventional-commits` | `lint-changed-only: true`, `hook-stage: pre-push` on both, `run-typecheck: false`, `run-tests: false`, `mise-version` pinned |

`v3` renamed `precommit-advisory.yml` to `prek-advisory.yml` and `actions/precommit-advisory-pr` to
`actions/prek-advisory-pr`, so a consumer's `uses:` path has to change with the ref — a call left on
the old path fails at workflow-parse time with no job and no check to re-run. `v2` stays
where it is and still resolves the old names, so nothing breaks until a repo repins.

Repin order for `v4`, and the reason for it: `github-actions-test` first, because it is the only
caller of `prek-advisory` and `release` and so the only place their renamed checks report at all.
`python-app-baseline` second — it never pinned `v3`, so it moves from `v2` to `v4` in one hop. The
`prek-*` path rename does not reach it: it calls `python-ci` and `conventional-commits` only, both at
defaults, so `v3` costs it nothing but the ref. Its `main` ruleset requires one approving review,
unlike the other two, so its repin cannot be merged unattended. `opus-magnum` has never migrated and goes straight to
`v4` whenever it does. `repo-factory` needs nothing: a composite action reports no check of its own.
Each repin updates that repository's own required status checks in the same change, or its next pull
request blocks on three contexts nothing will report.

`github-actions-test` exists to run these at `@v4` rather than to do work of its own. It is the only
caller of `opus-magnum`'s input combination, so it is where those inputs are known to work before
`opus-magnum` migrates onto them. Break a workflow and it goes red there, on a repository nobody
depends on.

`repo-factory` keeps its own workflows and calls only the `populate-pr-description` composite action.
It and `github-actions-test` are that action's only callers, so a change to its inputs reaches two.

`opus-magnum` defines no `typecheck` or `test` mise task — its `[tasks.*]` are all `make` wrappers —
so it needs `run-typecheck: false` and `run-tests: false` alongside the lint inputs.

`opus-magnum` needs `hook-stage: pre-push`: it reserves mypy for that stage, and without the input
those hooks silently stop running on PRs. It and `github-actions-test` are the only repos calling
`prek-advisory.yml`, so the only two granting `pull-requests: write` — pass `hook-stage` to both
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
