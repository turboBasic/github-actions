# Phase 0 Research: Tested Release Scripts

Every finding below was measured in this repository or read off GitHub, not assumed. Where a claim in
[`spec.md`](./spec.md) or issue #61 turned out to be wrong, that is stated.

## D1 — Where the Python lives {#d1}

**Decision**: one composite action, `actions/release-decisions/`, holding both the pure logic and a thin
`__main__`. `release.yml` reaches it with `uses:`; `release-proposal.yml` invokes the same file by its
in-repo path.

**Rationale**: this is forced, not preferred. `release.yml` declares `workflow_call`, and
`github-actions-test/.github/workflows/ci.yml` calls it as
`turboBasic/github-actions/.github/workflows/release.yml@v4`. Inside a reusable workflow
`github.repository` resolves to the **calling** repository, which is why `release.yml`'s
`actions/checkout` produces the caller's tree and why it reads the caller's `pyproject.toml` and releases
the caller — `github-actions-test` carries `v0.1.0`/`v0` from exactly this path. A file at
`scripts/verify_release.py` in *this* repository is therefore absent from that job.

An action is different: Actions downloads the action's own repository at the referenced ref, independent
of the workspace checkout, and `${GITHUB_ACTION_PATH}` points into it.
`actions/populate-pr-description/action.yml:47` already relies on this
(`uvx … python "${GITHUB_ACTION_PATH}/populate.py"`).

**This overturns the spec and the issue.** Both recorded the caller's-checkout problem as a trap for
"anyone who later widens this to a consumer-facing workflow". It applies now, to `release.yml`, because
`release.yml` already has a cross-repo caller. `spec.md` is amended accordingly.

**Alternatives considered**:

| Alternative | Rejected because |
| --- | --- |
| `scripts/` at repository root, as the issue proposes | Breaks `github-actions-test`'s call site — Principle I. This is the whole finding. |
| A `scripts-ref` input plus a second `actions/checkout` of this repository | New contract surface on a reusable workflow, which the spec scoped out; and GitHub exposes no context for a called workflow's own ref, so every consumer would have to keep the input in sync with its `@vN` pin by hand, with silent skew when it drifts. |
| Extract `release-proposal.yml` only, leaving `release.yml`'s shell | Leaves the refusal ladder — the tag-moving half — untested, *and* puts the surface path list in Python for one workflow and shell for the other. `#90` deliberately made the two copies identical after `#62` deadlocked a release on them disagreeing; splitting them across languages is worse than the status quo. |
| Drop `github-actions-test`'s `release` job so `release.yml` needs no external reach | Loses the only end-to-end proof that a real release works on tags nobody resolves, and retires `release / tag-and-publish` where `docs/consumers.md` records it as the only reporter. Against Principle VI. |
| A TypeScript/JavaScript action | Neutral on the actual blocker — it still has to live under `actions/` to be reachable, so it carries the same new-surface cost. Worse on two counts: Node has no TOML parser in its standard library at any version, so FR-003 would need a bundled dependency, `ncc`, a committed `dist/` and a freshness check; and this repository has no Node toolchain at all, against two config lines for Python. Its one edge, `using: node24` needing nothing from the caller, is moot — `release.yml` runs `python3 -c` twice today, so callers already supply Python. |

## D2 — How the suite imports it {#d2}

**Decision**: `[tool.pytest.ini_options].pythonpath = ["actions/release-decisions"]` and
`[tool.pyright].extraPaths = ["actions/release-decisions"]`.

**Rationale**: measured on a throwaway module and test in this repository, at these tool versions.

| Configuration | Result |
| --- | --- |
| both lines present | pytest 3 passed offline; pyright strict `0 errors, 0 warnings` |
| `extraPaths` omitted | pyright strict fails: `error: Import "probe_mod" could not be resolved (reportMissingImports)` **and** `error: Type of "next_version" is unknown (reportUnknownVariableType)` |
| `pythonpath` omitted | pytest cannot import the module at collection |

Both are needed, confirming #61's claim. The issue named only `reportUnknownVariableType`; the resolution
error comes first.

`[tool.pyright].include` and `[tool.ruff].src` already list `actions`, so neither needs a new entry for
type checking or lint discovery — only the two import-resolution lines above are new, plus `actions` in
`ruff.src` already covering isort's first-party classification. No bootstrap file and no `sys.path` shim.

**Alternatives considered**: a pytest bootstrap file inserting the path — rejected, it hides the dependency from
pyright, which needs its own `extraPaths` regardless. Making the action an installable package —
rejected, `[project].dependencies` stays empty and nothing is published (FR-015).

## D3 — How the script is executed on a runner {#d3}

**Decision**: `python3` directly, not `uv run`.

**Rationale**: the extracted logic is standard-library-only by FR-014, so there is nothing for uv to resolve.
`release.yml` already runs `python3 -c` twice today, so `python3` availability in that job is an existing
requirement rather than a new one, and both this repository's and `github-actions-test`'s `mise.toml`
pin `python = "3.14"`, which `mise-action` puts on `PATH` before any of these steps.

Measured for completeness: `uv run --script` works offline with no project present and no venv, and bare
`uv run` also works — but inside a project bare `uv run` implies a project sync, which `release.yml` does
not do and which would need the network. If a runtime dependency ever becomes unavoidable, `uv run
--script` is the escape hatch and the script is tested through its interface instead (FR-014).

**Constraint this imposes**: the extracted Python must parse under whatever `python3` resolves to. With
mise it is 3.14; without a mise config it is the runner's own. Keep the syntax conservative — no 3.14-only
constructs — since a caller with no `python` in its `mise.toml` falls back to the runner's interpreter.

## D4 — The action's interface {#d4}

**Decision**: one action with a required `decision` input naming which question to answer, plus the
inputs that question needs, all mapped to `env` in `action.yml`. Contract in
[`contracts/action.md`](./contracts/action.md).

**Rationale**: `release.yml` asks two distinct questions and #61's comment requires they stay two calls
with different arguments — the notes render reads the whole range, only the refusal reads the surface. One
action invoked twice keeps new public surface at a single name.

**Alternatives considered**: two cohesive actions (`verify-release`, `release-notes`) read better as
contracts, since "a consumer reads the input list as the contract", but double the new public surface for
something only `release.yml` calls. Recorded as the better choice if this ever gains a second caller.

## D5 — `actions/` versus `.github/actions/` {#d5}

**Decision**: `actions/release-decisions/`, following the written convention. **Flagged, not resolved
unilaterally.**

`docs/ai-instructions.md` says composite actions live in `actions/`, because `.github/actions/` "is the
convention for *repo-local* actions and would read as private-by-convention here". That rationale argues
the other way for this one: nothing outside `release.yml` should call it, and private-by-convention is
exactly the signal wanted. `.github/actions/` works mechanically — the path in a `uses:` reference is
arbitrary.

Following the written convention is the default because it is written, and because a reader looking for
composite actions looks in one place. This is a convention rather than a non-negotiable, so a request to
put it in `.github/actions/` is just a request, and it would be a one-line change to the plan.

## D6 — Holding the surface list to `OWN_CI` after the move {#d6}

**Decision**: `test_release_notes.py::test_the_surface_filter_agrees_with_own_ci` stops parsing YAML text
and imports the Python constant, comparing its exclusions to `OWN_CI` directly. A new assertion replaces
the old guard's other half: neither workflow may spell an `--include-path` or `--exclude-path` flag.

**Rationale**: today the test is parametrized over `SURFACE_FILTERED = ("release-proposal.yml",
"release.yml")` and reads the flags out of both files, because two identical shell copies were the only
reachable form. Once there is one definition the parametrization has nothing to iterate and the
text-scraping is the wrong shape — but the *guard* must survive, since it is what stops the two halves
disagreeing about what "breaking" means, which is what `#62` deadlocked on.

**Consequence for the increment**: this reduces the copies of that list from five to four — `OWN_CI`,
twice in `CONTRIBUTING.md`, and the new Python constant — and the two workflow copies go away. It does
**not** make the paths an input; that stays out of scope per the spec.

## D7 — Verification order, and why it is not the spec's {#d7}

**Decision**: `github-actions-test`, repointed at the **stage-2** branch, cuts a real release with the new
code before this repository's `main` does. Amended by [D9](#d9): repointing the *consumer* is fine, and
was always the cheap half. What D7 first assumed — that `release.yml` itself could be pinned at the branch
— is forbidden by an existing gate, which is why stage 2 exists and why nothing here is pinned.

**Rationale**: the spec framed the `@v4` pin as a lag to be tolerated — the new path proved externally
"on the release after". Re-examining it inverts the conclusion. `ci.yml` calls `release.yml` through the
`$/` self-call, which resolves at the merge commit, so **the moment this merges, the new code cuts this
repository's own release**. The question is not when `github-actions-test` catches up; it is whether the
first real tag-cutting run of new code happens against tags that are immutable — `refs/tags/v*.*.*` is
covered by a ruleset with `bypass_actors: []`, so a wrong tag here cannot be deleted by anyone — or
against `github-actions-test`'s, where `docs/consumers.md` says "a release that goes wrong here costs a
tag nobody resolves".

So the external route is pulled *earlier* rather than accepted late. Ladder in
[`quickstart.md`](./quickstart.md).

**Also found**: `release-proposal.yml` can be exercised **nowhere but this repository**. It has no
`workflow_call` trigger, so no other repo can call it, and its only manual route is
`workflow_dispatch`. Dispatching it from this branch writes the `release-proposal` branch and opens or
refreshes a real pull request — a real side effect needing cleanup, not a dry run. It has no `dry-run`
input and this change does not add one. Recorded as a task with explicit teardown.

## D9 — Two releases, not one {#d9}

**Decision**: stage 1 ships the complete action plus `release-proposal.yml`; stage 2 rewires
`release.yml`. Two pull requests, two releases.

**Rationale**: forced, by two facts that only became visible once the task list existed.

**The `@v4` reference cannot be introduced in the release that introduces the action.** At the merge
commit `ci.yml` calls `release.yml`, which resolves `actions/release-decisions@v4`; `v4` still points at
the previous release, which has no such directory. Actions fails with `Can't find action.yml`, so no
release is cut, so `v4` never moves to include the action. A permanent deadlock, not a transient failure.

**Pinning the branch instead is forbidden by an existing gate.**
`tests/test_action_pins.py::test_first_party_actions_use_the_major_tag` requires every `turboBasic/`
reference to match `^v\d+$` *and*, for self-references, to equal the major `[project].version` declares. A
`@003-tested-release-scripts` pin fails both halves. Relaxing that gate is precisely what Principle VII
forbids, and it is a supply-chain gate — widening it for developer convenience is the wrong trade.

The split resolves both at once. Stage 1 adds **no** `uses:`, because `release-proposal.yml` invokes the
module by in-repo path and only ever runs in this repository. Its release moves `v4` onto a tree
containing the action. Stage 2's `uses: …@v4` then resolves — from a branch as well as from `main` — so the
dry-run dispatch and the `github-actions-test` run are both reachable with nothing pinned and no gate
touched.

**Stage 1 must ship the action complete**, including the `verify-version` and `check-notes` decisions only
`release.yml` calls. If stage 2 added them, its branch and `@v4` would hold different code and the
stage-2 verification would prove nothing.

**Alternatives considered**:

| Alternative | Rejected because |
| --- | --- |
| One release, `release.yml` pinned at the branch during review and reverted before merge | Turns the suite red for the whole review, and the revert re-creates the deadlock at merge — the merged workflow resolves `@v4`, which does not yet contain the action |
| One release, exempt a feature-branch ref in `test_first_party_actions_use_the_major_tag` | Loosens a supply-chain gate to make a refactor convenient. Principle VII, and the exemption would outlive the change |
| One release, `release.yml` invokes the module by in-repo path like `release-proposal.yml` | Works for the `$/` self-call, where the checkout *is* this repository, and breaks `github-actions-test` — the original D1 finding |
| One release, accept `release.yml`'s first run being the merge that cuts it | That run is the deadlock. There is no first run |

## D8 — Line counts {#d8}

Re-measured, counting lines inside `run:` block scalars, since every figure in #61 was stale (now
corrected there):

| Workflow | All lines in `run:` blocks | Code only |
| --- | --- | --- |
| `release.yml` | 154 | 85 |
| `release-proposal.yml` | 147 | 106 |
| `conventional-commits.yml` | 15 | 13 |
| `python-ci.yml` | 7 (+4 single-line steps) | 5 |

The gap between the two columns is the point: `release.yml` is 45% comment, and much of that comment
exists to explain shell that will not survive this change. The comments that state a *rule* move to the
Python or to a test name; the ones that narrate an incident go, per `docs/ai-instructions.md`.
