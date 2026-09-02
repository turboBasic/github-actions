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
| `TD-1` | `precommit-advisory.yml` is described as non-blocking, and prek's verdict is — but the job's own `uv sync --locked` is not, so lockfile drift reddens a check whose name promises it cannot fail. Seen on `github-actions-test`'s `test/scenario-lockfile-drift` branch, where it failed alongside `ci / CI`. Left alone deliberately: tolerating the sync failure to keep the check green would report that prek ran when it never started. The README qualifies the claim instead of the workflow changing. | `precommit-advisory.yml` no longer runs `uv sync --locked` ahead of prek, or that step carries `continue-on-error: true` **and** the PR comment distinguishes a setup failure from a lint finding. |
