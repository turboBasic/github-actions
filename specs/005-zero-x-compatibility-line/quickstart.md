# Quickstart: verifying the 0.x compatibility line

The route, in order. Rungs 1–3 run here; rungs 4–7 need `github-actions-test` reset to an unreleased 0.x
state, because `is_ahead` spans every major and at `2.0.0` it can never publish 0.x again.

Two orderings are not negotiable. **The release here precedes the consumer rungs**, since
`github-actions-test` resolves `@v4` and cannot see an unreleased commit. And **the reset precedes any 0.x
release**, since a single leftover `vN.N.N` tag makes every 0.x version not-ahead.

## 1. Offline

```bash
mise run ci
```

Covers every row of both tables in [contracts/decisions.md](./contracts/decisions.md), the moving-tag names,
and the assertions that nothing at or above `1.0.0` moved. Read the output for two in particular:

- the line's split appears in exactly one function
- the `(4, 0, 3)` increment rows are untouched — that is SC-001, and a change there means the fix leaked
  above 0.x

## 2. The decisions by hand

```bash
python3 - <<'PY'
import sys; sys.path.insert(0, "actions/release-decisions")
from decisions import compatibility_line, moving_tag, moves_a_ref_onto_a_break, next_version
for v in [(0,0,3), (0,1,0), (0,2,0), (1,0,0), (4,1,1)]:
    print(v, compatibility_line(v), moving_tag(v))
print("refuse 0.1.1 over 0.1.0:", moves_a_ref_onto_a_break((0,1,1), (0,1,0), breaking=True))
print("refuse 0.2.0 over 0.1.0:", moves_a_ref_onto_a_break((0,2,0), (0,1,0), breaking=True))
print("propose from 0.1.0, breaking:", next_version((0,1,0), breaking=True, feature=False))
PY
```

Expect `v0.1` for `0.1.0`, `v4` for `4.1.1`, `True` then `False`, and `(0, 2, 0)`.

## 3. Release here

`mise run release-notes`, then merge and let `release-proposal.yml` propose. This is a **patch** — nothing
under `.github/workflows/` or `actions/` changes behaviour for any current caller, and both are `1.x`+.

Before cutting, confirm the interim window is harmless. Between merge and release, `ci.yml` runs the new
`release.yml` against the **old** action at `@v4` ([research.md D5](./research.md#d5)); the new workflow
passes `highest-major` as well as `highest-version` precisely so the old module's refusal still works. Check
it did:

- the `Check the notes` step's env shows **both** `HIGHEST_MAJOR` and `HIGHEST_VERSION`
- `HIGHEST_MAJOR` is not empty

An empty `HIGHEST_MAJOR` there means the refusal was disabled for that release, which is the failure D5
exists to prevent.

## 4. Reset the consumer

`github-actions-test` has no tag ruleset, and its `main` ruleset bypasses for the Repository admin role, so
this needs no relaxation of either.

1. Delete every release: `v2.0.0 v1.0.2 v1.0.1 v1.0.0 v0.1.0`.
2. Delete every tag, moving refs included: `v0 v0.1.0 v1 v1.0.0 v1.0.1 v1.0.2 v2 v2.0.0`.
3. **Rewrite `main` to its functional commits and force-push.** Not a collapse to one commit — the history
   should still read like a consumer's. Drop:
   - every `chore: cut vX.Y.Z` and `bump: release vX.Y.Z`, which describe releases that no longer exist;
   - `docs!: probe the release refusal with no declared surface` (#33) and `feat!: probe the refusal inside
     the declared surface` (#35), whose only content is verification comments.

   Keep `feat: declare the consumer surface as src/**` (#34) — that table is functional and is what `004`
   established.

   Dropping the two probes is not tidiness. With no tags, `--unreleased` covers the whole history, so their
   `!` markers would sit in every range below: rung (b) would be **refused** when it must proceed, and rung
   (c) would prove nothing, because the break it is supposed to introduce would already be there.
4. Set `[project].version = 0.1.0` with `uv.lock` in step (`uv version --no-sync 0.1.0`).

Its `pyproject.toml` version and `uv.lock` must agree or `uv sync --locked` fails the CI the release is
gated on.

## 5. The 0.x ladder

Each rung is a merge to its `main`; the `release` job is gated on `needs: [ci]` and runs only on push there,
so there is no dry-run path. Ranges accumulate until a release cuts them, so the order matters.

| # | Land | Version | Expect |
| --- | --- | --- | --- |
| a | the reset itself | `0.1.0` | proceeds — nothing released, so nothing to refuse. `v0.1.0` **and `v0.1`**, and **no `v0`** |
| b | a `fix:` | `0.1.1` | proceeds. `v0.1` now resolves to `0.1.1` — the moving ref moved within its line |
| c | a `feat!:` touching `src/` | `0.1.2` | **refused**: the line is `0.1` and the range breaks it. No tag |
| d | same range | `0.2.0` | **proceeds** — the defect this issue is about. `v0.2` created, `v0.1` still at `0.1.1` |

Rung (a) is the one to read closely: it is where `v0` would appear if the moving tag were still
`v${VERSION%%.*}`. Rung (d) is the fix. Rung (c) before (d) is what makes (d) mean anything — the same range
refused and then released, on the same evidence.

## 6. The proposal, under 0.x

After rung (c)'s refusal, look at what `release-proposal.yml` offered for that breaking range: it must be
`0.2.0`, not `1.0.0`. That is the second defect, and the reason rung (d) is reachable without a human editing
the number.

Also check a non-breaking `feat` proposes a **patch** under 0.x — `0.2.1`, not `0.3.0`. A consumer pinned to
`v0.2` has to be able to receive it.

## 7. Crossing out of 0.x

One more merge: a breaking range under `1.0.0`. Expect it to proceed, `v1.0.0` and `v1` created, and `v0.2`
left where it is. That is the graduation path, and it confirms the line comparison handles a régime change
rather than only the two régimes separately.

## Outcome

*Filled in when the ladder has run.*

## What rung 3 actually found

The interim window of [research.md D5](./research.md#d5) cuts **both** ways, and only the input half was
guarded. `v4.1.1` ([run 34088344548](https://github.com/turboBasic/github-actions/actions/runs/34088344548))
published its release and then failed:

```text
HIGHEST_MAJOR: 4                                        ← the guarded half worked
##[warning]Unexpected input(s) 'highest-version'        ← the old action ignoring the new input
MOVING_TAG:                                             ← the unguarded half
gh: Could not verify tag name (HTTP 422)
```

`steps.verify.outputs.moving-tag` resolves the action at `@v4`, which did not declare that output yet, so it
was the empty string. An unknown *input* is a warning; an absent *output* is silently `""` and flows into a
command — a strictly worse failure mode, and the one I did not think to guard.

It failed in the least recoverable order: notes rendered, `v4.1.1` tagged, release published, and only then
the ref move. Consumers stayed on `v4.1.0`, which is the fail-safe direction the workflow's design intends,
but the version tag could not be deleted — the `immutable release tags` ruleset covers it with no bypass — so
re-running was impossible and `@v4` still pointed at an action without the output, deadlocking every retry.

Recovered by completing the step by hand: an annotated `v4` tag object at the release commit, force-moved,
which is exactly what the failed line does. `v4` now tracks `v4.1.1`.

Fixed so it cannot recur: `release.yml` refuses an empty `MOVING_TAG` **before** creating any ref, with
`test_the_release_refuses_an_empty_moving_tag_before_creating_a_ref` asserting the check precedes the first
one. That turns an unrecoverable half-release into a re-runnable refusal.

**The general rule this earned:** an output newly consumed by `release.yml` is empty for exactly one release,
because the workflow resolves at the commit under review and the action resolves at the tag. Either guard it
or add it a release before you read it.
