import subprocess
from pathlib import Path

import pytest

from tbga import repository

# A real repository, not a fake runner. `git` is local, so this stays offline, and a fake would only
# assert the argv this file already chose — the thing worth holding is what git actually reports for a
# range, which is what the refusals read.
AUTHOR = {
    "GIT_AUTHOR_NAME": "t",
    "GIT_AUTHOR_EMAIL": "t@example.com",
    "GIT_COMMITTER_NAME": "t",
    "GIT_COMMITTER_EMAIL": "t@example.com",
}


def git(where: Path, *arguments: str) -> None:
    subprocess.run(
        ("git", *arguments), cwd=where, check=True, capture_output=True, text=True, env=None
    )


def commit(where: Path, subject: str, *, touching: str = "file.txt") -> None:
    (where / touching).write_text(subject, encoding="utf-8")
    git(where, "add", touching)
    git(
        where,
        "-c",
        f"user.name={AUTHOR['GIT_AUTHOR_NAME']}",
        "-c",
        "user.email=t@example.com",
        "commit",
        "-m",
        subject,
    )


@pytest.fixture
def tree(tmp_path: Path) -> Path:
    git(tmp_path, "init", "--initial-branch=main")
    commit(tmp_path, "feat: the first thing")
    return tmp_path


def test_a_repository_with_no_release_reads_its_whole_history(tree: Path) -> None:
    assert repository.release_tags(tree.as_posix()) == ()
    assert repository.span(tree.as_posix()) == ("HEAD",)
    assert repository.commit_messages(tree.as_posix()) == ("feat: the first thing",)


def test_the_range_starts_at_the_newest_release_tag(tree: Path) -> None:
    git(tree, "tag", "v0.1.0")
    commit(tree, "fix: the second thing")
    git(tree, "tag", "v0.1.1")
    commit(tree, "feat: the third thing", touching="other.txt")

    assert repository.release_tags(tree.as_posix())[0] == "v0.1.1"
    assert repository.span(tree.as_posix()) == ("v0.1.1..HEAD",)
    # Only what the newest release does not already cover.
    assert repository.commit_messages(tree.as_posix()) == ("feat: the third thing",)
    assert repository.changed_paths(tree.as_posix()) == ("other.txt",)


def test_a_moving_compatibility_ref_is_not_read_as_a_release(tree: Path) -> None:
    # `v0.1` is a tag this scheme moves, so a range starting at it would begin at whatever it points to
    # now rather than at the last release — and every version comparison would read it as a release.
    git(tree, "tag", "v0.1.0")
    git(tree, "tag", "v0.1")
    git(tree, "tag", "nightly")
    assert repository.release_tags(tree.as_posix()) == ("v0.1.0",)


def test_release_tags_are_newest_first_by_version_not_by_string(tree: Path) -> None:
    # Sorted as strings, v0.10.0 sorts below v0.9.0, so the range would start at the wrong release.
    for tag in ("v0.9.0", "v0.10.0", "v0.2.0"):
        git(tree, "tag", tag)
    assert repository.release_tags(tree.as_posix())[0] == "v0.10.0"


def test_a_message_holding_a_blank_line_survives_as_one_record(tree: Path) -> None:
    # Records are separated by an ASCII record separator rather than by lines, because a body is part of
    # the message the break check reads.
    commit(tree, "feat!: a break\n\nBREAKING CHANGE: the interface moved", touching="broken.txt")
    messages = repository.commit_messages(tree.as_posix())
    assert any("BREAKING CHANGE: the interface moved" in message for message in messages)


def test_the_declared_version_comes_from_the_repository_being_read(tree: Path) -> None:
    (tree / "pyproject.toml").write_text('[project]\nversion = "1.2.3"\n', encoding="utf-8")
    assert repository.declared_version(tree.as_posix(), "pyproject.toml") == "1.2.3"


def test_a_manifest_declaring_no_project_reads_as_no_version(tree: Path) -> None:
    (tree / "pyproject.toml").write_text("[tool.ruff]\nline-length = 100\n", encoding="utf-8")
    assert repository.declared_version(tree.as_posix(), "pyproject.toml") == ""


def test_a_failing_command_names_itself_and_what_it_printed(tmp_path: Path) -> None:
    # Not a git repository, so `git log` fails. An exit code alone would leave a maintainer guessing.
    with pytest.raises(RuntimeError) as raised:
        repository.git(tmp_path.as_posix(), "log")
    assert "git log" in str(raised.value)
    assert "128" in str(raised.value)
