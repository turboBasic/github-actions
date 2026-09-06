# Phase 1 Data Model: Tested Release Scripts

The spec's Key Entities, made concrete. Nothing here is persisted — every entity is a value derived
inside one job and either written to `GITHUB_OUTPUT` or discarded. There is no store and no schema
migration.

## Version

A plain three-part semantic version. The only form this repository releases.

| Field | Type | Notes |
| --- | --- | --- |
| `major` | int | The consumer-resolved tag is `v{major}` |
| `minor` | int | |
| `patch` | int | |

**Validation**: the whole string must match `^[0-9]+\.[0-9]+\.[0-9]+$`. No pre-release, no build
metadata, no `v` prefix — the `v` belongs to the tag, not the version. A value failing this refuses the
release before anything is tagged (FR-004).

**Ordering**: component-wise on the integer triple, never lexicographic. `sort -V` is what the shell
used; the replacement compares tuples, which is why `4.10.0 > 4.9.0` cannot regress.

**Source**: `[project].version` of the checked-out `pyproject.toml`, read as TOML and keyed by table
(FR-003). Never the first `version =` line, because a positional match would take the version from
whichever table came first.

## ReleaseSet

The existing releases, as read from the repository's tags.

| Field | Type | Notes |
| --- | --- | --- |
| `versions` | list[Version] | Tags matching `v` then a valid Version. Anything else is discarded |
| `highest` | Version \| None | `None` when nothing has been released |

**Validation**: computed across **all** majors, not within the declared version's major, because a
frozen major is never backported — only left where it is. `highest` being `None` must permit the
release rather than refuse it or raise (spec Edge Cases).

**Source**: `gh api …/git/matching-refs/tags/v`, which stays shell (FR-007). The Python receives the
already-fetched ref list.

## Verdicts

The two booleans that drive the increment, taken from the surface-filtered range.

| Field | Type | Notes |
| --- | --- | --- |
| `breaking` | bool | True when any commit in range carries `breaking == true` |
| `feature` | bool | True when any commit's raw message starts with `feat` |

**Validation**: `breaking` is read as an identity test against `true`, never as truthiness. git-cliff's
`--context` **omits the key entirely** on a commit matching no Conventional Commit, so an absent value
must read `false` rather than raise or answer true-ish. This is the second of the two defects #61 names,
and it gets a test by name (SC-002).

**Source**: the JSON `git-cliff --unreleased --context` emits, parsed with `json`. Replaces the two
inline `jq` filters (FR-005).

## ConsumerSurface

The paths a consumer resolves. One definition, replacing the identical copy in each workflow (FR-006).

| Field | Type | Notes |
| --- | --- | --- |
| `include` | tuple[str, ...] | `.github/workflows/**`, `actions/**` |
| `exclude` | tuple[str, ...] | `.github/workflows/<name>` for each name in `OWN_CI` |

**Validation**: `exclude` must equal `OWN_CI` mapped into workflow paths, asserted by importing both
rather than by scraping YAML text (D6). A workflow in one list and not the other either proposes a minor
for something no consumer resolves, or refuses a release over a file nobody reads.

**Consumed twice, differently.** `release.yml` renders its notes over the **whole** range and takes its
breaking verdict over the **filtered** range. One definition, two call sites with different arguments —
not one call, per #61's comment.

## RenderedNotes

The body a release or a proposal publishes.

| Field | Type | Notes |
| --- | --- | --- |
| `text` | str | git-cliff's output, verbatim |
| `is_empty` | bool | True when `text` holds no non-whitespace character |

**Validation**: emptiness is a property of content. Not of size — an empty render is **one** byte, a
trailing newline, so a `-s` test calls it non-empty. Not of the exit code — git-cliff exits 0 for a range
holding only a `bump:` and for one holding nothing, indistinguishably. This is the first of the two
defects #61 names, and the one-byte case gets a test by name (SC-002).

## ReleaseVerdict

What the refusal ladder answers. Not a boolean: the same condition means different things depending on
who asked, and the three-way split survives the extraction intact (FR-010).

| Field | Type | Notes |
| --- | --- | --- |
| `proceed` | bool | Written to `GITHUB_OUTPUT`; gates the later steps |
| `severity` | `notice` \| `error` | Chooses the workflow-command prefix |
| `message` | str | The text a maintainer reads in the run log |

**State transitions** — the declared version is not ahead of `highest`:

| Trigger | severity | proceed | Why |
| --- | --- | --- | --- |
| `push` to main | `notice` | false | `ci.yml` calls release after *every* merge and most merges are not releases. An error would redden main for doing nothing wrong |
| `workflow_dispatch`, `dry-run: true` | `notice` | true | On a branch the declared version *is* the released one by definition, so refusing would stop every dry run before it rendered anything |
| `workflow_dispatch`, `dry-run: false` | `error` | — | A human asked for a release, and doing nothing is not what they asked for |

Two further refusals, both `error` and both raised **before any tag exists**: the declared version is not
a valid Version, and the range breaks the ConsumerSurface while the declared version's major equals
`highest.major`. The second fires only when a `highest` exists to be moved onto.
