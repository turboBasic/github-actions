from . import ERROR, annotate, github, read_text

CREATE_TAG = "create-tag"
PUBLISH_RELEASE = "publish-release"
MOVE_REF = "move-ref"
WRITES = (CREATE_TAG, PUBLISH_RELEASE, MOVE_REF)


def run(write: str) -> int:
    repository = read_text("GH_REPO").strip()
    version = read_text("VERSION").strip()
    commit = read_text("COMMIT").strip()
    ref = read_text("MOVING_REF").strip()
    notes = read_text("NOTES").strip()

    missing = [
        name
        for name, value in (
            ("GH_REPO", repository),
            ("VERSION", version if write != MOVE_REF else "-"),
            ("COMMIT", commit if write != PUBLISH_RELEASE else "-"),
            ("MOVING_REF", ref if write == MOVE_REF else "-"),
            ("NOTES", notes if write == PUBLISH_RELEASE else "-"),
        )
        if not value
    ]
    if missing:
        # A write that ran with an empty value would name a ref after nothing, and a created ref cannot be
        # withdrawn. Refused before the first call rather than after it.
        annotate(ERROR, f"{write} was given no {', '.join(missing)}, so nothing was created")
        return 1

    try:
        if write == CREATE_TAG:
            github.create_tag(github.gh, repository, version, commit)
        elif write == PUBLISH_RELEASE:
            github.publish_release(github.gh, version, notes)
        else:
            github.move_ref(github.gh, repository, ref, commit)
    except RuntimeError as failure:
        annotate(ERROR, str(failure))
        return 1
    return 0
