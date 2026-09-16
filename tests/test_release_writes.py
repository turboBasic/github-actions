import json
from collections.abc import Sequence
from pathlib import Path

import pytest

from tbga import __main__, github, proposal, release_writes

# A recording runner. `gh` remains the transport in production, so what is asserted is the argv assembled
# for it — every value below is one the API rejects or misplaces if it is quoted wrongly.
SHA = "a" * 40
OTHER = "b" * 40


class Recorder:
    def __init__(self, replies: list[str] | None = None, failing: int | None = None) -> None:
        self.calls: list[tuple[str, ...]] = []
        self.replies = replies or []
        self.failing = failing

    def __call__(self, argv: Sequence[str]) -> str:
        self.calls.append(tuple(argv))
        if self.failing is not None and len(self.calls) == self.failing:
            raise RuntimeError(f"{' '.join(argv)} exited 1: refused")
        return self.replies[len(self.calls) - 1] if len(self.replies) >= len(self.calls) else ""

    def paths(self) -> list[str]:
        # Found by shape, not position: `-X PATCH` sits between `api` and its path.
        return [
            next(
                (argument for argument in call if argument.startswith("repos/")),
                " ".join(call[1:3]),
            )
            for call in self.calls
        ]


def test_the_tag_object_is_created_before_the_ref_that_names_it() -> None:
    # A ref naming a tag object that does not exist yet points at nothing, and neither can be withdrawn.
    runner = Recorder(replies=[SHA])
    returned = github.create_tag(runner, "owner/repo", "1.2.3", OTHER)

    assert runner.paths() == ["repos/owner/repo/git/tags", "repos/owner/repo/git/refs"]
    assert returned == SHA
    assert "-f" in runner.calls[0] and "tag=v1.2.3" in runner.calls[0]
    assert "object=" + OTHER in runner.calls[0]
    assert "type=commit" in runner.calls[0]
    # The ref names the sha the first call returned, not the commit.
    assert f"sha={SHA}" in runner.calls[1]
    assert "ref=refs/tags/v1.2.3" in runner.calls[1]


def test_a_reply_that_is_not_a_sha_stops_before_the_ref_is_written() -> None:
    # A tag naming a value that is not a sha names nothing, and the symptom is a bad ref, not an error.
    runner = Recorder(replies=["not a sha"])
    with pytest.raises(RuntimeError) as raised:
        github.create_tag(runner, "owner/repo", "1.2.3", OTHER)
    assert "not a sha" in str(raised.value)
    assert len(runner.calls) == 1, "the ref was written after the tag object came back unusable"


def test_the_release_verifies_the_tag_rather_than_creating_one() -> None:
    # Without it, `gh` creates a lightweight tag on the default branch instead.
    runner = Recorder()
    github.publish_release(runner, "1.2.3", "/tmp/notes.md")
    assert runner.paths() == ["release create"]
    assert "--verify-tag" in runner.calls[0]
    assert "--notes-file" in runner.calls[0] and "/tmp/notes.md" in runner.calls[0]


def test_the_moving_ref_is_forced_and_falls_back_to_creating_it() -> None:
    # The first release of a line has no ref to move. Every release after it must not create a second.
    moved = Recorder()
    github.move_ref(moved, "owner/repo", "v1", SHA)
    assert moved.paths() == ["repos/owner/repo/git/refs/tags/v1"]
    assert "PATCH" in moved.calls[0] and "force=true" in moved.calls[0]

    created = Recorder(failing=1)
    github.move_ref(created, "owner/repo", "v1", SHA)
    assert created.paths() == ["repos/owner/repo/git/refs/tags/v1", "repos/owner/repo/git/refs"]
    assert "ref=refs/tags/v1" in created.calls[1]


def test_no_assembled_call_reaches_a_shell() -> None:
    # Principle VI at the Python boundary. A single string is the shape that makes a value a command.
    runner = Recorder(replies=[SHA])
    github.create_tag(runner, "owner/repo", "1.2.3", OTHER)
    github.publish_release(runner, "1.2.3", "/tmp/notes.md")
    github.move_ref(runner, "owner/repo", "v1", SHA)
    for call in runner.calls:
        assert call[0] == "gh"
        assert all(isinstance(argument, str) for argument in call)
        assert not any(character in argument for argument in call for character in ";|&$`")


def _proposal_tree(tmp_path: Path) -> Path:
    (tmp_path / "pyproject.toml").write_text('[project]\nversion = "0.4.0"\n', encoding="utf-8")
    (tmp_path / "uv.lock").write_text("version = 1\n", encoding="utf-8")
    return tmp_path


def test_the_proposal_commit_carries_the_manifest_and_the_lockfile_together(tmp_path: Path) -> None:
    # The lockfile records the project's version. A manifest moved alone breaks `uv sync --locked` on the
    # branch whose merge releases.
    runner = Recorder(replies=[SHA, OTHER, "c" * 40, "d" * 40, "e" * 40])
    proposal.write_proposal(
        runner,
        "owner/repo",
        _proposal_tree(tmp_path).as_posix(),
        "0.4.0",
        "0.4.0",
        "f" * 40,
        "release/next",
    )

    trees = [call for call in runner.calls if call[2].endswith("/git/trees")]
    assert len(trees) == 1, f"expected one tree call, got {runner.paths()}"
    sent = json.loads(Path(trees[0][trees[0].index("--input") + 1]).read_text(encoding="utf-8"))
    assert [entry["path"] for entry in sent["tree"]] == ["pyproject.toml", "uv.lock"]
    assert {entry["mode"] for entry in sent["tree"]} == {"100644"}
    # Each blob's sha reaches the tree entry for the file it was made from, in order.
    assert [entry["sha"] for entry in sent["tree"]] == [SHA, OTHER]


def test_the_trailer_records_what_was_computed_not_what_was_written(tmp_path: Path) -> None:
    # A later run compares the trailer against the branch's version. Recording the written one instead
    # makes every override invisible.
    runner = Recorder(replies=[SHA, OTHER, "c" * 40, "d" * 40, "e" * 40])
    proposal.write_proposal(
        runner,
        "owner/repo",
        _proposal_tree(tmp_path).as_posix(),
        "1.0.0",
        "0.4.1",
        "f" * 40,
        "release/next",
    )

    commits = [call for call in runner.calls if call[2].endswith("/git/commits")]
    sent = json.loads(Path(commits[0][commits[0].index("--input") + 1]).read_text(encoding="utf-8"))
    assert "Computed-Version: 0.4.1" in sent["message"]
    assert sent["message"].startswith("chore: propose 1.0.0")


def test_a_blob_coming_back_unusable_writes_no_tree_and_moves_no_ref(tmp_path: Path) -> None:
    # Ordering is the protection. Otherwise the branch is force-moved to a commit built on nothing.
    runner = Recorder(replies=["not a sha"])
    with pytest.raises(RuntimeError):
        proposal.write_proposal(
            runner,
            "owner/repo",
            _proposal_tree(tmp_path).as_posix(),
            "0.4.0",
            "0.4.0",
            "f" * 40,
            "release/next",
        )
    assert not any("git/trees" in call[2] for call in runner.calls)
    assert not any("refs/heads" in argument for call in runner.calls for argument in call)


def test_a_failing_tree_call_moves_no_ref(tmp_path: Path) -> None:
    runner = Recorder(replies=[SHA, OTHER, "c" * 40], failing=4)
    with pytest.raises(RuntimeError):
        proposal.write_proposal(
            runner,
            "owner/repo",
            _proposal_tree(tmp_path).as_posix(),
            "0.4.0",
            "0.4.0",
            "f" * 40,
            "release/next",
        )
    assert not any("refs/heads" in argument for call in runner.calls for argument in call)


def test_the_proposal_is_edited_where_one_is_open_and_created_where_none_is(tmp_path: Path) -> None:
    notes = tmp_path / "notes.md"
    notes.write_text("- feat: something\n", encoding="utf-8")

    existing = Recorder(replies=["7"])
    proposal.open_proposal(existing, "release/next", "main", "0.4.0", notes.as_posix())
    assert existing.calls[1][:4] == ("gh", "pr", "edit", "7")

    fresh = Recorder(replies=[""])
    proposal.open_proposal(fresh, "release/next", "main", "0.4.0", notes.as_posix())
    assert fresh.calls[1][:3] == ("gh", "pr", "create")
    # The rendered notes reach the body, and the override is spelled out in it.
    body = Path(fresh.calls[1][fresh.calls[1].index("--body-file") + 1]).read_text(encoding="utf-8")
    assert "- feat: something" in body
    assert "overrides the computed one" in body


def test_every_write_the_entry_point_offers_has_a_table_entry() -> None:
    # The command list and the table are one structure, so a write cannot reach the runner as a KeyError.
    assert set(__main__.COMMANDS) >= set(release_writes.WRITES)
    for write, (needed, perform) in release_writes.WRITES.items():
        assert needed, f"{write} states no required values, so it would run on an empty environment"
        assert callable(perform), write


def test_a_write_missing_a_value_refuses_before_the_first_call(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # An empty value names a ref after nothing, and a created ref stays. Each write is checked with one
    # of its own values blanked, so the refusal cannot be passing for an unrelated reason.
    for write, (needed, _) in release_writes.WRITES.items():
        for blanked in needed:
            for name in needed:
                monkeypatch.setenv(name, "" if name == blanked else "value")
            assert release_writes.run(write) == 1, f"{write} ran without {blanked}"
            reported = capsys.readouterr()
            assert blanked in reported.err, f"{write} did not name {blanked}"
            assert "nothing was created" in reported.err


def test_an_unknown_write_is_refused_by_the_entry_point_not_the_table(
    capsys: pytest.CaptureFixture[str],
) -> None:
    # `run` indexes the table directly, so argparse is what has to reject an unknown name. Reaching
    # `run` with one would be a KeyError, which names nothing a maintainer can act on.
    with pytest.raises(SystemExit) as raised:
        __main__.main(["not-a-write"])
    assert raised.value.code == 2
    assert "invalid choice" in capsys.readouterr().err


def test_a_failing_call_is_reported_rather_than_raised(monkeypatch: pytest.MonkeyPatch) -> None:
    # The dispatcher is the boundary: below it a failure raises, and at it the run reports and exits.
    monkeypatch.setattr(release_writes.github, "create_tag", _refuse)
    for name in ("GH_REPO", "VERSION", "COMMIT"):
        monkeypatch.setenv(name, "value")
    assert release_writes.run(release_writes.CREATE_TAG) == 1


def _refuse(*_: object) -> None:
    raise RuntimeError("the API said no")
