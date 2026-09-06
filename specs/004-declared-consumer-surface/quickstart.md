# Quickstart: verifying the declared consumer surface

The ladder, in order. Rungs 1–3 run here; rungs 4–6 run in `github-actions-test`, and constitution
principle VI is why they are not optional: the behaviour turns entirely on the released repository's own
file, so nothing done in this repository can prove a caller's path.

The finding that makes the consumer rungs cheap: **a dry-run dispatch reaches the refusal without cutting a
tag.** `release.yml`'s `Check the notes` step is gated on `steps.verify.outputs.proceed == 'true'`, and a
dry run makes that true — `verify-version` downgrades the not-ahead refusal to a notice and proceeds. So
every rung below runs with `dry-run: true` and creates nothing, until the last one deliberately does not.

## 1. Offline

```bash
mise run ci
```

Proves every decision in [contracts/decisions.md](./contracts/decisions.md#new-tests): the three
declaration states, the validation refusals, the flag pairing, and that our own table reproduces the
deleted constants byte-for-byte (SC-001). Needs no network.

The two assertions to read the output for, because they are the ones the relocation could break quietly:

- our `surface-exclude` equals `OWN_CI`
- our table exists at all — delete it locally, confirm the suite fails and says why, restore it

```bash
mise run lint      # actionlint, zizmor, yamllint, check-jsonschema, cspell
mise run typecheck # pyright strict
```

## 2. Render the filter by hand

The line that will reach `git-cliff`, out of the file rather than retyped:

```bash
DECISION=surface-args python3 actions/release-decisions/decisions.py
```

Expect the six exclusions and two includes as `--include-path` / `--exclude-path` pairs, and **no**
notice — we declare a surface. Then prove the undeclared path without editing anything committed:

```bash
grep -v 'turbobasic-release' pyproject.toml > /tmp/bare.toml   # crude on purpose; drops the table header
PYPROJECT=/tmp/bare.toml DECISION=surface-args python3 actions/release-decisions/decisions.py
```

Expect no flags at all and a `::notice::` naming the omission. That is the unfiltered range, reached the way
a consumer with no table reaches it.

## 3. A dry run of our own release

```bash
mise run release-notes   # offline, creates nothing
```

Then, on this branch:

```bash
gh workflow run release.yml --ref 004-declared-consumer-surface -f dry-run=true
```

What this rung is for: our release path is unchanged, and the point is to see that it is. Read the
`Read the consumer-surface filter` step's log for the same flags rung 2 printed, and confirm the
`Render the notes` step's `read -ra` consumed them — an empty `SURFACE` would expand to an empty array
under `set -u`, which is the one shell behaviour no offline test covers.

**This rung cannot prove the feature.** Our surface is declared, so it exercises the declared path only —
the same path we had before. Rungs 4–6 are the feature.

## 4. The undeclared case, for real

In `github-actions-test`, **before** adding its table, dispatch its release with `dry-run: true`.

Expect: the notice from rung 2, no path flags, and the refusal judging the whole range. If its current range
carries no breaking commit, land one first — a `chore!:` touching anything at all will do, since nothing is
filtered.

Confirms SC-003, and it is the only chance to see this state on a real caller: rung 5 removes it.

## 5. A declared surface, both directions

Add to `github-actions-test`'s `pyproject.toml`:

```toml
[tool.turbobasic-release]
surface-include = ["src/**"]
```

Then two dispatches, and the pair is the point — one direction alone proves half of it:

| Land | Version | Expect |
| --- | --- | --- |
| a breaking commit touching `src/` | not a new major | **refused**, before any tag (SC-002, Story 1) |
| a breaking commit touching only `docs/` or `.github/workflows/` | a patch | **proceeds** (SC-002, Story 2) |

The second row is the one that was wrong before this change: under the old behaviour a breaking change to
that repository's own workflows was refused under a patch unless the filename happened to match one of ours.

## 6. A real release there

Drop `dry-run`. Confirm the tag, the release, and that its major tag moved — and that the notes describe the
**whole** range, not the filtered one (FR-011, Story 1 scenario 3). Its version tags are disposable where
ours are immutable, which is why the first real release of this behaviour happens there.

## 7. Then here

Only after rung 6. `release-proposal.yml` will have opened a proposal; the increment should be a **minor**
([research.md D7](./research.md#d7)) — this change touches `actions/**`, which our declared surface
includes, so the proposal computes it without help. Check the number rather than assuming it: a reviewer's
edit outranks the computed one, and a patch proposal here would mean the surface filter is not seeing this
change, which is itself a finding.

## Rejections worth triggering once

Not on the release path — rung 2's command is enough, and each should name the offending value:

```bash
printf '[project]\nversion = "1.0.0"\n[tool.turbobasic-release]\nsurface-include = "src/**"\n' > /tmp/bad.toml
PYPROJECT=/tmp/bad.toml DECISION=surface-args python3 actions/release-decisions/decisions.py

printf '[project]\nversion = "1.0.0"\n[tool.turbobasic-release]\nsurface-include = ["my src/**"]\n' > /tmp/bad.toml
PYPROJECT=/tmp/bad.toml DECISION=surface-args python3 actions/release-decisions/decisions.py

printf '[project]\nversion = "1.0.0"\n[tool.turbobasic-release]\nsurface-include = ["-x"]\n' > /tmp/bad.toml
PYPROJECT=/tmp/bad.toml DECISION=surface-args python3 actions/release-decisions/decisions.py
```

Each exits non-zero with an `::error::`. The suite covers all three; running them once is how you find out
the message is worth reading.
