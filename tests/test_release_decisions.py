import ast
import json
import sys

import pytest
from decisions import (
    SURFACE_EXCLUDE,
    SURFACE_INCLUDE,
    breaks_under_non_major,
    declared_version,
    highest_version,
    increment_reason,
    is_ahead,
    next_version,
    notes_are_empty,
    parse_version,
    release_verdict,
    surface_args,
    verdicts,
)

from test_action_pins import OWN_CI, REPO_ROOT

MODULE = REPO_ROOT / "actions" / "release-decisions" / "decisions.py"


def _context(*commits: dict[str, object]) -> str:
    # git-cliff's `--context` shape: a list of releases, each carrying its commits. Built here rather
    # than captured from a real render, so the absent-key case below can be expressed at all.
    return json.dumps([{"version": None, "commits": list(commits)}])


@pytest.mark.parametrize(
    ("breaking", "feature", "expected"),
    [
        (True, False, (5, 0, 0)),
        (False, True, (4, 1, 0)),
        (False, False, (4, 0, 4)),
        (True, True, (5, 0, 0)),
    ],
)
def test_the_increment_zeroes_every_component_below_it(
    breaking: bool, feature: bool, expected: tuple[int, int, int]
) -> None:
    # The last row is the one worth having: breaking outranks feature, so a range carrying both is a
    # major. Reversed, a breaking change would ship under a minor and move the major tag onto it.
    assert next_version((4, 0, 3), breaking=breaking, feature=feature) == expected


def test_each_increment_carries_a_different_reason() -> None:
    reasons = {
        increment_reason(breaking=True, feature=False),
        increment_reason(breaking=False, feature=True),
        increment_reason(breaking=False, feature=False),
    }
    assert len(reasons) == 3, (
        f"two increments share a reason string, so the notice a maintainer reads cannot tell them "
        f"apart: {sorted(reasons)}"
    )
    assert increment_reason(breaking=True, feature=True) == increment_reason(
        breaking=True, feature=False
    ), "a range with both verdicts is reported as a feature, not as the breaking change it is"


def test_an_empty_render_is_one_byte_of_whitespace_not_zero() -> None:
    # git-cliff emits a trailing newline for a range holding nothing and for one holding only a
    # `bump`, so a size test calls both non-empty and publishes a blank release body.
    assert notes_are_empty("\n") is True
    assert notes_are_empty("") is True
    assert notes_are_empty("  \n\t\n") is True


def test_a_body_with_any_word_at_all_is_not_empty() -> None:
    assert notes_are_empty("### 🐛 Fixes\n\n- something\n") is False
    assert notes_are_empty("\n\n-\n") is False


def test_an_absent_breaking_key_reads_as_no_breaking_change() -> None:
    # `--context` omits `breaking` entirely on a commit matching no Conventional Commit. A truthiness
    # test on the missing value answers wrongly, which is the second defect #61 names.
    assert verdicts(_context({"raw_message": "not a conventional commit"})) == (False, False)


def test_the_breaking_key_is_read_as_identity_against_true() -> None:
    truthy = _context({"raw_message": "fix: a subject", "breaking": "false"})
    assert verdicts(truthy) == (False, False), (
        "a `breaking` value that is merely truthy was read as a breaking change; git-cliff sets the "
        "key to a boolean, so anything else is not one"
    )
    assert verdicts(_context({"raw_message": "fix: a subject", "breaking": True})) == (True, False)


def test_a_feature_verdict_reads_the_raw_message() -> None:
    assert verdicts(_context({"raw_message": "feat: a subject"})) == (False, True)
    assert verdicts(_context({"raw_message": "feat(scope)!: a subject", "breaking": True})) == (
        True,
        True,
    )
    assert verdicts(_context({"raw_message": "a feat mentioned mid-subject"})) == (False, False)


def test_an_empty_range_carries_neither_verdict() -> None:
    assert verdicts(_context()) == (False, False)
    assert verdicts("[]") == (False, False)


@pytest.mark.parametrize("rejected", ["4.0", "v4.0.3", "4.0.3rc1", "4.0.3+1", "", "4.0.3.1"])
def test_only_a_plain_three_part_version_parses(rejected: str) -> None:
    # The `v` belongs to the tag, not to the version, and a pre-release or build suffix is a form
    # this repository never releases. `None` rather than an exception, so the caller owns the message.
    assert parse_version(rejected) is None
    assert parse_version("4.0.3") == (4, 0, 3)


def test_the_highest_version_orders_component_wise_across_every_major() -> None:
    # `sort -V` is what the shell used; a tuple comparison is what cannot regress to lexicographic,
    # where 4.9.0 outranks 4.10.0.
    assert highest_version(["refs/tags/v4.9.0", "refs/tags/v4.10.0"]) == (4, 10, 0)
    assert highest_version(["refs/tags/v3.9.9", "refs/tags/v4.0.0"]) == (4, 0, 0)
    # A frozen major is never backported, so the comparison spans majors rather than staying inside
    # the declared one.
    assert highest_version(["refs/tags/v5.0.0", "refs/tags/v4.0.3"]) == (5, 0, 0)


def test_tags_that_are_not_versions_are_discarded() -> None:
    assert highest_version(["refs/tags/v4", "refs/tags/v4.0", "refs/tags/v4.0.3"]) == (4, 0, 3)
    assert highest_version(["refs/tags/v4", "refs/tags/nightly"]) is None


def test_nothing_released_yet_permits_the_release() -> None:
    assert highest_version([]) is None
    assert is_ahead((0, 1, 0), None) is True


def test_a_version_must_be_strictly_ahead() -> None:
    assert is_ahead((4, 0, 4), (4, 0, 3)) is True
    assert is_ahead((4, 0, 3), (4, 0, 3)) is False
    assert is_ahead((4, 0, 2), (4, 0, 3)) is False


def test_a_breaking_range_under_the_same_major_would_move_a_tag_onto_it() -> None:
    assert breaks_under_non_major((4, 1, 0), 4, breaking=True) is True


def test_a_new_major_may_break_the_surface() -> None:
    assert breaks_under_non_major((5, 0, 0), 4, breaking=True) is False


def test_with_nothing_released_there_is_no_tag_to_move_onto_a_broken_contract() -> None:
    assert breaks_under_non_major((4, 1, 0), None, breaking=True) is False


@pytest.mark.parametrize("highest_major", [None, 3, 4, 5])
def test_a_non_breaking_range_never_refuses(highest_major: int | None) -> None:
    assert breaks_under_non_major((4, 1, 0), highest_major, breaking=False) is False


def test_the_declared_version_comes_from_the_project_table() -> None:
    # Keyed by table, never by the first `version = ` line: this is a one-shot write path, and a
    # positional match takes the version from whichever table happens to come first.
    raw = b'[tool.something]\nversion = "9.9.9"\n\n[project]\nversion = "4.0.3"\n'
    assert declared_version(raw) == "4.0.3"


def test_a_pyproject_with_no_project_version_raises_rather_than_guessing() -> None:
    with pytest.raises(KeyError):
        declared_version(b'[tool.something]\nversion = "9.9.9"\n')


def test_a_push_that_cuts_nothing_is_a_notice_and_stops() -> None:
    # ci.yml calls release after *every* merge and most merges are not releases, so an error here
    # would redden main for doing nothing wrong.
    verdict = release_verdict(
        version="4.0.3", highest="4.0.3", ahead=False, event_name="push", dry_run=False
    )
    assert (verdict.proceed, verdict.severity) == (False, "notice")
    assert "4.0.3" in verdict.message


def test_a_dry_run_reports_the_refusal_and_carries_on() -> None:
    # On a branch the declared version *is* the released one by definition, so refusing would stop
    # every dry run before it rendered anything.
    verdict = release_verdict(
        version="4.0.3",
        highest="4.0.3",
        ahead=False,
        event_name="workflow_dispatch",
        dry_run=True,
    )
    assert (verdict.proceed, verdict.severity) == (True, "notice")
    assert "would refuse" in verdict.message


def test_a_real_dispatch_that_cuts_nothing_is_an_error() -> None:
    verdict = release_verdict(
        version="4.0.3",
        highest="4.0.3",
        ahead=False,
        event_name="workflow_dispatch",
        dry_run=False,
    )
    assert (verdict.proceed, verdict.severity) == (False, "error")
    assert "4.0.3" in verdict.message


@pytest.mark.parametrize("event_name", ["push", "workflow_dispatch"])
@pytest.mark.parametrize("dry_run", [True, False])
def test_a_version_that_is_ahead_proceeds_whoever_asked(event_name: str, dry_run: bool) -> None:
    verdict = release_verdict(
        version="4.0.4", highest="4.0.3", ahead=True, event_name=event_name, dry_run=dry_run
    )
    assert verdict.proceed is True
    assert verdict.severity == "notice"


def test_the_surface_exclusions_are_own_ci_as_workflow_paths() -> None:
    assert set(SURFACE_EXCLUDE) == {f".github/workflows/{name}" for name in OWN_CI}, (
        f"decisions.py excludes {sorted(SURFACE_EXCLUDE)} from the consumer surface, but OWN_CI in "
        f"test_action_pins.py is {sorted(OWN_CI)}. A workflow in one list and not the other either "
        f"proposes a minor for a change nothing resolves, or refuses a release over a file nobody "
        f"reads."
    )


def test_the_surface_arguments_pair_every_path_with_its_flag() -> None:
    args = surface_args()
    assert args == [
        *(arg for path in SURFACE_INCLUDE for arg in ("--include-path", path)),
        *(arg for path in SURFACE_EXCLUDE for arg in ("--exclude-path", path)),
    ]
    assert not [arg for arg in args if " " in arg], (
        f"a surface argument contains a space, so the single line the workflows read it back from "
        f"splits it in two: {args}"
    )


def test_the_decisions_module_imports_only_the_standard_library() -> None:
    # This is what keeps `mise run ci` offline. A third-party import here would also have to be
    # declared twice — once for the runner, once for the suite that imports the module (FR-014).
    tree = ast.parse(MODULE.read_text())
    imported = {
        alias.name.split(".")[0]
        for node in tree.body
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        node.module.split(".")[0]
        for node in tree.body
        if isinstance(node, ast.ImportFrom)
        if node.module
    }
    assert imported <= sys.stdlib_module_names, (
        f"{MODULE.name} imports {sorted(imported - sys.stdlib_module_names)}, which is not in the "
        f"standard library. The runner resolves nothing for this module and the offline suite "
        f"imports it, so a dependency here needs declaring twice and puts the suite on the network."
    )
