import re
import tomllib
from typing import Any, cast

from capabilities import REPO

MANIFEST = REPO / "mise.toml"
PROJECT = REPO / "pyproject.toml"

# The directory holding what a composite action runs, and so the one checked against the runner's
# interpreter rather than the version mise pins.
ACTION_ROOT = "actions"

# The lint task's whole-tree invocation, read from the command rather than from the task's position in
# the file, so a second one is covered the moment it is written.
WHOLE_TREE_LINT = re.compile(r"prek run .*--all-files.*")
SHOWS_THE_DIFF = "--show-diff-on-failure"

# Anything that would leave a rewriting hook reporting a verdict the task then discards. A hook that
# fixes a file exits non-zero, which is what reddens the check a consumer requires.
SWALLOWS_THE_VERDICT = ("|| true", "|| :", "; true", "continue-on-error", "set +e")

# A version mise resolves differently on two machines on one commit. `latest` is the obvious one; a
# bare table with no version and a range are the same failure spelled differently.
FLOATING = frozenset({"latest", "", "*"})


def tools() -> dict[str, Any]:
    manifest: dict[str, Any] = tomllib.loads(MANIFEST.read_text(encoding="utf-8"))
    return cast(dict[str, Any], manifest["tools"])


def floating(entry: Any) -> bool:
    # A table entry states its version under `version`; anything that is not a string or a table
    # naming one cannot be read as a version at all.
    if isinstance(entry, str):
        return entry.strip() in FLOATING
    if isinstance(entry, dict):
        return floating(cast(dict[str, Any], entry).get("version", ""))
    return True


def test_no_tool_version_floats() -> None:
    declared = tools()
    assert declared, (
        f"{MANIFEST.name} declares no [tools], so this gate is reading the wrong table and every "
        "version in it is free to float"
    )
    unpinned = sorted(name for name, entry in declared.items() if floating(entry))
    assert unpinned == [], (
        f"{MANIFEST.name} leaves {unpinned} without a concrete version. Two machines on one commit "
        "would then resolve different linters, so a green run locally says nothing about CI. Name the "
        "version each of those resolves to today"
    )


def lint_commands() -> list[str]:
    manifest: dict[str, Any] = tomllib.loads(MANIFEST.read_text(encoding="utf-8"))
    run: Any = cast(dict[str, Any], manifest["tasks"]["lint"])["run"]
    return [str(run)] if isinstance(run, str) else [str(line) for line in cast(list[Any], run)]


def whole_tree_lints() -> list[str]:
    return [line for command in lint_commands() for line in WHOLE_TREE_LINT.findall(command)]


def test_the_lint_task_lints_the_whole_tree() -> None:
    # The one thing making a published verdict differ from the maintainer's own run was judging part of
    # the tree. `project-ci` delegates the lint stage to this task, so this is where that is held.
    assert whole_tree_lints(), (
        f"{MANIFEST.name}'s lint task runs {lint_commands()}, none of which lints the whole tree. A "
        "consumer requiring the check project-ci composes would then be told a change is clean on the "
        "strength of a run that read part of the tree"
    )


def test_every_whole_tree_lint_reports_the_diff_that_would_fix_it() -> None:
    silent = [line for line in whole_tree_lints() if SHOWS_THE_DIFF not in line]
    assert silent == [], (
        f"whole-tree lints running without {SHOWS_THE_DIFF}: {silent}. A hook that rewrites a file "
        "reports only its own name, so the log says which hook failed and not the change that "
        "satisfies it"
    )


def test_nothing_in_the_lint_task_swallows_a_rewriting_hook_s_verdict() -> None:
    # The task rewrites files, and a rewrite exits non-zero. Discarding that status is the one edit that
    # would turn an auto-fixed tree into a green required check.
    offending = [
        f"{marker!r} in {command!r}"
        for command in lint_commands()
        for marker in SWALLOWS_THE_VERDICT
        if marker in command
    ]
    assert offending == [], (
        f"{MANIFEST.name}'s lint task discards an exit status: {offending}. A hook that fixed a file "
        "would then report success, and the fix never reaches the branch under review"
    )


def test_the_lint_task_readers_find_what_they_are_looking_for() -> None:
    # Pre-flight both. The steady state of the swallow check is an empty list and every invocation
    # carries the flag, so neither gate can otherwise show it still reads a line at all.
    assert WHOLE_TREE_LINT.fullmatch("prek run --all-files --skip pyright")
    assert not WHOLE_TREE_LINT.search("prek run --from-ref HEAD~1 --to-ref HEAD")
    stripped = [line.replace(f"{SHOWS_THE_DIFF} ", "") for line in whole_tree_lints()]
    assert stripped
    for line in stripped:
        assert SHOWS_THE_DIFF not in line
    assert any(marker in "prek run --all-files || true" for marker in SWALLOWS_THE_VERDICT)


def series(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.split(".") if part.isdigit())


def action_environment() -> dict[str, Any] | None:
    project: dict[str, Any] = tomllib.loads(PROJECT.read_text(encoding="utf-8"))
    pyright = cast(dict[str, Any], project["tool"]["pyright"])
    environments = cast(list[dict[str, Any]], pyright.get("executionEnvironments", []))
    return next((env for env in environments if str(env.get("root", "")) == ACTION_ROOT), None)


def test_what_a_composite_action_runs_is_checked_against_the_runner_s_interpreter() -> None:
    # A module a composite action runs gets whichever `python3` the caller left on the runner, and there
    # is no resolution step to fail loudly — only an ImportError in a consumer's job. Checking it at the
    # version mise pins here would report a newer stdlib symbol as available when it is not.
    pinned = str(tools()["python"])
    environment = action_environment()
    assert environment is not None, (
        f"{PROJECT.name} declares no pyright executionEnvironment rooted at {ACTION_ROOT!r}, so what a "
        f"composite action runs is checked against the {pinned} that {MANIFEST.name} pins. That version "
        "is on the runner only where the caller's own configuration put it there"
    )
    checked = str(environment["pythonVersion"])
    assert series(checked) < series(pinned), (
        f"{PROJECT.name} checks {ACTION_ROOT}/ at {checked} while {MANIFEST.name} pins {pinned}. The "
        "point of the environment is that the runner's interpreter is older than the one this repository "
        "develops against, so a version at or above the pin holds nothing"
    )


def test_the_environment_reader_and_the_version_order_read_what_they_are_given() -> None:
    # Pre-flight both. The gate's steady state is one matching environment, so neither the finder
    # returning None for the wrong root nor the ordering being the right way round can otherwise show.
    assert series("3.12") < series("3.14")
    assert series("3.9") < series("3.12")
    assert not series("3.14") < series("3.14")
    found = action_environment()
    assert found is not None
    assert str(found["root"]) == ACTION_ROOT


def test_the_floating_reader_tells_a_version_from_a_range() -> None:
    # Pre-flight the reader. Nothing floats today, which is the point, so the gate above can never show
    # that it would still notice one.
    assert floating("latest")
    assert floating("")
    assert floating({"version": "latest"})
    assert floating({})
    assert floating(None)
    assert not floating("1.7.12")
    assert not floating({"version": "1.7.12"})
