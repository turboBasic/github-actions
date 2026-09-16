import argparse
import sys
from collections.abc import Sequence
from typing import cast

from . import grammar, preflight, release, release_writes, rulesets

RULESET_VERDICT = "ruleset-verdict"
PREFLIGHT = "preflight"
COMPILE_GRAMMAR = "compile-grammar"
LIST_RULESETS = "list-rulesets"
READ_RULESETS = "read-rulesets"
APPLY_RULESET = "apply-ruleset"

COMMANDS = (
    *release.DECISIONS,
    RULESET_VERDICT,
    LIST_RULESETS,
    READ_RULESETS,
    APPLY_RULESET,
    PREFLIGHT,
    COMPILE_GRAMMAR,
    *release_writes.WRITES,
)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="tbga",
        description=(
            "Answers one question a workflow of this repository asks. Every value the answer needs "
            "arrives in the environment, never on this command line."
        ),
    )
    parser.add_argument("command", choices=COMMANDS)
    command = cast(str, parser.parse_args(argv).command)
    if command == RULESET_VERDICT:
        return rulesets.run()
    if command == LIST_RULESETS:
        return rulesets.run_list()
    if command == READ_RULESETS:
        return rulesets.run_read()
    if command == APPLY_RULESET:
        return rulesets.run_apply()
    if command == PREFLIGHT:
        return preflight.run()
    if command == COMPILE_GRAMMAR:
        return grammar.run()
    if command in release_writes.WRITES:
        return release_writes.run(command)
    return release.run(command)


if __name__ == "__main__":
    sys.exit(main())
