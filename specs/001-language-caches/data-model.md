# Data Model: Language Dependency Caches

## Ecosystem cache

Represents one cacheable location selected by a supported manifest.

|Field|Constraint|
|---|---|
|ecosystem|One of UV, Cargo, Go, npm|
|location kind|UV package cache; Cargo registry, git, or target; Go module or build; npm package cache|
|default path|Native disposable cache path for the runner and tool configuration|
|override path|Optional consumer-supplied path; if empty, use the default; redirects both tool and cache action|
|manifest set|All matching ecosystem manifests/lockfiles in the checkout|
|key|OS, architecture, relevant toolchain declarations, and manifest set|

Cargo's registry and git cache locations share one Cargo home override, exclude the home root,
credentials, and configuration, and remain separate cache paths. The Cargo target location may
represent one or more workspace `target` directories.

## Cache key

The stable compatibility identity used to restore and save one ecosystem cache. Exact keys change when
the runner platform, relevant toolchain, or dependency manifests change. Restore prefixes never cross
the runner OS, architecture, or toolchain boundary.
