import json
import os
import re
import subprocess
import tomllib
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).parent.parent
FIRST_PARTY = "turboBasic/"
SELF_WORKFLOW = "turboBasic/github-actions/.github/workflows/"
# `$/` is GitHub's self-repository form and `./` its older workspace-relative spelling; neither
# carries a ref, because both resolve at the caller's own commit.
SELF_PREFIXES = ("$/", "./")
SHA = re.compile(r"^[0-9a-f]{40}$")
TAG_COMMENT = re.compile(r"#\s*v?\d")

# GitHub composes a called job's check name as `<caller job id> / <called job name>`, so both halves
# live in different files from the ruleset that requires them. Renaming either silently retires the
# context and blocks every pull request. This table is the single statement of that contract: the
# tree is checked against it offline, the live ruleset against it in CI.
REQUIRED_CHECKS = [
    ("ci / CI", "ci.yml", "python-ci.yml"),
    ("commits / PR title", "commit-messages.yml", "conventional-commits.yml"),
    ("commits / Commit messages", "commit-messages.yml", "conventional-commits.yml"),
]
REPO_URL = "https://api.github.com/repos/turboBasic/github-actions"
# This repo's own plumbing: nothing outside resolves these, so they are neither callable nor a
# reason to cut a release.
OWN_CI = {"ci.yml", "commit-messages.yml", "release.yml", "release-proposal.yml"}
# What a consumer resolves. `.github/workflows/` minus OWN_CI, plus every composite action.
CONSUMER_FACING = (".github/workflows/", "actions/")
# Applied rules for a branch, unlike the rulesets API, need no `administration` scope — it answers
# unauthenticated on a public repo, so the default GITHUB_TOKEN is enough.
BRANCH_RULES_URL = f"{REPO_URL}/rules/branches/main"
WENT_PRIVATE = (
    "this repository is no longer public, so every consumer's call to these workflows stops "
    'resolving until Settings → Actions → General → Access is set to "Accessible from '
    "repositories owned by 'turboBasic'\". Set that policy, then delete this test — it cannot "
    "assert the policy itself, which is why it asserts the visibility that makes it unnecessary."
)


def _api_json(url: str) -> Any:
    request = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json"})
    # Only to lift the 60/hour unauthenticated rate limit, which shared runner IPs do reach.
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def _live_required_contexts() -> set[str]:
    rules: list[dict[str, Any]] = _api_json(BRANCH_RULES_URL)
    return {
        str(check["context"])
        for rule in rules
        if rule.get("type") == "required_status_checks"
        for check in rule["parameters"]["required_status_checks"]
    }


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
        if target.startswith((FIRST_PARTY, *SELF_PREFIXES)):
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


def _mise_tool_versions() -> dict[str, str]:
    manifest: dict[str, Any] = tomllib.loads((REPO_ROOT / "mise.toml").read_text())
    tools: dict[str, Any] = manifest["tools"]
    return {name: str(spec) for name, spec in tools.items()}


def test_no_mise_tool_version_floats() -> None:
    # A `latest` resolves at install time, so one commit runs different linters on different
    # machines: zizmor 1.30.0 shipped a new audit and reddened a pull request that had passed
    # `mise run ci` locally minutes earlier. The digit rule admits a partial pin like `3.14` and
    # rejects every form that leaves the choice to whoever runs `mise install`.
    floating = sorted(
        f"{name} = {version!r}"
        for name, version in _mise_tool_versions().items()
        if not version[:1].isdigit()
    )
    assert not floating, (
        f"mise.toml leaves {floating} for install time to decide, so two machines on this commit "
        f"can lint it with different tools. Name the version — Renovate's mise manager bumps it."
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
                f"`$/.github/workflows/<name>.yml`, which resolves at the caller's own commit."
            )
    for caller_name, called in sorted({(c, d) for _, c, d in REQUIRED_CHECKS}):
        caller = REPO_ROOT / ".github" / "workflows" / caller_name
        assert f"uses: $/.github/workflows/{called}" in caller.read_text(), (
            f"{caller_name} must keep calling {called} at this same commit; that call is what "
            f"exercises it before it is tagged."
        )


def test_the_actionlint_ignore_is_still_needed(tmp_path: Path) -> None:
    # Asserts an upstream bug persists, so the workaround cannot outlive it: `.github/actionlint.yaml`
    # exists only because actionlint rejects `$/`, and nothing else would ever say that stopped being
    # true. Run against a config without the ignore — when this fails, rhysd/actionlint#711 has
    # shipped and the file should be deleted along with this test.
    empty = tmp_path / "actionlint.yaml"
    empty.write_text("paths: {}\n")
    result = subprocess.run(
        ["actionlint", "-config-file", str(empty), ".github/workflows/ci.yml"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=False,
    )
    assert "is not following the format" in result.stdout, (
        "actionlint no longer rejects the `$/` self-repository syntax, so the ignore in "
        ".github/actionlint.yaml is dead weight. Delete that file and this test."
    )


@pytest.mark.parametrize(("context", "caller_name", "called_name"), REQUIRED_CHECKS)
def test_the_required_check_names_are_intact(
    context: str, caller_name: str, called_name: str
) -> None:
    job_id, _, job_name = context.partition(" / ")
    caller = REPO_ROOT / ".github" / "workflows" / caller_name
    called = REPO_ROOT / ".github" / "workflows" / called_name
    assert f"\n  {job_id}:\n" in caller.read_text(), (
        f"{caller_name}'s calling job must keep the id `{job_id}`; it is the first half of the "
        f"required check `{context}`."
    )
    assert f"name: {job_name}\n" in called.read_text(), (
        f"{called_name} must keep `name: {job_name}`; it is the second half of the required "
        f"check `{context}`."
    )


def test_the_release_gates_on_a_required_context() -> None:
    # release.yml refuses to tag unless one named check passed on the commit being released. That
    # name is composed from a job id in one file and a job name in another, so a rename would turn
    # the gate into a permanent `missing` — it fails closed, but a release that refuses with no
    # visible cause is its own outage. REQUIRED_CHECKS stays the single statement of the name.
    workflow = (REPO_ROOT / ".github" / "workflows" / "release.yml").read_text()
    gated = [context for context, _, _ in REQUIRED_CHECKS if f'"{context}"' in workflow]
    assert gated, (
        "release.yml gates on no context from REQUIRED_CHECKS, so it either tags unverified "
        "code or waits on a check name nothing reports."
    )


def test_the_release_workflow_gives_gh_a_repository() -> None:
    # Nothing is cloned there, so a `gh` subcommand other than `gh api` — which carries the full
    # path — has no remote to infer the repository from and dies with `not a git repository`. That
    # is how the first dispatch failed, after the version tag had already been created. Every other
    # gate passed on that file: the shell is valid, the call is well-formed, and the flag it needs
    # is only discoverable by running it somewhere without a checkout.
    workflow = (REPO_ROOT / ".github" / "workflows" / "release.yml").read_text()
    without_repo = [
        line
        for raw in workflow.splitlines()
        if not (line := raw.strip()).startswith("#")
        if re.search(r"(?<!\S)gh (?!api\b)[a-z]", line) and "--repo" not in line
    ]
    assert not without_repo or "GH_REPO:" in workflow, (
        f"release.yml runs {without_repo} with no repository context. Set GH_REPO in the job env, "
        f"or pass --repo on the line."
    )


def test_the_release_waits_for_the_ci_verdict() -> None:
    # The release is a job in ci.yml behind `needs: [ci]`, and that dependency *is* FR-011: it is
    # what makes "CI passed on the commit being released" structurally true instead of something
    # queried. Drop it and the release runs in parallel with the tests it is supposed to be gated on,
    # tagging code nothing has verified — with every linter green, because a job without `needs` is
    # perfectly valid YAML.
    #
    # `needs: [ci, live]` is equally wrong in the other direction: `live` is red precisely when a
    # release is owed, so the release could only ever be cut when none was needed.
    ci = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text()
    release_job = re.search(r"(?ms)^  release:\n(.*?)(?=^  \w|\Z)", ci)
    assert release_job, (
        "ci.yml has no `release` job; that job is what cuts a release after a merge."
    )
    body = release_job.group(1)
    assert re.search(r"needs:\s*\[\s*ci\s*\]", body), (
        "ci.yml's release job does not declare `needs: [ci]`, so it no longer waits for the verdict "
        "that covers the commit it would tag (FR-011)."
    )
    assert "live" not in body, (
        "ci.yml's release job depends on `live`, which is red exactly when a release is owed — so a "
        "release could only be cut when none was needed."
    )
    assert "uses: $/.github/workflows/release.yml" in body, (
        "ci.yml's release job must call release.yml at this same commit with the `$/` form, so a "
        "change to it is validated by the version under review rather than by the last tag."
    )


def test_the_release_is_not_triggered_by_workflow_run() -> None:
    # `workflow_run` is the obvious trigger for "start when CI finishes" and is a high-severity
    # zizmor finding. It also cannot express what is wanted: its `conclusion` is the *workflow's*,
    # which includes ci.yml's `live` job — red precisely when a release is owed — so gating on it
    # would refuse every release the moment one was actually due.
    # Comments stripped: the header explains at length why this trigger is not used.
    workflow = "\n".join(
        line
        for raw in (REPO_ROOT / ".github" / "workflows" / "release.yml").read_text().splitlines()
        if not (line := raw.strip()).startswith("#")
    )
    assert "workflow_run" not in workflow.split("jobs:")[0], (
        "release.yml is triggered by workflow_run again. Its conclusion covers ci.yml's `live` job "
        "as well, so it is red exactly when a release is due; ci.yml calls this workflow behind "
        "`needs: [ci]` instead."
    )


def test_the_release_refuses_notes_with_no_content() -> None:
    # Neither the exit code nor the file's size can answer this. git-cliff exits 0 for a range
    # holding only a `bump` and for a range holding nothing, indistinguishably; and an empty render
    # is *one* byte, not zero, because a trailing newline is still emitted. Measured on a probe
    # branch whose entire range was one `bump`, after this gate had been written as `-s` on the
    # assumption of zero bytes — that version passed on the newline and would have published a
    # release body containing a blank line, with every other gate green.
    workflow = (REPO_ROOT / ".github" / "workflows" / "release.yml").read_text()
    assert "[^[:space:]]" in workflow, (
        "release.yml does not test the rendered notes for non-whitespace content, so a range that "
        "renders nothing would publish a blank release body (FR-007). A `-s` test is not enough: an "
        "empty render is a lone newline, which `-s` accepts."
    )


def test_the_release_publishes_the_rendered_notes() -> None:
    # `--generate-notes` asks GitHub to build the body from pull request labels, which is the
    # failure this whole feature exists to remove: nine merged PRs carry no label at all, and the
    # only breaking change ever shipped here was published under "Other changes". Reinstating it
    # would quietly route the notes back through labels with `.cliff.toml` still sitting there.
    # Comments stripped first: the line explaining why `--generate-notes` is gone contains it.
    workflow = "\n".join(
        line
        for raw in (REPO_ROOT / ".github" / "workflows" / "release.yml").read_text().splitlines()
        if not (line := raw.strip()).startswith("#")
    )
    assert "--notes-file" in workflow, (
        "release.yml does not publish the rendered notes with `--notes-file`, so whatever "
        ".cliff.toml produced is not what reaches the release body."
    )
    assert "--generate-notes" not in workflow, (
        "release.yml publishes with `--generate-notes`, which categorises by pull request label "
        "and ignores .cliff.toml entirely (FR-001)."
    )


def _declared_version() -> str:
    manifest: dict[str, Any] = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text())
    project: dict[str, Any] = manifest["project"]
    return str(project["version"])


@pytest.mark.live
def test_the_ruleset_requires_exactly_the_checks_that_exist() -> None:
    # The other direction, and the only assertion here that leaves the tree: REQUIRED_CHECKS is
    # what the workflows compose, so if the ruleset has drifted from it — a context renamed in the
    # UI, one added for a job that never ships — every pull request blocks on something that can
    # never report. Nothing in a file would look wrong, which is why this reads the live API.
    live = _live_required_contexts()
    expected = {context for context, _, _ in REQUIRED_CHECKS}
    assert live == expected, (
        f"the `main` ruleset requires {sorted(live)}, but the workflows compose "
        f"{sorted(expected)}. A required context that no job reports blocks every pull request; "
        f"reconcile the ruleset with REQUIRED_CHECKS."
    )


@pytest.mark.live
def test_this_repository_is_still_public() -> None:
    # Private `opus-magnum` can call these workflows only because this repository is public. The
    # setting that would replace that cannot be asserted — `actions/permissions/access` answers 422
    # while a repo is public — so this guards the precondition instead, and its message carries the
    # instruction nobody will remember at the moment of flipping the switch.
    try:
        repo: dict[str, Any] = _api_json(REPO_URL)
    except urllib.error.HTTPError as error:
        # Unauthenticated, a private repo is indistinguishable from a deleted one; either way the
        # consumers' precondition is gone.
        if error.code != 404:
            raise
        pytest.fail(WENT_PRIVATE)
    assert repo["private"] is False, WENT_PRIVATE


@pytest.mark.live
def test_no_consumer_facing_change_is_waiting_for_a_release() -> None:
    # The major tag is force-moved by hand-initiated dispatch, so nothing stops it sitting behind
    # main: it once did for 19 days and 29 commits, stranding four changes consumers resolve. No
    # file can show that — the state is a ref on GitHub — which is why this is live.
    #
    # Scoped to what a consumer resolves rather than to `main` being ahead at all. A docs or test
    # commit owes nobody a release, and a check that reddens after every merge is one nobody reads.
    major = f"v{_declared_version().split('.')[0]}"
    try:
        comparison: dict[str, Any] = _api_json(f"{REPO_URL}/compare/{major}...main")
    except urllib.error.HTTPError as error:
        if error.code != 404:
            raise
        # The state between a major bump merging and its first release: [project].version names a
        # major nothing has tagged, so there is no ref to compare against and a release is owed.
        pytest.fail(
            f"[project].version names major {major}, which has never been tagged. Run the Release "
            f"workflow to cut it."
        )

    files: list[dict[str, Any]] = comparison.get("files", [])
    stranded = sorted(
        {
            name
            for file in files
            if (name := str(file["filename"])).startswith(CONSUMER_FACING)
            and Path(name).name not in OWN_CI
        }
    )
    assert not stranded, (
        f"{major} predates changes to {stranded}, so every consumer pinned to @{major} still runs "
        f"the previous version of them. Bump [project].version in a pull request — that decides "
        f"the next version — then run the Release workflow."
    )


def test_every_reusable_workflow_declares_workflow_call() -> None:
    reusable = [
        p for p in (REPO_ROOT / ".github" / "workflows").glob("*.yml") if p.name not in OWN_CI
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


def block_of_words(path: Path, key: str) -> set[str]:
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
    declared = block_of_words(REPO_ROOT / ".github" / "workflows" / workflow, key)
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
