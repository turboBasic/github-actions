import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
FIRST_PARTY = "turboBasic/"
SELF_WORKFLOW = "turboBasic/github-actions/.github/workflows/"
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
            f"moving major tag, not a SHA — see README."
        )


def test_ai_instructions_names_no_concrete_major() -> None:
    # CLAUDE.md is one line pointing at this file, so a literal `@v2` here is what an agent writes
    # into a consumer — and it keeps resolving after that major is frozen. README's Versioning
    # section is the only place a major is written; this file states the form, `@vN`.
    doc = REPO_ROOT / "docs" / "ai-instructions.md"
    stale = [
        f"{number}: {line.strip()}"
        for number, line in enumerate(doc.read_text().splitlines(), start=1)
        if re.search(r"@v\d", line)
    ]
    assert not stale, (
        f"{doc.name} names a concrete major, which goes stale at the next bump: {stale}. "
        f"Write `@vN` and cite README's Versioning section for the value."
    )


def test_a_self_call_resolves_at_the_commit_under_review() -> None:
    # Every other gate accepts both forms — test_first_party_actions_use_the_major_tag accepts the
    # tagged one by design, since precommit-advisory.yml references a composite action that way —
    # so nothing else here would notice a self-call rewritten to resolve at the tag instead.
    for path in sorted((REPO_ROOT / ".github" / "workflows").glob("*.yml")):
        for number, ref in _uses_lines(path):
            target = ref.split("#")[0].strip()
            assert not target.startswith(SELF_WORKFLOW), (
                f"{path.name}:{number} calls this repo's own workflow at a tag ({target}), so a "
                f"change to it would be validated by the previous release of itself. Use "
                f"`./.github/workflows/<name>.yml`, which resolves at the caller's own commit."
            )
    caller = REPO_ROOT / ".github" / "workflows" / "commit-messages.yml"
    assert "uses: ./.github/workflows/conventional-commits.yml" in caller.read_text(), (
        f"{caller.name} must keep calling conventional-commits.yml relatively; that call is what "
        f"exercises it before it is tagged."
    )


def test_the_required_check_names_are_intact() -> None:
    # `commits / PR title` and `commits / Commit messages` are required contexts on the `main`
    # ruleset, composed from the caller's job id and the called workflow's job names. Rename
    # any of the three and both stop reporting, blocking every pull request until the ruleset
    # is edited by hand — and nothing in the tree would look wrong.
    caller = REPO_ROOT / ".github" / "workflows" / "commit-messages.yml"
    called = REPO_ROOT / ".github" / "workflows" / "conventional-commits.yml"
    assert "\n  commits:\n" in caller.read_text(), (
        f"{caller.name}'s calling job must keep the id `commits`; it is the prefix of both "
        f"required checks."
    )
    called_text = called.read_text()
    for job_name in ("PR title", "Commit messages"):
        assert f"name: {job_name}\n" in called_text, (
            f"{called.name} must keep `name: {job_name}`; it is the second half of the "
            f"required check `commits / {job_name}`."
        )


def test_every_reusable_workflow_declares_workflow_call() -> None:
    reusable = [
        p
        for p in (REPO_ROOT / ".github" / "workflows").glob("*.yml")
        if p.name not in {"ci.yml", "commit-messages.yml"}
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
    # Found by dedent, not by matching what an entry ought to look like: the old
    # `[ ]+[\w-]+` pattern ended the block at the first malformed line and hid everything
    # after it, so an appended `foo|bar` widened the accepted types unseen by this test.
    lines = path.read_text().splitlines()
    start = next((i for i, line in enumerate(lines) if line.strip() == f"{key}: |"), None)
    assert start is not None, f"could not find a `{key}: |` block in {path.name}"
    indent = len(lines[start]) - len(lines[start].lstrip())
    entries: list[str] = []
    for line in lines[start + 1 :]:
        if not line.strip():
            continue
        if len(line) - len(line.lstrip()) <= indent:
            break
        entries.extend(line.split())
    malformed = [e for e in entries if not re.fullmatch(r"[\w-]+", e)]
    assert not malformed, (
        f"{path.name} `{key}` has entries that are not bare words: {malformed}. The workflow "
        f"joins them with `|` into a regex alternation, so one containing `|` silently widens "
        f"what it accepts past commitizen's set."
    )
    return set(entries)


def test_allowed_types_match_the_commitizen_builtin_set() -> None:
    # commitizen has the final say on commit messages, through the commit-msg hook and
    # `cz check`. A type it accepts that this list rejects is a gate disagreeing with the
    # tool it mirrors, and `bump` is the one that differs from the action's own default —
    # which is why the list may not be left to a default. There is one declaration now:
    # the title and commit checks both read it from this input.
    workflow, key = "conventional-commits.yml", "default"
    declared = _block_of_words(REPO_ROOT / ".github" / "workflows" / workflow, key)
    builtin = _commitizen_types()
    assert declared == builtin, (
        f"{workflow} `{key}` disagrees with commitizen's built-in set: "
        f"missing {sorted(builtin - declared)}, extra {sorted(declared - builtin)}"
    )


def test_python_ci_requests_no_pull_request_permission() -> None:
    # A called workflow's job permissions are validated when the run starts, before any
    # `if:` can skip the job, so a `pull-requests: write` anywhere here would force every
    # caller to grant it. A job needing write belongs in precommit-advisory.yml, which
    # only its own callers invoke.
    workflow = REPO_ROOT / ".github" / "workflows" / "python-ci.yml"
    assert "pull-requests" not in workflow.read_text(), (
        "python-ci.yml requests a pull-requests permission; every caller would then be "
        "forced to grant it, failing at startup otherwise. Put the job that needs it in "
        "precommit-advisory.yml instead."
    )
