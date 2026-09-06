# Research: Declared Consumer Surface

Phase 0. Every decision that shaped the plan, with what was rejected and why. The first is the one the
whole design turns on.

## D1

**Where the surface is declared: a table in the released repository's own `pyproject.toml`, not a
`workflow_call` input.**

**Decision**: `[tool.turbobasic-release]` in the `pyproject.toml` of whichever repository is being
released, carrying `surface-include` and `surface-exclude` as arrays of strings. No workflow input exists.

**Rationale**: the bind that forced this is that the list has two readers inside this repository, and only
one of them can see a constant.

| Reader | How it reaches the surface today | Under a required input |
| --- | --- | --- |
| `release-proposal.yml` | in-repo path to the module; reads its constant | reads its constant — unaffected |
| `release.yml` via `ci.yml` | the same constant, inside the action | `ci.yml` must *supply* our list → a second definition in YAML |

So a **mandatory** input puts our surface in two places, one of which the `OWN_CI` comparison cannot see —
which is the gate the input was supposed to protect. An **optional** input has to default to something,
and for any caller but us that something is our layout by coincidence: the exact defect #110 exists to fix,
promoted to documented behaviour.

Both horns come from the list living where only we can reach it. It does not have to. `release.yml` is a
reusable workflow, so `actions/checkout` inside it checks out the **caller's** tree — which is why it reads
the caller's `pyproject.toml` for `[project].version` and releases the caller. A table in that file is
per-repository by construction and needs no transport at all.

Verified rather than assumed:

- `PYPROJECT` already reaches the module with `pyproject.toml` as its default (`action.yml:86`,
  `decisions.py:167`), and `action.yml` already declares the matching input. **Nothing in any workflow or
  in `action.yml` needs to change.**
- Every caller necessarily has a `pyproject.toml`: the release cannot decide a version without
  `[project].version`. `github-actions-test` has one, beside the `src/` that is its real surface.
- The module already imports `tomllib` and already parses that exact file in `declared_version`. No new
  file, no new parser, no new dependency.
- This repository already configures `ruff`, `pyright`, `pytest` and `commitizen` under `[tool.*]` there.

**What it buys beyond removing the duplication**:

- **No input means no bypass.** There is nothing for a `workflow_dispatch` form or a caller's `with:` to
  override, so FR-010 is structural rather than tested.
- **Absent and empty become distinguishable.** A string input cannot tell "never set" from "set to
  nothing", which is the only reason an earlier draft had to make a blank string mean "use ours". A missing
  table versus `surface-include = []` is unambiguous, and FR-003 spends the difference on a notice.
- **One fewer interpolation hop.** The paths never pass through `${{ }}` at all (principle IV).
- **Per-repository is the right granularity.** A repository has one surface; nothing wants two calls with
  different ones.

**Alternatives considered**:

- *The input as #110 asked, with `needs` plumbing.* Confirmed workable — GitHub's context-availability
  table allows `github, needs, strategy, matrix, inputs, vars` in `jobs.<job_id>.with.<with_id>` — so
  `ci.yml` could run a job emitting the module's list and pass it in, keeping one definition. Rejected: it
  still costs a major bump for `required: true`, adds a job to every push to `main`, and forces
  `ci.yml`'s release job to `needs: [ci, surface]`, which trips
  `test_the_release_waits_for_the_ci_verdict`'s `needs:\s*\[\s*ci\s*\]`. Loosening *that* regex to buy a
  required input is a bad trade against principle VII.
- *A dedicated `.github/consumer-surface.json`.* Same shape, plus a file. YAML is impossible — the module
  is standard-library-only and there is no stdlib YAML parser. JSON works and earns nothing over a table in
  a file that is already read and already parsed.
- *A third-party action or `yq`.* A pinned supply-chain dependency to solve a data-location problem, and
  none of them correlate a path match with a commit's breaking flag, which is the actual decision.
- *Both: table as default, input as override.* Two mechanisms, two things to document, and the input
  reinstates the bypass the table removes. Available later if a per-call override is ever wanted.

## D2

**What an undeclared surface means: unfiltered, with a notice.**

**Decision**: no table → no `--include-path` or `--exclude-path` flags at all, so the whole range is
considered and the refusal fires on any breaking change. The decision prints a `::notice::` naming the
omission and where to fix it. A table present but empty gets the same filter and no notice.

**Rationale**: fail closed. Over-refusing is an argument a maintainer can read and answer; under-refusing
publishes a broken contract under a moving tag. And it is only affordable *because* of D1 — with our own
table in our own file, the conservative fallback no longer regresses our release, which is what killed
this option while a coincidental default was in play.

Note the honest limit: absent and declared-empty produce the **same filter**. The distinction buys only the
notice — which is worth it, because it lets a caller who genuinely wants an unfiltered range say so and
stop being told.

**Alternatives considered**:

- *Refuse and demand a table.* Most honest, zero guessing, but it breaks `github-actions-test`'s call site
  until it declares one, which by principle I is a new major. Not worth a major on its own; available as a
  later tightening once every caller has a table.
- *Fall back to our list with a warning.* Ships as a patch and changes nothing observable, but keeps the
  coincidental default — merely no longer silent. Rejected: the coincidence is the defect, not its volume.
- *Refuse nothing when undeclared* (treat "no surface" as "nothing is surface"). Turns a safety gate off by
  default. Never considered seriously; recorded because it is the reading a naive `paths or []` would give.

## D3

**A path that cannot survive the carrier is refused, not supported.**

**Decision**: reject a path that is empty, holds whitespace, or begins with `-`. One pure predicate, and
the refusal happens in the `surface-args` step — before the notes render and before any ref exists.

**Rationale**: the flags travel from the decision to `release.yml` as one space-joined line and are split
with `read -ra`, a property the suite already asserts. A caller-supplied path holding a space would become
two paths, each matching nothing, and the refusal would then silently pass a range it should have judged.
A leading `-` would reach the renderer as a flag rather than a path. Neither is a privilege boundary — a
caller editing its own repository could pass anything — but both are typos whose natural failure is
confusing, and all three checks are one comprehension.

**Alternatives considered**:

- *Change the carrier to a multi-line value and read it back line by line*, as `release-proposal.yml`
  already does with `mapfile`. This would make paths with spaces work. Rejected for now: it means a
  heredoc-delimited `GITHUB_OUTPUT` write, hence a delimiter that must not collide with any content —
  trading a documented constraint for a new hazard, to serve a case no caller has. It is the recorded
  upgrade path, and the trigger is a caller that genuinely needs a space.

## D4

**Where the `OWN_CI` gate goes.**

**Decision**: `test_the_surface_exclusions_are_own_ci_as_workflow_paths` keeps asserting the same equality
and changes only where it reads the left-hand side — our `pyproject.toml` instead of a module constant.
`OWN_WORKFLOWS` is deleted from the module.

**Rationale**: the gate is *relocated*, not relaxed, and that distinction is principle VII. It is also a
net deletion: `OWN_WORKFLOWS` in `decisions.py` was a second copy of `OWN_CI` held equal by that very test,
and it stops existing. A third assertion is added for the failure mode the move creates — our table
missing entirely, which would put our own release on the unfiltered path.

## D5

**Naming.**

**Decision**: `[tool.turbobasic-release]`, with keys `surface-include` and `surface-exclude`.

**Rationale**: owner-scoped, so it cannot collide with a real tool's table. Named for what a consumer
thinks it is configuring — the release — rather than for `release-decisions`, an internal action they never
reference and which can be renamed without invalidating every consumer's config. The keys match
`git-cliff`'s `--include-path` / `--exclude-path` so the mapping needs no explaining.

**Alternatives considered**: `[tool.release-decisions]`, matching the action name — rejected because it
couples a consumer-facing config key to an internal file path. A nested
`[tool.turbobasic-release.surface]` — rejected as one level of nesting for two keys.

## D6

**Deriving this repository's surface instead of declaring it — rejected, and worth recording.**

Our surface is genuinely computable: `actions/**` plus every `.github/workflows/*.yml` declaring
`workflow_call`, which is exactly the property `test_every_reusable_workflow_declares_workflow_call`
already asserts is the complement of `OWN_CI`. Deriving it would delete our list rather than relocate it.

Rejected because it generalises to no consumer — a consumer's surface is its package source, which no rule
over the tree can find — so it would mean deriving ours and requiring theirs: two mechanisms for one
question, and the shared code path FR-009 depends on gone. Recorded because it means `OWN_CI` is
information already present in the files, and if that ever becomes worth collapsing it is a separate change
with its own argument.

## D7

**Version increment: a minor, and no major.**

**Decision**: minor. `README.md`'s Versioning section owes a major when the call site stops working, a
required check stops reporting, or a permission a caller must grant changes. None applies: the interface
delta is empty. Behaviour does move for an undeclared caller, in the stricter direction, which is
consumer-visible and therefore not a patch.

The number itself stays a human decision on a one-line diff, as always — `release-proposal.yml` proposes it
and a reviewer may change it. A `feat:` title is what makes the proposal a minor, and this change touches
`actions/**`, which our own declared surface includes, so the proposal computes one without help.
