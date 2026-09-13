import re
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# GitHub redirects a renamed repository's URLs, so a stale one keeps working and nothing announces the
# drift — hence a gate rather than a note. The remote is the only offline authority on what this
# repository is called; CI's checkout sets it to the same thing.
URL_OWNER_REPO = re.compile(r"https://github\.com/(turboBasic/[A-Za-z0-9._-]+)")

# No file is exempt: every self URL in the tree names the repository this clone is.
EXEMPT: dict[str, str] = {}

# Another repository of this owner's, named on purpose. The matcher cannot tell a stale self URL from a
# deliberate reference to a different repository, so each deliberate one is named here with why —
# exempting the file instead would stop checking that file's own self URLs, which is what the gate is for.
OTHER_REPOSITORIES: dict[str, str] = {
    "turboBasic/github-actions-test": (
        "the verification harness; a capability's caller-side behaviour is exercised from there, and it "
        "is deliberately not this repository"
    ),
}


# A `uses:` slug is a resolvable reference just like a URL, and GitHub redirects a renamed
# repository's refs too — so a stale one keeps working and nothing announces the drift. The README is
# not exempt here: its call sites have to resolve, unlike the prose that deliberately names both
# repositories.
USES_SLUG = re.compile(r"uses:\s*(turboBasic/[A-Za-z0-9._-]+)")

OWN_PATH = "tests/test_repo_urls.py"


def current_slug() -> str:
    url = subprocess.run(
        ["git", "-C", str(REPO), "remote", "get-url", "origin"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    return url.removesuffix(".git").split("github.com/", 1)[1]


def tracked_files() -> list[str]:
    out = subprocess.run(
        ["git", "-C", str(REPO), "ls-files", "-z"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return [p for p in out.split("\0") if p]


def test_every_self_url_names_the_repository_this_clone_actually_is() -> None:
    slug = current_slug()
    stale: list[str] = []
    for path in tracked_files():
        # This module owns the matcher, so it carries deliberate counter-examples that are meant not to
        # be this repository — the same reason the slug gate below skips itself.
        if path in EXEMPT or path == OWN_PATH:
            continue
        if path.startswith((".specify/", ".claude/skills/speckit-")):
            continue
        text = (REPO / path).read_text(encoding="utf-8", errors="ignore")
        stale += [
            f"{path}: {m}"
            for m in URL_OWNER_REPO.findall(text)
            if m != slug and m not in OTHER_REPOSITORIES
        ]
    assert stale == [], (
        f"URL names a repository other than {slug}: {stale}. Repoint it, or name the repository in "
        "OTHER_REPOSITORIES with why it is deliberately not this one"
    )


def test_every_exemption_carries_a_reason() -> None:
    assert all(reason.strip() for reason in EXEMPT.values())
    assert all(reason.strip() for reason in OTHER_REPOSITORIES.values())


def test_every_self_reference_by_slug_names_the_repository_this_clone_is() -> None:
    slug = current_slug()
    stale: list[str] = []
    for path in tracked_files():
        # This module owns the matcher, so it carries deliberate counter-examples that are meant not to
        # be this repository — scanning itself would report its own pre-flight as drift.
        if path.startswith((".specify/", ".claude/skills/speckit-")) or path == OWN_PATH:
            continue
        text = (REPO / path).read_text(encoding="utf-8", errors="ignore")
        stale += [f"{path}: {found}" for found in USES_SLUG.findall(text) if found != slug]
    assert stale == [], (
        f"`uses:` names a repository other than {slug}: {stale}. A rename leaves the old slug "
        "resolving through GitHub's redirect, so nothing else would report this"
    )


def test_the_url_reader_finds_a_self_url_it_is_given() -> None:
    # Pre-flight the matcher, or a change that stops it matching reports green over stale URLs. Its
    # sibling below has carried this since it was written; this one had not.
    assert URL_OWNER_REPO.findall("see https://github.com/turboBasic/some-other-repo/issues/1") == [
        "turboBasic/some-other-repo"
    ]
    assert URL_OWNER_REPO.findall("https://github.com/someone-else/github-actions") == []
    assert URL_OWNER_REPO.findall("https://example.com/turboBasic/github-actions") == []


def test_the_slug_reader_finds_a_reference_it_is_given() -> None:
    # Pre-flight the matcher, or a change that stops it matching reports green over stale slugs.
    assert USES_SLUG.findall("uses: turboBasic/github-actions/x.yml@v1") == [
        "turboBasic/github-actions"
    ]
    assert USES_SLUG.findall("    uses:  turboBasic/other-repo\n") == ["turboBasic/other-repo"]
    assert USES_SLUG.findall("uses: ./.github/workflows/x.yml") == []
