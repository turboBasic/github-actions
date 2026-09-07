import ast
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent

# Every instruction path belongs to exactly one layer. A path in none of these lists fails, so a new
# document has to be placed deliberately rather than drifting in unassigned.
#
# The tool configs and `tests/` are layer 3 by definition and are enumerated here because assignment
# needs every path named, not a definition. `.github/PULL_REQUEST_TEMPLATE.md` is layer 3 on the same
# reasoning as CONTRIBUTING.md: it tells a contributor what a pull request must carry. The issue
# templates are YAML forms rather than prose and never reach this scan.
LAYERS: dict[int, list[str]] = {
    1: [".specify/memory/constitution.md"],
    2: ["docs/ai-instructions.md"],
    3: [
        "README.md",
        "CONTRIBUTING.md",
        "SECURITY.md",
        "CODE_OF_CONDUCT.md",
        "docs/technical-debt.md",
        "docs/instruction-layers.md",
        ".github/PULL_REQUEST_TEMPLATE.md",
        "tests/",
        "mise.toml",
        "pyproject.toml",
        ".pre-commit-config.yaml",
        ".cspell.config.yaml",
        ".yamllint.yaml",
        ".cliff.toml",
        ".github/actionlint.yaml",
        ".github/zizmor.yml",
        ".github/renovate.json",
        ".github/dependabot.yml",
    ],
    4: ["CLAUDE.md", ".github/copilot-instructions.md"],
}

# A reason per entry, asserted present, so the list cannot quietly become a dial on the gate.
# `.specify/memory/constitution.md` sits inside a vendored tree and is deliberately absent here: it
# is ours, and it is layer 1.
EXEMPTIONS: dict[str, str] = {
    ".specify/templates/": "vendored, rewritten wholesale on refresh",
    ".specify/scripts/": "vendored, rewritten wholesale on refresh",
    ".specify/integrations/": "vendored, rewritten wholesale on refresh",
    ".specify/workflows/": "vendored, rewritten wholesale on refresh",
    ".claude/": "vendored with the same tool",
    "specs/": "completed feature directories are frozen work logs",
    "tmp/": "scratch, gitignored",
}


def _prose_files() -> list[str]:
    listed = subprocess.run(
        ["git", "ls-files", "*.md"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    return [f for f in listed if not f.startswith(tuple(EXEMPTIONS))]


def _layer_of_path() -> dict[str, int]:
    return {path: layer for layer, paths in LAYERS.items() for path in paths}


def derived_vocabulary() -> set[str]:
    # Derived from the tree at check time rather than listed, so it cannot go stale: every
    # `def test_*` and every compound module-level constant in caps.
    #
    # Single-word constants are deliberately excluded. `SHA`, `WORKFLOWS`, `SECTIONS` and `MODULE`
    # are all test constants and all words prose must stay free to use, so a one-word name is
    # indistinguishable from domain vocabulary. Only a compound name is derivable.
    names: set[str] = set()
    for module in sorted((REPO_ROOT / "tests").glob("*.py")):
        for node in ast.parse(module.read_text(encoding="utf-8")).body:
            if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                names.add(node.name)
            if isinstance(node, ast.Assign | ast.AnnAssign):
                targets = [node.target] if isinstance(node, ast.AnnAssign) else node.targets
                for target in targets:
                    if isinstance(target, ast.Name) and target.id.isupper() and "_" in target.id:
                        names.add(target.id)
    return names


def test_every_instruction_path_is_assigned_to_exactly_one_layer() -> None:
    directories = tuple(p for ps in LAYERS.values() for p in ps if p.endswith("/"))
    files = {p for ps in LAYERS.values() for p in ps if not p.endswith("/")}
    unassigned = [f for f in _prose_files() if f not in files and not f.startswith(directories)]
    assert not unassigned, (
        f"assigned to no layer: {unassigned}. Place each in LAYERS, or exempt it with a reason."
    )

    counted = [p for ps in LAYERS.values() for p in ps]
    duplicated = sorted({p for p in counted if counted.count(p) > 1})
    assert not duplicated, f"assigned to more than one layer: {duplicated}"


def test_the_derived_vocabulary_carries_no_domain_vocabulary() -> None:
    # The check is only usable while the derived set stays free of words GitHub named. Nothing here
    # is an allowlist: the filter in derived_vocabulary is what keeps them out, and this fails if it
    # stops working.
    domain = {
        "permissions",
        "workflow_call",
        "workflow_dispatch",
        "pull_request_target",
        "env",
        "uses",
        "secrets",
        "inputs",
        "outputs",
        "concurrency",
        "sha",
        "workflows",
    }
    vocabulary = derived_vocabulary()
    assert vocabulary, "derived nothing from tests/*.py; the ast walk has stopped working"
    collisions = {name for name in vocabulary if name.lower() in domain}
    assert not collisions, f"derived vocabulary collides with domain vocabulary: {collisions}"


def test_no_artefact_names_one_from_a_higher_layer() -> None:
    # Layer 4 is exempt as a source: naming every artefact by path is its entire content. It is not
    # exempt as a target — a layer 3 file naming CLAUDE.md is an upward citation like any other.
    owner = _layer_of_path()
    violations: list[str] = []
    edges: set[tuple[int, int]] = set()
    for layer, paths in LAYERS.items():
        for source in paths:
            path = REPO_ROOT / source
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8")
            for target, target_layer in owner.items():
                if target == source or target not in text:
                    continue
                if target_layer != layer:
                    edges.add((layer, target_layer))
                if target_layer > layer and layer != 4:
                    violations.append(f"layer {layer} {source} names layer {target_layer} {target}")
    assert not violations, "citations run concrete to abstract only: " + "; ".join(violations)

    # Every cross-layer citation strictly decreases, from every source the direction rule binds, so
    # the citation graph has no cycle.
    rising = sorted(e for e in edges if e[1] > e[0] and e[0] != 4)
    assert not rising, f"cycle in the citation graph via rising edges: {rising}"


def test_every_exemption_carries_a_reason() -> None:
    missing = sorted(path for path, reason in EXEMPTIONS.items() if not reason.strip())
    assert not missing, f"exemption without a reason: {missing}"
