import re

from capabilities import is_call_only, job_names, load, workflow_paths

# Half of the identifier a consumer types into a ruleset as a required check. Lowercase, digits and
# hyphens; never leading, trailing or doubled hyphens, which are the shapes a consumer would have to
# copy exactly and nobody would notice were deliberate.
KEBAB = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

# A workflow reachable only by a call never has a run of its own, so its entry in the Actions sidebar
# is permanently empty. The marker is what lets a reader tell that from a workflow that is broken.
CALL_ONLY = "🧩"
SELF_TRIGGERING = "🌜"


def expected_name(path: str, call_only: bool) -> str:
    return f"{CALL_ONLY if call_only else SELF_TRIGGERING} {path}"


def test_every_job_name_is_lowercase_kebab_case() -> None:
    checked = 0
    wrong: list[str] = []
    for path in workflow_paths():
        for job_id, name in job_names(load(path)).items():
            checked += 1
            if not KEBAB.match(name):
                wrong.append(f"{path.stem}: job {job_id} is named {name!r}")
    assert checked, "no jobs were read, so this gate holds no name at all"
    assert wrong == [], (
        f"job names not in lowercase-kebab-case: {wrong}. A job name is the second half of the context "
        "a consumer requires in its ruleset, so every oddity is one every consumer has to copy exactly — "
        "and tidying it later retires a required check in every one of them at once"
    )


def test_every_workflow_name_is_its_marker_and_its_filename() -> None:
    found = workflow_paths()
    assert found, "no workflows were read, so this gate holds no name at all"
    wrong: list[str] = []
    for path in found:
        doc = load(path)
        wanted = expected_name(path.stem, is_call_only(doc))
        actual = str(doc.get("name", ""))
        if actual != wanted:
            wrong.append(f"{path.name} is named {actual!r}, expected {wanted!r}")
    assert wrong == [], (
        f"workflow names not written as their marker and their filename stem: {wrong}. {CALL_ONLY} is a "
        f"workflow reachable only by a call, whose sidebar entry is always empty; {SELF_TRIGGERING} has "
        "triggers of its own and a run history. Without the distinction a reader cannot tell an empty "
        "entry from a broken one"
    )


def test_the_kebab_matcher_refuses_the_shapes_a_consumer_would_have_to_copy() -> None:
    # Pre-flight the matcher, or a rename reports green over a context nobody can type from memory.
    assert KEBAB.match("pr-title")
    assert KEBAB.match("project-ci")
    assert KEBAB.match("ci")
    assert not KEBAB.match("Python_CI")
    assert not KEBAB.match("pr title")
    assert not KEBAB.match("-leading")
    assert not KEBAB.match("trailing-")
    assert not KEBAB.match("double--hyphen")


def test_the_expected_name_follows_the_trigger_set_rather_than_a_list() -> None:
    # A workflow gaining a trigger changes marker on its own. Held here so the day it happens the gate
    # names the new expectation instead of a maintainer having to remember a table.
    assert is_call_only({"on": {"workflow_call": None}})
    assert not is_call_only({"on": {"workflow_call": None, "pull_request": None}})
    assert expected_name("project-ci", True) == f"{CALL_ONLY} project-ci"
    assert expected_name("ci", False) == f"{SELF_TRIGGERING} ci"
