# Conventional-commit validation tooling

Figures read 2026-09-01/02 via `gh api`, `mise registry`, `mise latest`, and local execution of
the actual binaries. Anything not established that way is marked `[unverified]`.

Baseline being compared against: `commitizen` 4.18.0 (in `uv.lock`, owns the `commit-msg` hook and
`cz check --rev-range` in CI) plus `amannn/action-semantic-pull-request` v6.1.1 for the PR title.

## Maintenance evidence

| Repo | Stars | `pushed_at` | Latest release | Archived |
| --- | --- | --- | --- | --- |
| `commitizen-tools/commitizen` | 3499 | 2026-08-25 | v4.18.0, 2026-08-19 | no |
| `conventional-changelog/commitlint` | 18719 | 2026-09-01 | v21.2.2, 2026-08-13 | no |
| `cocogitto/cocogitto` | 1180 | 2026-04-22 | 7.0.0, 2026-03-04 | no |
| `convco/convco` | 315 | 2026-08-31 | v0.7.1, 2026-08-03 | no |
| `crate-ci/committed` | 182 | 2026-09-01 | v1.1.11, 2026-02-25 | no |
| `jorisroovers/gitlint` | 970 | **2024-07-11** | **v0.19.1, 2023-03-10** | no |
| `compilerla/conventional-pre-commit` | 549 | 2026-07-20 | v4.4.0, 2026-02-18 | no |
| `amannn/action-semantic-pull-request` | 1380 | 2026-07-01 | v6.1.1, **2025-08-22** | no |

amannn's repo is not dead but is release-stale: the last three commits on `main` (2026-07-01,
2026-07-01, 2026-04-28) are Dependabot group bumps, and no release has shipped in ~12 months. It
declares `using: node24`.

## Comparison

| | mise install path | Exact latest | Closed type list? | PR title? | Local+CI parity, offline | Runtime |
| --- | --- | --- | --- | --- | --- | --- |
| **commitizen** | not in registry; `pipx:commitizen` works, or stay a `uv` dev dep (current) | 4.18.0 | yes — `cz_customize` `schema_pattern` (already how `conventional-commits.yml` does it) | **yes** — `cz check -m "$TITLE"`, verified working **outside a git repo** | yes, same binary both sides | Python (already required here) |
| **commitlint** | not in registry; `npm:@commitlint/cli` | 21.2.2 | yes — `type-enum`, verified rejecting `nope`, accepting `bump`, with no shareable config at all | yes, reads a message on stdin | yes | Node + **75 packages / 10.1 MiB** installed |
| **cocogitto (`cog`)** | `aqua:cocogitto/cocogitto` | 7.0.0 | **partly** — see below | yes, `cog verify "<msg>"`, works outside a git repo | yes | single static Rust binary |
| **convco** | **not in registry**; `ubi:`/`github:` backend resolves 0.7.1, or `cargo:convco` | 0.7.1 | yes, but with a footgun — see below | yes, `check --from-stdin`, **but requires a git repo** | yes | single static Rust binary |
| **committed** | `aqua:crate-ci/committed` | 1.1.11 | **yes, cleanly** — `style = "conventional"` + `allowed_types = [...]`; verified accepting `bump`, rejecting `nope` and non-conventional | yes, `--commit-file -`, **but requires a git repo** | yes | single static Rust binary |
| **gitlint** | not in registry; `pipx:gitlint` | 0.19.1 | yes — contrib rule `CT1 contrib-title-conventional-commits`, `types` option | commit messages only | n/a | Python |
| **conventional-pre-commit** | not in registry; pip / prek repo hook | 4.4.0 | yes — types are positional args | no; **no rev-range mode at all**, it takes one message file | one message at a time only | Python |
| **GitHub ruleset** (`commit_message_pattern`) | native, nothing to install | n/a | regex only, and the regex lives in GitHub settings | no | not runnable locally | none |

### The type-list findings, in detail (all executed, not read)

- **`cog` cannot be narrowed.** Its built-in allowed set is *exactly the twelve minus `bump`* —
  `bump` is rejected out of the box, `wip`/`improvement` too. `[commit_types]` only **adds**: with a
  `cog.toml` declaring only `feat`, `chore: x` still passed. So the twelve can be reached (`cog.toml`
  adding `bump`), but the list is never written down in one place — eleven of the twelve are cog's
  implicit default. A test asserting equality with commitizen's set would have to hardcode cog's
  defaults.
- **`convco` has a silent-fallback footgun.** A `types:` entry missing any of `type`/`increment`/
  `section`/`hidden` makes convco **discard the whole `types` block and use its defaults** — no
  warning. My first config listed all twelve as bare `- type: x` and `bump: …` was still rejected;
  `convco config` printed the stock ten. With all four fields per entry it enforced exactly the
  twelve, and narrowing to `feat` alone correctly rejected `chore`. A config that looks right can
  enforce something else.
- **`committed` is the only one that reads as a plain closed list.** Its error even echoes it:
  ``Disallowed type `nope` used, please use one of ["build", "bump", …]``. Note `style =
  "conventional"` also switches on `subject_length = 50`, `subject_capitalized`,
  `imperative_subject`, `subject_not_punctuated` — all off-switchable, but each is a
  consumer-visible behaviour change if adopted.
- **`commitizen`'s default set is exactly the twelve.** Verified one type at a time: all twelve
  ALLOWED, `improvement` and `wip` REJECTED.

### Git-repo requirement — the differentiator for the title job

The current title job checks out nothing. Verified in an empty non-git directory:

| | outside a git repo |
| --- | --- |
| `cz check -m "feat: ok"` | exit 0 |
| `cog verify "feat: ok"` | exit 0 |
| `committed --commit-file -` | **exit 64**, `could not find repository` |
| `convco check --from-stdin` | **exit 1**, `could not find repository at '.'` |

So `committed` or `convco` for the title means adding an `actions/checkout` to a job that currently
needs none.

## Recommendation

**Shortlist: (1) `cz check -m` for the PR title, dropping `amannn/action-semantic-pull-request`;
(2) keep `commitizen` for everything else.** No new tool.

`cz check -m "$TITLE"` is the whole change. It is the binary already in `uv.lock`, already driving
the `commit-msg` hook and the range check, and it accepts the *same* `cz_customize` config the
`commits` job already compiles from the `types` input — so both jobs would validate against one
generated `schema_pattern` instead of two independent implementations of "conventional-ish". It
removes a `node24` third-party action, its SHA pin, its `pull-requests: read` grant and its
`GITHUB_TOKEN`; the title comes from `github.event.pull_request.title` via `env`. It needs no
checkout. Caveats: the error output is `cz`'s terse one-liner, not amannn's PR-shaped message, and
the `-m` flag with `argparse` should be passed as `--message="${TITLE}"` (a leading-dash *subject*
after `feat:` was fine in testing, a leading-dash *title* would not be).

If a second, independent implementation is wanted as a cross-check rather than a replacement,
**`committed`** is the one: `aqua:crate-ci/committed` at 1.1.11, a single static binary, and the only
candidate where the twelve are a literal list in one config file. It costs a checkout in the title
job and brings four extra subject rules to switch off.

Why each other candidate lost:

- **commitlint** — the biggest tool for the smallest job. 75 npm packages and a Node runtime to
  re-implement a check `cz` already does, and it would give the commit-msg hook and CI two different
  engines, which is precisely the divergence `.pre-commit-config.yaml`'s comments already guard
  against. It does work with zero shareable config, which is nicer than expected.
- **cocogitto** — cannot express the twelve in one place (see above), and its release cadence is the
  slowest of the live Rust three (`pushed_at` 2026-04-22, release 2026-03-04). Otherwise it is the
  closest match: static binary, in mise's registry, works with no repo.
- **convco** — **not in mise's registry**, so it would be the only `ubi:`/`github:`-backend entry in
  a `[tools]` table of ten (and mise 2026.8.15 warns `ubi` is deprecated, removed in 2027.1.0, so it
  would have to be `github:convco/convco`). Renovate's mise manager does cover `github` and `ubi`.
  Combined with the silent `types` fallback, it is more risk than the incumbent for no gain.
- **gitlint** — disqualified, see below.
- **conventional-pre-commit** — no range mode, so it cannot do the CI half at all without a shell
  loop over commits. It is also `language: python` upstream, meaning prek would build its own copy at
  a `rev` Renovate bumps independently of `uv.lock` — the exact failure mode the existing
  `commitizen` hook comment was written to avoid.
- **GitHub ruleset `commit_message_pattern`** — verified present in the REST ruleset `rules[].type`
  enum. Rejected as a replacement, not as an idea: the regex would live in repository settings rather
  than in a reviewed file, it cannot be the single source for the twelve, it is not runnable in
  `mise run ci`, and it fires as a *merge/push rejection* rather than as a pre-merge required status
  check. Worth a line in a decision record as defence-in-depth, nothing more.
- **PR-title actions other than amannn** — all worse on maintenance or scope:
  `thehanimo/pr-title-checker` 130 stars, `pushed_at` 2024-11-25; `deepakputhraya/action-pr-title`
  138 stars, last release v1.0.2 in **2021-03-25**; `agenthunt/conventional-commit-checker-action`
  20 stars; `webiny/action-conventional-commits` 76 stars, release 2025-05-20;
  `wagoid/commitlint-github-action` 402 stars, `pushed_at` 2026-02-14 but **no releases via the API**
  (tags only) and it drags commitlint's Node tree in; `cocogitto/cocogitto-action` 41 stars;
  `tomtom-international/commisery-action` 13 stars. Every one of these is a *third* party to SHA-pin
  where `cz check -m` is a zero-dependency line.

## Disqualified

- **gitlint** — `pushed_at` 2024-07-11, last release **v0.19.1 on 2023-03-10**: over three years
  without a release and over a year without a commit. Not archived, but functionally dormant, and it
  would be the only Python linter here outside `uv.lock`'s control. Also commit-messages-only, so it
  cannot cover the title.
- **`deepakputhraya/action-pr-title`** — last release 2021-03-25.
- **`thehanimo/pr-title-checker`** — no activity since 2024-11-25.

## `[unverified]`, and which of it matters

- **Plan/visibility availability of ruleset metadata restrictions.** The rule type is in the REST
  enum, but the human-facing "Available rules for rulesets" docs page did not describe
  `commit_message_pattern` at all when fetched, so whether it is offered for a public repo on a free
  plan is `[unverified]`. Matters only if the ruleset idea is pursued.
- **Whether a squash merge's generated commit message is itself subject to
  `commit_message_pattern`** — `[unverified]`. This is the one that would decide whether a ruleset
  could ever replace the title check rather than supplement it.
- **`cz check -m` behaviour on a multi-line PR title, and its exit code on an empty title** —
  `[unverified]`; I tested single-line titles only. Worth one pre-flight before shipping the swap.
- **Adoption or trend claims for any tool** — not verifiable without web search. Star counts above
  are point-in-time only and are not evidence of momentum.
- **`gitlint`'s CT1 `types` option** — read from its docs page, not executed, since the tool was
  disqualified on staleness first.
- **Renovate's mise-manager backend list** — read from `docs.renovatebot.com/modules/manager/mise/`
  ("core, asdf, aqua, cargo, gem, github, go, npm, pipx, spm, ubi, and vfox"), not tested against
  this repo's `.github/renovate.json`.
