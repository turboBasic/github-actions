import json
import os
import urllib.error
import urllib.request
from typing import cast

import pytest
from decisions import moving_ref, parse_version

# Needs network and a live GitHub API token — the one module this repository's own offline suite must
# never require. Deselected by default (pyproject.toml's addopts) and run explicitly by
# .github/workflows/live-state.yml, the only place GH_REPO and GH_TOKEN are both set.
pytestmark = pytest.mark.live

API = "https://api.github.com"


def _get(path: str) -> dict[str, object]:
    request = urllib.request.Request(
        f"{API}/repos/{os.environ['GH_REPO']}{path}",
        headers={
            "Authorization": f"Bearer {os.environ['GH_TOKEN']}",
            "Accept": "application/vnd.github+json",
        },
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        return cast(dict[str, object], json.load(response))


def test_the_repository_is_still_public() -> None:
    repo = _get("")
    assert repo["private"] is False, (
        f"{os.environ['GH_REPO']} now reads as private. docs/ai-instructions.md: this repository "
        "stays public, or every consumer needs an access policy. Make it public again in Settings > "
        "General > Danger Zone > Change repository visibility."
    )


def test_the_compatibility_ref_carries_the_latest_release() -> None:
    # A repository with no release yet has nothing this check can compare, and that is a different
    # condition from the ref falling behind — so it is skipped rather than failed.
    try:
        release = _get("/releases/latest")
    except urllib.error.HTTPError as error:
        if error.code == 404:
            pytest.skip("no release has been published yet")
        raise
    tag = str(release["tag_name"])
    version = parse_version(tag.removeprefix("v"))
    assert version is not None, f"the latest release tag {tag!r} does not parse as a version"
    ref = moving_ref(version)
    ahead = cast(int, _get(f"/compare/{ref}...{tag}")["ahead_by"])
    assert ahead == 0, (
        f"{ref} is {ahead} commit(s) behind {tag}, the latest published release. release.yml moves "
        f"{ref} last; re-run it for this commit, or move refs/tags/{ref} to {tag} by hand."
    )
