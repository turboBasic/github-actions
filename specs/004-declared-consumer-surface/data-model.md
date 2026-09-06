# Data Model: Declared Consumer Surface

Phase 1. There is one entity, it lives in a committed file, and its whole lifecycle is one parse and one
render.

## The declaration

```toml
[tool.turbobasic-release]
surface-include = [".github/workflows/**", "actions/**"]
surface-exclude = [".github/workflows/ci.yml"]
```

| Key | Type | Absent means | Maps to |
| --- | --- | --- | --- |
| `surface-include` | list of strings | nothing is included by name, so every path is | `--include-path <p>` per entry |
| `surface-exclude` | list of strings | nothing is excluded | `--exclude-path <p>` per entry |

Both keys are optional within the table; the table itself is optional. Entries are `git-cliff` path
globs and are passed through unaltered — this repository does not interpret them, which is why an
unusable one is refused rather than repaired.

## Declaration state

Three states, and the third exists only because the surface is structured data rather than a string.

| State | How it looks | Filter | Notice |
| --- | --- | --- | --- |
| **Undeclared** | no `[tool.turbobasic-release]` table | unfiltered | yes — names the omission and where to fix it |
| **Declared** | table with at least one non-empty list | as declared | no |
| **Declared empty** | table present, both lists empty or absent | unfiltered | no |

Undeclared and declared-empty produce the **same filter**. That is a real limit, not a hidden feature: the
distinction buys only the notice, and it is worth having because it lets a caller who genuinely wants an
unfiltered range say so and stop being told about it. A string input could not have expressed the
difference at all, which is what forced an earlier draft to make a blank value mean "use ours"
([research.md D2](./research.md#d2)).

## Validation

Applied when the table is read, before any flag is rendered, and reported as an `::error::` that stops the
step. Both classes catch mistakes rather than defend a privilege boundary — a caller editing its own
`pyproject.toml` could equally edit its own workflow — but both have failure modes that are silent or
confusing without a check.

| Rule | Rejected because | Failure without it |
| --- | --- | --- |
| The value of either key is a list | a bare string is the obvious mistake, and iterating one yields characters | every character of the string becomes a path, and the filter matches nothing |
| Every entry is a string | TOML admits numbers and nested arrays | a non-string reaches an argument list |
| No entry is empty | `""` is not a path | an empty argument follows the flag, which `git-cliff` reads as a path matching nothing |
| No entry holds whitespace | the flags travel as one space-joined line, split with `read -ra` | the path silently becomes two, each matching nothing, and the refusal judges a range it should not have |
| No entry begins with `-` | it would arrive at the renderer as a flag | an unrelated `git-cliff` option is set, or the run fails with a message about a flag nobody wrote |

The whitespace rule is the one already implied by the existing suite, which asserts no surface argument
contains a space. It stops being a property of a constant we control and becomes a rule about caller data,
so it moves from an assertion to a refusal.

## Lifecycle

```text
pyproject.toml of the repository being released
  │  (already on disk: release.yml checks out the caller's tree,
  │   and PYPROJECT already points at this file)
  ▼
surface_config()      parse the table          → two lists, or "undeclared"
  ▼
unusable_paths()      validate                 → refuse, naming the path
  ▼
surface_args()        render                   → ["--include-path", "…", "--exclude-path", "…"]
  ▼
GITHUB_OUTPUT `args`  one space-joined line
  ▼
release.yml           read -ra                 → git-cliff --unreleased --context "${surface[@]}"
release-proposal.yml  mapfile                  → the same, for the increment it proposes
```

Nothing is stored, nothing is cached, and nothing is written back. The two workflows differ only in how
they read the rendered line — an existing difference this change does not touch.

## This repository's own declaration

Ours goes in our `pyproject.toml` and reproduces exactly what the deleted constants held, which is what
makes SC-001 a byte-identical comparison rather than an equivalence argument:

```toml
[tool.turbobasic-release]
surface-include = [".github/workflows/**", "actions/**"]
surface-exclude = [
  ".github/workflows/ci.yml",
  ".github/workflows/commit-messages.yml",
  ".github/workflows/dependabot-automerge.yml",
  ".github/workflows/drift.yml",
  ".github/workflows/release.yml",
  ".github/workflows/release-proposal.yml",
]
```

The exclusions are `OWN_CI` as workflow paths, and the suite holds them equal to it — the same assertion as
today, reading this file instead of a module constant ([research.md D4](./research.md#d4)). `OWN_WORKFLOWS`
in `decisions.py` was a second copy of that same set and is deleted, so the count of places `OWN_CI` is
restated goes down by one rather than up.

Omitting this table is the failure mode the move creates: our release would go unfiltered and start
refusing over changes to `ci.yml`, which is what 003 fixed. A test asserts the table is present, not merely
that its contents agree.
