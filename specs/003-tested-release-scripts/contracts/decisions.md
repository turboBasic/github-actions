# Contract: the `decisions` module

The pure logic. Every function here is a total function of its arguments with no I/O, which is what makes
it testable offline — the point of the whole change. I/O lives in the thin `__main__` that
[`action.md`](./action.md) describes, and in the workflow shell that stays.

Signatures are the contract; bodies are the implementation phase's business. Full type hints on every
signature, tests included, per `docs/ai-instructions.md`.

## Pure functions

| Function | Signature | Answers |
| --- | --- | --- |
| `parse_version` | `(str) -> tuple[int, int, int] \| None` | Is this a plain three-part version, and what are its parts? `None` rather than an exception, so the caller chooses the message |
| `highest_version` | `(Iterable[str]) -> tuple[int, int, int] \| None` | The greatest valid version among tag refs, across all majors. `None` when there are none |
| `is_ahead` | `(tuple[int, int, int], tuple[int, int, int] \| None) -> bool` | Is the declared version strictly ahead of the highest release? `True` when the second is `None` |
| `next_version` | `(tuple[int, int, int], breaking: bool, feature: bool) -> tuple[int, int, int]` | The increment. Breaking wins over feature, feature over patch |
| `increment_reason` | `(breaking: bool, feature: bool) -> str` | The one-line why a maintainer reads |
| `notes_are_empty` | `(str) -> bool` | Does this hold no non-whitespace character? |
| `verdicts` | `(str) -> tuple[bool, bool]` | The `(breaking, feature)` pair from a `--context` JSON payload |
| `declared_version` | `(bytes) -> str` | `[project].version` from `pyproject.toml` bytes, via `tomllib` |
| `release_verdict` | `(…) -> ReleaseVerdict` | The three-way severity from the event, the dry-run flag, and whether the version is ahead |
| `breaks_under_non_major` | `(tuple[int, int, int], highest_major: int \| None, breaking: bool) -> bool` | FR-004's **third** comparison: would publishing this move an existing major tag onto a broken contract? |

## Constants

| Constant | Type | Notes |
| --- | --- | --- |
| `SURFACE_INCLUDE` | `tuple[str, ...]` | `.github/workflows/**`, `actions/**` |
| `SURFACE_EXCLUDE` | `tuple[str, ...]` | One `.github/workflows/<name>` per `OWN_CI` entry |
| `surface_args()` | `() -> list[str]` | The `--include-path`/`--exclude-path` argument list, so no workflow spells the flags |

## Invariants the tests must pin

Each of these fails if the logic is inverted, and each maps to a spec requirement or success criterion.

| Invariant | Maps to |
| --- | --- |
| `next_version((4,0,3), breaking=True, feature=False) == (5,0,0)` | AS-1, FR-001 |
| `next_version((4,0,3), breaking=False, feature=True) == (4,1,0)` | AS-2 |
| `next_version((4,0,3), breaking=False, feature=False) == (4,0,4)` | AS-3 |
| Breaking wins even when both verdicts are true | FR-001 |
| `notes_are_empty("\n")` is `True` — the one-byte case, named in the test | AS-4, SC-002 |
| `notes_are_empty("")` is `True`; a body with any word is `False` | AS-4 |
| `verdicts` on a payload whose commits carry **no** `breaking` key returns `(False, …)` | AS-5, SC-002 |
| `verdicts` reads `breaking` as identity against `true`, not truthiness | FR-005 |
| `parse_version` rejects `4.0`, `v4.0.3`, `4.0.3rc1`, `4.0.3+1` | FR-004 |
| `highest_version([])` is `None`, and `is_ahead(v, None)` is `True` | Edge Cases |
| `highest_version` orders component-wise: `4.10.0` beats `4.9.0` | FR-004 |
| `highest_version` spans majors: a `v3.9.9` alongside `v4.0.0` yields `4.0.0` | FR-004 |
| `declared_version` reads the `[project]` table, not the first `version =` line | FR-003 |
| `release_verdict` yields notice/`proceed=false` on `push`, notice/continue on a dry run, error on a real dispatch | FR-010, data-model state table |
| `breaks_under_non_major((4,1,0), 4, breaking=True)` is `True` — same major, breaking range | FR-004 |
| `breaks_under_non_major((5,0,0), 4, breaking=True)` is `False` — a new major may break | FR-004 |
| `breaks_under_non_major((4,1,0), None, breaking=True)` is `False` — no tag exists to move | FR-004, Edge Cases |
| `breaks_under_non_major(v, major, breaking=False)` is always `False` | FR-004 |
| `SURFACE_EXCLUDE` equals `OWN_CI` mapped to workflow paths | FR-006, SC-004, D6 |
| Every module-level import in `decisions.py` resolves to the standard library | FR-014 |

## Guards on the YAML, not the Python

Two assertions belong in `tests/test_release_notes.py` rather than here, because they are properties of
the workflows:

- Neither `release.yml` nor `release-proposal.yml` contains an `--include-path` or `--exclude-path` flag
  (SC-004, US3 AS-1). This replaces the `SURFACE_FILTERED` parametrization, which has nothing left to
  iterate once there is one definition.
- Neither contains a comparison, an arithmetic increment, a version parse, or a `jq` filter over commit
  data (SC-003, US2 AS-1).

And one in `tests/test_action_pins.py`: the job names `tag-and-publish` and `propose` are pinned, because
renaming the first retires a required check in `github-actions-test` (FR-009a, SC-008).

## Existing tests this change breaks

Four gates in the suite today assert the *text* of the shell being removed. Each must be rewritten or
retired deliberately, in the stage that breaks it — a gate that disappears because nobody noticed it fail
is the thing Principle VII forbids.

| Gate | Breaks when | Because |
| --- | --- | --- |
| `test_the_surface_filter_agrees_with_own_ci` | stage 1, then stage 2 | Parametrized over both workflows; scrapes `--include-path` out of each |
| `test_only_a_breaking_change_to_the_surface_refuses_a_release` | stage 2 | `_surface_flags("release.yml")` returns `[]`, so its second assertion becomes `not _breaking(unfiltered)` and hard-fails. It does **not** pass for the wrong reason — the control assertion above it is what makes the failure loud |
| `test_the_release_refuses_notes_with_no_content` | stage 2 | Asserts the literal `[^[:space:]]` appears in `release.yml`; the check moves to `notes_are_empty` |
| `_surface_flags` helper | stage 2 | Reads flags out of workflow text; must read `surface_args()` instead |

**Two gates survive untouched**, and the design must keep them that way:

- `test_the_release_gates_on_a_required_context` asserts `"ci / python-ci"` appears in `release.yml`. The
  `workflow_dispatch`-only check-runs query that carries that string **stays shell** — it is a `gh api`
  call, so FR-007 already places it, and the action's contract deliberately does not cover it.
- `test_the_release_publishes_the_rendered_notes` asserts `--notes-file`, which is plumbing.
