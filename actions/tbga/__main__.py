import argparse
import sys
from collections.abc import Sequence
from typing import cast

from . import grammar, preflight, release, rulesets, writes

RULESET_VERDICT = "ruleset-verdict"
PREFLIGHT = "preflight"
COMPILE_GRAMMAR = "compile-grammar"

COMMANDS = (*release.DECISIONS, RULESET_VERDICT, PREFLIGHT, COMPILE_GRAMMAR, *writes.WRITES)


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
    if command == PREFLIGHT:
        return preflight.run()
    if command == COMPILE_GRAMMAR:
        return grammar.run()
    if command in writes.WRITES:
        return writes.run(command)
    return release.run(command)


if __name__ == "__main__":
    sys.exit(main())
