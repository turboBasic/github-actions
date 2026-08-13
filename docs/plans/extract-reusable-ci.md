# Plan — extract the reusable CI surface into `turboBasic/github-actions`

Analysis and implementation plan for consolidating GitHub Actions across four repositories:
`python-app-baseline`, `opus-magnum`, `python-cli-app-template`, and `repo-factory`. Delete this
file once the extraction is done or abandoned.

**Status:** steps 1–3 done; the current major is **`v2`** and consumers pin `@v2`. Step 4, rewiring
the four consumers, is open — nothing is rewired yet. See [`../consumers.md`](../consumers.md).

## Decisions taken before drafting

| Question | Decision |
| --- | --- |
| Destination | New public repo `turboBasic/github-actions`, holding both reusable workflows and composite actions |
| Canonical CI idiom | Merge the best of both: `mise` tasks + SHA pins from `python-app-baseline`, plus pre-commit caching and changed-files scoping from `opus-magnum` |
| Consumer pinning | Moving major tag `@v2`, which this repo advances |
| Scope of this task | Plan document only |

## What exists today

12 workflows and 2 composite actions across the four repositories.

| Repo | Visibility | Workflows | Composite actions |
| --- | --- | --- | --- |
| `python-app-baseline` | public | `ci.yml`, `semantic-pull-request.yml` | — |
| `opus-magnum` | **private** | `lint.yml`, `conventional-commits.yml` | `precommit-advisory-pr` |
| `repo-factory` | public | `lint.yml`, `conventional-commits.yml`, `populate-pr-description.yml`, `create-repo.yml` | `populate-pr-description` |
| `python-cli-app-template` | public, **is a template** | `build.yml`, `build-documentation.yml`, `release-drafter.yml`, `maintain-labels.yml`, `pull-request-labeler.yml` | — |

`turboBasic/.github` already exists, is public, and holds `FUNDING.yml`, `ISSUE_TEMPLATE/`
(`0-user-story.yml`, `1-bug-report.yml`, `config.yml`), and a `PULL_REQUEST_TEMPLATE.md`, plus
shared `.editorconfig`, `.cspell/`, `.gitattributes`, and `.mailmap`.

### Two incompatible idioms, not one convention drifting

The four repos have converged into two mutually exclusive house styles. This is the central finding:
there is no single existing workflow to promote, because the two styles disagree about what CI *is*.

| Dimension | `python-app-baseline` | `opus-magnum` / `repo-factory` |
| --- | --- | --- |
| What runs the checks | `mise run lint` / `typecheck` / `test` | `pre-commit run` directly |
| Action pinning | full 40-char SHA + tag comment | floating `@v6`, `@v47` |
| mise version | unpinned (`mise-action` default) | pinned (`2026.4.20`, `2026.3.9` — already drifted apart) |
| Commit-message check | `cz check --rev-range` in the CI job | `wagoid/commitlint-github-action` as a separate job |
| Scope of lint | always all files | changed files on PR, all files on push |
| pre-commit env caching | none | `actions/cache` keyed on config hash |
| `timeout-minutes` | absent | present (5–20) |
| Concurrency group | present | absent |

`conventional-commits.yml` is **near-duplicated** between `opus-magnum` and `repo-factory` — the
only differences are the `cspell:ignore` line, `branches: [main]` vs a block sequence, and comment
placement. The job bodies are byte-identical. `lint.yml` differs in three substantive ways
(mise version, the `pull-requests: write` permission, and whether the advisory action runs), which
reads as drift rather than intent.

### Findings that change the design

1. **`tj-actions/changed-files@v47` is pinned to a floating tag.** That action is the subject of
   CVE-2025-30066 (CVSS 8.6): in March 2025 a threat actor retroactively repointed tags v1–v45.0.7
   at a malicious commit that leaked secrets into build logs. A floating tag on *this specific
   action* is the exact exposure that CVE describes. Both `opus-magnum` and `repo-factory` carry it.
   The extracted version pins `9426d40962ed5378910ee2e21d5f8c6fcbf2dd96 # v47.0.6`.
2. **Workflows are not inherited from `.github`.** The default community-health mechanism covers
   `CODE_OF_CONDUCT.md`, `CONTRIBUTING.md`, `SECURITY.md`, `SUPPORT.md`, `GOVERNANCE.md`,
   `FUNDING.yml`, discussion forms, and issue/PR templates — *not* `.github/workflows/`. Sharing CI
   therefore requires `workflow_call` with an explicit `owner/repo/.github/workflows/x.yml@ref`
   reference in every consumer. There is no ambient inheritance to lean on.
3. **Starter-workflow templates are organization-only.** The `workflow-templates/` directory in a
   `.github` repo surfaces "New workflow" suggestions for organizations. `turboBasic` is a personal
   account, so this is unavailable — reinforcing `workflow_call` as the only real mechanism.
4. **Private consumers work because the source is public.** `opus-magnum` is private but can call a
   reusable workflow from a public repo with no extra configuration. Had the destination been
   private, it would have needed Settings → Actions → General → Access →
   "Accessible from repositories owned by 'turboBasic'".
5. **Permissions can only be reduced down the chain, never elevated.** A reusable workflow declares
   what it needs; the caller's grant caps it. Secrets need explicit `secrets:` mapping or
   `secrets: inherit`. `env` does **not** propagate from caller to called workflow — anything the
   called workflow needs must arrive as an `input`.

## What is worth extracting, and what is not

Extraction is only justified where the logic is duplicated *and* stable. Three tiers:

### Tier 1 — extract now (clear duplication, stable logic)

| Artifact | Kind | Replaces | Why |
| --- | --- | --- | --- |
| `conventional-commits.yml` | reusable workflow | 3 near-identical copies (`opus-magnum`, `repo-factory`, and baseline's `semantic-pull-request.yml`) | Highest duplication in the set; job bodies already byte-identical in two repos. Pure policy, no repo-specific logic. |
| `python-ci.yml` | reusable workflow | `python-app-baseline/ci.yml`, and the lint half of the other two | The merged idiom lands here. Inputs absorb the legitimate variation. |
| `precommit-advisory-pr` | composite action | `opus-magnum` copy | 90 lines of `github-script` for an idempotent marker-based PR comment — the single most reusable and least trivial artifact, and currently reachable by exactly one repo. |
| `populate-pr-description` | composite action | `repo-factory` copy | Renders the PR template as Jinja2 from commit messages. Repo-agnostic already; fully input-driven. |

### Tier 2 — extract later, once a second consumer exists

- **`release-drafter.yml` + `maintain-labels.yml` + `pull-request-labeler.yml`** — all three live
  only in `python-cli-app-template`. Each is a thin wrapper (5–15 lines) around a third-party
  action, so extraction saves little today. The *configuration* is the valuable part
  (`release-drafter.yml`'s category map, the 15-label `maintain-labels.yml`). Promote when a second
  repo needs releases. **The label set and release-drafter config should move to `.github` sooner**
  than the workflows, since label taxonomy is genuinely account-wide.
- **`build-documentation.yml`** — GitHub Pages deploy. Currently `hatch`-based and Python 3.11;
  needs rewriting to the `mise`/`uv` idiom before it is worth sharing.

### Tier 3 — do not extract

- **`create-repo.yml`** (`repo-factory`) — the repo's entire *raison d'être*, not a shared concern.
  It calls `scripts/create_repo.sh` and needs `REPO_AUTOMATION_*` secrets. Leave in place.
- **`build.yml`** (`python-cli-app-template`) — `hatch` + dynamic matrix + PyPI publish via OIDC,
  on Python 3.11 with `codecov`. Architecturally incompatible with the `mise`/`uv` baseline. A
  shared `python-release.yml` is a *rewrite*, not an extraction, and belongs in its own task.
- **`dependabot.yml`** — cannot be shared at all; Dependabot requires the file in each repo. The
  three variants also disagree substantively: baseline groups by ecosystem with `commit-message`
  prefixes, `opus-magnum` sets `open-pull-requests-limit: 0` (updates *disabled*, security only).
  Best handled as a documented copy-paste exemplar, not a shared artifact.

## Target layout

As built (step 1 landed more than this section originally specified):

```text
turboBasic/github-actions/                 (public, not yet tagged)
├── .github/
│   ├── workflows/
│   │   ├── conventional-commits.yml       # reusable: PR title + commit messages
│   │   ├── python-ci.yml                  # reusable: mise lint/typecheck/test
│   │   ├── ci.yml                         # this repo's own checks, inline
│   │   └── semantic-pull-request.yml      # this repo's own PR title check
│   ├── ISSUE_TEMPLATE/ · PULL_REQUEST_TEMPLATE.md
│   ├── dependabot.yml · renovate.json     # Renovate owns updates; see the comment in dependabot.yml
│   ├── zizmor.yml                         # reasoned suppressions + pin policy
│   └── copilot-instructions.md
├── actions/
│   ├── precommit-advisory-pr/action.yml
│   └── populate-pr-description/{action.yml,populate.py}
├── docs/
│   ├── ai-instructions.md · consumers.md
│   └── plans/extract-reusable-ci.md       # this file
├── tests/test_action_pins.py              # machine-enforces the pinning rules
├── mise.toml · pyproject.toml · uv.lock · .pre-commit-config.yaml · cspell.config.yaml
├── .editorconfig · .gitattributes · .gitignore
└── README.md · CONTRIBUTING.md · CODE_OF_CONDUCT.md · SECURITY.md · LICENSE
```

Two deviations from the original sketch, both deliberate: `self-lint.yml` became `ci.yml` plus
`semantic-pull-request.yml` (the reason is in the header comment of each), and `tests/` exists
because the SHA-pinning rule is worth enforcing mechanically rather than by review.

Composite actions sit in `actions/<name>/` rather than `.github/actions/<name>/`. Consumers
reference `turboBasic/github-actions/actions/<name>@v2`; the `.github/actions/` location is a
convention for *repo-local* actions only and would read as private-by-convention here.

### Why not the existing `.github` repo

`.github` is load-bearing for silent inheritance: community-health files there apply to every repo
automatically. Tagging that repo `v1` to version a workflow would also tag the issue templates,
coupling two things with unrelated release cadences. Keeping them apart means `.github` stays
untagged and ambient, while `github-actions` is explicitly versioned and explicitly referenced.

## The merged CI idiom

`python-ci.yml` resolves each row of the divergence table deliberately:

```yaml
name: Python CI
on:
  workflow_call:
    inputs:
      mise-version:      { type: string,  required: false, default: '' }        # '' = action default
      python-versions:   { type: string,  required: false, default: '' }        # JSON array; '' = mise.toml
      run-typecheck:     { type: boolean, required: false, default: true }
      run-tests:         { type: boolean, required: false, default: true }
      check-commits:     { type: boolean, required: false, default: true }
      lint-changed-only: { type: boolean, required: false, default: false }
      advisory-all-files: { type: boolean, required: false, default: false }
      timeout-minutes:   { type: number,  required: false, default: 20 }
```

The shipped contract diverges from this sketch — read `python-ci.yml` and the README table, not
this block. `python-versions` and `check-commits` were dropped (the mise config decides the Python
version; commit checking belongs to `conventional-commits.yml`), and `run-lint`,
`lint-task`/`typecheck-task`/`test-task`, `hook-stage`, and `cache-pre-commit` were added.

Resolutions, and the reasoning for each:

- **`mise` tasks are the entry point**, not `pre-commit` directly. `ai-instructions.md` makes the
  task hierarchy non-negotiable and `mise run ci` the local reproduction of CI. Consumers on the
  pre-commit idiom gain a `lint` task that shells out to pre-commit — a one-line `mise.toml`
  addition, no behaviour change.
- **Every action pinned to a full SHA** with the tag as a trailing comment. Non-negotiable in
  `ai-instructions.md`, and CVE-2025-30066 is the concrete argument.
- **pre-commit caching kept** from `opus-magnum` (`actions/cache` keyed on
  `hashFiles('.pre-commit-config.yaml')`). Pure win, no downside.
- **changed-files scoping kept but opt-in and off by default.** It is a real speedup on large
  repos, but it means a PR can pass while the tree is broken. Default `false`; `opus-magnum`
  enables it and pairs it with `advisory-all-files: true`, which is exactly the compensating
  control that pattern was invented for.
- **`cz check --rev-range` wins over `commitlint`.** commitizen is already a pre-commit hook and a
  dev dependency in the baseline, so this drops a Node action from the graph. Requires
  `fetch-depth: 0` — the baseline already documents why.
- **`concurrency` at the caller, `timeout-minutes` at the callee.** A reusable workflow cannot set
  the caller's concurrency group, so that stays in each consumer (~4 lines). Timeouts belong with
  the steps that might hang.
- **`permissions: contents: read` declared in the reusable workflow**, raised only where a job
  genuinely posts (`pull-requests: write` for the advisory comment). Permissions cannot be elevated
  by the callee, so consumers must grant at the call site.

### Pinned SHAs for the extracted workflows

Verified against the GitHub API at the time of writing:

```text
actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1                      # v7.0.1
actions/cache@55cc8345863c7cc4c66a329aec7e433d2d1c52a9                        # v6.1.0
actions/github-script@3a2844b7e9c422d3c10d287c895573f7108da1b3                # v9.0.0
jdx/mise-action@7e36c90d9ab29c415a2384db3006f3ec8a8cc654                      # v4.2.4
astral-sh/setup-uv@c771a70e6277c0a99b617c7a806ffedaca235ff9                   # v9.0.0
amannn/action-semantic-pull-request@48f256284bd46cdaab1048c3721360e808335d50  # v6.1.1
tj-actions/changed-files@9426d40962ed5378910ee2e21d5f8c6fcbf2dd96             # v47.0.6
```

Renovate maintains these; the list above is the state at extraction, not a thing to keep in sync by
hand. `tests/test_action_pins.py` is what actually enforces the rule.

`wagoid/commitlint-github-action` is dropped entirely in favour of `cz check`.

## Consumer call sites after extraction

`python-app-baseline/.github/workflows/ci.yml` collapses to:

```yaml
name: CI
on:
  push: { branches: [main] }
  pull_request:
concurrency:
  group: ${{ github.workflow }}-${{ github.head_ref || github.run_id }}
  cancel-in-progress: true
jobs:
  ci:
    uses: turboBasic/github-actions/.github/workflows/python-ci.yml@v2
    permissions:
      contents: read
```

Per-repo settings:

| Repo | Calls | Notable inputs |
| --- | --- | --- |
| `python-app-baseline` | `python-ci`, `conventional-commits` | defaults throughout |
| `opus-magnum` | `python-ci`, `conventional-commits` | `lint-changed-only: true`, `advisory-all-files: true`, `mise-version: 2026.4.20` |
| `repo-factory` | `python-ci`, `conventional-commits` | `lint-changed-only: true`, `run-typecheck: false` (mypy via pre-commit), keeps `create-repo.yml` local |
| `python-cli-app-template` | `conventional-commits` only | `build.yml` stays until the hatch→uv rewrite |

Net effect: roughly 340 lines of workflow YAML across four repos becomes roughly 120 lines of call
sites plus one versioned source.

## Versioning

`@v2` moves; `v2.x.y` tags are immutable. Release flow: tag `v2.1.0`, then force-move `v2` to it.
Consumers pin `@v2` and pick up fixes on their next run. `v1` is frozen and unmaintained.

This deliberately differs from the "pin third-party actions to a SHA" rule, and the distinction is
load-bearing: the rule exists because a third-party tag can be retroactively repointed by someone
else (CVE-2025-30066 again). `turboBasic/github-actions` is under the same sole ownership as its
consumers, so the threat model differs — and SHA-pinning first-party workflows would mean four
Dependabot PRs for every one-line fix. Record this reasoning in the repo's README, since it reads
as an exception to a documented rule.

Dependabot in each consumer still tracks `@v2 → @v3` because the `github-actions` ecosystem covers
reusable-workflow references.

## Implementation steps

### 1. Create and populate the source repo

```bash
GH_TOKEN=$(gh auth token -u turboBasic) gh repo create turboBasic/github-actions \
  --public --description "Reusable GitHub Actions workflows and composite actions"
```

Scaffold per the layout above: `.editorconfig`, `.gitattributes`, `.gitignore`, `mise.toml`
(actionlint + shellcheck), `.pre-commit-config.yaml`, `README.md`. Then add
`conventional-commits.yml`, `python-ci.yml`, both composite actions (copied verbatim from
`opus-magnum` and `repo-factory`, with `@v6`/`@v9` floating refs replaced by the SHAs above), and
`self-lint.yml`.

Done. Also landed: `tests/test_action_pins.py`, `renovate.json`, `zizmor.yml`, and the
community-health files.

### 2. Tag the major — **done**

```bash
git tag -a v2.0.0 -m "..." && git tag -f v2 v2.0.0 && git push origin v2.0.0 && git push -f origin v2
```

Tag before verifying, not after: `precommit-advisory.yml` references
`actions/precommit-advisory-pr@v2`, and a reusable workflow cannot interpolate its own ref, so that
path cannot resolve at `@main` at all. Safe while no consumer is wired up — a wrong tag costs a
force-move.

### 3. Verify before any consumer changes — **done**

Lint cannot establish that a reusable workflow runs. Verify from a throwaway repository calling the
workflows at the major tag, and re-verify there after any change to a call contract:

- a valid PR title passes, an invalid one fails;
- `cz check` catches a bad commit, and a narrowed `types` input is enforced by *both* jobs;
- `conventional-commits.yml` passes in a repo with **no `mise.toml`**;
- the advisory workflow posts exactly one comment and *updates* it on a second push;
- `hook-stage: pre-push` runs the pre-push hooks, and omitting it skips them;
- `python-ci.yml` runs for a caller granting only `contents: read`.

The last two need a fixture the repo under test cannot supply by accident: a pre-commit hook defined
only for `pre-push` that echoes a marker and fails, and a second hook matching a file no PR touches,
so `--all-files` fails while the changed-files run passes.

### 4. Migrate consumers, one PR each, in this order

1. **`python-app-baseline`** — closest to the target idiom, so the smallest diff and the fastest
   signal. Also the exemplar other repos are compared against.
2. **`repo-factory`** — adds `mise.toml` tasks (it currently has none; `mise exec --` is called
   directly in workflows). Verify `create-repo.yml` still works, since it shares the toolchain
   setup being changed. Its `.mise.toml` also carries a `python.precompiled_flavor` setting with a
   comment about a mise bug — check that still applies before touching it.
3. **`opus-magnum`** — private, and the only consumer of the advisory workflow, so the only one
   granting `pull-requests: write`. Calls `python-ci.yml` *and* `precommit-advisory.yml`, passing
   `hook-stage: pre-push` to both: its `make lint-push` reserves mypy for that stage, and the two
   runs must agree on which hooks apply. Its `[tasks.lint]` shells to `make lint`, so the default
   `lint-task` picks it up with no change.
4. **`python-cli-app-template`** — `conventional-commits` only, which needs no `mise.toml` (the
   workflow installs `uv` via `setup-uv` rather than `mise-action`). **It is a GitHub template repo**,
   so every future generated repo inherits whatever lands here; a broken `@v2` reference propagates
   silently. Verify by generating a throwaway repo from the template and confirming CI is green.

Each PR: Conventional Commit title, and the docs updated in the same change per
`ai-instructions.md`.

### 5. Move account-wide config to `.github`

Independent of the workflow extraction: move `maintain-labels.yml` (the label taxonomy) and
`release-drafter.yml`'s category map from `python-cli-app-template` into `turboBasic/.github` as
the canonical copies. Label taxonomy is genuinely account-wide; the workflows that consume it are
not yet.

## Risks

- **A bad `@v2` breaks four repos at once.** This is the cost of a moving tag. Mitigated by
  step 3's throwaway-repo verification before every `v1` move, and by `v1.x.y` immutable tags
  giving consumers an escape hatch.
- **The escape hatch has one hole.** `python-ci.yml`'s advisory job references
  `actions/precommit-advisory-pr@v1`, because a reusable workflow cannot interpolate its own ref
  into `uses:`. A consumer pinned to `@v1.2.3` still gets the current `v1` action in that job.
  Documented under Versioning in the README; the alternative is inlining ~50 lines of the composite
  action into the workflow, which was rejected as the worse trade.
- **`python-cli-app-template` propagates silently.** Generated repos inherit the reference; a
  breakage surfaces in repos that do not exist yet. Migrate it last, verify by generating.
- **`cz check` needs `fetch-depth: 0`**, which is slower on large histories and fails confusingly
  if a consumer overrides checkout depth. The reusable workflow owns its own checkout, so consumers
  cannot override it — worth stating in the README.
- **Two tool-resolution paths for pre-commit.** `python-ci.yml`'s changed-files step uses
  `uv run pre-commit`; the composite action uses `mise exec -- pre-commit`. Both resolve in all four
  target repos — `repo-factory` and `opus-magnum` declare pre-commit under a `lint` group, but their
  `dev` group includes `lint` and `uv sync` installs `dev` by default, so `uv run pre-commit` works
  there too (verified). Still one convention too many for the same tool; worth unifying on `uv run`
  in the composite action, which would also drop its implicit dependency on mise.
## Abort

Nothing is destructive before step 4. Each consumer migration is a single PR that can be reverted. If the approach
proves wrong after tagging, revert the consumer PRs and leave `turboBasic/github-actions`
unreferenced; delete it only once no repo mentions it.
