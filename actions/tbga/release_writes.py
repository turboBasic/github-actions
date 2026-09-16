from collections.abc import Callable

from . import ERROR, annotate, github, output, proposal, read_text, repository_directory

CREATE_TAG = "create-tag"
PUBLISH_RELEASE = "publish-release"
MOVE_REF = "move-ref"
WRITE_PROPOSAL = "write-proposal"
OPEN_PROPOSAL = "open-proposal"

Values = dict[str, str]


def _create_tag(values: Values) -> None:
    github.create_tag(output, values["GH_REPO"], values["VERSION"], values["COMMIT"])


def _publish_release(values: Values) -> None:
    github.publish_release(output, values["GH_REPO"], values["VERSION"], values["NOTES"])


def _move_ref(values: Values) -> None:
    github.move_ref(output, values["GH_REPO"], values["MOVING_REF"], values["COMMIT"])


def _write_proposal(values: Values) -> None:
    proposal.write_proposal(
        output,
        values["GH_REPO"],
        repository_directory(),
        values["VERSION"],
        values["COMPUTED"],
        values["COMMIT"],
        values["BRANCH"],
    )


def _open_proposal(values: Values) -> None:
    proposal.open_proposal(
        output,
        values["GH_REPO"],
        values["BRANCH"],
        values["BASE"],
        values["VERSION"],
        values["NOTES"],
    )


# Each write, what it cannot run without, and what it does. One entry per write: a table stating the
# names and a branch acting on them would be two owners, and a write missing from either reaches the
# runner as a KeyError or as a call with an empty value.
WRITES: dict[str, tuple[tuple[str, ...], Callable[[Values], None]]] = {
    CREATE_TAG: (("GH_REPO", "VERSION", "COMMIT"), _create_tag),
    PUBLISH_RELEASE: (("GH_REPO", "VERSION", "NOTES"), _publish_release),
    MOVE_REF: (("GH_REPO", "MOVING_REF", "COMMIT"), _move_ref),
    WRITE_PROPOSAL: (("GH_REPO", "VERSION", "COMPUTED", "COMMIT", "BRANCH"), _write_proposal),
    OPEN_PROPOSAL: (("GH_REPO", "BRANCH", "BASE", "VERSION", "NOTES"), _open_proposal),
}


def run(write: str) -> int:
    needed, perform = WRITES[write]
    values = {name: read_text(name).strip() for name in needed}
    missing = sorted(name for name, value in values.items() if not value)
    if missing:
        # Refused before the first call. An empty value names a ref after nothing, and a created ref stays.
        annotate(ERROR, f"{write} was given no {', '.join(missing)}, so nothing was created")
        return 1
    try:
        perform(values)
    except RuntimeError as failure:
        annotate(ERROR, str(failure))
        return 1
    return 0
