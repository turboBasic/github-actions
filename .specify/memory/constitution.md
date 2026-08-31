# turboBasic/github-actions Constitution

What must always be true of this repository. Seven principles, each one a gate a spec, plan or PR
can fail against.

This file does not restate the conventions — [`docs/ai-instructions.md`](../../docs/ai-instructions.md)
owns those, and owns the concrete rules behind every principle here. Read this for *what may never
be violated*; read that for *how to work*.

## Core Principles

### I. Consumer Contract Stability

A workflow's inputs, outputs, secrets and permissions are a public interface. A change that breaks
an existing call site is a new major tag, never a move of an existing one. `v1.x.y` tags are
immutable.

### II. Supply-Chain Pinning

Every third-party action is pinned to a full 40-character commit SHA with the version as a trailing
comment. A tag can be retroactively repointed at malicious code — CVE-2025-30066 did exactly that.
First-party references use the moving major tag, and only because this repo shares its owner with
every consumer.

### III. Least Privilege

A workflow declares the narrowest `permissions` it needs. Permissions only ever reduce down a call
chain, so a reusable workflow that asks for too much cannot be constrained by its caller.

### IV. Untrusted Input Is Data, Never Code

A PR title, branch name or body reaches a `run:` block through `env`, never through inline `${{ }}`.
`pull_request_target` is never combined with a checkout of the head ref.

### V. Secrets Never Persist

No secret is written to a file, a log, an artifact, or this repository — in any form, at any point.

### VI. Verification By Real Invocation

Lint does not verify a workflow. Every linter here passes on a workflow no caller can run. A
reusable workflow is unverified until a real PR has exercised it at a ref that resolves to the code
under review. Where its behaviour depends on caller-side configuration, that is not enough — it is
unverified until a consumer has exercised it at the ref that consumer pins.

### VII. Gates Are Never Loosened

No blanket `# type: ignore`, no relaxed tool mode, no silenced `zizmor` finding, no rule disabled to
make a run pass. A rule that genuinely has to go is turned off in the linter's own config, with the
reason written down, and reported.

## Cross-Repository Impact

This repository is shared infrastructure, so a change here is not a local change. Every spec for a
change to a reusable workflow or composite action states, before any plan is written:

- **Affected consumers** — from [`docs/consumers.md`](../../docs/consumers.md), which is the
  blast-radius list.
- **Interface delta** — the current input/output/permission surface against the proposed one.
- **Compatibility** — whether existing call sites keep working untouched, and if not, why a major
  bump is warranted.
- **Rollout and rollback** — the order consumers migrate in, and what reverting costs.

A spec that cannot answer these is not ready to plan.

## Governance

This constitution supersedes convenience. A change to a principle is a design change: name the
principle, state concretely what breaks without it, offer the smallest alternative that meets the
underlying need, then stop and wait for a decision. Reporting the conflict is mandatory even when
eroding a principle would only be a side effect.

Conventions are not governed here. Naming, file placement, how a test is organised — those live in
`docs/ai-instructions.md` and a request to change one is just a request.

**Version**: 1.1.0 | **Ratified**: 2026-08-31 | **Last Amended**: 2026-08-31
