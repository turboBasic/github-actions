# Security policy

## What this repo is

The CI that other `turboBasic` repositories run. It ships no service and is published to no package
index, but it is the highest-leverage repository in the account: code here executes in every
consumer listed in [`docs/consumers.md`](docs/consumers.md), holds a `GITHUB_TOKEN`, and in one case
runs on `pull_request_target`.

In scope, roughly in order of how much it matters:

- **Anything that lets an untrusted pull request execute code or reach a token.** A `${{ }}`
  interpolation of a PR title or branch name into a `run:` line, a `pull_request_target` workflow
  that checks out the head ref, a token passed to a step that did not need it.
- **A supply-chain regression in a pinned action.** Every third-party action here is pinned to a
  full commit SHA precisely because a tag can be retroactively repointed at malicious code —
  CVE-2025-30066 did that to `tj-actions/changed-files`, leaking secrets into build logs. A floating
  ref reaching `main` is a vulnerability, not a style lapse, and
  `tests/test_action_pins.py` exists to stop it.
- **A workflow that grants more permission than it needs.** Permissions can only be reduced down a
  call chain, so a reusable workflow asking for `write` where `read` suffices cannot be constrained
  by its callers.

There are no supported versions to list beyond the current major tag, which moves. If you pinned a
SHA or an immutable patch tag, you own that copy.

## Reporting

Use [private vulnerability reporting](https://github.com/turboBasic/github-actions/security/advisories/new).
It keeps the report unpublished while it is being looked at.

Do not open a public issue for something exploitable. For a workflow you think is merely
ill-advised, a public issue is the right place — that is a design argument, not a disclosure.

Expect a reply within a week. This is a personal project, not a staffed product; if that is too slow
for what you found, say so in the report and disclose on your own timeline.

## Secrets

No secret belongs in this repository, in any form, including a test fixture. The workflows here take
tokens as inputs or read `secrets.GITHUB_TOKEN` at the call site; none stores one.

If you find a live credential committed anywhere in this repo's history, report it privately. Push
protection and secret scanning are on, so a recognised token format is blocked at push time. Neither
catches everything.
