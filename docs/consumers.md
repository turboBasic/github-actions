# Consumers

The blast-radius list. A change to a workflow affects every repository named here, so keep this
current in the same change that alters an input contract.

**Nothing consumes this repo yet.** It was scaffolded ahead of the migration described in
[`plans/extract-reusable-ci.md`](plans/extract-reusable-ci.md); the table below is the intended
end state, not the current one.

| Repository | Visibility | Calls | Notable inputs |
| --- | --- | --- | --- |
| `python-app-baseline` | public | `python-ci`, `conventional-commits` | defaults throughout |
| `repo-factory` | public | `python-ci`, `conventional-commits` | `lint-changed-only: true`, `run-typecheck: false` |
| `opus-magnum` | private | `python-ci`, `conventional-commits` | `lint-changed-only: true`, `advisory-all-files: true`, `hook-stage: pre-push`, `mise-version` pinned |
| `python-cli-app-template` | public, template | `conventional-commits` only | — |

`opus-magnum` needs `hook-stage: pre-push` to keep current behaviour: it reserves mypy for that
stage, and without the input those hooks silently stop running on PRs.

`python-cli-app-template` has no `mise.toml`, which is why `conventional-commits.yml` installs `uv`
directly rather than through `mise-action` — dropping that would break the one repo that calls
nothing else.

`opus-magnum` is private and can still call these workflows because this repository is public. Were
it ever made private, every consumer would need
Settings → Actions → General → Access → "Accessible from repositories owned by 'turboBasic'".

`python-cli-app-template` is a GitHub template repository: every repo generated from it inherits its
call sites, so a breaking change there surfaces in repositories that do not exist yet. Migrate it
last and verify by generating a throwaway repo.
