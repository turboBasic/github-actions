# Consumers

The blast-radius list. A change to a workflow affects every repository named here, so keep this
current in the same change that alters an input contract.

`python-app-baseline` is migrated; the other three rows are the intended end state, not the current
one. Migration order and per-repo notes are in
[`plans/extract-reusable-ci.md`](plans/extract-reusable-ci.md).

| Repository | Visibility | Calls | Notable inputs |
| --- | --- | --- | --- |
| `python-app-baseline` | public, **migrated** | `python-ci`, `conventional-commits` | defaults throughout |
| `repo-factory` | public | `python-ci`, `conventional-commits` | `lint-changed-only: true`, `run-typecheck: false` |
| `opus-magnum` | private | `python-ci`, `precommit-advisory`, `conventional-commits` | `lint-changed-only: true`, `hook-stage: pre-push` on both, `mise-version` pinned |
| `python-cli-app-template` | public, template | `conventional-commits` only | — |

`opus-magnum` needs `hook-stage: pre-push`: it reserves mypy for that stage, and without the input
those hooks silently stop running on PRs. It is also the only repo calling `precommit-advisory.yml`,
so the only one granting `pull-requests: write` — pass `hook-stage` to both, or the blocking run and
the advisory run check different hooks. Every other consumer grants `contents: read` and nothing
more.

`python-cli-app-template` has no `mise.toml`, which is why `conventional-commits.yml` installs `uv`
directly rather than through `mise-action` — dropping that would break the one repo that calls
nothing else.

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

`python-cli-app-template` is a GitHub template repository: every repo generated from it inherits its
call sites, so a breaking change there surfaces in repositories that do not exist yet. Migrate it
last and verify by generating a throwaway repo.
