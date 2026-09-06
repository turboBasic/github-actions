import json
import re
import subprocess
import tomllib
from pathlib import Path
from typing import Any

import pytest
from decisions import surface_args

from test_action_pins import REPO_ROOT, block_of_words

CLIFF = REPO_ROOT / ".cliff.toml"
WORKFLOWS = REPO_ROOT / ".github" / "workflows"
TYPES_WORKFLOW = WORKFLOWS / "conventional-commits.yml"
# The two workflows the release path is made of. Neither decides anything in shell any more, and the
# two guards at the bottom of this file are what hold them to that.
RELEASE_PATH = ("release.yml", "release-proposal.yml")
# Each is the shell spelling of a decision that now lives in decisions.py, mapped to what answers it.
# Nothing can tell a plumbing branch from a decision by shape — `[[ ${conclusion} != success ]]` and
# `major="v${VERSION%%.*}"` both stay — so this names the constructs the removed decisions were
# written in rather than trying to recognise a decision in general.
SHELL_DECISIONS = {
    "$((": "an arithmetic increment; next_version does the increment",
    "sort -V": "an ordering of versions; highest_version and is_ahead answer that",
    "=~": "a regex match over a version; parse_version answers that",
    r"[0-9]+\.[0-9]+\.[0-9]+": "a semantic-version pattern; PLAIN_VERSION is the one copy",
    "python3 -c": "an inline interpreter reading the version; declared_version answers that",
    "[^[:space:]]": "a content test over the rendered notes; notes_are_empty answers that",
    ".breaking": "a jq filter over commit data; verdicts answers that",
}
SURFACE_FLAGS = ("--include-path", "--exclude-path")

# data-model.md's Section table, which FR-002 fixes in both title and position. Order 1 is
# deliberately not a `group`: a breaking commit also keeps its own type's section (FR-005), so
# the breaking section is a separate Tera block over every commit with `breaking` true rather
# than a seventh destination a commit could be routed to.
SECTIONS = [
    (1, "💥 Breaking changes"),
    (2, "🚀 Features"),
    (3, "🐛 Fixes"),
    (4, "📚 Documentation"),
    (5, "🚚 CI and dependencies"),
    (6, "🧹 Maintenance"),
    (7, "Other changes"),
]
CATCH_ALL = ".*"
EXCLUDED = "bump"
# `<!--N-->` sorts the groups in the rendered output and a postprocessor strips it again, so the
# number is the only statement of position anywhere.
ORDERING_PREFIX = re.compile(r"^<!--(\d+)-->(.*)$")


def _git_table() -> dict[str, Any]:
    config: dict[str, Any] = tomllib.loads(CLIFF.read_text())
    git: dict[str, Any] = config["git"]
    return git


def _parsers() -> list[dict[str, Any]]:
    parsers: list[dict[str, Any]] = _git_table()["commit_parsers"]
    return parsers


def _subjects(commit_type: str) -> list[str]:
    # Both spellings a squash subject can carry, since a scope or a `!` must not change which
    # section a type lands in.
    return [f"{commit_type}: a subject", f"{commit_type}(scope)!: a subject"]


def _first_match(subject: str) -> dict[str, Any]:
    # git-cliff walks commit_parsers in order and stops at the first pattern that matches, so a
    # parser's position is as load-bearing as its regex. Mirrored here rather than assumed.
    for parser in _parsers():
        if re.search(str(parser["message"]), subject):
            return parser
    raise AssertionError(f".cliff.toml has no parser matching {subject!r}, not even a catch-all")


def test_every_allowed_type_is_placed_or_skipped() -> None:
    # The assertion that matters most over time: a type added to conventional-commits.yml and
    # not here still renders, silently, under Other changes. That is FR-003's intended
    # behaviour for an *unknown* type and a defect for an allowed one, and no linter can tell
    # the two apart because both configs are valid.
    stray = sorted(
        subject
        for commit_type in block_of_words(TYPES_WORKFLOW, "default")
        for subject in _subjects(commit_type)
        if str(_first_match(subject)["message"]) == CATCH_ALL
    )
    assert not stray, (
        f"conventional-commits.yml allows these, but .cliff.toml routes them to the catch-all: "
        f"{stray}. Give each a group, or `skip = true` if it must not appear at all."
    )


def test_bump_is_the_only_excluded_type() -> None:
    skipping = [p for p in _parsers() if p.get("skip")]
    assert len(skipping) == 1, (
        f".cliff.toml has {len(skipping)} skipping parsers; FR-004 excludes exactly one type, "
        f"`{EXCLUDED}`, because a release's notes must not carry its own version bump."
    )
    excluded = sorted(
        commit_type
        for commit_type in block_of_words(TYPES_WORKFLOW, "default")
        for subject in _subjects(commit_type)
        if _first_match(subject).get("skip")
    )
    assert set(excluded) == {EXCLUDED}, (
        f".cliff.toml excludes {sorted(set(excluded))} from the notes; FR-004 excludes only "
        f"`{EXCLUDED}`. Anything else vanishing from a release body is a change consumers "
        f"cannot see."
    )


def test_the_seven_sections_keep_their_titles_and_order() -> None:
    seen: list[tuple[int, str]] = []
    for parser in _parsers():
        group = parser.get("group")
        if group is None:
            continue
        match = ORDERING_PREFIX.match(str(group))
        assert match, (
            f".cliff.toml group {group!r} carries no `<!--N-->` prefix, so its position in the "
            f"rendered notes is whatever group_by happens to sort it to."
        )
        entry = (int(match.group(1)), match.group(2))
        if entry not in seen:
            seen.append(entry)

    assert seen == SECTIONS[1:], (
        f".cliff.toml declares sections {seen}; data-model.md fixes them as {SECTIONS[1:]}. "
        f"A retitled or reordered section changes how every release reads (FR-002)."
    )

    body = str(tomllib.loads(CLIFF.read_text())["changelog"]["body"])
    assert f"### {SECTIONS[0][1]}" in body, (
        f"the breaking section `{SECTIONS[0][1]}` is missing from the body template. It is not a "
        f"group — it is the block that lets one commit occupy two sections (FR-005) and the only "
        f"place breaking_description is shown."
    )


def test_the_catch_all_parser_is_last() -> None:
    patterns = [str(p["message"]) for p in _parsers()]
    assert patterns.count(CATCH_ALL) == 1, (
        f".cliff.toml has {patterns.count(CATCH_ALL)} catch-all parsers; there is one section of "
        f"last resort, so there is one parser feeding it."
    )
    assert patterns[-1] == CATCH_ALL, (
        f".cliff.toml puts its catch-all at position {patterns.index(CATCH_ALL) + 1} of "
        f"{len(patterns)}. commit_parsers is first-match-wins, so every parser after it is dead "
        f"and every type would render under Other changes."
    )
    assert _first_match("a subject with no type at all").get("group"), (
        "a commit matching no Conventional Commit reaches no group, so it vanishes from the "
        "notes. FR-003 requires it to surface in the section of last resort instead."
    )


def test_tag_pattern_excludes_the_moving_major_tags() -> None:
    # `v1` and `v2` sit on main's tip. Let either match and `--unreleased` measures from there,
    # which renders an empty range with no warning at all — the failure research.md decision 1
    # records, and the one an empty release body would come from.
    pattern = str(_git_table()["tag_pattern"])
    assert re.search(pattern, "v2.0.2"), (
        f"tag_pattern {pattern!r} does not match a version tag like v2.0.2, so no range has a "
        f"lower bound and every release renders the whole history."
    )
    moving = [tag for tag in ("v1", "v2", "v2.0") if re.search(pattern, tag)]
    assert not moving, (
        f"tag_pattern {pattern!r} also matches the moving major tags {moving}, which sit on "
        f"main's tip. `--unreleased` would measure from there and render nothing."
    )


def _breaking(repo: Path, *flags: str) -> bool:
    context = subprocess.run(
        ["git-cliff", "--config", str(CLIFF), "--unreleased", "--context", *flags],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return any(
        commit.get("breaking") is True
        for release in json.loads(context)
        for commit in release["commits"]
    )


def test_only_a_breaking_change_to_the_surface_refuses_a_release(tmp_path: Path) -> None:
    # release.yml refuses a non-major version over a breaking range. Which range it reads is the
    # whole behaviour: unfiltered, a `!` on a commit touching nothing consumers resolve deadlocks a
    # release the proposal correctly numbered a patch, and the only ways out are a major nothing
    # justifies or rewriting the commit.
    #
    # The flags come from `surface_args()`, which is the one definition both range reads now take
    # them from — no workflow spells them, so there is no text left to scrape.
    def git(*args: str) -> None:
        subprocess.run(
            ["git", "-c", "user.name=t", "-c", "user.email=t@t", *args],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )

    git("init", "-q", "-b", "main", ".")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "technical-debt.md").write_text("1")
    git("add", ".")
    git("commit", "-qm", "chore!: a breaking change off the consumer surface")

    flags = surface_args()
    # The control. Without it a filter excluding everything satisfies the assertion below, which is
    # the way this test could pass while the refusal it guards never fires at all.
    assert _breaking(tmp_path), (
        "an unfiltered --context does not see a `!` commit as breaking, so this test proves nothing "
        "about the filtered one. Either .cliff.toml stopped setting `breaking` or the probe commit "
        "is not shaped like one."
    )
    assert not _breaking(tmp_path, *flags), (
        f"surface_args() {flags} still reports a breaking change for a commit touching only docs/. "
        f"That refuses a release the proposal numbered a patch, with a new major and history "
        f"rewriting as the only ways forward (#62)."
    )

    surface = tmp_path / ".github" / "workflows"
    surface.mkdir(parents=True)
    (surface / "python-ci.yml").write_text("1")
    git("add", ".")
    git("commit", "-qm", "feat!: a breaking change to a reusable workflow")
    assert _breaking(tmp_path, *flags), (
        f"surface_args() {flags} does not see a breaking change to a reusable workflow consumers "
        f"call, so the FR-012a refusal no longer fires where it must: the major tag would move onto "
        f"a broken contract."
    )


def test_an_item_without_a_pr_number_carries_its_commit_hash(tmp_path: Path) -> None:
    # The one assertion here that renders rather than reads the config. A Tera conditional cannot be
    # checked by shape: a regex that stops matching, or matches everything, leaves valid TOML and
    # notes that silently reference nothing. Rendered against a throwaway repository so it needs no
    # tag, no network and no state from this one.
    def git(*args: str) -> None:
        subprocess.run(
            ["git", "-c", "user.name=t", "-c", "user.email=t@t", *args],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )

    git("init", "-q", "-b", "main", ".")
    (tmp_path / "f").write_text("1")
    git("add", ".")
    git("commit", "-qm", "fix: numbered subject (#12)")
    (tmp_path / "f").write_text("2")
    git("commit", "-aqm", "fix: subject with no number")
    rendered = subprocess.run(
        ["git-cliff", "--config", str(CLIFF), "--unreleased"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    short = subprocess.run(
        ["git", "rev-parse", "--short=7", "HEAD"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    assert f"- fix: subject with no number ({short})" not in rendered, (
        "the hash was appended to the whole subject rather than the message git-cliff strips the "
        "type from; the item no longer reads as the notes' other lines do"
    )
    assert f"- subject with no number ({short})" in rendered, (
        f"an item whose subject carries no `(#N)` rendered without its commit hash, so it "
        f"references nothing at all. Rendered:\n{rendered}"
    )
    assert "- numbered subject (#12)" in rendered, (
        f"an item whose subject already carries `(#12)` was given a hash as well, so every line "
        f"now ends in two references. Rendered:\n{rendered}"
    )


def _shell(workflow: str) -> str:
    # Comment lines dropped, so prose naming a construct is documentation rather than a failure. What
    # is left is the shell a run executes and the `with:` blocks it passes.
    return "\n".join(
        line
        for raw in (WORKFLOWS / workflow).read_text().splitlines()
        if not (line := raw.strip()).startswith("#")
    )


@pytest.mark.parametrize("workflow", RELEASE_PATH)
def test_neither_release_workflow_decides_anything_in_shell(workflow: str) -> None:
    # The readable half of the extraction, and the half no linter can hold: shell quoting, `${{ }}`
    # interpolation and block-scalar rules stack in the same lines, so a decision written there is
    # reviewable only by someone holding all three grammars at once. Every one of them is a call into
    # decisions.py now, where it has a test.
    text = _shell(workflow)
    found = sorted(
        f"{construct!r} — {answered_by}"
        for construct, answered_by in SHELL_DECISIONS.items()
        if construct in text
    )
    assert not found, (
        f"{workflow} decides in shell again: {found}. Call the decision through "
        f"actions/release-decisions and give it a test in tests/test_release_decisions.py (SC-003)."
    )


@pytest.mark.parametrize("workflow", RELEASE_PATH)
def test_neither_release_workflow_spells_the_surface_filter(workflow: str) -> None:
    # One definition, in decisions.py, held to OWN_CI by tests/test_release_decisions.py. Two copies
    # in shell is what deadlocked a release when they disagreed (#62); a third copy anywhere is the
    # same defect waiting, so the flags may not appear in a workflow at all.
    text = _shell(workflow)
    spelled = [flag for flag in SURFACE_FLAGS if flag in text]
    assert not spelled, (
        f"{workflow} spells {spelled} itself. The consumer surface has one definition — take the "
        f"flags from the action's `surface-args` decision (SC-004)."
    )
