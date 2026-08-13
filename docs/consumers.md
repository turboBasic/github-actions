# Consumers

The blast-radius list. A change to a workflow affects every repository named here, so keep this
current in the same change that alters an input contract.

`repo-factory` and `python-cli-app-template` are out of scope for the workflow migration; only
`opus-magnum` is still intended.

| Repository | Visibility | Calls | Notable inputs |
| --- | --- | --- | --- |
| `python-app-baseline` | public | `python-ci`, `conventional-commits` | defaults throughout |
| `repo-factory` | public | `populate-pr-description` action only | — |
| `opus-magnum` | private, **not yet migrated** | `python-ci`, `precommit-advisory`, `conventional-commits` | `lint-changed-only: true`, `hook-stage: pre-push` on both, `run-typecheck: false`, `run-tests: false`, `mise-version` pinned |

`repo-factory` keeps its own workflows and calls only the `populate-pr-description` composite action.
It is the sole consumer of that action, so a change to its inputs reaches exactly one caller.

`opus-magnum` defines no `typecheck` or `test` mise task — its `[tasks.*]` are all `make` wrappers —
so it needs `run-typecheck: false` and `run-tests: false` alongside the lint inputs.

`opus-magnum` needs `hook-stage: pre-push`: it reserves mypy for that stage, and without the input
those hooks silently stop running on PRs. It is also the only repo calling `precommit-advisory.yml`,
so the only one granting `pull-requests: write` — pass `hook-stage` to both, or the blocking run and
the advisory run check different hooks. Every other consumer grants `contents: read` and nothing
more.

`conventional-commits.yml` installs `uv` directly rather than through `mise-action` so that a repo
with no mise config can still have its commit messages checked.

`opus-magnum` is private and can still call these workflows because this repository is public. Were
it ever made private, every consumer would need
Settings → Actions → General → Access → "Accessible from repositories owned by 'turboBasic'".

A call site changes the names of the repo's status checks to `<caller job> / <called job>`, so a
required check named after the old job stops reporting and blocks every merge. Update the required
checks in the same change — for `python-app-baseline` they became `ci / CI`, `commits / PR title` and
`commits / Commit messages`.

Call `conventional-commits.yml` from `pull_request`, never `pull_request_target`: both its jobs are
gated on `github.event_name == 'pull_request'`, so under `pull_request_target` they are skipped
without failing, and the commit job's checkout would resolve the base ref instead of the commits
under review.
