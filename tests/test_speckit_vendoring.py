import hashlib
import json
import tomllib
from pathlib import Path
from typing import Any, cast

import pytest

from capabilities import REPO

MANIFESTS = sorted((REPO / ".specify" / "integrations").glob("*.manifest.json"))

PIN = "pipx:specify-cli"

RESYNC = (
    "run `mise run spec-kit-upgrade` and commit what it rewrites. Never `specify self upgrade` — that "
    "replaces the binary outside mise, leaving the tree pinning one version and shipping another's files"
)


def pinned_version() -> str:
    manifest: dict[str, Any] = tomllib.loads((REPO / "mise.toml").read_text(encoding="utf-8"))
    pin = cast(dict[str, Any], manifest["tools"])[PIN]
    return cast(str, pin["version"]) if isinstance(pin, dict) else str(pin)


def recorded(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def test_at_least_one_manifest_is_read() -> None:
    assert MANIFESTS, (
        "no integration manifest found under .specify/integrations/, so both gates below are "
        "parametrised over nothing and report green without reading anything"
    )


@pytest.mark.parametrize("path", MANIFESTS, ids=lambda path: path.name)
def test_the_manifest_version_matches_the_pin(path: Path) -> None:
    # A dependency bot bumps the pin on its own and cannot run the re-sync, so between that merge and
    # someone remembering, the tree claims one version and ships another's files.
    version = str(recorded(path)["version"])
    assert version == pinned_version(), (
        f"{path.name} records Spec Kit {version} but mise.toml pins {PIN} = {pinned_version()}; {RESYNC}"
    )


@pytest.mark.parametrize("path", MANIFESTS, ids=lambda path: path.name)
def test_every_vendored_file_matches_its_recorded_hash(path: Path) -> None:
    # The upgrade skips a shared path that already exists and only warns, whether or not the new version
    # changed it — a warning nobody can act on by reading. These hashes can: a skip that mattered leaves
    # a mismatch here.
    files = cast(dict[str, str], recorded(path)["files"])
    assert files, f"{path.name} records no files, so this gate compares nothing"
    wrong: list[str] = []
    for relative, expected in files.items():
        vendored = REPO / relative
        if not vendored.exists():
            wrong.append(f"{relative}: missing")
        elif hashlib.sha256(vendored.read_bytes()).hexdigest() != expected:
            wrong.append(f"{relative}: edited in place, or left at an older version")
    assert wrong == [], (
        f"{path.name} records {len(files)} vendored files and {len(wrong)} do not match: {wrong}. These "
        f"are upgraded wholesale, never edited by hand — {RESYNC}"
    )
