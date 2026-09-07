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
Whether a caller on the current major can absorb this by resolving the new ref. A removed
or renamed input, a renamed job composing a check context, or a permission the caller must
grant needs a new major instead — say which. `patch — nothing consumer-facing changed` is a
complete answer where it is true, and the answer is in this diff.
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
README is the consumer-facing contract and documents inputs. Name what you touched, or
`none — no doc describes this`.
-->

---

<!--
Trading away a rule marked non-negotiable in docs/ai-instructions.md is a design change:
name the rule and what breaks without it, here, before the review starts.

Agent-written code is welcome — this repo exists to make it predictable. You are still
the author, and reviewers will expect you to explain any part of this diff yourself.
-->
