import subprocess
import tomllib
from collections.abc import Sequence
from typing import Any, cast

# A commit message holds newlines, so `git log` separates them with this rather than with a line break.
RECORD = "\x1e"

# The tag shape a release carries. A moving compatibility ref is a tag too, so the range and the refusals
# would both read one as a release without this.
RELEASE_TAG = "v[0-9]*.[0-9]*.[0-9]*"


def output(argv: Sequence[str], cwd: str) -> str:
    # No shell. Every value here is a path, a ref or a config name chosen outside this repository, and a
    # string handed to a shell is the one shape that turns any of them into a command.
    finished = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, check=False)
    if finished.returncode != 0:
        raise RuntimeError(
            f"{' '.join(argv)} exited {finished.returncode}: {finished.stderr.strip()}"
        )
    return finished.stdout


def git(repository: str, *arguments: str) -> str:
    return output(("git", *arguments), repository)


def release_tags(repository: str) -> tuple[str, ...]:
    listed = git(repository, "tag", "--list", RELEASE_TAG, "--sort=-v:refname")
    return tuple(line.strip() for line in listed.splitlines() if line.strip())


def span(repository: str) -> tuple[str, ...]:
    # The range starts at the newest release, or at the beginning of history where there is none. Both
    # are handed to `git log` as its own arguments, never assembled into one.
    tags = release_tags(repository)
    return (f"{tags[0]}..HEAD",) if tags else ("HEAD",)


def commit_messages(repository: str) -> tuple[str, ...]:
    logged = git(repository, "log", f"--format=%B{RECORD}", *span(repository))
    return tuple(record.strip() for record in logged.split(RECORD) if record.strip())


def changed_paths(repository: str) -> tuple[str, ...]:
    logged = git(repository, "log", "--format=", "--name-only", *span(repository))
    return tuple(sorted({line.strip() for line in logged.splitlines() if line.strip()}))


def render_notes(repository: str, config: str, destination: str) -> str:
    # Written to a file rather than returned through an output: the notes are the release body, and a
    # value that large travelling through `GITHUB_OUTPUT` and back is four rounds of quoting for text
    # rendered from commit messages.
    rendered = output(("git-cliff", "--config", config, "--unreleased"), repository)
    with open(destination, "w", encoding="utf-8") as handle:
        handle.write(rendered)
    return rendered


def declared_version(repository: str, manifest: str) -> str:
    with open(f"{repository}/{manifest}", "rb") as handle:
        table = tomllib.load(handle)
    project = table.get("project")
    if not isinstance(project, dict):
        return ""
    return str(cast(dict[str, Any], project).get("version", ""))
