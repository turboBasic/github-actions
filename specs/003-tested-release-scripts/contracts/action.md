# Contract: `actions/release-decisions`

The one new public artifact. A composite action, so it runs inside the calling job and its files arrive
with the action download rather than with the workspace checkout — which is the whole reason it exists
([research.md D1](../research.md#d1)).

**Reference**: `turboBasic/github-actions/actions/release-decisions@v4`

Called only by `release.yml` (twice, with different `decision` values) and, by in-repo path rather than
by `uses:`, by `release-proposal.yml`. Not documented in `README.md`'s consumer sections beyond the
Actions list, because nothing outside this repository has a reason to call it.

## Inputs

`decision` is the discriminator. Every other input is optional and applies to a subset; `action.yml`
documents which, and each is mapped to `env` before the script runs — never interpolated into a shell
line (FR-011, Principle IV).

| Input | Required | Applies to | Meaning |
| --- | --- | --- | --- |
| `decision` | yes | all | `verify-version`, `check-notes`, or `next-version` |
| `pyproject` | no | `verify-version`, `next-version` | Path to the `pyproject.toml` to read `[project].version` from. Defaults to `pyproject.toml` in the workspace |
| `tag-refs` | no | `verify-version` | Newline-separated `refs/tags/…` list, as `gh api` produced it. The action does no network I/O of its own |
| `event-name` | no | `verify-version` | Selects the three-way severity. `push` or `workflow_dispatch` |
| `dry-run` | no | `verify-version` | `true` softens the not-ahead refusal to a notice |
| `notes-file` | no | `check-notes` | Path to the rendered notes, tested for content rather than size |
| `context-file` | no | `check-notes`, `next-version` | Path to `git-cliff --context` JSON over the **surface-filtered** range |
| `current-version` | no | `next-version` | The version to increment from. Defaults to `pyproject`'s |

## Outputs

| Output | From | Meaning |
| --- | --- | --- |
| `proceed` | `verify-version` | `true` when the later steps should run |
| `version` | `verify-version` | The validated declared version |
| `highest-major` | `verify-version` | Major of the highest existing release; empty when none exists |
| `breaking` | `check-notes`, `next-version` | The breaking verdict over the filtered range |
| `feature` | `next-version` | The feature verdict over the filtered range |
| `next-version` | `next-version` | The proposed version |
| `reason` | `next-version` | The one-line why, as a maintainer reads it |

## Behaviour the contract fixes

- **Exit non-zero only to refuse.** A refusal that must stop the release exits non-zero after emitting
  `::error::`. The not-ahead case on a `push` exits **zero** with `proceed=false`, because `ci.yml` calls
  release after every merge and most merges are not releases.
- **Every refusal happens before any tag exists.** The action never creates a tag, a ref, or a release;
  that is `release.yml`'s remaining shell (FR-007).
- **No network.** The action reads files and environment variables. `gh api` and `git-cliff` stay in the
  workflow, so their output arrives as an input path or a string. This includes the
  `workflow_dispatch`-only "is `ci / python-ci` green on this SHA" check-runs query, which is a `gh api`
  call and stays shell — the literal `"ci / python-ci"` must remain in `release.yml`, because
  `test_the_release_gates_on_a_required_context` asserts it is there.
- **No permissions block.** It inherits the calling job's, and needs none of its own (Principle III).
- **`python3`, not `uv run`.** The logic is standard-library-only, so there is nothing to resolve, and
  `release.yml` already depends on `python3` ([research.md D3](../research.md#d3)).

## What this contract does *not* include

The consumer-surface path list is **not** an input. It is a constant in the module, held to `OWN_CI` by
test. Making it an input is consumer-facing contract surface on `release.yml` and owns its own spec —
excluded by the spec's scope decision and by #61's comment.

## The self-reference wart, and the bootstrap it forces

`release.yml` must write `@v4` literally, because a reusable workflow cannot interpolate its own ref into
a `uses:`. `prek-advisory.yml:70` already carries this and documents it: the line moves with every major,
and left behind it pins a frozen tag so no later fix reaches a consumer.

**That literal `@v4` cannot be introduced in the same release that introduces the action.** At the merge
commit, `ci.yml` calls `release.yml`, which would resolve `actions/release-decisions@v4` — and `v4` still
points at the previous release, where the directory does not exist. Actions fails the job with
`Can't find action.yml`, so no release is cut, so `v4` never moves to include the action. That is a
permanent deadlock, not a one-run failure.

Pinning the branch instead is not available either: `test_first_party_actions_use_the_major_tag` requires
every `turboBasic/` reference to match `^v\d+$` *and* to equal the currently declared major, so a
`@003-tested-release-scripts` pin turns the suite red. Relaxing that gate to get past it is what
Principle VII forbids.

**So this ships as two releases**, and the split is the design rather than a scheduling preference:

| Stage | Contains | Why it is safe |
| --- | --- | --- |
| 1 | the complete action — module, `__main__`, all three decisions, `action.yml` — plus `release-proposal.yml` rewired to invoke it **by in-repo path** | No `uses:` is added, so nothing resolves `@v4`. `release-proposal.yml` only ever runs in this repository, so the path is always on disk. The release this stage cuts moves `v4` onto a tree that contains the action |
| 2 | `release.yml` rewired to `uses: …@v4` | `v4` now contains the action, so the reference resolves — including from a branch, which makes the dry-run dispatch and the `github-actions-test` run both reachable with no forbidden pin |

Stage 1 must ship the action **complete**, including the `verify-version` and `check-notes` decisions that
only `release.yml` will call. If stage 2 had to add them, its branch and `@v4` would hold different code
and the stage-2 verification would prove nothing.
