import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# Every markdown document in the tree, assigned to exactly one layer. A new file assigned to
# none fails the check below, which is the point: placement is a decision, not a default.
LAYERS: dict[int, frozenset[str]] = {
    1: frozenset({".specify/memory/constitution.md"}),
    2: frozenset({"docs/ai-instructions.md"}),
    3: frozenset(
        {
            "README.md",
            "CONTRIBUTING.md",
            "SECURITY.md",
            "CODE_OF_CONDUCT.md",
            "docs/instruction-layers.md",
            "docs/technical-debt.md",
            ".github/PULL_REQUEST_TEMPLATE.md",
        }
    ),
    4: frozenset({"AGENTS.md", "CLAUDE.md", ".github/copilot-instructions.md"}),
}

# Each exemption carries its reason, and the reason is asserted present — an exemption list
# without reasons becomes a dial on the gate.
EXEMPT: dict[str, str] = {
    ".specify/": "vendored Spec Kit machinery, rewritten byte-for-byte by `specify integration upgrade`",
    ".claude/skills/speckit-": "vendored Spec Kit skills, rewritten by the same command",
    "specs/": "frozen work logs; a completed feature directory is never edited again",
    "docs/decisions/": "one ruling per file, each its own artefact rather than a layer member",
}


def tracked_markdown() -> set[str]:
    out = subprocess.run(
        ["git", "-C", str(REPO), "ls-files", "-z", "*.md"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return {p for p in out.split("\0") if p}


def test_every_document_belongs_to_exactly_one_layer() -> None:
    assigned = LAYERS[1] | LAYERS[2] | LAYERS[3] | LAYERS[4]
    total = sum(len(paths) for paths in LAYERS.values())
    assert len(assigned) == total, "a path is assigned to more than one layer"

    # An explicit assignment beats an exempt prefix, so a file inside a vendored tree that is
    # nonetheless ours — the constitution — stays checked.
    found = {p for p in tracked_markdown() if p in assigned or not p.startswith(tuple(EXEMPT))}
    assert found - assigned == set(), "document in the tree belongs to no layer"
    assert assigned - found == set(), "layer claims a document that is not in the tree"


def test_every_exemption_carries_a_reason() -> None:
    assert all(reason.strip() for reason in EXEMPT.values())


def test_the_exempt_prefix_for_the_constitution_does_not_swallow_it() -> None:
    # `.specify/` is exempt wholesale, but memory/constitution.md is ours and is layer 1.
    # Ordering the check the other way round would silently drop the invariants layer.
    assert ".specify/memory/constitution.md" in LAYERS[1]
    assert ".specify/memory/constitution.md" in tracked_markdown()
