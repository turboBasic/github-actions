import subprocess
from collections.abc import Callable, Sequence

# Every call assembled here, invoked through one function a test can replace. `gh` stays the transport:
# it holds the auth, the retries and the pagination, and none of that is worth reimplementing to tidy a
# call site. What was missing was anywhere to assert the calls, since a `run:` block has none.
Runner = Callable[[Sequence[str]], str]

# A sha as the API returns one. Checked because a tree naming a value that is not a sha names nothing,
# and the failure would arrive as a ref pointing at rubbish rather than as an error.
SHA_LENGTH = 40


def gh(argv: Sequence[str]) -> str:
    # No shell, and every value its own argument. A version, a ref and a commit subject are all text
    # chosen outside this repository, and a string handed to a shell is what makes any of them a command.
    finished = subprocess.run(argv, capture_output=True, text=True, check=False)
    if finished.returncode != 0:
        raise RuntimeError(
            f"{' '.join(argv)} exited {finished.returncode}: {finished.stderr.strip()}"
        )
    return finished.stdout


def checked_sha(value: str, what: str) -> str:
    sha = value.strip()
    if len(sha) != SHA_LENGTH or not all(character in "0123456789abcdef" for character in sha):
        raise RuntimeError(f"{what} came back as {sha!r} rather than a sha, so nothing was created")
    return sha


def create_tag(run: Runner, repository: str, version: str, commit: str) -> str:
    # An annotated tag object, then the ref that names it. This is the ref a consumer may pin exactly, so
    # it is created once and never force-updated.
    tag = checked_sha(
        run(
            (
                "gh",
                "api",
                f"repos/{repository}/git/tags",
                "-f",
                f"tag=v{version}",
                "-f",
                f"message=v{version}",
                "-f",
                f"object={commit}",
                "-f",
                "type=commit",
                "--jq",
                ".sha",
            )
        ),
        "the tag object",
    )
    run(
        (
            "gh",
            "api",
            f"repos/{repository}/git/refs",
            "-f",
            f"ref=refs/tags/v{version}",
            "-f",
            f"sha={tag}",
        )
    )
    return tag


def publish_release(run: Runner, version: str, notes: str) -> None:
    run(
        (
            "gh",
            "release",
            "create",
            f"v{version}",
            "--title",
            f"v{version}",
            "--notes-file",
            notes,
            # The tag has to exist already. Without this `gh` would create one of its own, lightweight
            # and pointing wherever the default branch happens to be.
            "--verify-tag",
        )
    )


def move_ref(run: Runner, repository: str, ref: str, commit: str) -> None:
    # Force-moved where it exists, created where it does not. The first release of a line has no ref to
    # move, and every release after it must not create a second one.
    try:
        run(
            (
                "gh",
                "api",
                "-X",
                "PATCH",
                f"repos/{repository}/git/refs/tags/{ref}",
                "-F",
                "force=true",
                "-f",
                f"sha={commit}",
            )
        )
    except RuntimeError:
        run(
            (
                "gh",
                "api",
                f"repos/{repository}/git/refs",
                "-f",
                f"ref=refs/tags/{ref}",
                "-f",
                f"sha={commit}",
            )
        )
