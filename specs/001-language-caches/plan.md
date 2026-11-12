# Implementation Plan: Language Dependency Caches

**Branch**: `001-language-caches` | **Date**: 2026-11-12 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-language-caches/spec.md`

## Summary

Extend the existing `project-ci` job with automatically selected, best-effort caches for UV, Cargo,
Go, and npm. A standard-library-only `tbga` subcommand resolves native cache locations, applies the
six independent tool/cache path overrides, creates cache directories, and exposes paths as workflow outputs.
Cache steps remain inside the existing job and use platform, toolchain configuration, and dependency
manifests in their keys. The public check name and the five caller-selected tasks remain unchanged.

## Technical Context

**Language/Version**: GitHub Actions YAML; Python 3 standard library only, matching `actions/tbga/`.

**Primary Dependencies**: Existing pinned `actions/cache` v6; no new external action or package.

**Storage**: GitHub Actions cache service; no persistent repository data.

**Testing**: Pytest workflow-property tests and unit tests for cache path resolution, plus existing
schema, lint, typecheck, and CI entry points.

**Target Platform**: GitHub-hosted runners on Linux, macOS, and Windows, with platform-partitioned keys.

**Project Type**: Reusable workflow and its internal standard-library helper package.

**Performance Goals**: An exact key hit restores every configured cache; cache service failures do not
fail selected stages.

**Constraints**: Preserve the `project-ci` check name, contents-read permission, caller-owned stage
tasks, one-component boundary, and `actions/tbga/` standard-library-only imports. Caller cache paths
must arrive as environment values and must never be interpolated into a command line.

**Scale/Scope**: One workflow job per component; recursively detect all supported ecosystem manifests
in the checkout; six independently overridable tool cache locations.

## Constitution Check

- **I. One Owner Per Fact**: Workflow inputs/defaults live in `project-ci.yml`; README points there for
  the current input list. The ADR states the policy, while tests hold executable properties.
- **II. Secrets Never Persist**: Cache only Cargo registry/git download directories, never the Cargo
  home root; exclude credentials, configuration, `node_modules`, and virtual environments.
- **III. Gates Are Never Loosened**: Keep strict tests and linters; no new suppressions.
- **IV. What A Consumer Cannot Absorb Needs A New Line**: Inputs are optional and the check name stays
  fixed. Add all six names to `tests/published_surface.toml` in the same change.
- **V. A Published Ref Cannot Be Withdrawn**: Release compatibility is judged from the published
  surface fixture. Do not move or delete any ref.
- **VI. Caller-Controlled Text Never Reaches A Command Line**: Read path inputs from environment in
  Python; pass resulting paths only through `GITHUB_OUTPUT` to the cache action.
- **VII. A Required Gate Never Passes Without Judging**: The same job keeps its stage refusal and
  check identity; cache steps are advisory and cannot skip or fail stage judging.

**Gate result**: Pass with the ADR 0005 ruling and the listed safeguards.

## Project Structure

### Documentation (this feature)

```text
specs/001-language-caches/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── project-ci-cache-inputs.md
└── tasks.md
```

### Source Code

```text
.github/workflows/project-ci.yml       # Optional cache inputs, resolution, cache steps
actions/tbga/cache_paths.py            # Native paths, overrides, safe directory creation
actions/tbga/__main__.py               # Dispatch the cache-paths subcommand
docs/ai-instructions.md                # Cache exception to the language-neutral capability rule
docs/decisions/0004-*.md                # Mark superseded by ADR 0005
docs/decisions/0005-cache-component-dependencies.md
README.md                               # Explain automatic cache selection and link to inputs
tests/published_surface.toml            # Published optional workflow inputs
tests/test_cache_paths.py               # Path resolution and creation properties
tests/test_workflow_properties.py       # Detection, keys, paths, and unchanged task contract
tests/test_cli_commands.py               # CLI command registry
```

**Structure Decision**: Keep behavior in the existing reusable workflow and its `tbga` helper
package.
Do not add a separate workflow or capability. The helper receives all six path inputs through
environment variables, detects manifests without shell interpolation, creates cache roots, writes
tool overrides to `GITHUB_ENV`, and writes cache paths to `GITHUB_OUTPUT`. Cache steps consume those
outputs directly.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
| --------- | ---------- | ------------------------------------- |
| Language-specific cache knowledge in `project-ci` | Shared-job consumers cannot add steps inside the called job | Caller tasks cannot restore caches before they run; a separate workflow would split the component verdict |
