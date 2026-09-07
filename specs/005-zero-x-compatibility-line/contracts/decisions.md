# Contract: the compatibility line

## The entity

```python
Line = tuple[int, ...]

def compatibility_line(version: Version) -> Line:
    major, minor, _ = version
    return (major, minor) if major == 0 else (major,)
```

The set of versions one moving ref may span. Everything below reads it, and **nothing else tests
`major == 0`** — a test asserts the split appears exactly once, so a fourth reader cannot restate it.

| Version | Line | Moving ref |
| --- | --- | --- |
| `0.0.3` | `(0, 0)` | `v0.0` |
| `0.1.0` | `(0, 1)` | `v0.1` |
| `0.2.0` | `(0, 2)` | `v0.2` |
| `1.0.0` | `(1,)` | `v1` |
| `4.1.1` | `(4,)` | `v4` |

## The three readers

```python
def moving_tag(version: Version) -> str: ...
```

`"v" + ".".join(str(part) for part in compatibility_line(version))`. Replaces `major="v${VERSION%%.*}"` in
`release.yml`, which is FR-006 — the name is a decision, so it lives beside the others.

```python
def moves_a_ref_onto_a_break(
    version: Version, highest: Version | None, *, breaking: bool
) -> bool: ...
```

Replaces `breaks_under_non_major`, whose name asks the wrong question. The rule stops being "is this a new
major" and becomes **"does the ref this release would move already exist"**:

```python
return breaking and highest is not None and compatibility_line(version) == compatibility_line(highest)
```

Every row of the spec's table falls out, including `0.2.1` over `0.2.0`, which the issue does not mention:

| Version | Highest | Lines | Refused |
| --- | --- | --- | --- |
| `0.1.1` | `0.1.0` | `(0,1)` = `(0,1)` | yes — a patch may not break |
| `0.2.0` | `0.1.0` | `(0,2)` ≠ `(0,1)` | **no** — the defect |
| `1.0.0` | `0.1.0` | `(1,)` ≠ `(0,1)` | no |
| `0.2.1` | `0.2.0` | `(0,2)` = `(0,2)` | yes |
| `4.2.0` | `4.1.1` | `(4,)` = `(4,)` | yes — unchanged |
| `5.0.0` | `4.1.1` | `(5,)` ≠ `(4,)` | no — unchanged |
| any | `None` | — | no — nothing to move |

```python
def next_version(current: Version, *, breaking: bool, feature: bool) -> Version: ...
```

A breaking range starts a new line; anything else advances within it.

```python
major, minor, patch = current
if breaking:
    return (major, minor + 1, 0) if major == 0 else (major + 1, 0, 0)
# Under 0.x the minor *is* the line, so a feature may not touch it: a consumer pinned to v0.1
# has to be able to receive features without crossing into v0.2.
if feature and major != 0:
    return (major, minor + 1, 0)
return (major, minor, patch + 1)
```

| Current | Range | Proposed |
| --- | --- | --- |
| `0.1.0` | breaking | `0.2.0` — was `1.0.0` |
| `0.1.0` | feat | `0.1.1` — was `0.2.0` |
| `0.1.0` | fix | `0.1.1` — unchanged |
| `0.1.0` | breaking + feat | `0.2.0` — breaking wins, as above 0.x |
| `4.1.1` | any | unchanged in every case |

**A 0.x `feat` and a 0.x `fix` propose the same version.** Recorded, not hidden: the line consumes two
components and only the patch is left. `increment_reason` still distinguishes them in the notice, so the
maintainer reads which it was even though the number cannot say.

## The action's interface

| Name | Was | Becomes |
| --- | --- | --- |
| `highest-major` in/out | major of the highest release | **kept for one release**, then removed ([research.md D5](../research.md#d5)) |
| `highest-version` in/out | — | the full `N.N.N` of the highest release |
| `moving-tag` out | — | the ref this release publishes |

`release.yml` passes **both** `highest-major` and `highest-version` to `check-notes`. That is not
belt-and-braces: `release.yml` is reached as `$/` while the action is reached as `@v4`, so one run happens
with the new workflow and the old module, and a workflow passing only `highest-version` would leave the old
module's `HIGHEST_MAJOR` empty and its refusal permanently `False`. Removing the pair is a follow-up task
once `v4` has moved.

Its tag step takes `MOVING_TAG` from `steps.verify.outputs.moving-tag` instead of composing
`v${VERSION%%.*}`. The `PATCH`-then-`POST` fallback is unchanged — the POST is now the first release of a
new *line* rather than of a new major, which is the same thing one component down.

## Tests that move

- **`test_tag_pattern_excludes_the_moving_major_tags`** — extended from `("v1", "v2", "v2.0")` to include
  `v0.1`, the new moving shape. The same assertion over a larger set, not a rewrite: a moving ref must never
  match `.cliff.toml`'s `tag_pattern` or it becomes a range's lower bound and the notes render empty.
- **The `breaks_under_non_major` tests** — renamed with the function. Their four existing cases are kept
  verbatim as the above-0.x no-change evidence (FR-007), with the 0.x rows added beside them.
- **`test_the_increment_zeroes_every_component_below_it`** — its `(4, 0, 3)` rows stay untouched and are
  what proves nothing above 0.x moved. 0.x rows are a separate case, so a regression names which régime broke.

## New tests

| Test | Holds |
| --- | --- |
| the line is `(major,)` above 0.x and `(major, minor)` below | the entity, directly |
| the split lives in exactly one function | `major == 0` appears once in the module, so the rule cannot drift |
| the moving tag is `v0.1` / `v1` / `v4` | FR-005, and that no `v0` is ever produced |
| every row of the refusal table | SC-002, `0.2.1` over `0.2.0` included |
| every row of the increment table | SC-003 |
| nothing at or above `1.0.0` changes | SC-001, asserted against the values produced today |
| a 0.x feat and fix agree on the number but not the reason | the consequence in D3, pinned so it is deliberate |
| no workflow spells a moving tag | FR-006 / SC-005 |
