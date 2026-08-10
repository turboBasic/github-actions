<!--
The title is a Conventional Commit — a squash merge takes its subject from there.
Everything below renders as prose; these hints disappear.
-->

## Why?

<!--
Required. The problem this solves, in your own words — not a restatement of the diff.
Link the issue if there is one (`Closes #12`).
-->

## Blast radius

<!--
Which consumers this reaches — see docs/consumers.md. Say `none — not yet referenced`
if nothing calls the changed workflow. If an input contract moved, say whether it is
backwards-compatible or needs a major tag.
-->

## Verification

<!--
`mise run ci` covers lint, typecheck, and tests. A reusable workflow that has never been
called is unverified: say which workflow you called at which ref, and that you saw it both
pass and fail. A check that cannot fail is not a check.
-->

## Docs

<!--
Documentation moves with the change — stale framing is a defect, not a follow-up. The
README documents inputs; docs/consumers.md is the blast-radius list. Name what you
touched, or `none — no doc describes this`.
-->

---

<!--
Trading away a rule marked non-negotiable in docs/ai-instructions.md is a design change:
name the rule and what breaks without it, here, before the review starts.

Agent-written code is welcome — this repo exists to make it predictable. You are still
the author, and reviewers will expect you to explain any part of this diff yourself.
-->
