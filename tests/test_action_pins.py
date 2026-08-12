import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
FIRST_PARTY = "turboBasic/"
SHA = re.compile(r"^[0-9a-f]{40}$")
TAG_COMMENT = re.compile(r"#\s*v?\d")


def _yaml_files() -> list[Path]:
    return sorted(
        [
            *(REPO_ROOT / ".github" / "workflows").glob("*.yml"),
            *REPO_ROOT.glob("actions/*/action.yml"),
        ]
    )


def _uses_lines(path: Path) -> list[tuple[int, str]]:
    lines: list[tuple[int, str]] = []
    for number, raw in enumerate(path.read_text().splitlines(), start=1):
        stripped = raw.strip().removeprefix("- ").strip()
        if stripped.startswith("uses:"):
            lines.append((number, stripped.removeprefix("uses:").strip()))
    return lines


@pytest.mark.parametrize("path", _yaml_files(), ids=lambda p: str(p.relative_to(REPO_ROOT)))
def test_third_party_actions_are_pinned_to_a_full_sha(path: Path) -> None:
    for number, ref in _uses_lines(path):
        target = ref.split("#")[0].strip()
        if target.startswith((FIRST_PARTY, "./")):
            continue
        assert "@" in target, f"{path.name}:{number} has no ref: {target}"
        _, _, version = target.partition("@")
        assert SHA.match(version), (
            f"{path.name}:{number} pins a floating ref ({version}); a tag can be "
            f"retroactively repointed (CVE-2025-30066). Use the full commit SHA."
        )
        assert TAG_COMMENT.search(ref), (
            f"{path.name}:{number} pins a SHA with no `# vX.Y.Z` comment, leaving "
            f"the human-readable version unknowable and Renovate unable to track it."
        )


@pytest.mark.parametrize("path", _yaml_files(), ids=lambda p: str(p.relative_to(REPO_ROOT)))
def test_first_party_actions_use_the_major_tag(path: Path) -> None:
    for number, ref in _uses_lines(path):
        target = ref.split("#")[0].strip()
        if not target.startswith(FIRST_PARTY):
            continue
        _, _, version = target.partition("@")
        assert re.match(r"^v\d+$", version), (
            f"{path.name}:{number} references first-party {target}; these track the "
            f"moving major tag (@v1), not a SHA — see README."
        )


def test_every_reusable_workflow_declares_workflow_call() -> None:
    reusable = [
        p
        for p in (REPO_ROOT / ".github" / "workflows").glob("*.yml")
        if p.name not in {"ci.yml", "semantic-pull-request.yml"}
    ]
    assert reusable, "no reusable workflows found"
    for path in reusable:
        assert "workflow_call:" in path.read_text(), f"{path.name} is not callable"


def test_default_types_match_the_commitizen_builtin_set() -> None:
    # A consumer's commit-msg hook runs commitizen's built-in schema, so any type the
    # hook accepts and this default rejects is a local-vs-CI disagreement — the exact
    # thing the workflow claims to make impossible. `bump` was missing here, and
    # `cz bump` emits "bump: version X → Y", so releases failed CI.
    from commitizen.config.base_config import BaseConfig
    from commitizen.cz.conventional_commits.conventional_commits import (
        ConventionalCommitsCz,
    )

    pattern = ConventionalCommitsCz(BaseConfig()).schema_pattern()
    group = re.search(r"\(([a-z|]{10,})\)", pattern)
    assert group, f"could not find the type alternation in {pattern!r}"
    builtin = set(group.group(1).split("|"))

    workflow = (REPO_ROOT / ".github" / "workflows" / "conventional-commits.yml").read_text()
    block = re.search(r"default: \|\n((?:\s{10}\w+\n)+)", workflow)
    assert block, "could not find the types default block"
    declared = set(block.group(1).split())

    assert declared == builtin, (
        f"conventional-commits.yml types default disagrees with commitizen's built-in "
        f"set: missing {sorted(builtin - declared)}, extra {sorted(declared - builtin)}"
    )
