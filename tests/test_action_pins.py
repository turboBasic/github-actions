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
SELF_REPO = "turboBasic/github-actions/"
SELF_WORKFLOW = f"{SELF_REPO}.github/workflows/"
# `$/` is GitHub's self-repository form and `./` its older workspace-relative spelling; neither
# carries a ref, because both resolve at the caller's own commit.
SELF_PREFIXES = ("$/", "./")
SHA = re.compile(r"^[0-9a-f]{40}$")
# Column zero, so it cannot match a job's or a step's name.
WORKFLOW_NAME = re.compile(r"^name: (.+)$", re.MULTILINE)
TAG_COMMENT = re.compile(r"#\s*v?\d")

# GitHub composes a called job's check name as `<caller job id> / <called job name>`, so both halves
# live in different files from the ruleset that requires them. Renaming either silently retires the
# context and blocks every pull request. This table is the single statement of that contract: the
# tree is checked against it offline, the live ruleset against it in CI.
REQUIRED_CHECKS = [
    ("ci / python-ci", "ci.yml", "python-ci.yml"),
    ("commits / pr-title", "commit-messages.yml", "conventional-commits.yml"),
    ("commits / commit-messages", "commit-messages.yml", "conventional-commits.yml"),
]
REPO_URL = "https://api.github.com/repos/turboBasic/github-actions"
LABEL_WRITERS = (
    Path(".github/ISSUE_TEMPLATE/1-bug-report.yml"),
    Path(".github/ISSUE_TEMPLATE/2-idea.yml"),
    Path(".github/renovate.json"),
)
LABEL_TABLE_ROWS = 3
# Every prose document except README, which is the authority for which major is current. `specs/` is
# out because a completed feature directory is never edited again, and `.specify/templates/` and
# `.claude/skills/` are vendored. Globs are non-recursive, so a new documentation subdirectory needs a
# line here.
PROSE_DOCS = sorted(
    path.relative_to(REPO_ROOT)
    for directory in (
        REPO_ROOT,
        REPO_ROOT / "docs",
        REPO_ROOT / ".github",
        REPO_ROOT / ".specify" / "memory",
    )
    for path in directory.glob("*.md")
    if path.name != "README.md"
)
# This repo's own plumbing. A change to how one *behaves* alters nothing a consumer's own build
# does, so it is neither a reason to cut a release nor a version increment — the version describes
# the consumer-facing surface, not this repository's history. Input contracts are a separate
# question: `release.yml` declares `workflow_call` with a `dry-run` input that a real caller pins,
# so breaking that input is a major like any other. Membership excuses behaviour, not contracts.
#
# The criterion is not whether anything outside can reach them. `github-actions-test` calls
# `release.yml` at a tag, as standing coverage of this repository's release path rather than
# because it needs a release cut, so its copy lags a change here until the next release —
# acceptable, because every real release exercises the same path. Moving `release.yml` onto the
# consumer surface instead would make every release-plumbing fix a version bump describing
# something no consumer resolves.
OWN_CI = {
    "ci.yml",
    "commit-messages.yml",
    "drift.yml",
    "release.yml",
    "release-on-merge.yml",
    "release-proposal.yml",
}
# What a consumer resolves. `.github/workflows/` minus OWN_CI, plus every composite action.
CONSUMER_FACING = (".github/workflows/", "actions/")
# Applied rules for a branch, unlike the rulesets API, need no `administration` scope — it answers
# unauthenticated on a public repo, so the default GITHUB_TOKEN is enough.
BRANCH_RULES_URL = f"{REPO_URL}/rules/branches/main"
# Applied rules are ruleset-derived only, so a context set through legacy branch protection would be
# enforced and invisible. This endpoint carries the legacy view and needs no `administration:read`,
# which GITHUB_TOKEN cannot be granted — `branches/main/protection`, which does, would cost an admin
# PAT to close a blind spot. That `protection.required_status_checks.contexts` reads empty here while
# the ruleset requires three checks is what shows it answers for legacy protection alone.
BRANCH_URL = f"{REPO_URL}/branches/main"
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
    from_rulesets = {
        str(check["context"])
        for rule in rules
        if rule.get("type") == "required_status_checks"
        for check in rule["parameters"]["required_status_checks"]
    }
    branch: dict[str, Any] = _api_json(BRANCH_URL)
    protection: dict[str, Any] = branch.get("protection") or {}
    legacy: dict[str, Any] = protection.get("required_status_checks") or {}
    return from_rulesets | {str(context) for context in legacy.get("contexts", [])}


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
        # Shape alone is not enough: a ref left on the *previous* major keeps matching `^v\d+$`
        # forever while pointing at a tag README has since declared frozen, so no later fix to the
        # target ever reaches a consumer.
        #
        # Scoped to this repository rather than to FIRST_PARTY: [project].version describes this
        # repository's surface, so forcing its major onto a ref to a *different* turboBasic repo
        # would fail a gate that has no business judging it.
        if not target.startswith(SELF_REPO):
            continue
        current = f"v{_declared_version().split('.')[0]}"
        assert version == current, (
            f"{path.name}:{number} references {target}, but [project].version declares {current}. A "
            f"ref on a frozen major stops moving, so nothing done to the target after that major was "
            f"frozen reaches anyone resolving this line."
        )


def test_readme_names_the_declared_major() -> None:
    # README is the only place a concrete major is written literally, which makes it both the copy a
    # consumer pastes and the authority for which major is current.
    #
    # Two shapes: a `uses:` call site, and the Versioning section's opening sentence, which carries
    # no `uses:` and is what every other document reads the value from. Its later paragraphs must
    # stay free to name a frozen major, so this reads the first line of the section only.
    readme = (REPO_ROOT / "README.md").read_text()
    current = f"v{_declared_version().split('.')[0]}"

    stale = [
        f"{number}: {line.strip()}"
        for number, line in enumerate(readme.splitlines(), start=1)
        if "uses:" in line and (found := re.search(rf"{re.escape(FIRST_PARTY)}\S+@(v\d+)", line))
        if found.group(1) != current
    ]
    assert not stale, (
        f"README names a major other than {current}, which [project].version declares, on a call "
        f"site a consumer copies: {stale}."
    )

    section = readme.split("\n## Versioning\n", 1)
    assert len(section) == 2, "README.md has no `## Versioning` section"
    opening = section[1].strip().split("\n\n", 1)[0]
    named = set(re.findall(r"@?(v\d+)", opening))
    assert named == {current}, (
        f"README's Versioning section opens naming {sorted(named)}; [project].version declares "
        f"{current}, and this sentence is what every other document is told to read the current "
        f"major from. A frozen major belongs in a later paragraph."
    )


def _mise_tool_versions() -> dict[str, str]:
    manifest: dict[str, Any] = tomllib.loads((REPO_ROOT / "mise.toml").read_text())
    tools: dict[str, Any] = manifest["tools"]
    return {name: str(spec) for name, spec in tools.items()}


def test_no_mise_tool_version_floats() -> None:
    # A `latest` resolves at install time, so one commit runs different linters on different
    # machines. The digit rule admits a partial pin like `3.14` and rejects every form that leaves
    # the choice to whoever runs `mise install`.
    floating = sorted(
        f"{name} = {version!r}"
        for name, version in _mise_tool_versions().items()
        if not version[:1].isdigit()
    )
    assert not floating, (
        f"mise.toml leaves {floating} for install time to decide, so two machines on this commit "
        f"can lint it with different tools. Name the version — Renovate's mise manager bumps it."
    )


@pytest.mark.parametrize("doc", PROSE_DOCS, ids=str)
def test_no_prose_document_names_a_concrete_major(doc: Path) -> None:
    # README's Versioning section is the only place a major is written literally, and every other
    # document is told to read the value from there. A literal `@v2` in ai-instructions is what an
    # agent writes into a consumer, and it keeps resolving after that major is frozen; a bare `v4` in
    # prose rots the same way without being copied anywhere, which is why neither form is allowed.
    stale = [
        f"{number}: {line.strip()}"
        for number, line in enumerate((REPO_ROOT / doc).read_text().splitlines(), start=1)
        if re.search(r"@?\bv\d", line)
    ]
    assert not stale, (
        f"{doc} names a concrete major, which goes stale at the next bump: {stale}. Write `@vN`, or "
        f"say the current major, and cite README's Versioning section for the value."
    )


def test_a_self_call_resolves_at_the_commit_under_review() -> None:
    # Every other gate accepts both forms — test_first_party_actions_use_the_major_tag accepts the
    # tagged one by design, since prek-advisory.yml references a composite action that way —
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
    # Anchored on the four-space job indent, because a workflow-level `name:` sits at column 0 and
    # an unanchored match would accept it in place of the job's.
    assert f"\n    name: {job_name}\n" in called.read_text(), (
        f"{called_name} must keep `name: {job_name}`; it is the second half of the required "
        f"check `{context}`."
    )


@pytest.mark.parametrize(
    ("workflow", "job_name"),
    [("release.yml", "tag-and-publish"), ("release-proposal.yml", "propose")],
)
def test_the_release_job_names_are_pinned(workflow: str, job_name: str) -> None:
    # `tag-and-publish` composes `release / tag-and-publish`, the context `github-actions-test`
    # reports and requires. A required context that stops reporting blocks every pull request there
    # until its own ruleset is edited, which no ref can do for it — so a rename is a major bump.
    # `propose` is pinned for the same reason a step away: nothing requires it today, and the cost of
    # finding out otherwise is another repository's blocked queue.
    text = (REPO_ROOT / ".github" / "workflows" / workflow).read_text()
    assert f"\n    name: {job_name}\n" in text, (
        f"{workflow} no longer names its job `{job_name}`. That name is half of a check context "
        f"consumers type into a ruleset by hand; renaming it is a major bump (FR-009a)."
    )


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip())


def _under(lines: list[str], header: str) -> list[str]:
    # Indent-based, like block_of_words and for the same reason: a pattern matching what a key ought
    # to look like ends the block at the first line it does not recognise and hides the rest.
    start = next((i for i, line in enumerate(lines) if line.strip() == header), None)
    assert start is not None, f"no `{header}` block found"
    depth = _indent(lines[start])
    nested: list[str] = []
    for line in lines[start + 1 :]:
        if line.strip() and _indent(line) <= depth:
            break
        nested.append(line)
    return nested


def _entries(lines: list[str]) -> set[str]:
    # A comment-only line carries no entry, and counting one would both skew the depth and add `""`
    # to the result.
    populated = [line for line in lines if line.strip() and not line.strip().startswith("#")]
    depth = min(_indent(line) for line in populated)
    return {line.split("#")[0].strip().rstrip(":") for line in populated if _indent(line) == depth}


def _triggers(path: Path) -> set[str]:
    return _entries(_under(path.read_text().splitlines(), "on:"))


@pytest.mark.parametrize(
    ("workflow", "job_id", "inputs", "permissions"),
    [
        ("release.yml", "release", {"dry-run"}, {"contents: write"}),
        ("release-proposal.yml", "propose", set[str](), {"contents: read"}),
    ],
)
def test_the_release_interface_is_frozen(
    workflow: str, job_id: str, inputs: set[str], permissions: set[str]
) -> None:
    # The two halves of these workflows a caller writes into its own file, and both are validated
    # before any job exists — so a renamed input breaks the call site outright, and a caller granting
    # a permission that is no longer enough fails at startup with no job and no log to read. Stated
    # here rather than diffed against a commit, so it holds for every later change too.
    lines = (REPO_ROOT / ".github" / "workflows" / workflow).read_text().splitlines()
    job = _under(_under(lines, "jobs:"), f"{job_id}:")

    assert _entries(_under(job, "permissions:")) == permissions, (
        f"{workflow}'s `{job_id}` job no longer asks for exactly {sorted(permissions)}. Job "
        f"permissions can only be reduced down a call chain, so a caller cannot make up a shortfall "
        f"— widening this is a major bump (FR-009)."
    )

    if not inputs:
        assert "workflow_call:" not in "\n".join(lines), (
            f"{workflow} gained a `workflow_call` trigger, so it now has an input contract and "
            f"callers this table does not account for (FR-009)."
        )
        return
    assert _entries(_under(_under(lines, "workflow_call:"), "inputs:")) == inputs, (
        f"{workflow} no longer declares exactly the inputs {sorted(inputs)} under `workflow_call`. A "
        f"removed or renamed input breaks every call site that passes it, which no ref can fix for "
        f"the caller — that is a major bump (FR-009)."
    )


def test_the_release_workflow_has_no_trigger_of_its_own() -> None:
    # A `needs:` edge in a caller is the whole gate: it is what makes "CI passed on the commit being
    # tagged" structurally true rather than queried. A trigger here would be a second way in that
    # nothing gates — and it would fail open, because release.yml verifies nothing about CI itself.
    triggers = _triggers(REPO_ROOT / ".github" / "workflows" / "release.yml")
    assert triggers == {"workflow_call"}, (
        f"release.yml declares {sorted(triggers)}. Anything but `workflow_call` alone is a path to a "
        f"release with no verdict behind it; the manual path belongs on release-on-merge.yml, which "
        f"gates it the same way a merge is gated."
    )


def test_the_release_workflow_gives_gh_a_repository() -> None:
    # Nothing is cloned there, so a `gh` subcommand other than `gh api` — which carries the full
    # path — has no remote to infer the repository from and dies with `not a git repository`. No
    # linter sees it: the shell is valid and the call well-formed, so the missing flag is only
    # discoverable by running it somewhere without a checkout.
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
    # release-on-merge.yml cuts the release behind `needs: [verify]`, and that dependency *is*
    # FR-011: it is what makes "CI passed on the commit being released" structurally true instead of
    # something queried. Drop it and the release runs in parallel with the tests it is supposed to be
    # gated on, tagging code nothing has verified — with every linter green, because a job without
    # `needs` is perfectly valid YAML. `verify` has to be python-ci itself for the same reason: a
    # `needs` on a job that checks nothing is a green edge and no verdict.
    #
    # `needs: [verify, drift]` is equally wrong in the other direction: `drift` is red precisely when
    # a release is owed, so the release could only ever be cut when none was needed.
    workflow = (REPO_ROOT / ".github" / "workflows" / "release-on-merge.yml").read_text()
    verify = re.search(r"(?ms)^  verify:\n(.*?)(?=^  \w|\Z)", workflow)
    assert verify and "uses: $/.github/workflows/python-ci.yml" in verify.group(1), (
        "release-on-merge.yml's `verify` job does not call python-ci.yml at this same commit, so "
        "what the release job waits on verifies nothing (FR-011)."
    )
    release_job = re.search(r"(?ms)^  release:\n(.*?)(?=^  \w|\Z)", workflow)
    assert release_job, (
        "release-on-merge.yml has no `release` job; that job is what cuts a release after a merge."
    )
    body = release_job.group(1)
    assert re.search(r"needs:\s*\[\s*verify\s*\]", body), (
        "release-on-merge.yml's release job does not declare `needs: [verify]`, so it no longer "
        "waits for the verdict that covers the commit it would tag (FR-011)."
    )
    assert "drift" not in body, (
        "release-on-merge.yml's release job depends on `drift`, which is red exactly when a release "
        "is owed — so a release could only be cut when none was needed."
    )
    assert "uses: $/.github/workflows/release.yml" in body, (
        "release-on-merge.yml's release job must call release.yml at this same commit with the `$/` "
        "form, so a change to it is validated by the version under review rather than by the last tag."
    )


def test_the_release_refuses_notes_with_no_content() -> None:
    # The rule this used to assert as text — that emptiness is a content question, never a size and
    # never an exit code — is `notes_are_empty`'s now, with its own tests. What is left to hold here
    # is that release.yml still asks: the notes it renders reach the `check-notes` decision, whose
    # refusal is what stops a range that renders nothing from publishing a blank release body.
    workflow = (REPO_ROOT / ".github" / "workflows" / "release.yml").read_text()
    asking = [step for step in workflow.split("\n      - ") if "decision: check-notes" in step]
    assert len(asking) == 1, (
        f"release.yml has {len(asking)} steps invoking the `check-notes` decision, expected one. "
        f"Without it nothing refuses a range that renders no notes, and the release publishes a "
        f"blank body (FR-007)."
    )
    assert "notes-file: ${{ env.NOTES }}" in asking[0], (
        f"release.yml's `check-notes` step passes no notes-file, so the decision cannot see what "
        f"git-cliff rendered and answers about the wrong thing:\n{asking[0]}"
    )


def test_the_release_refuses_an_empty_moving_tag_before_creating_a_ref() -> None:
    # The moving ref's name comes from a composite action that a caller resolves at a *tag*, so a
    # release cut between adding an output there and moving that tag reads it as empty. Unguarded, that
    # is the worst ordering available: `gh release create` succeeds, the version tag exists, and only
    # then does the ref move fail — leaving consumers on the previous release with a version tag the
    # `immutable release tags` ruleset forbids anyone from deleting. Recovery is a hand-moved ref, so
    # the guard has to come before the first ref is created rather than anywhere in the step.
    workflow = (REPO_ROOT / ".github" / "workflows" / "release.yml").read_text()
    guard = workflow.find("-z ${MOVING_TAG}")
    assert guard != -1, (
        "release.yml does not check that MOVING_TAG is non-empty. An empty ref name reaches `gh api` "
        "only after the release is published, and the version tag cannot then be deleted."
    )
    first_ref = workflow.find("git/tags")
    assert first_ref != -1, (
        "release.yml creates no tag object; this test is anchored on the wrong step"
    )
    assert guard < first_ref, (
        "release.yml checks MOVING_TAG after it has already started creating refs. The check is only "
        "worth having before the first one."
    )


def test_the_release_publishes_the_rendered_notes() -> None:
    # `--generate-notes` asks GitHub to build the body from pull request labels, and nothing here
    # labels a pull request — reinstating it would route the notes back through labels with
    # `.cliff.toml` still sitting there. Comments stripped: the line explaining why
    # `--generate-notes` is gone contains it.
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


@pytest.mark.drift
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


@pytest.mark.drift
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


@pytest.mark.drift
def test_no_consumer_facing_change_is_waiting_for_a_release() -> None:
    # The major tag is force-moved by hand-initiated dispatch, so nothing stops it sitting behind
    # main. No file can show that — the state is a ref on GitHub — which is why this is live.
    #
    # Scoped to what a consumer resolves rather than to `main` being ahead at all. A docs or test
    # commit owes nobody a release, and a check that reddens after every merge is one nobody reads.
    major = f"v{_declared_version().split('.')[0]}"
    try:
        comparison: dict[str, Any] = _api_json(f"{REPO_URL}/compare/{major}...main")
    except urllib.error.HTTPError as error:
        if error.code != 404:
            raise
        # [project].version names a major nothing has tagged, so there is no ref to compare against.
        # A release in flight cannot be mistaken for one that is owed: drift.yml carries no `push`
        # trigger, so this never shares a run with the release that would move the tag.
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


def _declared_labels() -> set[str]:
    # CONTRIBUTING's Labels table is the set. A second copy of it here is what this test exists to
    # catch happening on GitHub, so it reads the documentation rather than restating it — and someone
    # adding a label edits the page a contributor actually reads.
    section = (REPO_ROOT / "CONTRIBUTING.md").read_text().split("\n## Labels\n", 1)
    assert len(section) == 2, "CONTRIBUTING.md has no `## Labels` section"
    rows = re.findall(r"^\|[^|]+\|([^|]+)\|", section[1].split("\n## ", 1)[0], re.MULTILINE)
    # Header and separator carry no backticks, so they drop out on their own. The row count is
    # asserted because a reformatted table that parses to nothing would leave both tests vacuous.
    rows_of_labels = [names for row in rows if (names := set(re.findall(r"`([^`]+)`", row)))]
    assert len(rows_of_labels) == LABEL_TABLE_ROWS, (
        f"CONTRIBUTING's Labels table parsed to {len(rows_of_labels)} rows of labels, expected "
        f"{LABEL_TABLE_ROWS}. Adjust LABEL_TABLE_ROWS if an axis was genuinely added."
    )
    return set[str]().union(*rows_of_labels)


def test_every_label_a_file_applies_is_declared() -> None:
    # An issue form naming a label that does not exist is dropped in silence — GitHub neither creates
    # it nor complains — so the issue opens unlabelled and every `kind:` report undercounts.
    declared = _declared_labels()
    for path in LABEL_WRITERS:
        for block in re.findall(r'(?i)labels"?:\s*\[([^\]]*)\]', (REPO_ROOT / path).read_text()):
            applied = set(re.findall(r'"([^"]+)"', block))
            # A bare `kind:bug` in a YAML flow sequence is ambiguous, so entries here are quoted;
            # an unquoted one reads as empty and would otherwise pass this test by matching nothing.
            assert applied, f"{path} has an unquoted or unreadable labels list: [{block}]"
            assert not (applied - declared), (
                f"{path} applies {sorted(applied - declared)}, which CONTRIBUTING's Labels table "
                f"does not declare. Add it there, or fix the reference."
            )


@pytest.mark.drift
def test_the_repository_has_exactly_the_declared_labels() -> None:
    # Labels exist only on GitHub, where anyone can add one from the issue sidebar in a click, and
    # nothing in the tree would look wrong afterwards. That is the whole failure: a second name for
    # a kind splits a count in half and the report stays plausible. Names only — a drifted colour
    # or description misleads nobody who is grouping by name.
    declared = _declared_labels()
    live = {str(label["name"]) for label in _api_json(f"{REPO_URL}/labels?per_page=100")}
    assert live == declared, (
        f"the repository's labels have drifted from CONTRIBUTING's Labels table: "
        f"{sorted(live - declared)} exist and are undeclared, {sorted(declared - live)} are declared "
        f"and missing. Reconcile with `gh label create` / `gh label delete`, or amend the table if "
        f"the set really did change."
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
    # Found by dedent, not by matching what an entry ought to look like: a pattern that matches
    # entries ends the block at the first malformed line and hides everything after it, so an
    # appended `foo|bar` would widen the accepted types unseen.
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


def test_every_workflow_name_carries_its_prefix() -> None:
    # The Actions sidebar sorts by name by code point, so the prefix is what keeps these together and
    # below the entries GitHub injects and nobody can rename. Which block a workflow belongs to is its
    # trigger: a `workflow_call`-only workflow never has a run of its own, because its jobs appear
    # inside its caller's run, so 🧩 promises an empty page and 🌜 promises a history. Labelling by any
    # other criterion sends a reader somewhere there is nothing to read.
    #
    # Deliberately not OWN_CI, which answers whether a change obliges a release. The two coincide for
    # every file but `release.yml`, which a consumer calls while staying off the version surface — and
    # that one file is the whole reason the questions are asked separately.
    offenders: list[str] = []
    for path in sorted((REPO_ROOT / ".github" / "workflows").glob("*.yml")):
        found = WORKFLOW_NAME.search(path.read_text())
        name = found.group(1).strip() if found else "<none>"
        want = f"{'🧩' if _triggers(path) == {'workflow_call'} else '🌜'} {path.stem}"
        if name != want:
            offenders.append(f"{path.name}: {name!r}, want {want!r}")
    assert not offenders, (
        f"a workflow's name is 🌜 or 🧩, a space, then its filename stem: {offenders}."
    )


def test_every_job_name_is_lowercase_kebab() -> None:
    # `REQUIRED_CHECKS` pins three names, not the shape of a fourth, so nothing else holds a new job
    # to the scheme every check context here follows.
    #
    # Casing only. Whether a callee's name says what the job is rather than repeating its caller is
    # judgement, and docs/ai-instructions.md owns it; this is the half a regex can hold.
    offenders = [
        f"{path.name}:{number}: {line.strip()}"
        for path in sorted((REPO_ROOT / ".github" / "workflows").glob("*.yml"))
        for number, line in enumerate(path.read_text().splitlines(), start=1)
        # `(.+)` rather than `(\S+)`: a name containing a space is the main thing being ruled out, and
        # a non-space pattern skips those lines entirely instead of failing them.
        if (found := re.match(r"^    name: (.+)$", line))
        if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", found.group(1).strip())
    ]
    assert not offenders, (
        f"job names are lowercase-kebab-case, and these are not: {offenders}. A job name is half of "
        f"a check context consumers type into a ruleset by hand."
    )


def test_python_ci_requests_no_pull_request_permission() -> None:
    # A called workflow's job permissions are validated when the run starts, before any
    # `if:` can skip the job, so a `pull-requests: write` anywhere here would force every
    # caller to grant it. A job needing write belongs in prek-advisory.yml, which
    # only its own callers invoke.
    workflow = REPO_ROOT / ".github" / "workflows" / "python-ci.yml"
    assert "pull-requests" not in workflow.read_text(), (
        "python-ci.yml requests a pull-requests permission; every caller would then be "
        "forced to grant it, failing at startup otherwise. Put the job that needs it in "
        "prek-advisory.yml instead."
    )
