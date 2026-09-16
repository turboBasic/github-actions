import re
import shutil
import subprocess
import tomllib
from pathlib import Path
from typing import Any, cast

from capabilities import REPO, allowed_commit_types

# Read by this module alone, so the path lives here rather than beside the workflow reader's.
CLIFF = REPO / "cliff.toml"

Table = dict[str, Any]

# What a parser routes a commit to when it does not name a group. Not a group name itself, so it
# cannot collide with one.
SKIP = "\0skip"


def config() -> Table:
    return tomllib.loads(CLIFF.read_text(encoding="utf-8"))


def parsers() -> list[Table]:
    return cast(list[Table], config()["git"]["commit_parsers"])


def destination(subject: str) -> str | None:
    # git-cliff takes the first parser that matches and stops, so a type's destination is that
    # parser's group, or the skip marker where it has one. None means the type reaches nothing and
    # every commit of it is dropped from the notes without a word.
    for parser in parsers():
        pattern = parser.get("message")
        if pattern is not None and re.search(str(pattern), subject):
            return SKIP if parser.get("skip") else str(parser.get("group"))
    return None


def test_every_parser_names_exactly_one_destination() -> None:
    found = parsers()
    assert found, f"{CLIFF.name} declares no commit parsers, so this gate places nothing"
    wrong = [
        parser for parser in found if (parser.get("group") is None) == (parser.get("skip") is None)
    ]
    assert wrong == [], (
        f"{CLIFF.name} has parsers naming both a group and a skip, or neither: {wrong}. Each routes a "
        "commit to one destination — give it `group` to place it in a section or `skip = true` to leave "
        "it out"
    )


def test_every_allowed_type_reaches_a_destination() -> None:
    types = allowed_commit_types()
    assert types, (
        "conventional-commits.yml declares no types, so this gate compares the notes against nothing"
    )
    homeless = sorted(kind for kind in types if destination(f"{kind}: a subject") is None)
    assert homeless == [], (
        f"the commit grammar admits {homeless} and {CLIFF.name} routes them nowhere, so every commit of "
        f"those types is dropped from the release notes silently. Give each one a `group` in "
        f"`commit_parsers` to place it in a section, or `skip = true` to leave it out deliberately"
    )


# The published shape of a release body: the breaking block where there is one, then six sections,
# these titles, this order. Written out rather than read from the order the parsers happen to be
# declared in — a gate taking its expectation from the artefact it judges would follow a reorder
# instead of failing it.
#
# The block is not a parser group: a breaking commit keeps its own type's section and is lifted into
# the block as well. So the parsers declare six groups, and a seventh appearing there is a change to
# what a release publishes.
BREAKING_SECTION = "💥 Breaking changes"

SECTIONS = (
    (1, "🚀 Added"),
    (2, "🐛 Fixed"),
    (3, "⚡ Performance"),
    (4, "♻️ Changed"),
    (5, "⏪ Reverted"),
    (6, "📚 Documentation"),
)

# Tera sorts groups by their string, so the number is what puts a section in its place, and a
# postprocessor strips it again. It is the only statement of position anywhere: without it the order
# is alphabetical, which makes a retitle silently a reorder.
ORDERING_PREFIX = re.compile(r"^<!--(\d+)-->(.*)$")


def numbered_sections() -> tuple[list[tuple[int, str]], list[str]]:
    numbered: list[tuple[int, str]] = []
    unprefixed: list[str] = []
    for group in dict.fromkeys(
        str(parser["group"]) for parser in parsers() if parser.get("group") is not None
    ):
        match = ORDERING_PREFIX.match(group)
        if match is None:
            unprefixed.append(group)
        else:
            numbered.append((int(match.group(1)), match.group(2)))
    return numbered, unprefixed


def test_the_six_sections_keep_their_titles_and_their_order() -> None:
    numbered, unprefixed = numbered_sections()
    assert unprefixed == [], (
        f"{CLIFF.name} has group names carrying no `<!--N-->` ordering prefix: {unprefixed}. Without a "
        "number the sections render in alphabetical order, so retitling one moves it. Prefix every "
        f"group with its position from {[f'{n} {title}' for n, title in SECTIONS]}"
    )
    numbers = [number for number, _ in numbered]
    assert len(numbers) == len(set(numbers)), (
        f"{CLIFF.name} gives two sections the same position: {sorted(numbered)}. Two groups sharing a "
        "number render in an order nothing states"
    )
    assert sorted(numbered) == list(SECTIONS), (
        f"{CLIFF.name} declares sections {sorted(numbered)}; a release body publishes exactly "
        f"{list(SECTIONS)}. A retitle, a reorder, a seventh section or a removed one all change what a "
        "release says it contains — if the change is intended, change SECTIONS in the same commit"
    )


def test_the_ordering_prefix_reader_finds_a_number_it_is_given() -> None:
    # Pre-flight the matcher, or a change that stops it matching reports green over a body rendering
    # every section in the wrong place with the markers still visible.
    match = ORDERING_PREFIX.match("<!--3-->Performance")
    assert match is not None and match.groups() == ("3", "Performance")
    assert ORDERING_PREFIX.match("Performance") is None


# A release the notes are cut for. The range runs from the last of these, so anything else matching
# would start it somewhere that is not a release.
EXACT_VERSIONS = ("v1.2.3", "v0.1.0", "v10.20.30")

# A moving compatibility ref is a tag too. Matching one would start the range at wherever the last
# release moved it to rather than at the last release, so the notes would repeat or lose commits.
NOT_A_RELEASE = ("v1", "v1.2", "v0", "v1.2.3-rc1", "v1.2.3.4", "latest", "1.2.3")


def test_the_tag_pattern_matches_an_exact_version_and_no_moving_ref() -> None:
    pattern = re.compile(str(config()["git"]["tag_pattern"]))
    missed = [tag for tag in EXACT_VERSIONS if not pattern.search(tag)]
    assert missed == [], (
        f"{CLIFF.name}'s tag_pattern does not match {missed}, which are exact version tags. The range "
        "would start before the last release, so the notes would repeat commits already published"
    )
    caught = [tag for tag in NOT_A_RELEASE if pattern.search(tag)]
    assert caught == [], (
        f"{CLIFF.name}'s tag_pattern matches {caught}, which are not releases — a moving compatibility "
        "ref among them would start the range at wherever the last release moved it to rather than at "
        "the last release. Anchor the pattern to exactly three numbers"
    )


def test_the_destination_reader_places_a_type_it_is_given_and_reports_one_it_cannot() -> None:
    # Pre-flight the resolver, or a parser list that stops matching reports green while the notes
    # quietly drop everything.
    assert destination("feat: a subject") not in (None, SKIP)
    assert destination("chore: a subject") == SKIP
    assert destination("nonsense: a subject") is None


# One commit of every type, plus the four subjects whose rendering is the whole point: a subject that
# already carries a number, one that carries none, a ref pin, and an address.
SUBJECTS = (
    "feat: a numbered subject (#12)",
    "fix: subject with no number",
    "fix: repin every call site to @v5 (#20)",
    "fix: stop mailing t@t.example on release (#21)",
    "perf: faster (#4)",
    "refactor: moved (#5)",
    "revert: undone (#6)",
    "docs: documented (#7)",
    "chore: not published (#8)",
)

NO_NUMBER = "subject with no number"

# A breaking change, planted with the footer whose first paragraph the block publishes. Its type is one
# the parsers place, so the rendering shows both halves of the rule: lifted into the block, kept in
# 🚀 Added.
BREAKING_SUBJECT = "feat!: retire the old input (#30)"
BREAKING_FOOTER = "BREAKING CHANGE: the mise-version input is gone,\npin it in mise.toml instead"
BREAKING_DESCRIPTION = "the mise-version input is gone, pin it in mise.toml instead"
BREAKING_ITEM = "- Retire the old input (#30)"


def _git(repo: Path, *args: str) -> str:
    # A list, never a shell string: a subject here is text this test chose, and the habit of handing it
    # to a shell is the one that matters where the text comes from outside.
    return subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t.invalid", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def plant(repo: Path) -> None:
    _git(repo, "init", "-q", "-b", "main", ".")
    for index, subject in enumerate(SUBJECTS):
        (repo / "f").write_text(str(index), encoding="utf-8")
        _git(repo, "add", "f")
        _git(repo, "commit", "-qm", subject)
    (repo / "f").write_text("breaking", encoding="utf-8")
    _git(repo, "add", "f")
    _git(repo, "commit", "-qm", BREAKING_SUBJECT, "-m", BREAKING_FOOTER)


def short_id(repo: Path, grep: str) -> str:
    return _git(repo, "log", "--format=%H", "-1", f"--grep={grep}").strip()[:7]


def render(repo: Path) -> str:
    # Rendered rather than read. A pattern that has rotted into matching nothing, or into matching
    # everything, leaves valid TOML and a body that reads correctly to everyone except the person
    # GitHub notifies — so there is no shape to assert, only output.
    assert shutil.which("git-cliff"), (
        "git-cliff is not on PATH, so the release notes cannot be rendered and the two gates below are "
        "not running. Run the suite as `mise run test`, which puts the pinned tools on PATH"
    )
    return subprocess.run(
        # `--config` explicitly: git-cliff finds a configuration by name, and the planted repository
        # must not be able to supply one of its own. `cwd`, never `mise exec --cd`, which would render
        # this repository and pass whatever was planted.
        ["git-cliff", "--config", str(CLIFF), "--unreleased"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def test_the_rendered_sections_are_the_committed_titles_in_order(tmp_path: Path) -> None:
    plant(tmp_path)
    rendered = render(tmp_path)
    headings = [
        line.removeprefix("### ") for line in rendered.splitlines() if line.startswith("### ")
    ]
    expected = [BREAKING_SECTION, *(title for _, title in SECTIONS)]
    assert headings == expected, (
        f"a release body rendered its sections as {headings}, and a release publishes {expected}. Either "
        f"a section moved, or an ordering prefix is no longer being stripped and is now visible to every "
        f"reader. Rendered:\n{rendered}"
    )
    assert "Not published" not in rendered, (
        f"a skipped type reached the notes, so a commit a consumer cannot observe is being published as "
        f"a change. Rendered:\n{rendered}"
    )


def test_an_item_without_a_pull_request_number_carries_its_commit_id(tmp_path: Path) -> None:
    plant(tmp_path)
    rendered = render(tmp_path)
    short = short_id(tmp_path, NO_NUMBER)
    assert f"- Subject with no number ({short})" in rendered, (
        f"an item whose subject carries no `(#N)` rendered without its commit id, so it references "
        f"nothing and no reader can find the change it describes. Expected `({short})`. "
        f"Rendered:\n{rendered}"
    )
    assert "- A numbered subject (#12)\n" in rendered, (
        f"an item that already carries `(#12)` was given a second reference as well, so every such line "
        f"now ends in two. Rendered:\n{rendered}"
    )


def test_a_breaking_change_leads_the_body_and_stays_in_its_own_section(tmp_path: Path) -> None:
    plant(tmp_path)
    rendered = render(tmp_path)
    assert f"{BREAKING_ITEM} — {BREAKING_DESCRIPTION}\n" in rendered, (
        f"a breaking change rendered without the first paragraph of its `BREAKING CHANGE:` footer on one "
        f"line, so the body names the change and not what a consumer has to do about it. Expected "
        f"`{BREAKING_DESCRIPTION}`. Rendered:\n{rendered}"
    )
    assert rendered.count(BREAKING_ITEM) == 2, (
        f"a breaking change is published twice — in the block that leads the body, and in "
        f"{SECTIONS[0][1]}, where a reader looks for what the release changed. It rendered "
        f"{rendered.count(BREAKING_ITEM)} times. Rendered:\n{rendered}"
    )


def test_a_ref_pin_in_a_subject_mentions_nobody(tmp_path: Path) -> None:
    plant(tmp_path)
    rendered = render(tmp_path)
    assert "- Repin every call site to `@v5` (#20)" in rendered, (
        f"a ref pin rendered as a bare `@v5`, which GitHub resolves to whoever holds that login: it "
        f"credits them as a contributor on the release and notifies them, and a published release "
        f"cannot be withdrawn. Rendered:\n{rendered}"
    )
    assert "t@t.example" in rendered and "`@t.example`" not in rendered, (
        f"the mention pattern is not anchored on a preceding space or bracket, so it broke an address "
        f"mid-word instead of neutralizing a mention. Rendered:\n{rendered}"
    )
