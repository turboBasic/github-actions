# Contract: the rendering

One `.cliff.toml`, three callers, one output shape. This is the interface between them — what each
caller invokes, what it gets back, and what it must refuse on.

Not a consumer-facing contract: nothing outside this repository resolves any of it. It is written down
because three call sites sharing a config is exactly where a drift goes unnoticed.

## Invocation

| Caller | Command | Working ref |
| --- | --- | --- |
| `release-proposal.yml` | `git-cliff --unreleased` | `main`'s tip |
| `release.yml` | `git-cliff --unreleased` | the commit being released, checked out at that SHA |
| `mise run release-notes` | `git-cliff --unreleased`, or `git-cliff <from>..<to>` for an arbitrary range | whatever is checked out |

- **No `--config` flag.** `--config`'s default is the literal `cliff.toml`, but git-cliff's discovery is
  wider than that default: it searches the working directory and its ancestors for `cliff.toml` *and*
  `.cliff.toml`. Verified against 2.13.1 — with only a `.cliff.toml` present it logs
  `Using configuration from parent directory: …/.cliff.toml` and renders from it. So there is no path to
  keep correct in three call sites. `-c .cliff.toml` is the explicit fallback if that discovery ever
  narrows.
- **`git-cliff --init` writes `cliff.toml`, not the dotfile.** Anyone running it here would create a
  second config that then wins by name. Not worth a guard; worth the comment at the top of the file.
- **No `--tag`.** The template emits no version heading — the release's title is the tag already, and
  the proposal's heading is its pull request title. This also sidesteps `--strip header`, which
  `evidence/changelog.md` flags as present in 2.13.1's `--help` but unexercised.
- **`--unreleased` means "since the newest tag matching `tag_pattern`"**, which is what excludes the
  moving `v1` / `v2` tags. See data-model.md.
- Output goes to stdout, redirected to a file. `gh release create --notes-file` reads that file;
  no commit text is ever interpolated into a `run:` line.

## Output

Markdown, no leading H1, sections in the fixed order of data-model.md's table, empty sections omitted.

```markdown
### 💥 Breaking changes

- **drop the old input** (#99) — the `foo` input is gone; pass `bar` instead.

### 🚀 Features

- subject for feat (#42)
- drop the old input (#99)
```

The breaking commit appears twice, and only the first occurrence carries its explanation. Verified in
`evidence/changelog.md`'s spike against a real binary.

**The explanation is the footer's first paragraph, not all of it.** Conventional Commits ends a
`BREAKING CHANGE:` footer's value at the next footer-looking line, so a commit whose body continues with
several paragraphs of rationale puts all of them in that one bullet. v2.0.0's happens to stop after one
sentence, but only because a body line begins `advisory-all-files:` and the parser reads it as a new
footer — a long-bodied `feat!:` would render a bullet of paragraphs. `split(pat="\n\n") | first` takes
the "what broke" statement and leaves the reasoning in the commit message, which is where a reader who
wants it will look.

`(#99)` survives verbatim from the squash-merge subject, and GitHub renders it as a link in a release body —
which is why no pull-request-link configuration is needed and git-cliff's `--remote.github` integration
stays off (FR-015).

## The three facts a caller reads back

| Fact | How | Refusal it drives |
| --- | --- | --- |
| Notes are empty | the redirected file has zero size | FR-007 — the proposal is not raised; a release fails with an explicit error and creates no tag |
| The range contains a breaking change | `git-cliff --unreleased --context \| jq 'any(.[].commits[]; .breaking == true)'` | FR-012a — a release refuses unless the version is a new major |
| A `feat` touched the consumer surface | the same, plus `--include-path` / `--exclude-path` scoped to the surface | the increment the proposal proposes |

**All three were exercised against 2.13.1**, on a throwaway repository carrying one commit of every
shape on distinguishable paths. The harness itself was scratch in gitignored `tmp/`; the configuration
it validated is preserved in the appendix below. What it established:

- **An empty range is `exit 0` with zero bytes on stdout and no warning** — for a range holding only a
  `bump` and for a range holding nothing at all, indistinguishably. So FR-007 is a **file-size check**,
  never an exit-code check. A workflow that trusted the exit code would publish an empty release body.
- **A *broken* range is `exit 1`**, with
  `SetCommitRangeError("v1.1.0..v2.0.0", … "revspec 'v1.1.0' not found")`. So the two failures are
  distinguishable and must be handled separately: a non-zero exit is a bad range or a bad config and is
  a hard error; a zero exit with an empty file is FR-007's "nothing to release". Conflating them would
  either publish an empty body or refuse a legitimate release because a tag lookup misfired.
- **`--context` carries a per-commit `breaking` boolean — but the key is *absent*, not `false`, on a
  commit that matched no Conventional Commit.** Hence `.breaking == true` in the jq above rather than
  `.breaking`: the naive form yields `[false, false, false, true, null, false, false]`, and a `null`
  in a boolean test is how this reaches production as a wrong answer. The probe's own first attempt
  passed only because `any()` short-circuited on the `true` before reaching the `null`.
- **A detached HEAD renders identically.** `release.yml` checks out the released SHA, not a branch, and
  `--unreleased` still resolves the same lower bound there — verified in a detached worktree. No
  `--use-branch-tags` needed.
- **The path filters do exactly what the version proposal needs.** Given commits touching
  `.github/workflows/python-ci.yml`, `.github/workflows/ci.yml`, `README.md`, `actions/thing/action.yml`,
  `pyproject.toml` and an untyped subject, the filtered pass kept exactly two: the consumer-facing
  `feat` and the breaking `actions/` commit. Own-CI commits, the README fix, the bump and the untyped
  commit were all dropped.

**`jq` is pre-installed on `ubuntu-latest`**, so this adds no tool. Locally it arrives with the
existing toolchain; it is not pinned in `mise.toml` and does not need to be for a boolean read.

## The mapping, and what holds it

`.cliff.toml` is the single declaration of type-to-section. `tests/test_release_notes.py` reads it as
TOML — offline, no git-cliff invocation, so `mise run ci` still passes on a shallow clone — and asserts:

1. every one of the twelve allowed types is either placed in a group or explicitly skipped;
2. the seven titles are exactly data-model.md's, in that order;
3. `bump` is the only skipped type;
4. the catch-all parser is last, since `commit_parsers` is first-match-wins;
5. `tag_pattern` still excludes two-component tags, so the moving majors cannot re-enter.

Assertion 1 is the one that matters most over time: a type added to `conventional-commits.yml`'s
`types` default and not to `.cliff.toml` would silently land in Other changes, which is FR-003's
intended behaviour for an *unknown* type and a defect for an allowed one.

**A sixth assertion belongs to the same file but not to the same object**: that the consumer-surface
path filter agrees with `OWN_CI` in `tests/test_action_pins.py` (research.md decision 9). That filter
is a set of `--include-path` / `--exclude-path` **flags in `release-proposal.yml`**, not a key in
`.cliff.toml` — git-cliff takes them only on the command line — so the assertion reads a workflow as
YAML and cannot be written until that workflow exists. It therefore lands with the workflow rather than
with the five above, which are complete as soon as `.cliff.toml` is.

## Appendix: the verified candidate configuration

Reproduced here because the probe harness lives in gitignored `tmp/`, and this is the artifact worth
keeping. It is the evidence spike's template with the four corrections research.md decisions 1 and 3
record: `bump` skipped rather than grouped, a `'''` literal body, the footer's newlines collapsed, and
Tera whitespace control in place of a trailing backslash.

**Copy this into `.cliff.toml`; do not retype it.** Every behaviour asserted above was observed from
exactly these bytes, and the repo's own rule is that a retyping tests the typing.

```toml
[git]
conventional_commits = true
filter_unconventional = false
protect_breaking_commits = true
tag_pattern = "v[0-9]+\\.[0-9]+\\.[0-9]+"
commit_parsers = [
  { message = '^bump(\([^)]*\))?!?:', skip = true },
  { message = "^feat", group = "<!--2-->🚀 Features" },
  { message = "^fix", group = "<!--3-->🐛 Fixes" },
  { message = "^perf", group = "<!--3-->🐛 Fixes" },
  { message = "^revert", group = "<!--3-->🐛 Fixes" },
  { message = "^docs", group = "<!--4-->📚 Documentation" },
  { message = "^(ci|build)", group = "<!--5-->🚚 CI and dependencies" },
  { message = "^(chore|refactor|style|test)", group = "<!--6-->🧹 Maintenance" },
  { message = ".*", group = "<!--7-->Other changes" },
]

[changelog]
trim = true
body = '''
{%- set breaking = commits | filter(attribute="breaking", value=true) -%}
{% if breaking | length > 0 %}
### 💥 Breaking changes
{% for commit in breaking %}
- {{ commit.message }}{% if commit.breaking_description and commit.breaking_description != commit.message %} — {{ commit.breaking_description | split(pat="\n") | join(sep=" ") | trim }}{% endif %}
{%- endfor %}
{% endif %}
{% for group, commits in commits | group_by(attribute="group") %}
### {{ group | upper_first }}
{% for commit in commits %}
- {{ commit.message }}
{%- endfor %}
{% endfor %}'''
postprocessors = [{ pattern = '<!--[0-9]+-->', replace = "" }]
```

Still owed when this becomes `.cliff.toml`:

- a header comment naming the file, since `git-cliff --init` writes the non-dotted name and would
  create a rival config (research.md decision 1);
- squeezing the double space that collapsing a paragraph break leaves in a long footer;
- `taplo fmt` will reformat the tables — run it and commit the result rather than fighting it.
