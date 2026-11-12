# `tbga`

`tbga` is internal Python support code for this repository's reusable workflows and composite actions.
It is not a published action or a supported consumer interface.

The package handles cache path discovery, tool preflight checks, commit grammar compilation, release
decisions and writes, and ruleset operations. Consumers call the workflow or action that owns the
capability; those definitions invoke this package behind the scenes.

Automation runs its commands as `python3 -m tbga <command>`. Composite actions load the package from
their action path. The `project-ci` workflow loads it from the workflow repository at the resolved commit,
since its default checkout is the caller's repository.
