from pathlib import Path
from typing import Any

import pytest

from tbga.rulesets import (
    CREATE,
    NOTHING,
    REFUSE,
    UPDATE,
    Doc,
    decide,
    emit,
    normalize,
    render_difference,
    shape_problem,
)

# A ruleset that admits every check below. Each test changes exactly what it is about.
COMMITTED: Doc = {
    "name": "protect-default-branch",
    "target": "branch",
    "enforcement": "active",
    "conditions": {"ref_name": {"include": ["~DEFAULT_BRANCH"], "exclude": []}},
    "rules": [
        {"type": "deletion"},
        {
            "type": "required_status_checks",
            "parameters": {"required_status_checks": [{"context": "python / project-ci"}]},
        },
    ],
    "bypass_actors": [{"actor_id": 5, "actor_type": "RepositoryRole", "bypass_mode": "always"}],
}


def _detail(**overrides: Any) -> Doc:
    # What `GET /repos/{owner}/{repo}/rulesets/{id}` returns: the committed shape plus the read-only
    # fields a write rejects. `decide` is handed a list of these, never the list endpoint's summaries.
    detail: Doc = {
        **COMMITTED,
        "id": 1,
        "source_type": "Repository",
        "node_id": "n1",
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
        "_links": {"self": {"href": "..."}},
        "current_user_can_bypass": "always",
    }
    detail.update(overrides)
    return detail


def test_shape_problem_names_an_unknown_field() -> None:
    bad: Doc = {**COMMITTED, "id": 1}
    message = shape_problem(bad)
    assert message is not None
    assert "['id']" in message


def test_shape_problem_names_a_missing_field() -> None:
    bad = dict(COMMITTED)
    del bad["bypass_actors"]
    message = shape_problem(bad)
    assert message is not None
    assert "bypass_actors" in message


def test_shape_problem_names_a_target_it_does_not_manage() -> None:
    message = shape_problem({**COMMITTED, "target": "push"})
    assert message is not None
    assert "'push'" in message


def test_a_tag_ruleset_needs_no_required_status_checks_rule() -> None:
    # A tag ruleset protects the ref itself. Demanding a checks rule would refuse the only shape that
    # makes a released version immutable.
    tag_ruleset: Doc = {
        **COMMITTED,
        "target": "tag",
        "rules": [{"type": "deletion"}, {"type": "update"}],
    }
    assert shape_problem(tag_ruleset) is None


def test_shape_problem_refuses_a_ruleset_carrying_no_rules_whatever_its_target() -> None:
    for target in ("branch", "tag"):
        message = shape_problem({**COMMITTED, "target": target, "rules": []})
        assert message is not None, target
        assert "gates nothing" in message


def test_shape_problem_names_the_absent_required_status_checks_rule() -> None:
    bad = {**COMMITTED, "rules": [{"type": "deletion"}]}
    message = shape_problem(bad)
    assert message is not None
    assert "['deletion']" in message


def test_shape_problem_names_an_empty_context_list() -> None:
    bad: Doc = {
        **COMMITTED,
        "rules": [{"type": "required_status_checks", "parameters": {"required_status_checks": []}}],
    }
    message = shape_problem(bad)
    assert message is not None
    assert "empty set" in message


def test_shape_problem_is_none_for_a_well_formed_ruleset() -> None:
    assert shape_problem(COMMITTED) is None


def test_a_malformed_committed_file_refuses_before_any_live_ruleset_is_read() -> None:
    bad = {**COMMITTED, "target": "push"}
    verdict = decide(bad, [])
    assert verdict.verdict == REFUSE
    assert "push" in verdict.message


def test_no_matching_name_creates() -> None:
    verdict = decide(COMMITTED, [])
    assert verdict.verdict == CREATE
    assert verdict.body == COMMITTED


def test_a_match_whose_source_type_is_not_repository_is_not_a_match() -> None:
    verdict = decide(COMMITTED, [_detail(source_type="Organization")])
    assert verdict.verdict == CREATE


def test_a_ruleset_of_another_name_is_not_a_match() -> None:
    verdict = decide(COMMITTED, [_detail(name="something-else")])
    assert verdict.verdict == CREATE


def test_two_rulesets_sharing_the_name_refuse() -> None:
    verdict = decide(COMMITTED, [_detail(), _detail(id=2)])
    assert verdict.verdict == REFUSE
    assert "2 rulesets" in verdict.message
    assert "'1'" in verdict.message
    assert "'2'" in verdict.message


def test_a_matching_detail_reads_as_nothing_to_change() -> None:
    verdict = decide(COMMITTED, [_detail()])
    assert verdict.verdict == NOTHING
    assert verdict.ruleset_id == "1"
    assert verdict.difference == ""
    assert verdict.body is None


def test_read_only_fields_do_not_cause_a_reported_difference() -> None:
    # R4: id, node_id, created_at, updated_at, _links and current_user_can_bypass come back on a read
    # and are not settable. A byte comparison would report drift on updated_at at every dispatch.
    detail = _detail(updated_at="2099-01-01T00:00:00Z", current_user_can_bypass="never")
    assert decide(COMMITTED, [detail]).verdict == NOTHING


def test_reordered_rules_and_contexts_still_read_as_nothing_to_change() -> None:
    reordered = _detail(
        rules=[
            {
                "type": "required_status_checks",
                "parameters": {"required_status_checks": [{"context": "python / project-ci"}]},
            },
            {"type": "deletion"},
        ]
    )
    assert decide(COMMITTED, [reordered]).verdict == NOTHING


def test_a_real_difference_updates_with_the_difference_rendered_both_sides() -> None:
    verdict = decide(COMMITTED, [_detail(enforcement="evaluate")])
    assert verdict.verdict == UPDATE
    assert verdict.ruleset_id == "1"
    assert verdict.body == COMMITTED
    assert "enforcement" in verdict.difference
    assert "active" in verdict.difference
    assert "evaluate" in verdict.difference


def test_render_difference_names_both_sides_for_every_differing_field() -> None:
    difference = render_difference(normalize(COMMITTED), normalize(_detail(target="tag")))
    assert '-  "target": "tag"' in difference
    assert '+  "target": "branch"' in difference


def test_render_difference_is_empty_when_the_two_documents_agree() -> None:
    same = normalize(_detail())
    assert render_difference(same, same) == ""


def test_render_difference_keeps_a_nested_change_to_the_line_it_happened_on() -> None:
    # The failure this replaces: one changed context printed both `rules` arrays on a single line,
    # leaving the reader to diff them by eye before an irreversible write.
    live = normalize(_detail())
    committed = normalize(COMMITTED)
    difference = render_difference(committed, live)
    changed = [line for line in difference.splitlines() if line[:1] in {"-", "+"}]
    assert all(len(line) < 200 for line in changed), difference


def test_normalize_drops_everything_but_the_six_writable_fields() -> None:
    assert set(normalize(_detail())) == {
        "name",
        "target",
        "enforcement",
        "conditions",
        "rules",
        "bypass_actors",
    }


def test_a_value_holding_the_delimiter_cannot_close_the_block_early(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Every value here comes from an API response, so a ruleset named after a fixed delimiter would end
    # the block and let the rest be read as further outputs. The delimiter is random per value instead.
    output = tmp_path / "github_output"
    output.write_text("", encoding="utf-8")
    monkeypatch.setenv("GITHUB_OUTPUT", str(output))

    hostile = "delimiter0\nverdict=create\nname=__RULESET_DECISIONS__"
    emit(difference=hostile, verdict=NOTHING)

    written = output.read_text(encoding="utf-8")
    # The hostile text survives whole, and the delimiter that closes its block appears nowhere in it.
    assert hostile in written
    opening = written.split("\n", 1)[0]
    assert opening.startswith("difference<<")
    delimiter = opening.removeprefix("difference<<")
    assert delimiter not in hostile
