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


def _commitizen_types() -> set[str]:
    from commitizen.config.base_config import BaseConfig
    from commitizen.cz.conventional_commits.conventional_commits import (
        ConventionalCommitsCz,
    )

    pattern = ConventionalCommitsCz(BaseConfig()).schema_pattern()
    group = re.search(r"\(([a-z|]{10,})\)", pattern)
    assert group, f"could not find the type alternation in {pattern!r}"
    return set(group.group(1).split("|"))


def _block_of_words(path: Path, key: str) -> set[str]:
    block = re.search(rf"{key}: \|\n((?:[ ]+[\w-]+\n)+)", path.read_text())
    assert block, f"could not find a `{key}: |` block in {path.name}"
    return set(block.group(1).split())


@pytest.mark.parametrize(
    ("workflow", "key"),
    [("conventional-commits.yml", "default"), ("semantic-pull-request.yml", "types")],
)
def test_allowed_types_match_the_commitizen_builtin_set(workflow: str, key: str) -> None:
    # Commit messages are checked by commitizen — the `commit-msg` hook locally, and
    # `cz check` in ci.yml — so any type commitizen accepts and one of these lists
    # rejects is a gate disagreeing with the tool it claims to mirror.
    #
    # It has happened twice. conventional-commits.yml omitted `bump`, so a `cz bump`
    # release commit passed the hook and failed CI. semantic-pull-request.yml passed no
    # types at all and inherited the action's own default, which comes from
    # conventional-commit-types and also has no `bump` — and squash is the only merge
    # method here, so the title becomes the commit.
    declared = _block_of_words(REPO_ROOT / ".github" / "workflows" / workflow, key)
    builtin = _commitizen_types()
    assert declared == builtin, (
        f"{workflow} `{key}` disagrees with commitizen's built-in set: "
        f"missing {sorted(builtin - declared)}, extra {sorted(declared - builtin)}"
    )


def test_python_ci_requests_no_pull_request_permission() -> None:
    # A called workflow's job permissions are validated when the run starts, before any
    # `if:` can skip the job. So a `pull-requests: write` anywhere in python-ci.yml
    # forces every caller to grant it — and a caller that does not gets a bare
    # startup_failure with no job, no log and no diagnostic. That is why the advisory
    # job lives in precommit-advisory.yml, which only its own callers invoke.
    workflow = REPO_ROOT / ".github" / "workflows" / "python-ci.yml"
    assert "pull-requests" not in workflow.read_text(), (
        "python-ci.yml requests a pull-requests permission; every caller would then be "
        "forced to grant it, failing at startup otherwise. Put the job that needs it in "
        "precommit-advisory.yml instead."
    )
