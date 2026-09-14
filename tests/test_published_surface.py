from typing import Any

from capabilities import (
    Doc,
    action_docs,
    action_inputs,
    blanket_permissions,
    check_names,
    declared_inputs,
    declared_secrets,
    fixture,
    is_capability,
    permission_demand,
    workflow_docs,
)

# Every field the gate reads. A row carrying anything else is refused rather than ignored: a
# misspelled field would otherwise read as an absent one, and an absent one asserts nothing.
REQUIRED = frozenset(
    {"kind", "published", "inputs", "permissions", "tool_prerequisites", "skips_under"}
)
OPTIONAL = frozenset({"check_name", "judges", "secrets"})


def tree_surface() -> dict[str, Doc]:
    surface: dict[str, Doc] = {}
    for name, doc in workflow_docs().items():
        if is_capability(doc):
            surface[name] = {
                "kind": "workflow",
                "check_name": check_names(doc),
                "inputs": sorted(declared_inputs(doc)),
                "secrets": sorted(declared_secrets(doc)),
                "permissions": permission_demand(doc),
            }
    for name, doc in action_docs().items():
        surface[name] = {
            "kind": "action",
            "inputs": sorted(action_inputs(doc)),
            "permissions": permission_demand(doc),
        }
    return surface


def paired() -> list[tuple[str, Doc, Doc]]:
    # Only capabilities present on both sides. A capability with no fixture row, or a row naming no
    # capability, is the correspondence test's failure to report — every other test here would
    # otherwise pile an opaque lookup error on top of it and bury the one message worth reading.
    committed = fixture()
    return [
        (name, committed[name], actual)
        for name, actual in tree_surface().items()
        if name in committed
    ]


def test_the_fixture_names_no_field_the_gate_does_not_read() -> None:
    for name, row in fixture().items():
        unknown = set(row) - REQUIRED - OPTIONAL
        assert unknown == set(), f"{name}: unknown field {sorted(unknown)} in the surface fixture"
        missing = REQUIRED - set(row)
        assert missing == set(), f"{name}: surface fixture omits {sorted(missing)}"


def test_every_capability_in_the_tree_is_in_the_fixture() -> None:
    tree, committed = set(tree_surface()), set(fixture())
    assert tree - committed == set(), (
        f"capability in the tree with no fixture row: {sorted(tree - committed)}. "
        "Add its row to tests/published_surface.toml in this change"
    )
    assert committed - tree == set(), (
        f"fixture row naming no capability in the tree: {sorted(committed - tree)}. "
        "Removing a capability retires a consumer's call site, so it starts a new compatibility line"
    )


def test_every_capability_is_the_kind_the_fixture_records() -> None:
    for name, committed, actual in paired():
        assert committed["kind"] == actual["kind"], (
            f"{name}: fixture records kind {committed['kind']!r}, tree has {actual['kind']!r}"
        )


def test_every_published_input_name_set_matches_the_fixture() -> None:
    for name, committed, actual in paired():
        # An unpublished capability promises nothing to anyone outside the release path, so its
        # inputs are surface only in name and are deliberately not compared.
        if not committed["published"]:
            continue
        expected: list[Any] = sorted(committed["inputs"])
        assert expected == actual["inputs"], (
            f"{name}: fixture lists inputs {expected}, tree declares {actual['inputs']}. "
            "Renaming or removing one breaks every call site that names it"
        )


def test_every_published_secret_name_set_matches_the_fixture() -> None:
    for name, committed, actual in paired():
        if actual["kind"] != "workflow" or not committed["published"]:
            continue
        # An absent row asserts the capability demands none, so no row needs an empty list.
        expected: list[Any] = sorted(committed.get("secrets") or [])
        assert expected == actual["secrets"], (
            f"{name}: fixture lists secrets {expected}, tree declares {actual['secrets']}. "
            "A required secret a caller does not pass fails the run before any job exists, with no "
            "log and no annotation to read"
        )


def test_every_permission_demand_matches_the_fixture() -> None:
    for name, committed, actual in paired():
        assert committed["permissions"] == actual["permissions"], (
            f"{name}: fixture demands {committed['permissions']}, tree demands "
            f"{actual['permissions']}. A demand a caller does not grant fails the run before any "
            "job exists, with no log and no annotation to read"
        )


def test_every_composed_check_name_matches_the_fixture() -> None:
    for name, committed, actual in paired():
        if actual["kind"] != "workflow":
            continue
        expected = sorted(committed.get("check_name") or [])
        assert expected == actual["check_name"], (
            f"{name}: fixture composes {expected}, tree composes {actual['check_name']}. "
            "A retired check name blocks every pull request in every consumer requiring it"
        )


def test_no_capability_grants_itself_every_scope() -> None:
    for name, doc in {**workflow_docs(), **action_docs()}.items():
        blanket = blanket_permissions(doc)
        assert blanket == [], (
            f"{name}: {blanket} sets permissions to a blanket value naming no scope, which the "
            "surface gate cannot compare against the fixture"
        )


def test_the_blanket_permission_reader_returns_a_block_that_names_no_scope() -> None:
    # Pre-flight the reader. Nothing in the tree sets a blanket value, which is the point, so the gate
    # above can never show that its reader would still find one.
    blanket: Doc = {"permissions": "read-all", "jobs": {"one": {"permissions": "write-all"}}}
    assert blanket_permissions(blanket) == ["workflow", "one"]
    assert blanket_permissions({"permissions": {"contents": "read"}}) == []


def test_check_name_is_absent_for_an_action_and_present_for_a_published_workflow() -> None:
    # A published workflow with no check name is a gate a consumer cannot require; an action
    # composes no context at all, so a check name on one would name nothing.
    for name, row in fixture().items():
        composed = row.get("check_name")
        if row["kind"] == "action":
            assert composed is None, f"{name}: an action composes no check name"
        elif row["published"]:
            assert composed, f"{name}: a published workflow with no check name cannot be required"
