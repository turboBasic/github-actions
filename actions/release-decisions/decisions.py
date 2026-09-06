import json
import re
import tomllib
from collections.abc import Iterable
from typing import Any, Literal, NamedTuple

# A plain alias rather than a `type` statement: a caller whose mise.toml pins no python falls back
# to the runner's own interpreter, so this module keeps to syntax every maintained version parses.
Version = tuple[int, int, int]
Severity = Literal["notice", "error"]

# The whole string, so no pre-release, no build metadata, and no `v` — the `v` belongs to the tag.
PLAIN_VERSION = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")

# What a consumer resolves: every reusable workflow and composite action, minus this repository's own
# plumbing. tests/test_release_decisions.py holds the exclusions to OWN_CI.
SURFACE_INCLUDE = (".github/workflows/**", "actions/**")
OWN_WORKFLOWS = (
    "ci.yml",
    "commit-messages.yml",
    "dependabot-automerge.yml",
    "drift.yml",
    "release.yml",
    "release-proposal.yml",
)
SURFACE_EXCLUDE = tuple(f".github/workflows/{name}" for name in OWN_WORKFLOWS)


class ReleaseVerdict(NamedTuple):
    proceed: bool
    severity: Severity
    message: str


def parse_version(text: str) -> Version | None:
    # `None` rather than an exception, so the caller chooses the message.
    found = PLAIN_VERSION.match(text)
    return (int(found[1]), int(found[2]), int(found[3])) if found else None


def highest_version(refs: Iterable[str]) -> Version | None:
    # Refs arrive as `gh api` produced them, `refs/tags/v4.0.3`. Compared as integer triples across
    # every major, because a frozen major is never backported, only left where it is.
    found = [
        version
        for ref in refs
        if (version := parse_version(ref.rpartition("/")[2].removeprefix("v")))
    ]
    return max(found) if found else None


def is_ahead(version: Version, highest: Version | None) -> bool:
    return highest is None or version > highest


def next_version(current: Version, *, breaking: bool, feature: bool) -> Version:
    major, minor, patch = current
    if breaking:
        return (major + 1, 0, 0)
    if feature:
        return (major, minor + 1, 0)
    return (major, minor, patch + 1)


def increment_reason(*, breaking: bool, feature: bool) -> str:
    if breaking:
        return "a breaking change to the consumer surface"
    if feature:
        return "a feat touching the consumer surface"
    return "nothing consumers resolve changed"


def notes_are_empty(text: str) -> bool:
    # Content, never size and never an exit code: git-cliff emits a trailing newline for a range
    # holding nothing and for one holding only a `bump`, and exits 0 for both.
    return not text.strip()


def verdicts(context: str) -> tuple[bool, bool]:
    releases: Any = json.loads(context)
    commits: list[dict[str, Any]] = [
        commit for release in releases for commit in release["commits"]
    ]
    # Identity against `true`: `--context` omits the key entirely on a commit matching no
    # Conventional Commit, and an absent value is not a false one.
    breaking = any(commit.get("breaking") is True for commit in commits)
    feature = any(str(commit.get("raw_message", "")).startswith("feat") for commit in commits)
    return breaking, feature


def breaks_under_non_major(version: Version, highest_major: int | None, *, breaking: bool) -> bool:
    # False when no highest major exists: there is no tag to be moved onto a broken contract.
    return breaking and highest_major is not None and version[0] == highest_major


def declared_version(raw: bytes) -> str:
    # Keyed by table, never by the first `version = ` line: a positional match would take the version
    # from whichever table came first.
    manifest: dict[str, Any] = tomllib.loads(raw.decode())
    project: dict[str, Any] = manifest["project"]
    return str(project["version"])


def release_verdict(
    *, version: str, highest: str, ahead: bool, event_name: str, dry_run: bool
) -> ReleaseVerdict:
    # Three verdicts for one condition, because what it means depends on who asked.
    if ahead:
        return ReleaseVerdict(True, "notice", "")
    if event_name == "push":
        return ReleaseVerdict(
            False,
            "notice",
            f"v{version} is already released, so this merge cuts nothing. "
            f"Bump [project].version to release again.",
        )
    not_ahead = (
        f"pyproject.toml declares {version}, which is not ahead of the highest release v{highest}"
    )
    if dry_run:
        return ReleaseVerdict(True, "notice", f"would refuse: {not_ahead}")
    return ReleaseVerdict(
        False,
        "error",
        f"{not_ahead}. Bump [project].version in a pull request — that is what decides the next "
        f"version.",
    )


def surface_args() -> list[str]:
    return [
        *(arg for path in SURFACE_INCLUDE for arg in ("--include-path", path)),
        *(arg for path in SURFACE_EXCLUDE for arg in ("--exclude-path", path)),
    ]
