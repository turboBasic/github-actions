import ast
import re
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
CONSTITUTION = ".specify/memory/constitution.md"
CONVENTIONS = "docs/ai-instructions.md"

# Every instruction path belongs to exactly one layer. A path in none of these lists fails, so a new
# document has to be placed deliberately rather than drifting in unassigned.
#
# The tool configs and `tests/` are layer 3 by definition and are enumerated here because assignment
# needs every path named, not a definition. The issue templates are YAML forms rather than prose and
# never reach this scan.
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
        "tests/",
        "mise.toml",
        "pyproject.toml",
        ".pre-commit-config.yaml",
        ".cspell.config.yaml",
        ".yamllint.yaml",
        ".markdownlint-cli2.jsonc",
        ".taplo.toml",
        ".cliff.toml",
        ".github/actionlint.yaml",
        ".github/zizmor.yml",
        ".github/renovate.json",
        ".github/dependabot.yml",
    ],
    4: ["CLAUDE.md", ".github/copilot-instructions.md"],
}

# One row per fact with more than one plausible home. The anchor is a distinctive phrase from the
# owner's own text, and each row is asserted twice: the anchor is still in its owner, and it is
# nowhere else. The first assertion is what stops a row rotting into a pattern that matches nothing.
#
# Two rows from the contract carry no anchor and are absent here, because a gate already holds them:
# the allowed commit types are held equal to commitizen's set, and the frozen input and permission
# surface is the WORKFLOW_CONTRACTS table. Both live in test_action_pins.py. Which major is current
# is likewise already asserted, by the no-concrete-major scan.
#
# A deliberate paraphrase is a new statement and a reviewer's problem, not this check's.
ANCHORED_FACTS: list[tuple[str, str, str]] = [
    (CONSTITUTION, "I", "Patch tags are immutable"),
    (CONSTITUTION, "II", "retroactively repointed at malicious code"),
    (CONSTITUTION, "III", "only ever reduce down a call chain"),
    (CONSTITUTION, "IV", "never through inline"),
    (CONSTITUTION, "V", "written to a file, a log, an artifact"),
    (CONSTITUTION, "VI", "Lint does not verify a workflow"),
    (CONSTITUTION, "VII", "no rule disabled to"),
    (CONSTITUTION, "Governance", "smallest alternative that meets the underlying need"),
    (CONSTITUTION, "Governance", "Conventions are not governed here"),
    (CONSTITUTION, "Governance", "expensive to reverse and cheap to commit by accident"),
    (CONSTITUTION, "Governance", "a revert would fix is a convention"),
    (CONVENTIONS, "Changes to these rules", "cites the owner instead of restating it"),
    ("CONTRIBUTING.md", "Labels", "This table is the label set"),
    ("CONTRIBUTING.md", "Releasing", "the only place the version is decided"),
    ("CONTRIBUTING.md", "Releasing", "approve a proposal"),
    ("CONTRIBUTING.md", "Verifying a workflow change", "Run every workflow you change"),
]

# The user-level layer is concatenated into context ahead of the conventions with no override
# mechanism, and it is looser in two places. Prose is the only place that contradiction can be
# resolved, so the paragraph resolving it is required and asserted by anchor.
PRECEDENCE_ANCHOR = "This repository's rules win where they are stricter"

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
    ".github/PULL_REQUEST_TEMPLATE.md": (
        "a Jinja2 template rendered by a composite action, and the default a caller inherits — "
        "a form, not prose stating a rule"
    ),
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
    # Navigation needs no exemption as a source, because it carries the highest number: naming every
    # artefact by path is its entire content, and no citation from it can rise. It is not exempt as a
    # target — a layer 3 file naming a navigation file is an upward citation like any other.
    owner = _layer_of_path()
    violations: list[str] = []
    edges: set[tuple[int, int]] = set()
    for layer, paths in LAYERS.items():
        for source in paths:
            path = REPO_ROOT / source
            # Prose only, as a source. A tool config names the paths it operates on — a filter list,
            # an ignore glob — and that is an operand rather than a citation of a fact. A config stays
            # a target, so prose naming one is still caught.
            if not path.is_file() or path.suffix != ".md":
                continue
            text = path.read_text(encoding="utf-8")
            for target, target_layer in owner.items():
                if target == source or target not in text:
                    continue
                if target_layer != layer:
                    edges.add((layer, target_layer))
                if target_layer > layer:
                    violations.append(f"layer {layer} {source} names layer {target_layer} {target}")
    assert not violations, "citations run concrete to abstract only: " + "; ".join(violations)

    # Every cross-layer citation strictly decreases, so the citation graph has no cycle.
    rising = sorted(e for e in edges if e[1] > e[0])
    assert not rising, f"cycle in the citation graph via rising edges: {rising}"


def test_every_exemption_carries_a_reason() -> None:
    missing = sorted(path for path, reason in EXEMPTIONS.items() if not reason.strip())
    assert not missing, f"exemption without a reason: {missing}"


# A renamed test leaves prose that is wrong with nothing to say so, which is why a mechanism name is
# forbidden above the layer that owns it. The patterns catch the same class of silent rot in a
# reference nobody derives: an upstream issue that gets closed, a REST route that moves, a status
# code that stops being what the endpoint returns.
MECHANISM_PATTERNS: dict[str, str] = {
    "test module path": r"tests/test_\w+\.py",
    "pytest marker": r"@pytest\.mark\.\w+",
    "upstream issue reference": r"\b[\w.-]+/[\w.-]+#\d+\b",
    "REST path": r"/repos/\{",
    "bare status code": r"`[45]\d\d`",
}


@pytest.mark.parametrize("layer", [1, 2])
def test_no_mechanism_identifier_appears_above_layer_3(layer: int) -> None:
    vocabulary = derived_vocabulary()
    found: list[str] = []
    for source in LAYERS[layer]:
        text = (REPO_ROOT / source).read_text(encoding="utf-8")
        found += [f"{source} names {name}" for name in sorted(vocabulary) if name in text]
        for label, pattern in MECHANISM_PATTERNS.items():
            found += [f"{source} carries a {label}: {hit}" for hit in re.findall(pattern, text)]
    assert not found, f"layer {layer} carries a mechanism identifier: {'; '.join(found)}"


def _collapsed(text: str) -> str:
    # Three of the anchors span a line break in their owner, so a line-based match finds none of
    # them. Every comparison here is on whitespace-collapsed text.
    return re.sub(r"\s+", " ", text)


def _unquoted(text: str) -> str:
    # A quotation attributed to its owner is a citation with the text inlined, not a second copy, so
    # a line inside a blockquote is not one. The explanatory write-up needs this: a reader whose own
    # repository has no rule layers yet cannot follow a rule the document only points at.
    #
    # It narrows the check, and deliberately. An unattributed blockquote would slip a restatement
    # past, and only review catches that. The alternative narrows it further — with no exemption the
    # cheapest way to clear the check is to reword until the phrase differs, which leaves the second
    # copy in place and this gate holding neither.
    return "\n".join(line for line in text.splitlines() if not line.lstrip().startswith(">"))


@pytest.mark.parametrize(
    ("owner", "section", "anchor"),
    ANCHORED_FACTS,
    ids=[f"{Path(o).stem}-{s}-{a[:24]}" for o, s, a in ANCHORED_FACTS],
)
def test_an_owned_fact_is_stated_only_by_its_owner(owner: str, section: str, anchor: str) -> None:
    needle = _collapsed(anchor)
    assert needle in _collapsed((REPO_ROOT / owner).read_text(encoding="utf-8")), (
        f"{owner} {section} no longer contains {anchor!r}; the owner was rewritten and this row "
        "was not updated with it"
    )
    elsewhere = [
        path
        for path in _prose_files()
        if path != owner
        and needle in _collapsed(_unquoted((REPO_ROOT / path).read_text(encoding="utf-8")))
    ]
    assert not elsewhere, f"{anchor!r} is owned by {owner} {section} but is restated in {elsewhere}"


def test_both_rule_layers_are_reachable_from_navigation() -> None:
    claude = (REPO_ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    # An import inside a fence is skipped, so a fenced one reads as present and loads nothing.
    outside_fences = re.sub(r"```.*?```", "", claude, flags=re.DOTALL).replace("`", "")
    for target in (CONSTITUTION, CONVENTIONS):
        assert f"@{target}" in outside_fences, (
            f"CLAUDE.md does not import {target} outside a code fence; a fenced import loads nothing"
        )

    copilot = (REPO_ROOT / ".github/copilot-instructions.md").read_text(encoding="utf-8")
    for target in (CONSTITUTION, CONVENTIONS):
        assert target in copilot, (
            f".github/copilot-instructions.md does not link {target}; Copilot has no import "
            "mechanism and reaches the rule layers only by link"
        )


def test_the_conventions_still_override_the_user_level_layer() -> None:
    conventions = _collapsed((REPO_ROOT / CONVENTIONS).read_text(encoding="utf-8"))
    assert _collapsed(PRECEDENCE_ANCHOR) in conventions, (
        f"{CONVENTIONS} no longer states {PRECEDENCE_ANCHOR!r}; nothing else resolves a looser "
        "user-level rule, because memory files concatenate with no override mechanism"
    )


# A navigation file states no rule, and a rule in prose is written in the imperative. Matching the
# mood is not possible, so this matches the openings the repository's own rules are written in — the
# verbs that start a sentence in layers 1, 2 and 3. A rule phrased around them slips through and is
# a reviewer's catch; one written the way every other rule here is written does not.
IMPERATIVE_OPENERS = (
    "use ",
    "do not ",
    "don't ",
    "never ",
    "always ",
    "prefer ",
    "ensure ",
    "avoid ",
    "add ",
    "run ",
    "write ",
    "keep ",
    "read ",
    "check ",
    "declare ",
    "pin ",
    "move ",
    "delete ",
    "update ",
    "fix ",
    "follow ",
    "state ",
    "treat ",
    "put ",
    "make ",
)


MARKDOWN_PREFIX = "#*_->`| \t"


def _sentences(text: str) -> list[str]:
    # Split the raw text, never the collapsed form. Collapsing removes the line breaks that separate a
    # heading from the prose under it and one table row from the next, which leaves a whole document as
    # a handful of sentences each beginning `#` or `|` — where no opener can ever match. Table cells
    # split too, so a rule written into a gloss column is still reached.
    cells = [cell for line in text.splitlines() for cell in line.split("|")]
    return [piece for cell in cells for piece in re.split(r"(?<=[.:])\s+", cell) if piece.strip()]


@pytest.mark.parametrize("navigation", LAYERS[4])
def test_a_navigation_file_carries_pointers_and_no_rule(navigation: str) -> None:
    text = (REPO_ROOT / navigation).read_text(encoding="utf-8")
    assert CONSTITUTION in text and CONVENTIONS in text, (
        f"{navigation} does not point at both rule layers"
    )

    imperative = [
        sentence.strip()
        for sentence in _sentences(text)
        if sentence.strip().lower().lstrip(MARKDOWN_PREFIX).startswith(IMPERATIVE_OPENERS)
    ]
    assert not imperative, (
        f"{navigation} is navigation and states no rule, but reads as imperative: {imperative}"
    )


def test_navigation_glosses_every_artefact_it_places() -> None:
    # Every layer 3 artefact that exists gets a line in CLAUDE.md saying what it answers. A path
    # assigned to a layer with nothing said about it is a path a reader cannot route to.
    claude = (REPO_ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    missing_gloss = [
        path for path in LAYERS[3] if (REPO_ROOT / path).exists() and path.rstrip("/") not in claude
    ]
    assert not missing_gloss, (
        f"CLAUDE.md places these at layer 3 but says nothing about them: {missing_gloss}"
    )
