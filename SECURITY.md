# Security policy

## What this repository is

The CI that other `turboBasic` repositories run. It ships no service and is published to no package
index, but it is the highest-leverage repository in the account: code here executes in every repository
that pins it, and it runs holding whatever token the caller's job grants.

In scope, roughly in order of how much it matters:

- **Anything that lets an untrusted pull request execute code or reach a token.** A `${{ }}`
  interpolation of a pull request title or a branch name into a `run:` line, a workflow triggered on
  `pull_request_target`, a token passed to a step that did not need it. Constitution principle VI gives
  the reason, and `tests/test_no_interpolation.py` holds it.
- **A supply-chain regression in a pinned action.** Every third-party action here is pinned to a full
  commit SHA. CVE-2025-30066 is the reason realised: a repointed tag on `tj-actions/changed-files` leaked
  secrets into build logs. A floating ref reaching `main` is a vulnerability, not a style lapse, and
  `tests/test_action_pins.py` exists to stop it.
- **A capability that demands more permission than it needs.** Permissions only reduce down a call chain,
  so a caller cannot constrain a reusable workflow that asks for too much, and reverting the code here
  does not un-grant what a consumer already granted. What each capability demands is frozen in
  `tests/published_surface.toml`.

There are no supported versions to list beyond the moving compatibility ref, which moves. If you pinned an
exact release tag, you own that copy.

## Reporting

Use [private vulnerability reporting](https://github.com/turboBasic/github-actions/security/advisories/new).
It keeps the report unpublished while it is being looked at.

Do not open a public issue for something exploitable. For a workflow you think is merely ill-advised, a
public issue is the right place — that is a design argument, not a disclosure.

Expect a reply within a week. This is a personal project, not a staffed product; if that is too slow for
what you found, say so in the report and disclose on your own timeline.

## Secrets

No secret belongs in this repository, in any form, including a test fixture (constitution principle II).
The capabilities here read `secrets.GITHUB_TOKEN` at the call site or mint a narrowed App token in the step
that uses it; none stores one.

If you find a live credential committed anywhere in this repository's history, report it privately. Push
protection and secret scanning are on, so a recognised token format is blocked at push time. Neither
catches everything.
