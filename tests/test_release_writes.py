from collections.abc import Sequence

import pytest

from tbga import github

# A recording runner. `gh` stays the transport in production — it holds the auth, the retries and the
# pagination — so what is worth asserting is the argv assembled for it, which a `run:` block gave nowhere
# to check. Every value below is one the API would reject or misplace if it were quoted wrongly.
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
        # The endpoint or subcommand of each call, in order. The endpoint is found by shape rather than by
        # position, because `-X PATCH` sits between `api` and the path it applies to.
        return [
            next(
                (argument for argument in call if argument.startswith("repos/")),
                " ".join(call[1:3]),
            )
            for call in self.calls
        ]


def test_the_tag_object_is_created_before_the_ref_that_names_it() -> None:
    # A ref naming a tag object that does not exist yet is a ref pointing at nothing, and neither can be
    # withdrawn once pushed.
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
    # The failure this guards: a tree or tag naming a value that is not a sha names nothing, and the
    # symptom arrives as a ref pointing at rubbish rather than as an error.
    runner = Recorder(replies=["not a sha"])
    with pytest.raises(RuntimeError) as raised:
        github.create_tag(runner, "owner/repo", "1.2.3", OTHER)
    assert "not a sha" in str(raised.value)
    assert len(runner.calls) == 1, "the ref was written after the tag object came back unusable"


def test_the_release_verifies_the_tag_rather_than_creating_one() -> None:
    # Without --verify-tag, gh creates a tag of its own: lightweight, and pointing wherever the default
    # branch happens to be rather than at the commit the annotated tag names.
    runner = Recorder()
    github.publish_release(runner, "1.2.3", "/tmp/notes.md")
    assert runner.paths() == ["release create"]
    assert "--verify-tag" in runner.calls[0]
    assert "--notes-file" in runner.calls[0] and "/tmp/notes.md" in runner.calls[0]


def test_the_moving_ref_is_forced_and_falls_back_to_creating_it() -> None:
    # The first release of a line has no ref to move; every release after it must not create a second.
    moved = Recorder()
    github.move_ref(moved, "owner/repo", "v1", SHA)
    assert moved.paths() == ["repos/owner/repo/git/refs/tags/v1"]
    assert "PATCH" in moved.calls[0] and "force=true" in moved.calls[0]

    created = Recorder(failing=1)
    github.move_ref(created, "owner/repo", "v1", SHA)
    assert created.paths() == ["repos/owner/repo/git/refs/tags/v1", "repos/owner/repo/git/refs"]
    assert "ref=refs/tags/v1" in created.calls[1]


def test_no_assembled_call_reaches_a_shell() -> None:
    # Principle VI at the Python boundary: a version and a ref are text chosen outside this repository,
    # and each has to be its own argument. A single string would be the shape that makes one a command.
    runner = Recorder(replies=[SHA])
    github.create_tag(runner, "owner/repo", "1.2.3", OTHER)
    github.publish_release(runner, "1.2.3", "/tmp/notes.md")
    github.move_ref(runner, "owner/repo", "v1", SHA)
    for call in runner.calls:
        assert call[0] == "gh"
        assert all(isinstance(argument, str) for argument in call)
        assert not any(character in argument for argument in call for character in ";|&$`")
