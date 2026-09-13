import json
import re
import tomllib
from typing import Any, cast

from commitizen.config.base_config import BaseConfig
from commitizen.cz.conventional_commits.conventional_commits import ConventionalCommitsCz

from capabilities import CONVENTIONAL_COMMITS, REPO, allowed_commit_types, load, values_at

LOCKFILE = REPO / "uv.lock"
RENOVATE = REPO / ".github" / "renovate.json"

TOOL = "commitizen"

# The version the workflow names literally, as `CZ_VERSION: "x.y.z"` in the shared env block.
PINNED_IN_WORKFLOW = re.compile(r"^\s*CZ_VERSION:\s*[\"']?([0-9][0-9A-Za-z.\-+]*)[\"']?\s*$")

# The alternation at the head of the tool's own schema, which is the set of types it ships.
SHIPPED_TYPES = re.compile(r"\(([a-z]+(?:\|[a-z]+)+)\)")


def shipped_types() -> list[str]:
    # Read from the tool rather than restated here. A literal list in this file would be the third copy
    # of a fact that already has two, which is what this gate exists to prevent.
    pattern = ConventionalCommitsCz(BaseConfig()).schema_pattern()
    found = SHIPPED_TYPES.search(pattern)
    assert found is not None, (
        f"{TOOL}'s schema pattern no longer opens with an alternation of its types, so this gate cannot "
        f"read what it ships. The pattern read: {pattern}"
    )
    return sorted(found.group(1).split("|"))


def workflow_version() -> str | None:
    for line in CONVENTIONAL_COMMITS.read_text(encoding="utf-8").splitlines():
        match = PINNED_IN_WORKFLOW.match(line)
        if match is not None:
            return match.group(1)
    return None


def locked_version() -> str | None:
    locked: dict[str, Any] = tomllib.loads(LOCKFILE.read_text(encoding="utf-8"))
    for package in cast(list[dict[str, Any]], locked.get("package", [])):
        if package.get("name") == TOOL:
            return str(package["version"])
    return None


def test_the_declared_types_are_the_set_the_commit_tool_ships() -> None:
    declared = sorted(allowed_commit_types())
    shipped = shipped_types()
    assert declared and shipped, (
        f"one side of this comparison is empty — declared {declared}, shipped {shipped} — so it is "
        "holding nothing"
    )
    assert declared == shipped, (
        f"conventional-commits.yml admits {declared} and {TOOL} {locked_version()} ships {shipped}. The "
        f"local commit-msg hook judges with the tool's set and both required checks judge with the "
        f"workflow's, so a message accepted on a maintainer's machine would fail in CI, or the reverse. "
        f"Missing from the workflow: {sorted(set(shipped) - set(declared))}; unknown to the tool: "
        f"{sorted(set(declared) - set(shipped))}"
    )


def test_the_commit_tool_version_is_one_fact() -> None:
    in_workflow, in_lockfile = workflow_version(), locked_version()
    assert in_workflow is not None, (
        f"no CZ_VERSION found in {CONVENTIONAL_COMMITS.name}, so this gate is reading the wrong place "
        "and the two versions are free to drift"
    )
    assert in_lockfile is not None, (
        f"{LOCKFILE.name} resolves no package named {TOOL}, so this gate is reading the wrong place"
    )
    assert in_workflow == in_lockfile, (
        f"{CONVENTIONAL_COMMITS.name} installs {TOOL} {in_workflow} and {LOCKFILE.name} resolves "
        f"{in_lockfile}. The hook judges a message with the locked one and CI with the named one, so a "
        f"dependency bump that moves only one leaves the two verdicts on different binaries. Set "
        f"CZ_VERSION to {in_lockfile}, or bump the dependency and run `uv lock`"
    )


def test_the_readers_find_a_version_they_are_given() -> None:
    # Pre-flight both. Either returning None would fail the gate above loudly, but a reader matching the
    # wrong thing would not, so each is shown a line it must read and one it must not.
    match = PINNED_IN_WORKFLOW.match('  CZ_VERSION: "4.18.0"')
    assert match is not None and match.group(1) == "4.18.0"
    assert PINNED_IN_WORKFLOW.match("  CZ_CONFIG: |") is None
    assert SHIPPED_TYPES.search("(?s)(build|chore|feat)(\\(\\S+\\))?") is not None
    assert SHIPPED_TYPES.search("(?s)(feat)") is None


def renovate_cz_pattern() -> str:
    config = json.loads(RENOVATE.read_text(encoding="utf-8"))
    (manager,) = [m for m in config["customManagers"] if m["depNameTemplate"] == TOOL]
    (pattern,) = manager["matchStrings"]
    # Renovate's regex flavour names a group as JS does, `(?<name>`; Python's re module requires the
    # `P` that JS omits. Translating it is what lets this test compile the same pattern Renovate runs.
    return pattern.replace("(?<currentValue>", "(?P<currentValue>")


def test_renovates_reader_finds_the_version_the_test_finds() -> None:
    # renovate.json is a second reader of the same CZ_VERSION line, held to nothing until now.
    # Pre-flight it the same way the test's own reader is pre-flighted above, or a quoting change
    # nothing here rejects could pass this suite while leaving Renovate extracting nothing.
    match = re.search(renovate_cz_pattern(), CONVENTIONAL_COMMITS.read_text(encoding="utf-8"))
    assert match is not None, (
        f"{RENOVATE.name}'s commitizen customManagers pattern does not match anything in "
        f"{CONVENTIONAL_COMMITS.name}, so Renovate would never propose a CZ_VERSION bump"
    )
    assert match.group("currentValue") == workflow_version()


def test_the_workflow_installs_the_version_it_names() -> None:
    # The literal is only one fact while every install in the workflow reads it. A second `pipx install`
    # naming a version inline would pass the gate above and judge with something else.
    doc = load(CONVENTIONAL_COMMITS)
    inline = [
        f"{where}: {run}"
        for where, run in values_at(doc, "run")
        if TOOL in run and "$CZ_VERSION" not in run
    ]
    assert inline == [], (
        f"{CONVENTIONAL_COMMITS.name} installs {TOOL} without reading CZ_VERSION: {inline}. A version "
        "written inline is a second answer to which binary judges a message"
    )
