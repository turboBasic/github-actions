# turboBasic/github-actions

The navigation layer, shared by every AI coding tool that reads this repository.

This file states no rule. It names each artefact and says what that artefact answers, so a tool told
that "exactly one artefact declares which major tag is current" can find which one. The rules
themselves are two layers above: the invariants in `.specify/memory/constitution.md`, the conventions
in `docs/ai-instructions.md`.

Conventionally an `AGENTS.md` carries build commands, code style and test instructions. Those are
layer 3 here, and each has an owner in the second table below. Restating one would give this
repository two answers to the same question, which is the arrangement the layering exists to remove.

## The instruction layers

Four layers, the most abstract first.

| # | Layer | Purpose | Stability | Artefacts |
| --- | --- | --- | --- | --- |
| 1 | Invariants | what may never be violated | amended and versioned, rarely | `.specify/memory/constitution.md` |
| 2 | Conventions | how work is done here | edited as practice settles | `docs/ai-instructions.md` |
| 3 | Mechanics | the consumer contract, the procedures, the gates | moves with the code | `README.md`, `CONTRIBUTING.md`, `docs/technical-debt.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`, `tests/`, and the configs below |
| 4 | Navigation | where each fact lives | moves when an artefact does | this file, `CLAUDE.md`, `.github/copilot-instructions.md` |

How each tool reaches the rule layers differs, and layer 4 is where that difference is absorbed.
Claude Code reads `CLAUDE.md`, which imports this file and both rule layers eagerly, in every session.
GitHub Copilot reads `.github/copilot-instructions.md` and this file directly, has no import
mechanism, and reaches the rule layers by link. Layer 3 is read on demand by both.

## What each layer 3 artefact answers

| Artefact | Answers |
| --- | --- |
| `README.md` | what each workflow and action does, its inputs and their defaults, a copyable call site, and which major tag is current |
| `CONTRIBUTING.md` | the setup, the label set, how a workflow change is verified, and how a release is cut |
| `docs/technical-debt.md` | which shortcuts are deliberate, and the condition that clears each |
| `docs/instruction-layers.md` | the layering itself, explained for another repository to adopt |
| `SECURITY.md` | how something exploitable is reported |
| `CODE_OF_CONDUCT.md` | what taking part requires |
| `tests/` | every rule a gate holds, including the tables that freeze the reusable surface |
| `mise.toml` | every tool version, and the task names |
| `pyproject.toml` | the Python dependencies, the tool settings, the released version, and the surface it describes |
| `.pre-commit-config.yaml` | the prek hooks |
| `.github/actionlint.yaml`, `.github/zizmor.yml`, `.yamllint.yaml`, `.cspell.config.yaml`, `.markdownlint-cli2.jsonc`, `.taplo.toml` | each linter's own rules and exemptions |
| `.github/renovate.json`, `.github/dependabot.yml` | which bot owns version updates, and which owns security alerts |
| `.cliff.toml` | the commit types the release notes are rendered from |
