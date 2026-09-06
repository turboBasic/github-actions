import json
import os
import re
import tomllib
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any, Literal, NamedTuple, NoReturn

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


# Everything below is the I/O the pure functions above are kept clear of: environment in, GITHUB_OUTPUT
# and workflow commands out. Every value arrives through `env`, declared in action.yml, so no `${{ }}`
# reaches an argument list or a shell line.


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, "") or default


def _out(name: str, value: str) -> None:
    path = _env("GITHUB_OUTPUT")
    if path:
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(f"{name}={value}\n")


def _say(severity: Severity, message: str) -> None:
    print(f"::{severity}::{message}")


def _stop(severity: Severity, message: str) -> NoReturn:
    # Non-zero is how a caller learns the answer without comparing a string in shell. An `error`
    # fails the job; a `notice` is a workflow that declines to act, which its caller swallows.
    _say(severity, message)
    raise SystemExit(1)


def _pyproject_version() -> str:
    return declared_version(Path(_env("PYPROJECT", "pyproject.toml")).read_bytes())


def _render(version: Version) -> str:
    return ".".join(str(part) for part in version)


def _flag(value: bool) -> str:
    return "true" if value else "false"


def _declared_version() -> None:
    version = _pyproject_version()
    # Both channels: stdout for a caller invoking this by in-repo path inside a larger step, the
    # output for one reaching it through `uses:`.
    print(version)
    _out("version", version)


def _surface_args() -> None:
    args = surface_args()
    print("\n".join(args))
    # One line, safe because no argument holds a space — asserted by
    # tests/test_release_decisions.py, which is what lets a caller read it back with `read -ra`.
    _out("args", " ".join(args))


def _verify_version() -> None:
    dry_run = _env("DRY_RUN") == "true"
    ref = _env("GITHUB_REF")
    if ref != "refs/heads/main" and not dry_run:
        _stop(
            "error",
            f"releases are cut from main; this run is on {ref}. Dispatch with dry-run to exercise "
            f"this workflow from a branch.",
        )

    version = _pyproject_version()
    parsed = parse_version(version)
    if parsed is None:
        _stop("error", f"pyproject.toml declares no plain semantic version: '{version}'")

    highest = highest_version(_env("TAG_REFS").split())
    verdict = release_verdict(
        version=version,
        highest=_render(highest) if highest else "",
        ahead=is_ahead(parsed, highest),
        event_name=_env("EVENT_NAME", _env("GITHUB_EVENT_NAME")),
        dry_run=dry_run,
    )
    if verdict.message:
        _say(verdict.severity, verdict.message)
    if verdict.severity == "error":
        raise SystemExit(1)

    _out("proceed", _flag(verdict.proceed))
    _out("version", version)
    _out("highest-major", str(highest[0]) if highest else "")


def _check_notes() -> None:
    current = _env("CURRENT_VERSION")
    if notes_are_empty(Path(_env("NOTES_FILE")).read_text(encoding="utf-8")):
        if _env("SEVERITY") == "notice":
            _stop(
                "notice",
                f"nothing has landed since v{current} that the notes would describe, so no release "
                f"is due.",
            )
        _stop(
            "error",
            "the range since the previous version tag renders no notes, so there is nothing to "
            "release. No tag was created.",
        )

    # Absent for a caller that only asks about emptiness. The refusal below reads the
    # surface-filtered range, while the notes it just tested read the whole one.
    context_file = _env("CONTEXT_FILE")
    if not context_file:
        return

    breaking, _ = verdicts(Path(context_file).read_text(encoding="utf-8"))
    _out("breaking", _flag(breaking))
    highest_major = _env("HIGHEST_MAJOR")
    parsed = parse_version(current)
    if parsed and breaks_under_non_major(
        parsed, int(highest_major) if highest_major else None, breaking=breaking
    ):
        _stop(
            "error",
            f"the range breaks the consumer surface but {current} is not a new major, so publishing "
            f"it would move v{highest_major} onto a broken contract. No tag was created.",
        )


def _next_version() -> None:
    current = _env("CURRENT_VERSION", _pyproject_version())
    parsed = parse_version(current)
    if parsed is None:
        _stop("error", f"pyproject.toml declares no plain semantic version: '{current}'")

    breaking, feature = verdicts(Path(_env("CONTEXT_FILE")).read_text(encoding="utf-8"))
    proposed = _render(next_version(parsed, breaking=breaking, feature=feature))
    why = increment_reason(breaking=breaking, feature=feature)

    _say("notice", f"proposing {proposed}: {why}.")
    _out("next-version", proposed)
    _out("reason", why)
    _out("breaking", _flag(breaking))
    _out("feature", _flag(feature))


DECISIONS: dict[str, Callable[[], None]] = {
    "check-notes": _check_notes,
    "declared-version": _declared_version,
    "next-version": _next_version,
    "surface-args": _surface_args,
    "verify-version": _verify_version,
}


if __name__ == "__main__":
    decision = _env("DECISION")
    if decision not in DECISIONS:
        _stop("error", f"unknown decision {decision!r}; expected one of {sorted(DECISIONS)}")
    DECISIONS[decision]()
