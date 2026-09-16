from collections.abc import Callable, Sequence

# One indirection so a test can record the argv. `gh` remains the transport — it owns the auth, the
# retries and the pagination.
Runner = Callable[[Sequence[str]], str]

SHA_LENGTH = 40


def checked_sha(value: str, what: str) -> str:
    sha = value.strip()
    if len(sha) != SHA_LENGTH or not all(character in "0123456789abcdef" for character in sha):
        raise RuntimeError(f"{what} came back as {sha!r} rather than a sha, so nothing was created")
    return sha


def create_tag(run: Runner, repository: str, version: str, commit: str) -> str:
    # Never force-updated: this is the ref a consumer pins exactly.
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
            "--verify-tag",  # or `gh` invents a lightweight tag on the default branch
        )
    )


def move_ref(run: Runner, repository: str, ref: str, commit: str) -> None:
    # The first release of a line has no ref to move.
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
