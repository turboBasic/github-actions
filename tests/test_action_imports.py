import ast
import sys
from pathlib import Path

ACTIONS = Path(__file__).parent.parent / "actions"

# What `imported_roots` reports for a relative import, which resolves against a package rather than a
# name. No standard-library name matches it, so it is judged separately below.
RELATIVE = "."


def imported_roots(source: str) -> set[str]:
    roots: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            roots |= {alias.name.split(".")[0] for alias in node.names}
        if isinstance(node, ast.ImportFrom):
            roots.add(node.module.split(".")[0] if node.level == 0 and node.module else RELATIVE)
    return roots


# Every module below the actions directory, not only the ones beside an `action.yml`. A one-level glob
# still finds those and still passes the non-empty check, so it would report green over every module a
# package holds underneath them.
def action_modules(root: Path) -> list[Path]:
    return sorted(root.rglob("*.py"))


def foreign_imports(root: Path) -> list[str]:
    found: list[str] = []
    for module in action_modules(root):
        # A relative import needs a package to resolve against. Where the directory has no
        # `__init__.py` there is none, and a hyphen in the name means there never can be.
        packaged = (module.parent / "__init__.py").exists()
        where = module.relative_to(root).as_posix()
        for name in sorted(imported_roots(module.read_text(encoding="utf-8"))):
            if name == RELATIVE:
                if not packaged:
                    found.append(f"{where} imports {name}")
            elif name not in sys.stdlib_module_names:
                found.append(f"{where} imports {name}")
    return found


def test_every_module_a_composite_action_runs_imports_only_the_standard_library() -> None:
    assert action_modules(ACTIONS), "no action module was read, so this gate holds no import at all"
    assert foreign_imports(ACTIONS) == [], (
        f"an action module imports outside the standard library: {foreign_imports(ACTIONS)}. Nothing "
        "installs a dependency before the module runs, and the interpreter is whichever `python3` the "
        "caller's own configuration left on the runner — so there is no resolution step to fail loudly "
        "here, only an ImportError in a consumer's job. Move the work to the suite, or into the action's "
        "own steps"
    )


def test_the_import_walk_reads_the_forms_it_is_given() -> None:
    # Pre-flight the walk, or a change that stops it finding imports reports green over a module
    # importing whatever it likes.
    assert imported_roots("import os\nimport a.b.c\n") == {"os", "a"}
    assert imported_roots("from collections.abc import Iterable\n") == {"collections"}
    assert imported_roots("def f() -> None:\n    import yaml\n") == {"yaml"}
    assert imported_roots("from . import sibling\n") == {RELATIVE}
    assert RELATIVE not in sys.stdlib_module_names


def test_the_walk_reaches_a_module_nested_below_an_action_directory(tmp_path: Path) -> None:
    # Pre-flight the depth. The module beside the action is what a one-level glob finds, so a gate
    # reading only that would pass this tree while never opening the nested file at all.
    beside = tmp_path / "an-action"
    beside.mkdir()
    (beside / "beside.py").write_text("import os\n", encoding="utf-8")
    nested = tmp_path / "pkg" / "domain"
    nested.mkdir(parents=True)
    (tmp_path / "pkg" / "__init__.py").write_text("", encoding="utf-8")
    (nested / "__init__.py").write_text("", encoding="utf-8")
    (nested / "deep.py").write_text("import yaml\n", encoding="utf-8")

    walked = {path.relative_to(tmp_path).as_posix() for path in action_modules(tmp_path)}
    assert "pkg/domain/deep.py" in walked, (
        f"the walk stopped above the nested module: {sorted(walked)}"
    )
    assert foreign_imports(tmp_path) == ["pkg/domain/deep.py imports yaml"]


def test_a_relative_import_is_admitted_only_where_the_directory_is_a_package(
    tmp_path: Path,
) -> None:
    # Pre-flight both sides. Admitting a relative import everywhere would pass a script beside an
    # action, where it raises ImportError on the runner rather than resolving to anything.
    packaged = tmp_path / "pkg"
    packaged.mkdir()
    (packaged / "__init__.py").write_text("", encoding="utf-8")
    (packaged / "sibling.py").write_text("from . import other\n", encoding="utf-8")
    loose = tmp_path / "an-action"
    loose.mkdir()
    (loose / "script.py").write_text("from . import other\n", encoding="utf-8")

    assert foreign_imports(tmp_path) == ["an-action/script.py imports ."]
