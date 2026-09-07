# Contract: The Layer Contract

Normative. `tests/test_instruction_layers.py` encodes this as a table and validates the tree
against it offline, in the idiom `WORKFLOW_CONTRACTS` and `REQUIRED_CHECKS` already use.

## Assignment

Every path in the instruction set belongs to exactly one layer. A path that belongs to none fails
the check, so a new document has to be placed deliberately.

```text
LAYERS = {
  1: [".specify/memory/constitution.md"],
  2: ["docs/ai-instructions.md"],
  3: ["README.md", "CONTRIBUTING.md", "docs/technical-debt.md",
      "docs/instruction-layers.md", "SECURITY.md", "CODE_OF_CONDUCT.md"],
  4: ["CLAUDE.md", ".github/copilot-instructions.md"],
}
```

`tests/` and the tool configs are layer 3 by definition and are not scanned as prose; they are the
target of the direction rule, not a subject of it.

## Direction

| From | May name | Must not name |
| --- | --- | --- |
| 1 Invariants | nothing in this repository; domain vocabulary only | any artefact, any layer-3 mechanism, any tool this repository chose |
| 2 Conventions | layer 1, by principle name or number | layer 3 artefacts, mechanism identifiers |
| 3 Mechanics | layers 1 and 2 by section; each other | — |
| 4 Navigation | every artefact, by path | any rule of its own |

Layer 4 is exempt from the direction rule because navigation is its entire content. A rule
appearing in layer 4 is a violation of a different kind, and is checked separately: layer 4 files
carry pointers and a one-line gloss each, and nothing imperative.

## Forbidden vocabulary above layer 3

Derived from the tree at check time rather than listed, so it cannot go stale:

| Vocabulary | Source |
| --- | --- |
| test function names | `ast` over `tests/*.py`, every `def test_*` |
| test module constants | `ast` over `tests/*.py`, module-level assignments in caps |
| upstream issue references | pattern `\b[\w.-]+/[\w.-]+#\d+\b` |
| REST paths and status codes | patterns `/repos/\{` and `\b4\d\d\b` beside a verb |

The test for membership is silent rot. A renamed test function leaves prose that is wrong and
nothing says so, which is why it is forbidden above the layer that owns it.

**Tool and task names are deliberately not on that list.** `prek`, `zizmor` and `mise run lint` are
the content of a rule rather than a mechanism behind it: a hierarchy that says "the project's task,
then the hook runner" without naming either is not a rule an agent can follow, and the guidance this
design is built on puts build commands in always-loaded memory for exactly that reason. They also do
not rot silently — a renamed task breaks every invocation of it, loudly, for humans first.

Domain vocabulary is legal at every layer and is not derived, because it is not ours: GitHub named
`workflow_call`, `pull_request_target`, `permissions` and `env`. The test carries no allowlist for
it — the derived lists simply do not contain it.

## Import reachability

Layers 1 and 2 must be reachable from layer 4 by `@` import, because an unloaded rule is a rule
that gets restated. Imports are eager and recursive to four hops, so one hop from `CLAUDE.md` to
each is enough and is what the check asserts: `CLAUDE.md` contains an import of the constitution
and an import of the conventions, neither inside a code fence.

## Precedence over the user-level layer

Layer 0 is concatenated into context with no override mechanism, and it is looser than this
repository in two places: it permits a third-party action pinned to a tag rather than a SHA, and it
permits `@main` for in-house references. Layer 2 owns one paragraph stating that this repository's
rules win where they are stricter, and naming those two cases. That paragraph is required, and the
check asserts it exists by anchor phrase — the contradiction is invisible to every mechanism, so
prose is the only place it can be resolved.

## Exemptions

| Path | Reason |
| --- | --- |
| `.specify/templates/**`, `.specify/scripts/**`, `.specify/integrations/**`, `.specify/workflows/**` | vendored, rewritten wholesale on refresh |
| `.claude/skills/speckit-*/**` | vendored with the same tool |
| `specs/**` | completed feature directories are frozen work logs |
| `tmp/**` | scratch, gitignored |

`.specify/memory/constitution.md` sits inside a vendored tree and is explicitly **not** exempt: it
is ours. The exemption list is a literal in the test with the reason beside each entry, and an
entry without a reason fails.
