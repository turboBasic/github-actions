import ast
from pathlib import Path

import pytest

from tbga import release, version
from tbga.release import (
    ALREADY_RELEASED,
    BAD_SURFACE,
    BREAKS_A_RELEASED_LINE,
    DELIBERATE,
    DRY_RUN,
    ERROR,
    MALFORMED_VERSION,
    NO_NOTES,
    NOTICE,
    OFF_DEFAULT_BRANCH,
    ROUTINE,
    UNRELEASED,
    Refusal,
    Request,
    Surface,
    compatibility_line,
    decide,
    increment,
    moving_ref,
    parse_version,
    range_verdicts,
    read_surface,
    refusals,
    surface_notice,
    touches_surface,
)

# The boundary and its readers live in `version`, so that is the module this parses.
SOURCE = Path(version.__file__).read_text(encoding="utf-8")

# A request that every refusal admits. Each test below changes exactly what it is about, so a failure
# names one cause rather than a combination.
ADMITTED = Request(
    version_text="0.2.0",
    branch="main",
    default_branch="main",
    occasion=DELIBERATE,
    existing=((0, 1, 0),),
    notes="- feat: something a consumer can see",
    breaking=False,
    feature=True,
    changed_paths=(".github/workflows/project-ci.yml",),
    surface=Surface(include=(), exclude=(), declared=True),
)


def test_a_plain_three_part_version_parses() -> None:
    assert parse_version("1.2.3") == (1, 2, 3)
    assert parse_version("0.1.0") == (0, 1, 0)
    assert parse_version("10.20.30") == (10, 20, 30)


def test_anything_but_three_plain_numbers_is_absent_rather_than_raised() -> None:
    # The `v` belongs to the tag and not to the version, and a pre-release or build metadata would
    # make the comparison against the highest release mean something nobody here decided. Absence is
    # returned rather than raised so the caller chooses the message.
    for text in [
        "v1.2.3",
        "1.2",
        "1.2.3.4",
        "1.2.3-rc1",
        "1.2.3+build",
        "1.2.x",
        "01.2.3",
        " 1.2.3",
        "1.2.3 ",
        "",
    ]:
        assert parse_version(text) is None, text


def test_the_line_is_the_major_from_the_first_stable_version_up() -> None:
    assert compatibility_line((1, 0, 0)) == (1,)
    assert compatibility_line((1, 4, 9)) == (1,)
    assert compatibility_line((2, 0, 0)) == (2,)


def test_the_line_is_the_major_and_the_minor_below_it() -> None:
    assert compatibility_line((0, 1, 0)) == (0, 1)
    assert compatibility_line((0, 1, 7)) == (0, 1)
    assert compatibility_line((0, 2, 0)) == (0, 2)


def test_exactly_one_function_reads_the_boundary() -> None:
    # Principle I, and what principle V turns on. Below the first stable version, reading the boundary off
    # the major is wrong and permissively so: it lets a break move a ref consumers pin. The refusal, the
    # increment and the ref name all read the line instead.
    module = ast.parse(SOURCE)
    readers = sorted(
        node.name
        for node in ast.walk(module)
        if isinstance(node, ast.FunctionDef)
        and any(
            isinstance(inner, ast.Name) and inner.id == "FIRST_STABLE" for inner in ast.walk(node)
        )
    )
    assert readers == ["compatibility_line"], (
        f"{readers} read FIRST_STABLE. The boundary has one owner and everything else reads the line "
        "it returns"
    )


def test_the_moving_ref_below_the_boundary_spans_a_minor() -> None:
    assert moving_ref((0, 1, 0)) == "v0.1"
    assert moving_ref((0, 1, 9)) == "v0.1"
    assert moving_ref((0, 2, 0)) == "v0.2"


def test_the_moving_ref_above_the_boundary_spans_a_major() -> None:
    assert moving_ref((1, 0, 0)) == "v1"
    assert moving_ref((1, 9, 9)) == "v1"
    assert moving_ref((2, 0, 0)) == "v2"


def test_the_moving_ref_is_total_and_never_bare_v_zero() -> None:
    # The ref has at least one component for every version, so an empty one is unreachable. What matters
    # is that `v0` never appears: it would span every pre-1.0 break at once, which is the one thing a
    # moving ref exists to prevent.
    for major in range(4):
        for minor in range(4):
            for patch in range(4):
                ref = moving_ref((major, minor, patch))
                assert ref.startswith("v") and len(ref) > 1, (major, minor, patch)
                assert ref != "v0", (major, minor, patch)


def test_below_the_boundary_a_break_advances_the_minor() -> None:
    assert increment((0, 1, 4), breaking=True, feature=False) == (0, 2, 0)
    assert increment((0, 1, 4), breaking=True, feature=True) == (0, 2, 0)


def test_below_the_boundary_a_feature_advances_only_the_patch() -> None:
    # A consumer pinned to v0.1 must be able to receive a feature without crossing into v0.2. So a
    # feature advances only a component the line does not own.
    assert increment((0, 1, 4), breaking=False, feature=True) == (0, 1, 5)


def test_above_the_boundary_a_break_advances_the_major_and_a_feature_the_minor() -> None:
    assert increment((1, 4, 2), breaking=True, feature=False) == (2, 0, 0)
    assert increment((1, 4, 2), breaking=True, feature=True) == (2, 0, 0)
    assert increment((1, 4, 2), breaking=False, feature=True) == (1, 5, 0)


def test_neither_a_break_nor_a_feature_advances_the_patch_on_either_side() -> None:
    assert increment((0, 1, 4), breaking=False, feature=False) == (0, 1, 5)
    assert increment((1, 4, 2), breaking=False, feature=False) == (1, 4, 3)


def keys(request: Request) -> list[str]:
    return [refusal.key for refusal in refusals(request)]


def test_a_request_every_refusal_admits_produces_none() -> None:
    assert refusals(ADMITTED) == []


def test_a_run_off_the_default_branch_is_refused_naming_both_branches() -> None:
    found = refusals(ADMITTED._replace(branch="topic"))
    assert [refusal.key for refusal in found] == [OFF_DEFAULT_BRANCH]
    assert "topic" in found[0].message and "main" in found[0].message


def test_a_version_that_does_not_parse_stops_the_ladder() -> None:
    # Nothing below the version can be decided without one, and a refusal derived from a version that
    # was never read would name a comparison nobody made.
    assert keys(ADMITTED._replace(version_text="v0.2", notes="")) == [MALFORMED_VERSION]


def test_a_version_not_ahead_of_the_highest_release_is_refused() -> None:
    assert ALREADY_RELEASED in keys(ADMITTED._replace(version_text="0.1.0", existing=((0, 1, 0),)))


def test_the_comparison_is_against_every_line_not_the_declared_one() -> None:
    # A frozen line is left where it is rather than backported, so a version behind a release on any
    # line is refused even when its own line has none.
    assert ALREADY_RELEASED in keys(ADMITTED._replace(version_text="0.3.0", existing=((1, 0, 0),)))


def test_a_range_rendering_no_notes_is_refused() -> None:
    for notes in ["", "   ", "\n\n"]:
        assert NO_NOTES in keys(ADMITTED._replace(notes=notes)), repr(notes)


def test_a_break_staying_on_a_line_that_already_has_a_release_is_refused() -> None:
    assert BREAKS_A_RELEASED_LINE in keys(
        ADMITTED._replace(version_text="0.1.5", breaking=True, existing=((0, 1, 0),))
    )


def test_a_break_that_starts_the_next_line_is_admitted() -> None:
    assert refusals(ADMITTED._replace(version_text="0.2.0", breaking=True)) == []


def test_a_break_outside_the_declared_surface_does_not_freeze_the_line() -> None:
    # The declaration narrows this refusal and nothing else.
    narrowed = ADMITTED._replace(
        version_text="0.1.5",
        breaking=True,
        surface=Surface(include=("actions",), exclude=(), declared=True),
        changed_paths=("README.md",),
    )
    assert BREAKS_A_RELEASED_LINE not in keys(narrowed)


def test_a_routine_push_declines_the_already_released_case_with_a_notice() -> None:
    # A default branch must not redden for doing nothing wrong: a merge that did not bump the version
    # is not a mistake.
    verdict = decide(ADMITTED._replace(occasion=ROUTINE, version_text="0.1.0"))
    assert verdict.proceed is False
    assert verdict.severity == NOTICE


def test_a_dry_run_proceeds_and_reports_what_it_would_have_refused() -> None:
    verdict = decide(ADMITTED._replace(occasion=DRY_RUN, branch="topic", version_text="0.1.0"))
    assert verdict.proceed is True
    assert verdict.severity == NOTICE
    assert "topic" in verdict.message and "0.1.0" in verdict.message


def test_anything_else_refuses_the_already_released_case_as_an_error() -> None:
    verdict = decide(ADMITTED._replace(occasion=DELIBERATE, version_text="0.1.0"))
    assert verdict.proceed is False
    assert verdict.severity == ERROR
    assert "0.1.0" in verdict.message


def test_a_routine_push_still_errors_on_any_other_refusal() -> None:
    # Only the already-released case is what a blameless merge looks like. An malformed version or
    # an empty range is a defect whichever event reached it.
    verdict = decide(ADMITTED._replace(occasion=ROUTINE, notes=""))
    assert verdict.proceed is False
    assert verdict.severity == ERROR


def test_a_request_every_refusal_admits_proceeds() -> None:
    assert decide(ADMITTED).proceed is True


def test_an_absent_declaration_considers_every_path_and_is_reported() -> None:
    surface = read_surface(None)
    assert isinstance(surface, Surface)
    assert surface.declared is False
    assert touches_surface(surface, ["anything/at/all.md"]) is True
    assert surface_notice(surface)


def test_a_declaration_with_both_lists_empty_considers_every_path_and_says_nothing() -> None:
    surface = read_surface({})
    assert isinstance(surface, Surface)
    assert surface.declared is True
    assert touches_surface(surface, ["anything/at/all.md"]) is True
    assert surface_notice(surface) is None


def test_a_declaration_narrows_to_what_it_declares() -> None:
    surface = read_surface(
        {"include": [".github/workflows"], "exclude": [".github/workflows/ci.yml"]}
    )
    assert isinstance(surface, Surface)
    assert touches_surface(surface, ["README.md"]) is False
    assert touches_surface(surface, [".github/workflows/project-ci.yml"]) is True
    assert touches_surface(surface, [".github/workflows/ci.yml"]) is False


def test_an_unknown_key_is_refused_rather_than_ignored() -> None:
    # A misspelled key would otherwise read as an absent one, which is the declared-but-empty state —
    # silently widening the surface to every path while looking configured.
    refused = read_surface({"includes": ["actions"]})
    assert isinstance(refused, Refusal)
    assert refused.key == BAD_SURFACE
    assert "includes" in refused.message


def test_a_non_list_value_is_refused_rather_than_coerced() -> None:
    # Iterating a string yields characters, so every letter would become a path and the filter would
    # match nothing while looking configured.
    assert isinstance(read_surface({"include": "actions"}), Refusal)
    assert isinstance(read_surface({"exclude": 3}), Refusal)


def test_a_declaration_that_is_not_a_table_is_refused() -> None:
    assert isinstance(read_surface(["actions"]), Refusal)
    assert isinstance(read_surface("actions"), Refusal)


def test_a_path_that_is_empty_or_holds_whitespace_or_begins_with_a_hyphen_is_refused() -> None:
    for path in ["", " ", "two words", "\tx", "-rf", "-"]:
        for key in ["include", "exclude"]:
            refused = read_surface({key: [path]})
            assert isinstance(refused, Refusal), (key, repr(path))


def test_a_bang_in_the_subject_is_a_break() -> None:
    assert range_verdicts(["feat!: drop an input"]) == (True, True)
    assert range_verdicts(["fix(scope)!: rename a check"]) == (True, False)


def test_a_breaking_change_footer_is_a_break() -> None:
    # Reading only the subject would miss a break its author declared exactly as the grammar says to.
    assert range_verdicts(["fix: a thing\n\nBREAKING CHANGE: a check was renamed"]) == (True, False)
    assert range_verdicts(["fix: a thing\n\nBREAKING-CHANGE: a check was renamed"]) == (True, False)


def test_a_feature_is_read_from_the_type_alone() -> None:
    assert range_verdicts(["feat: add an input"]) == (False, True)
    assert range_verdicts(["feat(ci): add an input"]) == (False, True)


def test_neither_verdict_is_reached_by_a_range_holding_neither() -> None:
    assert range_verdicts(["docs: reword a section", "chore: bump a pin"]) == (False, False)
    assert range_verdicts([]) == (False, False)


def test_one_break_anywhere_in_the_range_counts() -> None:
    assert range_verdicts(["docs: reword", "refactor!: move a call site"]) == (True, False)


def test_a_routine_push_declines_quietly_even_when_the_range_breaks_something() -> None:
    # The version is behind, so it has not been bumped yet; a break "on a released line" only restates
    # that. Reddening the default branch here trains people to ignore a red default branch.
    verdict = decide(
        ADMITTED._replace(
            occasion=ROUTINE, version_text="0.1.0", existing=((0, 1, 0),), breaking=True
        )
    )
    assert verdict.proceed is False
    assert verdict.severity == NOTICE


def test_a_routine_push_declines_quietly_when_the_range_renders_no_notes_either() -> None:
    verdict = decide(
        ADMITTED._replace(occasion=ROUTINE, version_text="0.1.0", existing=((0, 1, 0),), notes="")
    )
    assert verdict.proceed is False
    assert verdict.severity == NOTICE


def test_a_bumped_version_that_breaks_its_own_released_line_is_an_error_on_any_occasion() -> None:
    # The one this must not swallow. 0.1.5 is ahead of 0.1.0, so somebody asserted it — and releasing it
    # would force `v0.1` across a break, which is the thing a moving ref exists to prevent.
    for occasion in (ROUTINE, DELIBERATE):
        verdict = decide(
            ADMITTED._replace(
                occasion=occasion, version_text="0.1.5", existing=((0, 1, 0),), breaking=True
            )
        )
        assert verdict.proceed is False, occasion
        assert verdict.severity == ERROR, occasion


def test_the_unreleased_version_is_not_ahead_of_itself() -> None:
    # What makes 0.0.0 mean "not released yet": with no releases the baseline is itself, so it is
    # refused, and a routine merge declines quietly for as long as the manifest stands there.
    behind = ADMITTED._replace(version_text="0.0.0", existing=())
    assert [r.key for r in refusals(behind)] == [ALREADY_RELEASED]
    assert "unreleased" in refusals(behind)[0].message
    verdict = decide(behind._replace(occasion=ROUTINE))
    assert verdict.proceed is False
    assert verdict.severity == NOTICE


def test_asking_deliberately_to_release_the_unreleased_version_is_an_error() -> None:
    verdict = decide(ADMITTED._replace(version_text="0.0.0", existing=(), occasion=DELIBERATE))
    assert verdict.proceed is False
    assert verdict.severity == ERROR


def test_any_version_ahead_of_the_baseline_is_admitted_with_no_releases() -> None:
    for text in ("0.0.1", "0.1.0", "1.0.0"):
        assert refusals(ADMITTED._replace(version_text=text, existing=())) == [], text


def test_the_baseline_is_the_lowest_version_there_is() -> None:
    # Nothing can sit below it, so no version is unreachable by a bump.
    assert UNRELEASED == (0, 0, 0)
    assert parse_version("0.0.0") == UNRELEASED


def test_a_value_holding_the_delimiter_cannot_close_the_block_early(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The notes are rendered from commit messages, so a commit quoting a fixed delimiter would end the
    # block and let the rest be read as further outputs. The delimiter is random per value instead.
    output = tmp_path / "github_output"
    output.write_text("", encoding="utf-8")
    monkeypatch.setenv("GITHUB_OUTPUT", str(output))

    hostile = "delimiter0\nproceed=true\nref=__RELEASE_DECISIONS__"
    release.emit(message=hostile, proceed="false")

    written = output.read_text(encoding="utf-8")
    assert hostile in written
    opening = written.split("\n", 1)[0]
    assert opening.startswith("message<<")
    delimiter = opening.removeprefix("message<<")
    assert delimiter not in hostile


def test_the_trailer_is_found_under_a_commit_carrying_none_of_its_own() -> None:
    # A person's edit becomes the branch's newest commit and carries no trailer of its own — the
    # trailer being sought sits on the workflow's own commit underneath it.
    messages = (
        "chore: edit the version by hand\n",
        "chore: propose 0.2.0\n\nComputed-Version: 0.2.0\n",
    )
    assert release.find_last_computed(messages) == "0.2.0"


def test_the_newest_trailer_wins_over_an_older_one() -> None:
    messages = (
        "chore: propose 0.3.0\n\nComputed-Version: 0.3.0\n",
        "chore: propose 0.2.0\n\nComputed-Version: 0.2.0\n",
    )
    assert release.find_last_computed(messages) == "0.3.0"


def test_no_trailer_anywhere_is_empty() -> None:
    assert release.find_last_computed(("chore: propose 0.2.0\n",)) == ""


def test_a_branch_matching_the_last_computation_is_not_an_override() -> None:
    version, overridden = release.settle_proposal_version(
        computed="0.2.0", on_branch="0.2.0", last_computed="0.2.0"
    )
    assert (version, overridden) == ("0.2.0", False)


def test_a_branch_disagreeing_with_the_last_computation_is_kept() -> None:
    # The branch carries 0.3.0, this workflow last computed 0.2.0 — the difference is a person's edit,
    # and it survives even though the fresh computation has since moved on to 0.2.1.
    version, overridden = release.settle_proposal_version(
        computed="0.2.1", on_branch="0.3.0", last_computed="0.2.0"
    )
    assert (version, overridden) == ("0.3.0", True)


def test_a_branch_with_no_stored_computation_is_not_an_override() -> None:
    # A branch this workflow never wrote a trailer to has nothing to compare against. Treating that
    # absence as a difference would freeze the branch's content forever on the next run.
    version, overridden = release.settle_proposal_version(
        computed="0.1.1", on_branch="0.2.0", last_computed=""
    )
    assert (version, overridden) == ("0.1.1", False)


def test_no_branch_yet_is_not_an_override() -> None:
    version, overridden = release.settle_proposal_version(
        computed="0.1.1", on_branch="", last_computed=""
    )
    assert (version, overridden) == ("0.1.1", False)


def test_a_malformed_on_branch_version_is_not_trusted() -> None:
    version, overridden = release.settle_proposal_version(
        computed="0.1.1", on_branch="not-a-version", last_computed="0.1.0"
    )
    assert (version, overridden) == ("0.1.1", False)
