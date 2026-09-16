import os

from . import ERROR, annotate, github, proposal, read_text

CREATE_TAG = "create-tag"
PUBLISH_RELEASE = "publish-release"
MOVE_REF = "move-ref"
WRITE_PROPOSAL = "write-proposal"
OPEN_PROPOSAL = "open-proposal"
WRITES = (CREATE_TAG, PUBLISH_RELEASE, MOVE_REF, WRITE_PROPOSAL, OPEN_PROPOSAL)

# Checked before the first call. An empty value names a ref after nothing, and a created ref stays.
NEEDED = {
    CREATE_TAG: ("GH_REPO", "VERSION", "COMMIT"),
    PUBLISH_RELEASE: ("VERSION", "NOTES"),
    MOVE_REF: ("GH_REPO", "MOVING_REF", "COMMIT"),
    WRITE_PROPOSAL: ("GH_REPO", "VERSION", "COMPUTED", "COMMIT", "BRANCH"),
    OPEN_PROPOSAL: ("BRANCH", "BASE", "VERSION", "NOTES"),
}


def run(write: str) -> int:
    values = {name: read_text(name).strip() for name in NEEDED[write]}
    missing = sorted(name for name, value in values.items() if not value)
    if missing:
        annotate(ERROR, f"{write} was given no {', '.join(missing)}, so nothing was created")
        return 1

    where = read_text("REPO_DIR") or read_text("GITHUB_WORKSPACE") or os.getcwd()
    try:
        if write == CREATE_TAG:
            github.create_tag(github.gh, values["GH_REPO"], values["VERSION"], values["COMMIT"])
        elif write == PUBLISH_RELEASE:
            github.publish_release(github.gh, values["VERSION"], values["NOTES"])
        elif write == MOVE_REF:
            github.move_ref(github.gh, values["GH_REPO"], values["MOVING_REF"], values["COMMIT"])
        elif write == WRITE_PROPOSAL:
            proposal.write_proposal(
                github.gh,
                values["GH_REPO"],
                where,
                values["VERSION"],
                values["COMPUTED"],
                values["COMMIT"],
                values["BRANCH"],
            )
        else:
            proposal.open_proposal(
                github.gh, values["BRANCH"], values["BASE"], values["VERSION"], values["NOTES"]
            )
    except RuntimeError as failure:
        annotate(ERROR, str(failure))
        return 1
    return 0
