# Contract: `project-ci` Cache Inputs

All inputs are optional strings. An empty value selects the tool-native default. A non-empty value
sets the tool's own cache environment variable and the matching cache action path. Consumers that use
defaults need not change their workflow call.

|Input|Cache location|
|---|---|
|`uv-cache-path`|UV package cache|
|`cargo-home-cache-path`|Cargo home (`CARGO_HOME`); cache only its registry and git subdirectories|
|`cargo-target-cache-path`|Cargo compiled target output (`CARGO_TARGET_DIR`); defaults cover detected workspace targets|
|`go-module-cache-path`|Go module download cache (`GOMODCACHE`)|
|`go-build-cache-path`|Go compiled build cache (`GOCACHE`)|
|`npm-cache-path`|npm package download cache (`npm_config_cache`); not `node_modules`|

The workflow detects supported ecosystems recursively using `uv.lock`, `Cargo.lock`, `go.mod`, and
`package-lock.json`. Cache keys include platform, relevant toolchain declarations, and all matching
dependency manifests/lockfiles. Cache actions are best-effort; cache failures do not change the verdict
of the selected component tasks.
