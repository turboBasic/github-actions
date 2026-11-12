# Research: Language Dependency Caches

## Cache location and compatibility behavior

### Decision: Use each tool's disposable dependency/build cache, not installed environments

UV exposes its cache directory and documents platform-specific defaults; it can be relocated through
`UV_CACHE_DIR`. Cargo's download cache lives under Cargo home, whose default is `$HOME/.cargo`; only the
registry and git cache subdirectories are selected because Cargo home also contains credentials and
configuration. Cargo output defaults to `target` at the workspace root. Go exposes separate module and
build cache locations. npm stores downloaded package data in its configured cache directory, separate
from `node_modules`.

Rationale: These directories are disposable inputs to task-owned installs/builds and match the observed
consumer work. Installed virtual environments and `node_modules` are rebuilt by the tasks. Cargo home
must not be cached wholesale because it can contain registry credentials.

Alternatives considered: Cache only downloads (misses measured Rust/Go compilation cost); cache
installed environments (platform-sensitive and duplicates task outputs); cache all of Cargo home
(risks persisting credentials and duplicates extracted sources).

Sources:

- [UV cache directory](https://docs.astral.sh/uv/concepts/cache/)
- [Cargo home and CI caching](https://doc.rust-lang.org/cargo/guide/cargo-home.html)
- [Cargo target directory](https://doc.rust-lang.org/cargo/reference/config.html#buildtarget-dir)
- [Go module cache](https://go.dev/ref/mod#module-cache)
- [Go module and build cache locations](https://go.dev/doc/manage-install)
- [npm cache](https://docs.npmjs.com/cli/v7/commands/npm-cache/)

## Cache key behavior

### Decision: Key by OS, architecture, toolchain declarations, and ecosystem manifests

GitHub Actions cache keys support runner contexts and expressions. Restore keys search compatible
prefixes after an exact miss. A cache entry's version also incorporates path metadata. Include the
relevant lockfiles/manifests and toolchain pin files in each ecosystem's exact key; restore prefixes
retain OS, architecture, and toolchain identity while allowing reuse after a dependency change.

Rationale: Compiled outputs cannot cross runner or compiler boundaries. Download caches can be more
portable, but one consistent compatibility boundary is easier to review and test.

Alternatives considered: Lockfile-only keys (can reuse compiled output across incompatible runners or
toolchains); no restore prefixes (throws away compatible package data after each lockfile update).

Source: [GitHub Actions dependency caching](https://docs.github.com/en/actions/reference/workflows-and-actions/dependency-caching).

## Cache failures and absent directories

### Decision: Prepare selected cache paths before restore (best-effort)

Cache locations may not exist until after a package task runs. The resolver creates them before restore.
When an override is supplied, it also sets the corresponding tool environment variable for later stages
so the cache action and package manager use the same directory. Cache steps use `continue-on-error` so
cache service failures do not block the caller's judgment.

Rationale: Cache availability is an optimization and cannot become a correctness prerequisite.

Alternative considered: Fail the job when a cache cannot be restored or saved (would make an optional
optimization a required gate).
