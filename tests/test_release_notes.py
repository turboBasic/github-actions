import re
import tomllib
from typing import Any

from test_action_pins import REPO_ROOT, block_of_words

CLIFF = REPO_ROOT / ".cliff.toml"
TYPES_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "conventional-commits.yml"

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
