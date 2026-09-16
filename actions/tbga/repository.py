import subprocess
import tomllib
from typing import Any, cast

from . import output
from .version import is_release_tag

# A commit message holds newlines, so `git log` separates them with this rather than with a line break.
RECORD = "\x1e"

# Narrows what git lists; `is_release_tag` decides. A glob cannot anchor, so this admits `v1.2.3-rc1`
# and `v1.2.3.4`, and `--sort=-v:refname` puts the four-part one first.
RELEASE_TAG_GLOB = "v[0-9]*.[0-9]*.[0-9]*"


def git(repository: str, *arguments: str) -> str:
    return output(("git", *arguments), repository)


def release_tags(repository: str) -> tuple[str, ...]:
    listed = git(repository, "tag", "--list", RELEASE_TAG_GLOB, "--sort=-v:refname")
    return tuple(tag for line in listed.splitlines() if is_release_tag(tag := line.strip()))


def span(repository: str) -> tuple[str, ...]:
    # No release yet means the whole history.
    tags = release_tags(repository)
    return (f"{tags[0]}..HEAD",) if tags else ("HEAD",)


def commit_messages(repository: str) -> tuple[str, ...]:
    logged = git(repository, "log", f"--format=%B{RECORD}", *span(repository))
    return tuple(record.strip() for record in logged.split(RECORD) if record.strip())


def changed_paths(repository: str) -> tuple[str, ...]:
    logged = git(repository, "log", "--format=", "--name-only", *span(repository))
    return tuple(sorted({line.strip() for line in logged.splitlines() if line.strip()}))


def ref_exists(repository: str, ref: str) -> bool:
    finished = subprocess.run(
        ("git", "rev-parse", "--verify", "--quiet", ref),
        cwd=repository,
        capture_output=True,
        text=True,
        check=False,
    )
    return finished.returncode == 0


def version_on_ref(repository: str, ref: str, manifest: str) -> str:
    # An absent branch and a branch declaring no version both read as empty; the caller treats them alike.
    if not ref or not ref_exists(repository, ref):
        return ""
    try:
        shown = git(repository, "show", f"{ref}:{manifest}")
    except RuntimeError:
        return ""
    table = tomllib.loads(shown)
    project = table.get("project")
    if not isinstance(project, dict):
        return ""
    return str(cast(dict[str, Any], project).get("version", ""))


def messages_between(repository: str, base: str, ref: str) -> tuple[str, ...]:
    # Newest first: the trailer search walks down past a person's edits to the workflow's own commit.
    if not ref or not base or not ref_exists(repository, ref):
        return ()
    logged = git(repository, "log", f"--format=%B{RECORD}", f"{base}..{ref}")
    return tuple(record.strip() for record in logged.split(RECORD) if record.strip())


def render_notes(repository: str, config: str, destination: str) -> str:
    # A file, not an output. The notes are the release body, and `gh release create` reads a file anyway.
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
