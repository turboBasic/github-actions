# Feature Specification: Language Dependency Caches

**Feature Branch**: `001-language-caches`

**Created**: 2026-11-12

**Status**: Draft

**Input**: User description: "Provide language-specific caches to consumers with sane defaults and ability to override cache locations. Consumers already use UV, Cargo, Go and Node (npm/node_modules)."

## User Scenarios & Testing

### User Story 1 - Reuse dependency and build caches (Priority: P1)

As a consumer of `project-ci`, I want its job to restore and save caches for the package ecosystems used in my repository so repeated CI runs spend less time downloading dependencies and rebuilding artifacts.

**Why this priority**: The consumer cannot add steps to the called job, and current runs repeatedly download dependencies and compile code.

**Independent Test**: Call `project-ci` with a repository containing a supported ecosystem manifest; verify that its matching cache is restored or saved without changing the consumer workflow, and that an unrelated ecosystem is not configured.

**Acceptance Scenarios**:

1. **Given** a repository with `uv.lock`, `Cargo.lock`, `go.mod`, or npm `package-lock.json`, **When** `project-ci` runs, **Then** it configures only the matching ecosystem caches using their defaults.
2. **Given** a supported manifest nested below the repository root, **When** `project-ci` scans the checkout, **Then** it detects and caches that ecosystem.
3. **Given** a repository with no supported manifests, **When** `project-ci` runs, **Then** no language cache is configured and the existing stages and check name still work.
4. **Given** a repository with several supported ecosystems, **When** `project-ci` runs, **Then** every detected ecosystem receives its corresponding caches.

### User Story 2 - Override cache locations (Priority: P2)

As a consumer with non-default tool configuration, I want to override an individual cache location and have the corresponding tool use it without changing other caches or rewriting tasks.

**Why this priority**: Native defaults serve most consumers, while independently configurable paths make the behavior usable when a repository or runner relocates a tool cache.

**Independent Test**: Set one cache path input and leave all others unset; verify that only the selected tool/cache pair uses the override and the other caches retain their defaults.

**Acceptance Scenarios**:

1. **Given** a detected ecosystem and no path override, **When** `project-ci` runs, **Then** that cache uses its tool-native default location.
2. **Given** a path override for one cache location, **When** `project-ci` runs, **Then** the corresponding tool and cache action use it and the other cache locations are unchanged.
3. **Given** a path override for a cache whose directory does not yet exist, **When** `project-ci` runs, **Then** restoring or saving that cache does not fail solely because the directory was initially absent.

### User Story 3 - Keep reused cache data compatible and safe (Priority: P1)

As a consumer, I want cache entries isolated by the operating environment, toolchain, and dependency declarations, so a cache hit cannot silently reuse incompatible compiled output or persist credentials.

**Why this priority**: Compiled outputs are platform-sensitive, and cache contents can be read by workflows with repository access.

**Independent Test**: Inspect generated cache keys and paths for fixtures with changed OS, architecture, toolchain, lockfile, and credential/configuration files; verify isolation and exclusions.

**Acceptance Scenarios**:

1. **Given** otherwise matching cache inputs but a different runner OS or architecture, **When** a cache is restored, **Then** entries from the other platform are not reused.
2. **Given** a changed relevant toolchain or lockfile, **When** a cache is restored, **Then** the exact key changes and compatible prior entries may be reused through restore prefixes.
3. **Given** the selected cache locations, **When** cache paths are assembled, **Then** Cargo credentials/configuration, Python virtual environments, and generated `node_modules` are excluded.

## Edge Cases

- Several manifests for one ecosystem may exist in different subdirectories; all relevant manifests and lockfiles must contribute to the ecosystem cache key.
- A workflow may use only one ecosystem even when unrelated manifests exist elsewhere in the checkout; detection is repository-wide as selected for this feature.
- An optional cache path input may be empty or point to a directory that does not yet exist.
- A repository with no supported manifests must continue to run all selected stages and report the existing `project-ci` check.
- Cache misses and cache service failures must not prevent dependency tools and stages from running.

## Requirements

### Functional Requirements

- **FR-001**: `project-ci` MUST detect UV, Cargo, Go, and npm manifests by scanning the checked-out repository recursively and configure caches only for ecosystems represented by `uv.lock`, `Cargo.lock`, `go.mod`, or `package-lock.json`.
- **FR-002**: The UV cache MUST use the tool-native package cache location by default.
- **FR-003**: Cargo caches MUST cover downloaded registry and git data and compiled `target` output by default.
- **FR-004**: Go caches MUST cover module downloads and the Go build cache by default.
- **FR-005**: npm MUST cache its package download store by default and MUST NOT cache generated `node_modules`.
- **FR-006**: Six optional path inputs MUST independently redirect both the relevant tool and cache action: UV cache, Cargo home/download cache, Cargo target, Go module cache, Go build cache, and npm cache. Cargo registry and git download directories MUST share the Cargo home input while remaining separate cache paths. An omitted override MUST retain that tool's native default.
- **FR-007**: Cache keys MUST include runner OS, architecture, relevant toolchain identity, and all relevant manifests and lockfiles. Restore prefixes MAY reuse prior data only within the same OS, architecture, and toolchain boundaries.
- **FR-008**: Cache locations MUST exclude credentials and tool configuration that can contain secrets, including Cargo credentials, and MUST exclude Python virtual environments.
- **FR-009**: Cache misses, missing initial cache directories, or cache service failures MUST NOT skip or fail the caller's selected stages solely because of caching.
- **FR-010**: The change MUST preserve the existing `project-ci` job/check name, its one-component scope, and its caller-selected stages; it MUST NOT introduce a second required check.
- **FR-011**: The change MUST add a decision record superseding ADR 0004's prohibition only for language-specific cache preparation, and update the conventions and README to describe the shipped inputs and behavior.
- **FR-012**: Tests MUST cover ecosystem detection, nested manifests, defaults, independent overrides, key isolation and restore prefixes, missing cache directories, secret/configuration exclusions, and preservation of the existing workflow contract.

### Key Entities

- **Ecosystem cache**: A set of package-download or compiled-output locations selected by a supported ecosystem manifest, with an independent default path, override path, and key inputs.
- **Cache key**: The identifier derived from runner platform, toolchain identity, and the relevant dependency manifests or lockfiles.

## Success Criteria

### Measurable Outcomes

- **SC-001**: A second run with unchanged platform, toolchain, and manifests can restore every available cache for each detected ecosystem.
- **SC-002**: A consumer using only default paths adds no cache configuration to its workflow call.
- **SC-003**: A consumer can override any one tool/cache location without changing the defaults used by other locations.
- **SC-004**: Changes to runner OS, architecture, relevant toolchain, or dependency lockfiles produce the required cache-key boundaries.
- **SC-005**: Repositories without supported manifests continue to run the same selected stages under the existing required check name.

## Assumptions

- Ecosystem detection is based on the presence of the named manifest or lockfile anywhere in the checkout; the shared workflow does not infer which tasks use each ecosystem.
- Native package-download and build cache locations are the defaults, subject to each tool's existing runner configuration.
- Cache entries are an optimization only; cache availability must not become a prerequisite for correctness.
- A separate decision record will supersede the relevant part of ADR 0004, while its component boundary and check identity remain in force.
