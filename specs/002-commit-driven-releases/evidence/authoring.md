# Commit-message authoring tooling

Research axis: the generator/prompter side of conventional commits. Validation is out of scope —
`cz check` on the `commit-msg` hook plus `conventional-commits.yml` already own that.

All figures read from `gh api` and `mise` on **2026-09-01/02**.

## The two facts that decide this axis

**1. Half the commits are not typed by a human.** 24 of 51 commits (47%) carry
`Co-Authored-By: Claude`; 35 of 39 PRs ever are one author, the other 4 Renovate. An interactive
prompter sits on a code path that is used less than half the time and shrinking. It cannot be wired
into the agent's path either: `prek`/`git commit -m` is non-interactive by construction, and a TTY
prompt in that position is a hang, not a gate.

**2. The prompter already installed here disagrees with the repo's own declaration.** commitizen's
`cz check` accepts all twelve —

```text
(build|bump|chore|ci|docs|feat|fix|perf|refactor|revert|style|test)
```

— but `ConventionalCommitsCz.questions()` offers only **nine** choices: `fix feat docs style
refactor perf test build ci`. Missing: `bump`, `chore`, `revert`.

`chore` is this repo's most-used type (17 of 51 commits; `chore` + `docs` = 61% of history). So
`cz commit`, the prompter this repo could adopt for free today, cannot produce its single most
common commit type. That is the whole axis in one line: the prompter is not just redundant, the
one on the shelf is *wrong* for this repo, and fixing it means `cz_customize` — a second, separately
maintained declaration of the twelve types, which
`test_allowed_types_match_the_commitizen_builtin_set` exists specifically to prevent.

## Candidates

| Tool | Stars | `pushed_at` | Latest release | mise install | Types → exactly 12? | Buys a solo author |
| --- | --- | --- | --- | --- | --- | --- |
| `commitizen` (`cz commit`) | 3,499 | 2026-08-25 | v4.18.0, 2026-08-19 | `pipx:commitizen` → 4.18.0 (already in `uv.lock` at 4.18.0) | **No** — prompt hardcodes 9, omits `chore`/`bump`/`revert`. Fixable only via `cz_customize`, a second declaration | Nothing it does not already do as a validator |
| `cocogitto` (`cog commit`) | 1,180 | 2026-04-22 | 7.0.0, 2026-03-04 | `aqua:cocogitto/cocogitto` → 7.0.0 (in registry) | Partially — `cog.toml` `[commit_types]` *adds* to the builtin set, it does not restrict it | Negative: a second validator and a second bumper competing with commitizen and `release.yml` |
| `convco` | 315 | 2026-08-31 | v0.7.1, 2026-08-03 | `cargo:convco` → 0.7.1 (no registry short name) | **No** — `CommitCommand` in `src/cli.rs` is one clap flag per type (`--fix --feat --build --chore --ci --docs --style --refactor --perf --test`) plus `--type <TYPE>`. Not config-driven | Same as above, plus a Rust toolchain build |
| `czg` / `cz-git` | 1,521 | 2026-08-22 | v1.14.0, 2026-08-22 | `npm:czg` → 1.14.0 | **Yes** — `types` array in `.czrc` / `cz.config.js`, single declaration. Best of the four on this criterion | The nicest prompt of the lot; still a prompt nobody reaches |
| `aicommits` | 9,095 | 2026-09-01 | v4.2.1, 2026-09-01 (npm at 4.2.0) | `npm:aicommits` → 4.2.0 | `type` config selects a convention, not a list `[unverified]` | Nothing — see below |
| `opencommit` | 7,528 | 2026-08-25 | tag v3.3.10, 2026-07-30. **No GitHub release since 2023** (latest release object is `github-action-v1.0.2`, 2023-05-21) | `npm:opencommit` → 3.3.10 | `OCO_OMIT_SCOPE` / prompt template, not a declarative list `[unverified]` | Nothing — see below |

None is archived. All six resolve through a mise backend, so "can it be pinned" is not a
differentiator here and should not be treated as one.

### The AI-assisted category is the wrong shape for this repo

`aicommits` and `opencommit` are the healthiest repos in the table by stars and recency, and the
least useful here. They shell out to an LLM with the staged diff and return a subject line. The
agent that wrote the diff already has the diff **plus** the issue, the spec, the review comments and
the conversation that produced it. Handing a second, blinder model the same diff to re-describe is a
strictly worse summary behind an extra API key and an extra network call in the commit path. They
solve "I have a diff and no words for it" — a problem that does not occur when a reasoning agent
authored the change.

They also both restate the type set in their own config or prompt, adding the same second-declaration
problem as `cz_customize` with less determinism.

## Recommendation: adopt nothing

An interactive commit prompter is **obsolete in this repository's workflow**. The argument:

1. The generator role is filled. An agent writes the message with more context than any prompter or
   diff-summariser can obtain.
2. The validator role is filled, by the tool that already ships here, reading the one authoritative
   type list.
3. A prompter is unreachable from the path that produces most commits, and adding one would create a
   second declaration of the twelve types — which the repo has a test specifically to forbid.
4. The one candidate that gets the type list right (`czg`) gets it right in a config file that is,
   by construction, that forbidden second declaration.

The steelman for adopting one — that a prompter *teaches* the convention and stops malformed
messages before the hook rejects them — is an onboarding argument. With one human author who wrote
the type list, there is nothing to teach. And the cost of a rejected commit message is retyping one
line, which is cheaper than a pinned dependency plus a config file plus the test that would have to
guard it.

### What would change the answer

- **A second or third human author.** The teaching argument becomes real the moment someone who did
  not write `conventional-commits.yml` starts committing. At that point `czg` is the shortlist of
  one, on its configurable `types` array — and the adoption cost includes a test asserting
  `.czrc`'s array equals the workflow's `types` default, mirroring
  `test_allowed_types_match_the_commitizen_builtin_set`.
- **commitizen shipping a config-driven prompt for `cz_conventional_commits`** that reads the same
  pattern `cz check` uses. That removes the second-declaration objection entirely, at which point
  `cz commit` is free and worth turning on. Not available in 4.18.0.
- **Commit messages becoming a recurring CI failure.** They are not: `bump` appears once and every
  type in the history is valid.
