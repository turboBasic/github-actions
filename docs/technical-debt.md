# Technical debt

Deliberate shortcuts and known-wrong states accepted for now.

An entry belongs here when all three hold:

- It is a real defect or a corner deliberately cut, not a preference.
- It states a **condition this repository can answer** — a file, a version, a command's output — so a
  sweep can tell whether it still applies without asking anyone.
- Nobody is going to do it. Work someone will actually do is an issue; a plan's leftover task is a task
  in the next phase. Only what is knowingly left alone lands here.

An entry that stops holding is deleted rather than annotated — git remembers. An entry that turns into
work becomes an issue and the row goes.

| ID | What | Condition that clears it |
| --- | --- | --- |
| `TD-1` | `prek-advisory.yml` is described as non-blocking, and prek's verdict is — but the job's own `uv sync --locked` is not, so lockfile drift reddens a check whose name — `advisory / prek-advisory` — promises it cannot fail. Seen on `github-actions-test`'s `test/scenario-lockfile-drift` branch, where it failed alongside `ci / python-ci`. Left alone deliberately: tolerating the sync failure to keep the check green would report that prek ran when it never started. The README qualifies the claim instead of the workflow changing. | `prek-advisory.yml` no longer runs `uv sync --locked` ahead of prek, or that step carries `continue-on-error: true` **and** the PR comment distinguishes a setup failure from a lint finding. |
| `TD-2` | On a merge that cuts a release, `drift` deterministically fails and reddens `main`. `ci.yml`'s `drift` job declares no `needs`, so it starts immediately, while `release` waits on `needs: [ci]` — about twenty seconds later. `test_no_consumer_facing_change_is_waiting_for_a_release` asserts the declared major is tagged, which on that commit it is not yet. Measured at `e4f4b2c`: drift failed 22:33:20, `v4.0.0` was created 22:33:38. `v3`'s merge failed identically — `Drift` completed `failure` at 15:15:45, `v3.0.0` was created at 15:16:05 — and only shows green because it was re-run at 15:18:40. So the failure is deterministic on every release-cutting merge, not a queue-latency fluke. Left alone because `needs: [release]` is not the fix — `release` is `if:`-gated to pushes on `main`, and a skipped need skips its dependant, so `drift` would stop running on pull requests, which is where it is actually read. | `ci.yml`'s `drift` job no longer runs on `push` to `main`, or the assertion tolerates a release run in flight on the same commit. |
| `TD-3` | `test_the_ruleset_requires_exactly_the_checks_that_exist` cannot see a required check configured through legacy branch protection. `_live_required_contexts` reads `rules/branches/main`, which is ruleset-derived only, so a context set the old way would be enforced and invisible to the assertion. None exists today — `GET /repos/turboBasic/github-actions/branches/main/protection` answers `404 Branch not protected` — which is why this is a blind spot rather than a bug. | `_live_required_contexts` reads `branches/main/protection` as well as `rules/branches/main`. The 404 is why this is tolerable, not why it clears — a condition the entry already satisfies would delete the row while the blind spot remains. |
| `TD-4` | All five of `github-actions-test`'s scenario branches are pinned to `@v2` — `test/checks-disabled`, `test/lockfile-drift`, `test/mise-version-pin`, `test/stages-off`, `test/custom-task-names` — and that repository's `main` ruleset now requires the `v4` check names, so none of them can satisfy it. They also still call `precommit-advisory.yml`, the path `v3` renamed. Their open pull requests report `ci / CI` and `commits / PR title`, contexts nothing requires any more, so each reads blocked for a reason unrelated to what it demonstrates. Left alone because repinning changes what each branch demonstrates, and the recorded observations were taken against the old contexts — a repin without re-observing would replace true evidence with plausible evidence. | Every scenario branch resolves the major `README.md`'s Versioning section names, and each `tests/scenario-*/README.md` records observations taken against that ref. |
