import json
import os
import tempfile

from .github import Runner, checked_sha

# One commit, both files. The lockfile records the project's version, so a manifest moved alone breaks
# `uv sync --locked` on the branch whose merge releases.
PROPOSED_FILES = ("pyproject.toml", "uv.lock")

MODE = "100644"


def blob(run: Runner, repository: str, where: str, name: str, scratch: str) -> str:
    # A file, not an argument: a lockfile exceeds the argument limit. The API takes UTF-8 unencoded.
    with open(os.path.join(where, name), encoding="utf-8") as handle:
        content = handle.read()
    body = os.path.join(scratch, f"blob-{name}.json")
    with open(body, "w", encoding="utf-8") as handle:
        json.dump({"content": content, "encoding": "utf-8"}, handle)
    returned = run(("gh", "api", f"repos/{repository}/git/blobs", "--input", body, "--jq", ".sha"))
    return checked_sha(returned, f"the blob for {name}")


def send(
    run: Runner, repository: str, endpoint: str, payload: object, scratch: str, what: str
) -> str:
    body = os.path.join(scratch, f"{what.replace(' ', '-')}.json")
    with open(body, "w", encoding="utf-8") as handle:
        json.dump(payload, handle)
    returned = run(("gh", "api", f"repos/{repository}/{endpoint}", "--input", body, "--jq", ".sha"))
    return checked_sha(returned, what)


def write_proposal(
    run: Runner, repository: str, where: str, version: str, computed: str, commit: str, branch: str
) -> str:
    # The git data API, not a push. A token in a remote URL is a secret on a command line.
    scratch = tempfile.mkdtemp()
    shas = [blob(run, repository, where, name, scratch) for name in PROPOSED_FILES]
    base = checked_sha(
        run(("gh", "api", f"repos/{repository}/git/commits/{commit}", "--jq", ".tree.sha")),
        "the base tree",
    )
    tree = send(
        run,
        repository,
        "git/trees",
        {
            "base_tree": base,
            "tree": [
                {"path": name, "mode": MODE, "type": "blob", "sha": sha}
                for name, sha in zip(PROPOSED_FILES, shas, strict=True)
            ],
        },
        scratch,
        "the tree",
    )
    # The trailer records the computed version, not the written one. A later run compares the two to
    # detect a person's edit.
    proposed = send(
        run,
        repository,
        "git/commits",
        {
            "message": f"chore: propose {version}\n\nComputed-Version: {computed}\n",
            "tree": tree,
            "parents": [commit],
        },
        scratch,
        "the proposed commit",
    )
    try:
        run(
            (
                "gh",
                "api",
                "-X",
                "PATCH",
                f"repos/{repository}/git/refs/heads/{branch}",
                "-F",
                "force=true",
                "-f",
                f"sha={proposed}",
            )
        )
    except RuntimeError:
        run(
            (
                "gh",
                "api",
                f"repos/{repository}/git/refs",
                "-f",
                f"ref=refs/heads/{branch}",
                "-f",
                f"sha={proposed}",
            )
        )
    return proposed


def open_proposal(run: Runner, branch: str, base: str, version: str, notes: str) -> None:
    scratch = tempfile.mkdtemp()
    body = os.path.join(scratch, "body.md")
    with open(notes, encoding="utf-8") as reading, open(body, "w", encoding="utf-8") as writing:
        writing.write(
            f"Merging this releases v{version}. The notes below are the ones it will publish.\n\n"
            "Editing the version in pyproject.toml on this branch overrides the computed one, and "
            "survives every refresh.\n\n"
        )
        writing.write(reading.read())
    title = f"chore: release v{version}"
    number = run(
        (
            "gh",
            "pr",
            "list",
            "--head",
            branch,
            "--state",
            "open",
            "--json",
            "number",
            "--jq",
            '.[0].number // ""',
        )
    ).strip()
    if number:
        run(("gh", "pr", "edit", number, "--title", title, "--body-file", body))
    else:
        run(
            (
                "gh",
                "pr",
                "create",
                "--head",
                branch,
                "--base",
                base,
                "--title",
                title,
                "--body-file",
                body,
            )
        )
