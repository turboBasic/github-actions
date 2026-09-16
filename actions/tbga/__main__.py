import argparse
import sys
from collections.abc import Sequence
from typing import cast

from . import release, rulesets

RULESET_VERDICT = "ruleset-verdict"

COMMANDS = (*release.DECISIONS, RULESET_VERDICT)


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
    return release.run(command)


if __name__ == "__main__":
    sys.exit(main())
