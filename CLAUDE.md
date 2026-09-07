# turboBasic/github-actions

@.specify/memory/constitution.md

@docs/ai-instructions.md

## The instruction layers

Four layers. This one is navigation: it names every artefact and states no rule.

| # | Layer | Purpose | Stability | Artefacts |
| --- | --- | --- | --- | --- |
| 1 | Invariants | what may never be violated | amended and versioned, rarely | `.specify/memory/constitution.md` |
| 2 | Conventions | how work is done here | edited as practice settles | `docs/ai-instructions.md` |
| 3 | Mechanics | the consumer contract, the procedures, the gates | moves with the code | `README.md`, `CONTRIBUTING.md`, `docs/technical-debt.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`, `tests/`, and the configs below |
| 4 | Navigation | where each fact lives | moves when an artefact does | this file, `.github/copilot-instructions.md` |

Layers 1 and 2 arrive by the two imports above, eagerly, in every session; layer 3 is read on demand.
GitHub Copilot has no import mechanism and reaches both rule layers by link from
`.github/copilot-instructions.md`.

## What each layer 3 artefact answers

| Artefact | Answers |
| --- | --- |
| `README.md` | what each workflow and action does, its inputs and their defaults, a copyable call site, and which major tag is current |
| `CONTRIBUTING.md` | the setup, the label set, how a workflow change is verified, and how a release is cut |
| `docs/technical-debt.md` | which shortcuts are deliberate, and the condition that clears each |
| `.github/PULL_REQUEST_TEMPLATE.md` | what a pull request has to answer before review starts |
| `docs/instruction-layers.md` | the layering itself, explained for another repository to adopt |
| `SECURITY.md` | how something exploitable is reported |
| `CODE_OF_CONDUCT.md` | what taking part requires |
| `tests/` | every rule a gate holds, including the tables that freeze the reusable surface |
| `mise.toml` | every tool version, and the task names |
| `pyproject.toml` | the Python dependencies, the tool settings, the released version, and the surface it describes |
| `.pre-commit-config.yaml` | the prek hooks |
| `.github/actionlint.yaml`, `.github/zizmor.yml`, `.yamllint.yaml`, `.cspell.config.yaml` | each linter's own rules and exemptions |
| `.github/renovate.json`, `.github/dependabot.yml` | which bot owns version updates, and which owns security alerts |
| `.cliff.toml` | the commit types the release notes are rendered from |
