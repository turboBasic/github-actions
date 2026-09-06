# Contract: the `[tool.turbobasic-release]` table

What a repository calling `release.yml` writes, and what it gets. This is the whole consumer-facing surface
of the feature — there is no input, no output and no permission to document.

## The declaration

In the `pyproject.toml` of the repository being released — the same file whose `[project].version` decides
which version that is.

```toml
[tool.turbobasic-release]
surface-include = ["src/**"]
surface-exclude = ["src/**/_generated/**"]
```

| Key | Type | Required | Default |
| --- | --- | --- | --- |
| `surface-include` | array of strings | no | none, meaning every path |
| `surface-exclude` | array of strings | no | none, meaning nothing excluded |

Entries are `git-cliff` path globs, passed through unaltered.

## What it changes

One refusal, and only that one. `release.yml` refuses to publish a version that is not a new major when the
range being released carries a breaking change **to the consumer surface**. This table is what "consumer
surface" means for your repository.

It does **not** affect the release notes, which describe the whole range, nor the two other refusals — a
version that is not ahead of the highest release, and a range that renders no notes. Those never depended
on the surface.

## Behaviour by declaration state

| Your `pyproject.toml` | The refusal considers | The run says |
| --- | --- | --- |
| no `[tool.turbobasic-release]` table | every path in the range | a notice: no surface declared, here is where to declare one |
| a table declaring paths | only what you declared | nothing |
| a table with both lists empty | every path in the range | nothing — you decided |

Declaring nothing is safe in the sense that matters: the refusal fires more often, never less. It cannot
let a breaking change through under a patch. It can refuse a release over a change nothing of yours
resolves, which is the cost of not having said.

## Rejected values

Each of these stops the release with an `::error::` naming the offending value, before the notes are
rendered and before any tag or release exists.

| Value | Why |
| --- | --- |
| `surface-include = "src/**"` | a string where an array belongs; iterating it would yield characters |
| `surface-include = ["src/**", 3]` | every entry must be a string |
| `surface-include = [""]` | not a path |
| `surface-include = ["my src/**"]` | the flags travel as one whitespace-split line, so this would become two paths matching nothing |
| `surface-include = ["-x"]` | would reach the notes renderer as a flag rather than a path |

A path with a space is the one worth knowing about in advance: it is a real limitation, not an oversight.
If you need one, say so — the fix is to change what the flags travel on, and it is deliberately not done
speculatively ([research.md D3](../research.md#d3)).

## Migrating from `@v4`'s earlier behaviour

Before this change, the refusal measured **this repository's** layout against your range:
`.github/workflows/**` and `actions/**`, minus workflow files whose names happened to match ours. That is
gone. If you were relying on it — you were not, because it could not have been right for you — declare the
equivalent explicitly.

Two directions it was wrong, both of which your table fixes:

- A breaking change to your own source was invisible, so the refusal never fired where it mattered.
- A breaking change to your own `.github/workflows/**` was refused under a patch, unless the file was
  called `ci.yml` or `release.yml`, which our exclusions named — so which of your plumbing files counted
  turned on filename coincidence.

Nothing about your call site changes. Adding the table is the whole migration, and not adding it leaves you
with the conservative fallback rather than a broken call.
