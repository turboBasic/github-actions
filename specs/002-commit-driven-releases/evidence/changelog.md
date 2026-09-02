# Conventional-commit changelog generators — evaluation

Scratch research. Not documentation; nothing here is authoritative for repo behaviour.

All figures read from `gh api` on **2026-09-01T22:42Z / 2026-09-02** (UTC). No web search was
available: adoption or popularity claims beyond the star counts below are absent by design, and
anything not directly observed is marked `[unverified]`.

Everything under "Spikes" was run locally against real binaries — a throwaway git repo with one
commit of every allowed type plus a `feat!` carrying a `BREAKING CHANGE:` footer, and (for
git-cliff) this repository itself.

## Maintenance

| Project | Stars | `pushed_at` | Latest release | Archived |
| --- | --- | --- | --- | --- |
| `orhun/git-cliff` | 12194 | 2026-09-01 | `v2.14.1` 2026-09-01 | no |
| `changesets/changesets` | 12350 | 2026-08-31 | `@changesets/write@1.0.1` 2026-08-19 | no |
| `semantic-release/semantic-release` | 24011 | 2026-08-29 | `v26.0.0-beta.1` 2026-08-07 | no |
| `conventional-changelog/standard-version` | 7979 | 2026-07-16 | `v9.5.0` **2022-05-15** | no (but see below) |
| `googleapis/release-please` | 7433 | 2026-08-24 | `v17.11.2` 2026-08-24 | no |
| `commitizen-tools/commitizen` | 3499 | 2026-08-25 | `v4.18.0` 2026-08-19 | no |
| `cookpete/auto-changelog` | 1396 | 2026-05-29 | no GitHub releases; tag `v2.6.0` 2026-05-29 | no |
| `cocogitto/cocogitto` | 1180 | 2026-04-22 | `7.0.0` 2026-03-04 | no |
| `convco/convco` | 315 | 2026-08-31 | `v0.7.1` 2026-08-03 | no |
| `miniscruff/changie` | 902 | 2026-08-29 | `v1.26.0` 2026-08-20 | no |
| `knope-dev/knope` | 187 | 2026-09-01 | `versioning/v0.8.0` 2026-05-24 | no |

`standard-version`'s own README opens with: "**`standard-version` is deprecated**. If you're a
GitHub user, I recommend release-please as an alternative." Self-disqualifying.

## mise availability (`mise registry`, `mise latest`, 2026-09-02)

| Tool | Pin | `mise latest` |
| --- | --- | --- |
| git-cliff | `aqua:orhun/git-cliff` (registry short name `git-cliff`); also `npm:git-cliff` | **2.13.1** |
| cocogitto | `aqua:cocogitto/cocogitto` (short name `cocogitto`) | 7.0.0 |
| convco | no registry short name; `ubi:convco/convco` works (installed and run below), `cargo:convco` builds from source | 0.7.1 (`cargo:`) |
| commitizen | `pipx:commitizen` | 4.18.0 |
| release-please | `npm:release-please` | 17.11.2 |
| auto-changelog | `npm:auto-changelog` | 2.6.0 |
| standard-version | `npm:standard-version` | 9.5.0 |

Two notes that matter for pinning:

- **The aqua registry lags upstream**: `mise latest aqua:orhun/git-cliff` → `2.13.1` while GitHub's
  latest release is `v2.14.1`, published 2026-09-01T14:46Z, eight hours before this was read. Not a
  blocker — an exact pin is what `mise.toml` wants anyway — but Renovate will sit at 2.13.1 until
  aqua catches up. Reason for the lag is `[unverified]`.
- Renovate's `mise` manager documents support for `core, asdf, aqua, cargo, gem, github, go, npm,
  pipx, spm, ubi`, with caveats for aqua `http` package types and ubi entries using `tag_regex`.
  So both `aqua:orhun/git-cliff` and `ubi:convco/convco` are bumpable; a plain `ubi:` pin without
  `tag_regex` is inside the supported set.

## Capability comparison

Axes: (2) custom emoji section titles + explicit ordering, (3) breaking-change *footer text* and
dual placement, (4) a single release's range rendered *before* the tag exists, (5) config cost for
the seven sections, (6) full clone / stdout.

| Tool | Emoji titles + ordering | Breaking footer text | Both sections | Pre-tag range | Config cost | Clone / stdout |
| --- | --- | --- | --- | --- | --- | --- |
| **git-cliff 2.13.1** | yes, `commit_parsers[].group`; ordering via `<!--N-->` group prefixes stripped by a `postprocessors` regex — verified | yes, `commit.breaking_description` and `commit.footers[]` in the template context | yes — a Tera `filter(attribute="breaking")` block plus the normal `group_by`; verified, same commit rendered twice | yes, `--unreleased --tag v2.0.3`; `tag_pattern` excludes moving `v1`/`v2` | one `cliff.toml`: 8 parser lines + ~20 template lines | needs history + tags (`fetch-depth: 0`); stdout is the default sink |
| **convco 0.7.1** | yes, `.versionrc`/`convco.yml` `types[].section`; order = array order — verified | yes, renders the footer body under `⚠ BREAKING CHANGE` | yes, out of the box — breaking note *and* the commit under Features; verified | yes, `-u v2.0.3` titles the unreleased block with the version | ~14 lines of JSON, no template | same; `-o` defaults to `-` (stdout) |
| cocogitto 7.0.0 | yes, `[commit_types]` with `changelog_title` and an integer `order` (docs) | `[unverified]` for the built-in templates | `[unverified]` | `cog changelog --at`, `cog changelog a..b`, `..1.0.0`; pre-tag behaviour `[unverified]` | small config, or a custom Tera template with `macros::*` | git-based; stdout `[unverified]` |
| commitizen 4.18.0 | partially: `change_type_map` / `change_type_order` are top-level settings, but only for types the parser sees | no — the default `commit_parser` captures subject groups only | no | `cz changelog --unreleased-version` | see below — the parser cannot be widened from top-level config | git-based, writes `CHANGELOG.md` by default (`--dry-run` prints) |
| release-please 17.11.2 | yes, `changelog-sections[] {type, section, hidden}` per its `schemas/config.json` | via conventional-changelog notes `[unverified]` | `[unverified]` | no local path: its commands are `release-pr` and `github-release`, both GitHub-API driven | a manifest plus a release-PR workflow | needs a token and the network; no notes-to-stdout mode (`--dry-run` only "reports the activity that would happen") |
| auto-changelog 2.6.0 | not by commit type — it groups by tag and merge, templates are `compact`/`keepachangelog`/`json` | no | no | `-u/--unreleased` | you would reimplement conventional parsing in Handlebars helpers | git-based, `--output` or stdout |
| standard-version 9.5.0 | yes (config spec) | yes | yes | it tags and commits as part of the run | — | deprecated by its author |
| changesets | n/a | n/a | n/a | n/a | n/a — notes come from hand-written changeset files, not commits | n/a |
| semantic-release 24.x | via `@semantic-release/release-notes-generator` presets | yes | yes | it owns the whole release: tag, notes, publish | a Node toolchain plus plugin list | network + token; not a generator you call for a range |
| status quo: `gh release create --generate-notes` | seven sections already, from `.github/release.yml` | no — PR labels only, no commit body | a PR labelled both ways appears twice | notes are generated with the release | zero | needs neither clone nor stdout |

## Spikes

**git-cliff 2.13.1**, one `cliff.toml` (config at `/tmp/cliff.toml`, throwaway):

```text
## v2.0.3
### 💥 Breaking changes
* drop the old input (#99)
  the `foo` input is gone; pass `bar` instead.
### 🚀 Features
* subject for feat (#42083)
* drop the old input (#99) [breaking]
### 🐛 Fixes … 📚 Documentation … 🚚 CI and dependencies … 🧹 Maintenance
```

All twelve types landed somewhere (`perf`/`revert` folded into Fixes, `build`/`bump`/`ci` into CI
and dependencies, `chore`/`refactor`/`style`/`test` into Maintenance), the `(#N)` suffixes survived
verbatim, ordering held after the `<!--N-->` prefixes were stripped, and the breaking commit
appeared in both places with its footer text. Run against this repository the same config produced
the three commits since `v2.0.2` under Documentation and Maintenance, with the moving `v1`/`v2`
tags — both pointing at `main`'s tip — correctly ignored by
`tag_pattern = "v[0-9]+\\.[0-9]+\\.[0-9]+"`.

**convco 0.7.1**, a 14-line `.versionrc`, no template:

```text
## [v2.0.3](///compare/v2.0.2...6659b72) (2026-09-02)
### ⚠ BREAKING CHANGE
* the `foo` input is gone; pass `bar` instead.
### 🚀 Features
* drop the old input (#99) (a03172d), closes #99
…
```

Two blemishes, both cosmetic and both fixable: it prepends a `# Changelog` H1 even with
`--max-versions 1`, and it appends `(sha), closes #N` per line. `convco config --default` exposes a
`template: null` key, so the Handlebars templates are overridable — the exact override surface in
0.7.1 is `[unverified]`.

## Checking the two prior conclusions

**commitizen — confirmed, and the config question is answered "no".** From source at HEAD:
`commitizen/cz/conventional_commits/conventional_commits.py:37` is

```python
commit_parser = r"^((?P<change_type>feat|fix|refactor|perf|BREAKING CHANGE)(?:\((?P<scope>[^()\r\n]*)\)|\()?(?P<breaking>!)?|\w+!):\s(?P<message>.*)?"
```

and `changelog_pattern = defaults.BUMP_PATTERN`, whose entries are only `.+!`, `BREAKING CHANGE`,
`feat`, `fix`, `refactor`, `perf`. So `docs`, `chore`, `ci`, `test`, `build`, `style`, `bump` and
`revert` are dropped silently.

It cannot be widened from top-level config. `commitizen/commands/changelog.py` reads
`self.cz.commit_parser` and `self.cz.changelog_pattern` **off the plugin class only** (lines 193-194),
while `change_type_map` and `change_type_order` do fall back to `config.settings` (lines 99-105).
In `defaults.py`, `commit_parser` and `changelog_pattern` live in `CzSettings` — the `customize`
sub-table — not in `Settings`, and `cz/customize/customize.py:55` bails unless
`"customize" in self.config.settings`. Widening therefore means `name = "cz_customize"`, which
also replaces the commit-message plugin that validates our commits. Not worth it.

**git-cliff — confirmed and extended.** Reproduced independently above, plus the two things the
earlier spike had not established: the `BREAKING CHANGE:` footer *text* renders
(`commit.breaking_description`), and one commit can occupy two sections.

## Recommendation

**git-cliff**, pinned as `git-cliff = "2.13.1"` in `mise.toml` (`aqua:orhun/git-cliff`, the registry
short name, Renovate-bumpable), with a `cliff.toml` and

```sh
git-cliff --unreleased --tag "v$version" --strip header > notes.md
gh release create "v$version" --notes-file notes.md
```

Why it wins on this repo's constraints:

- A single pinned static binary. Nothing to `npm install`, no token, no network — `--remote.github`
  integration exists and stays off, which keeps `mise run ci` offline.
- It generates to stdout for a version that does not exist yet, so a rendering failure happens
  before `gh release create` and cannot leave a tag without a release.
- `tag_pattern` is the one feature that makes the moving `v1`/`v2` tags safe. Every git-log-based
  candidate needs an equivalent; git-cliff's is one config line and is verified.
- The template is the escape hatch for the two requirements plain type→section config cannot
  express: the breaking-footer text, and a commit in two sections.

Cost, stated plainly: ~30 lines of `cliff.toml`, of which ~20 are Tera. That is more than convco's
14 lines of JSON, and it is what buys requirements (3) and the ordering control.

**Runner-up: convco.** Smaller config, correct breaking behaviour with no template at all, stdout by
default. It loses on three things: 315 stars and one maintainer-scale project versus git-cliff's
12k, no `mise registry` short name (so `ubi:` or `cargo:`), and the fixed output shape — the
`# Changelog` H1 and the trailing `(sha), closes #N` would need either template overrides of
unverified scope or a `sed` in the release workflow. Pick it if the `cliff.toml` template is judged
too much machinery.

**Also worth saying: staying put is defensible.** `--generate-notes` already produces the seven
sections for zero configuration and zero new pins. The case for switching is that it categorises on
PR labels, so an unlabelled PR silently lands in "Other changes" — whereas a validated conventional
type cannot be absent. That is the whole benefit; if label discipline is not actually a problem in
practice, this is a change worth not making.

## Disqualified, why

- **commitizen `cz changelog`** — drops eight of the twelve allowed types, and the parser is only
  widenable by switching to `cz_customize`, which would displace the commit plugin that validates
  messages. Keep commitizen for what it already does; do not make it the generator.
- **standard-version** — deprecated by its author, last release 2022-05-15, README points at
  release-please.
- **release-please** — wrong shape. It owns a release-PR flow, manages a committed `CHANGELOG.md`,
  and its commands (`release-pr`, `github-release`) talk to the GitHub API; there is no
  render-a-range-to-stdout mode, so requirement (4) is unreachable. Also a Node dependency tree
  where a binary would do.
- **auto-changelog** — not conventional-commit driven at all. It groups by tag and merge; mapping
  twelve types to seven emoji sections means writing the parser yourself in Handlebars helpers.
- **changesets** — notes come from hand-authored changeset files, not commits. It also assumes npm
  package versioning. Nothing here is published.
- **semantic-release** — owns tagging, notes and publishing as one unattended pipeline, which
  directly contradicts the rule that the version is a reviewed one-line diff to
  `pyproject.toml`'s `[project].version`.
- **cocogitto** — closest to a real contender among the rejects and the reason it is not the
  runner-up is only evidence: `[commit_types].changelog_title` plus `order` reads exactly right in
  the docs, but its breaking-footer rendering, dual placement and pre-tag range behaviour are all
  `[unverified]` here, and `pushed_at` 2026-04-22 with the last release 2026-03-04 is the quietest
  of the three Rust candidates. Worth a spike only if git-cliff's template is rejected *and*
  convco's output shape is too.
- **changie** — fragment-file model like changesets, not commit-driven.
- **knope** — 187 stars, latest tagged release 2026-05-24, and it is a release-orchestrator rather
  than a notes generator. Too small a project to pin a release path to.
- **release-plz** — Rust-crate release automation (it wraps git-cliff for notes). Nothing here is a
  crate; the wrapper adds only cargo assumptions.

## `[unverified]` claims that matter

1. **The aqua-registry lag on git-cliff.** Verified as a fact (2.13.1 vs 2.14.1); the *cause* and
   its typical duration are not. If Renovate must track upstream promptly, `npm:git-cliff` also
   reports 2.13.1, so a `ubi:orhun/git-cliff` pin is the fallback — untested.
2. **convco's template override surface.** `template: null` exists in `convco config --default`, so
   overriding is clearly intended, but what a template file may redefine in 0.7.1 was not tested.
   The runner-up recommendation assumes only the default output, which was tested.
3. **cocogitto's breaking-change rendering and pre-tag range.** Docs-only, from a fetched page, not
   a binary. It is a reject on evidence, not on a demonstrated failure.
4. **release-please's notes internals** (whether breaking commits appear in both a breaking section
   and their type's section). Not tested — irrelevant to the verdict, which turns on requirement (4).
5. `git-cliff --strip header` — `-s, --strip <PART>` is present in 2.13.1's `--help`, but the flag
   was **not** exercised; the spike used a template that conditionally emits the version heading
   instead. Pre-flight the exact line, copied not retyped, before it goes in a workflow.
