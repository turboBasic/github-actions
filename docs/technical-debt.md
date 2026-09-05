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
| `TD-2` | On a merge that cuts a release, `drift` deterministically fails and reddens `main`. `ci.yml`'s `drift` job declares no `needs`, so it starts immediately, while `release` waits on `needs: [ci]` — about twenty seconds later. `test_no_consumer_facing_change_is_waiting_for_a_release` asserts the declared major is tagged, which on that commit it is not yet. Measured at `e4f4b2c`: drift failed 22:33:20, `v4.0.0` was created 22:33:38. `v3`'s merge was green only because that runner queued three minutes late. Left alone because `needs: [release]` is not the fix — `release` is `if:`-gated to pushes on `main`, and a skipped need skips its dependant, so `drift` would stop running on pull requests, which is where it is actually read. | `ci.yml`'s `drift` job no longer runs on `push` to `main`, or the assertion tolerates a release run in flight on the same commit. |
| `TD-3` | `release.yml:209` tells a human recovering a half-applied release to delete the version tag first. Nobody can: ruleset `22277040` covers `refs/tags/v*.*.*` with `deletion` and `update`, `bypass_actors: []`, and `current_user_can_bypass: "never"`. Nobody can carry out the instruction as written, an admin included. Left alone because the immutability is the more valuable of the two — a moving version tag is worse than an unhelpful comment. | `release.yml`'s recovery note names a route that exists — a new patch version rather than a tag deletion — or `22277040` gains a bypass actor. |
| `TD-4` | `test_the_ruleset_requires_exactly_the_checks_that_exist` cannot see a required check configured through legacy branch protection. `_live_required_contexts` reads `rules/branches/main`, which is ruleset-derived only, so a context set the old way would be enforced and invisible to the assertion. None exists today — `GET /repos/turboBasic/github-actions/branches/main/protection` answers `404 Branch not protected` — which is why this is a blind spot rather than a bug. | `_live_required_contexts` also reads `branches/main/protection`, or that endpoint still answers 404. |
