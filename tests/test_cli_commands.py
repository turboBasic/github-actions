import re
from typing import Any, cast

from capabilities import Doc, action_docs, workflow_docs
from tbga.__main__ import COMMANDS

# What an action's step runs: either the subcommand as a literal, or an environment value the shell
# expands into one argument.
LITERAL = re.compile(r"python3 -m tbga ([a-z][a-z0-9-]*)")
FROM_ENVIRONMENT = re.compile(r'python3 -m tbga "\$([A-Z_]+)"')

# `${{ inputs.name }}`, which is how an action's env entry names the input carrying its subcommand.
INPUT = re.compile(r"\$\{\{\s*inputs\.([a-z][a-z0-9-]*)\s*\}\}")

SELF = "$/actions/"


def steps(doc: Doc) -> list[Doc]:
    return cast(list[Doc], cast(Doc, doc.get("runs", {})).get("steps", []))


def literals() -> dict[str, str]:
    # Action directory to the subcommand its step names outright.
    found: dict[str, str] = {}
    for name, doc in action_docs().items():
        for step in steps(doc):
            script = str(step.get("run", ""))
            if FROM_ENVIRONMENT.search(script):
                continue
            match = LITERAL.search(script)
            if match:
                found[name] = match.group(1)
    return found


def by_input() -> dict[str, str]:
    # Action directory to the input whose value becomes the subcommand.
    found: dict[str, str] = {}
    for name, doc in action_docs().items():
        for step in steps(doc):
            variable = FROM_ENVIRONMENT.search(str(step.get("run", "")))
            if not variable:
                continue
            declared = str(cast(dict[str, Any], step.get("env", {})).get(variable.group(1), ""))
            carried = INPUT.search(declared)
            if carried:
                found[name] = carried.group(1)
    return found


def named_by_workflows() -> list[tuple[str, str, str]]:
    # Every subcommand a workflow names, as (workflow, action, value).
    carries = by_input()
    found: list[tuple[str, str, str]] = []
    for workflow, doc in workflow_docs().items():
        for job in cast(dict[str, Doc], doc.get("jobs", {})).values():
            for step in cast(list[Doc], job.get("steps", [])):
                uses = str(step.get("uses", ""))
                if not uses.startswith(SELF):
                    continue
                action = uses.removeprefix(SELF)
                if action not in carries:
                    continue
                given = cast(dict[str, Any], step.get("with", {}))
                found.append((workflow, action, str(given.get(carries[action], ""))))
    return found


def test_every_subcommand_an_action_names_outright_exists() -> None:
    named = literals()
    assert named, "no action names a subcommand as a literal, so this gate ties nothing"
    unknown = sorted(
        f"{action} runs {command!r}" for action, command in named.items() if command not in COMMANDS
    )
    assert unknown == [], (
        f"{unknown}, which the entry point does not offer. argparse refuses it at runtime, on a path no "
        f"pull request check reaches. It answers only {sorted(COMMANDS)}"
    )


def test_every_subcommand_a_workflow_names_exists() -> None:
    # The failure this exists for: `publish-release` misspelled leaves the version tag created, the
    # release never published and the moving ref never moved. None of the three can be withdrawn, and
    # nothing else reads that string.
    named = named_by_workflows()
    assert named, "no workflow names a subcommand, so this gate ties nothing"
    unknown = sorted(
        f"{workflow} passes {value!r} to {action}"
        for workflow, action, value in named
        if value not in COMMANDS
    )
    assert unknown == [], (
        f"{unknown}, which the entry point does not offer. It answers only {sorted(COMMANDS)}"
    )


def test_every_action_that_runs_the_package_is_reached_one_of_the_two_ways() -> None:
    # Neither reader may quietly stop matching: every action running the package names its subcommand
    # either outright or through an input, and none does both or neither.
    running = {
        name
        for name, doc in action_docs().items()
        if any("python3 -m tbga" in str(step.get("run", "")) for step in steps(doc))
    }
    assert running, "no action runs the package, so both readers above are reading nothing"
    assert running == set(literals()) | set(by_input())
    assert not set(literals()) & set(by_input())


def first(pattern: re.Pattern[str], text: str) -> str | None:
    found = pattern.search(text)
    return found.group(1) if found else None


def test_the_readers_read_the_shapes_they_are_given() -> None:
    # Pre-flight both forms. The tree's steady state is every subcommand valid, so neither gate above can
    # otherwise show that it still reads a step at all.
    assert first(LITERAL, "python3 -m tbga compile-grammar") == "compile-grammar"
    assert first(FROM_ENVIRONMENT, 'python3 -m tbga "$COMMAND"') == "COMMAND"
    assert first(FROM_ENVIRONMENT, "python3 -m tbga preflight") is None
    assert first(INPUT, "${{ inputs.command }}") == "command"
    assert first(INPUT, "${{ inputs.decision }}") == "decision"
    # Both readers find the tree's own actions, so a rename of either form fails rather than passing.
    assert "preflight" in literals()
    assert by_input()["release-decisions"] == "decision"
