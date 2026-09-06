# Contract: `actions/release-decisions/decisions.py`

The module's side. Pure functions first, then the one I/O wrapper that changes, then the tests that move.

## Deleted

```python
SURFACE_INCLUDE = (".github/workflows/**", "actions/**")
OWN_WORKFLOWS = ...
SURFACE_EXCLUDE = tuple(f".github/workflows/{name}" for name in OWN_WORKFLOWS)
```

All three go. `OWN_WORKFLOWS` was a second copy of `OWN_CI` held equal to it by the very test that guards
the surface, so the number of places `OWN_CI` is restated goes **down** by one. Its content moves to this
repository's own `pyproject.toml`, where it is data rather than code
([data-model.md](../data-model.md#this-repositorys-own-declaration)).

## Added

```python
SURFACE_TABLE = "turbobasic-release"


def surface_config(raw: bytes) -> tuple[list[str], list[str]] | None: ...
```

Parses `[tool.turbobasic-release]` out of a `pyproject.toml`'s bytes. Returns the two lists, or `None` when
the table is absent — the distinction FR-003 spends on a notice. Raises on a mis-shaped value, with the key
named; a mis-shaped value is a mistake to report, never something to coerce.

```python
def unusable_paths(paths: Iterable[str]) -> list[str]: ...
```

Every entry that is empty, holds whitespace, or begins with `-`, in declaration order. A list rather than a
bool so the refusal can name what it found. Empty list means the declaration is usable.

## Changed

```python
def surface_args(include: Iterable[str], exclude: Iterable[str]) -> list[str]: ...
```

Same body as today, but the lists arrive as arguments instead of being read from module constants. Given two
empty lists it returns `[]`, which is the unfiltered range with no branch anywhere — `git-cliff` with no
`--include-path` considers every path. That is why FR-002 needs no special value and no workflow change.

```python
def _surface_args() -> None: ...
```

The I/O wrapper, and the only place the three functions above are composed:

1. Read the same file `PYPROJECT` already points at — `pyproject.toml` by default, which under
   `release.yml` is the **caller's**, because a reusable workflow checks out the caller's tree.
2. `surface_config`. `None` → two empty lists, and a `::notice::` naming the omission and where to fix it.
3. `unusable_paths` over both lists together → `::error::` and exit non-zero, naming every offender.
4. `surface_args` → stdout line by line, and one space-joined line to `GITHUB_OUTPUT` as `args`.

Steps 1 and 4 are unchanged in shape, which is why no workflow and no `action.yml` moves.

## Unchanged, and load-bearing that it is

- **`action.yml`** — the `pyproject` input already exists and already maps to `PYPROJECT`.
- **`release.yml`** — its `surface-args` step already passes everything needed. Only a comment changes: it
  currently promises the paths will become an input and points at #110.
- **`release-proposal.yml`** — already invokes the same decision by in-repo path and already reads our
  `pyproject.toml`, so it picks up our table with no edit. This is FR-009 holding for free rather than by
  construction.
- **The `args` output and its carrier** — still one space-joined line, still read with `read -ra`. FR-006
  exists to keep that true against caller data ([research.md D3](../research.md#d3)).

## Existing tests this change touches

Two, and neither is relaxed.

### `test_the_surface_exclusions_are_own_ci_as_workflow_paths` — relocated

Asserts the same equality against a different left-hand side: our `pyproject.toml`'s `surface-exclude`
instead of `SURFACE_EXCLUDE`. Same failure message shape, same two sides named. Principle VII turns on this
being a relocation and not a loosening, so the assertion keeps its exact form.

It gains a companion for the failure mode the move creates: **our table missing entirely**. A deleted table
would put our own release on the unfiltered path and start refusing over changes to `ci.yml` — a silent
regression of what 003 fixed, and one the equality assertion alone would report as a confusing mismatch
rather than as the real cause.

### `test_the_surface_arguments_pair_every_path_with_its_flag` — rewritten

Today it calls `surface_args()` with no arguments and rebuilds the expected list from the module constants,
so it is close to a restatement. With the lists arriving as parameters it becomes a real test of the
pairing, and its second assertion — that no argument holds a space — moves from a property of constants we
control to `unusable_paths`, where it is a refusal about caller data.

### Not touched, and it is the proof of the interface claim

`test_the_release_interface_is_frozen` still asserts `release.yml` declares exactly `{dry-run}` under
`workflow_call`. Under the rejected input design it would have had to be edited. It standing unchanged is
the cheapest evidence the interface delta is empty (FR-010).

## New tests

Offline, no marker, in `tests/test_release_decisions.py`.

| Test | Holds |
| --- | --- |
| an absent table reads as undeclared | `surface_config` returns `None`, distinguishably from a declared-empty table |
| a declared table reads both lists | including one key present and the other absent |
| a declared-empty table is not undeclared | the state FR-003 spends the notice on |
| an undeclared surface renders no flags | `surface_args([], [])` is `[]`, which is the unfiltered range |
| a mis-shaped value raises, naming the key | a bare string, and a list holding a non-string |
| each unusable path is caught | empty, space, tab, leading `-`, and a valid glob that must **not** be caught |
| the arguments pair every path with its flag | include before exclude, flag before path |
| our own declaration reproduces the deleted constants | SC-001, byte-identical rather than equivalent |
| our exclusions equal `OWN_CI` | relocated from the constant |
| our table exists at all | the failure mode the relocation creates |
| the module still imports only the standard library | unchanged, and still true — `tomllib` was already there |
