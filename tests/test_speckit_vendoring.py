import hashlib
import json
import tomllib
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).parent.parent
MANIFESTS = sorted((REPO_ROOT / ".specify" / "integrations").glob("*.manifest.json"))
RESYNC = (
    "run `mise run spec-kit-upgrade` and commit what it rewrites. Never `specify self upgrade` — "
    "it replaces the binary outside mise."
)


def _pinned_specify_version() -> str:
    manifest: dict[str, Any] = tomllib.loads((REPO_ROOT / "mise.toml").read_text())
    return str(manifest["tools"]["pipx:specify-cli"])


@pytest.mark.parametrize("path", MANIFESTS, ids=lambda p: p.name)
def test_the_manifest_version_matches_the_pin(path: Path) -> None:
    # The window this closes is narrow and real: Renovate bumps the pin on its own, since it cannot
    # run the re-sync, so between that merge and the task the tree claims one version and ships
    # another's files.
    manifest: dict[str, Any] = json.loads(path.read_text())
    assert manifest["version"] == _pinned_specify_version(), (
        f"{path.name} records Spec Kit {manifest['version']} but mise.toml pins "
        f"{_pinned_specify_version()}; {RESYNC}"
    )


@pytest.mark.parametrize("path", MANIFESTS, ids=lambda p: p.name)
def test_every_vendored_file_matches_its_recorded_hash(path: Path) -> None:
    # `specify integration upgrade` skips a shared path that already exists and says so, whether or
    # not the new version changed it — a warning nobody can act on by reading. These hashes can:
    # a skip that mattered leaves a mismatch here.
    manifest: dict[str, Any] = json.loads(path.read_text())
    files: dict[str, str] = manifest["files"]
    assert files, f"{path.name} records no files"
    wrong: list[str] = []
    for relative, expected in files.items():
        vendored = REPO_ROOT / relative
        if not vendored.exists():
            wrong.append(f"{relative}: missing")
        elif hashlib.sha256(vendored.read_bytes()).hexdigest() != expected:
            wrong.append(f"{relative}: edited or left at an older version")
    assert not wrong, (
        f"{path.name} describes {len(files)} vendored files and {len(wrong)} do not match: "
        f"{wrong}. These are upgraded wholesale, never edited in place — {RESYNC}"
    )
