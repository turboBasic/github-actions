# Phase 0 Research: Layered AI Instructions

Three questions had to be answered before a shape could be chosen: what Claude Code actually
does with instruction files, which rules are duplicated today, and what a check can assert
precisely rather than heuristically.

## 1. Claude Code loading behaviour

Verified against the published documentation, not assumed. Sources are
`code.claude.com/docs/en/memory.md`, `.../skills.md`, `.../best-practices.md` and
`.../large-codebases.md`.

| Question | Documented answer | What it forces |
| --- | --- | --- |
| How do memory files combine? | Managed policy, then user, then ancestor directories, then the working directory. **All discovered files are concatenated; there is no override mechanism.** Precedence is implicit in load order and is not documented as a table. | A layer cannot silently override an outer one. Where this repository is stricter than the user-level file, it must say so in prose. |
| Are `@path` imports eager? | Yes — imported files are expanded and loaded at launch alongside the file that references them. Recursive to four hops. Relative paths resolve against the importing file. Imports inside code spans and fences are skipped. | An import is organisation, not containment. Anything imported is in the always-loaded layer and costs context every session. |
| What does a skill preload? | Names and descriptions only. The body loads on invocation and then persists. Supporting files in the skill directory load only when accessed. Recommended under 500 lines. | Skills are genuine containment: the body is absent from context until used. |
| Is there size guidance? | Target under 200 lines per memory file; longer files "consume more context and reduce adherence". | 292 lines of conventions plus 336 in the user-level file is roughly three times the target. |
| Is there guidance on what belongs where? | Memory holds facts for every session — commands, conventions, layout, "always do X". **"If an entry is a multi-step procedure or only matters for one part of the codebase, move it to a skill or a path-scoped rule instead."** Excluded: what can be derived from the code, standard conventions, detailed reference, long explanations. | A decision rule for placement that is not a matter of taste. |
| Are there path-scoped instructions? | Yes: `.claude/rules/` files with a `paths:` frontmatter glob load only when files matching it are read. Nested memory files in subdirectories load on demand. | A second containment mechanism, and the one that maps most directly to "detail contained by the part of the tree it concerns". |
| Can another tool follow a pointer? | Not answerable from these sources. Claude Code's `/init` can *read* `.github/copilot-instructions.md`, but no include mechanism for that file is documented. | A design that fragments the canonical text is a design that only Claude Code can read. |

**Decision**: treat the always-loaded set as a real cost, use prose for precedence because the
mechanism offers none, and do not assume any other tool can follow an include.

## 2. What is duplicated today

Read line by line across `.specify/memory/constitution.md`, `docs/ai-instructions.md`,
`README.md`, `CONTRIBUTING.md` and `~/.claude/CLAUDE.md`.

**Six of the seven principles are restated in full in the conventions layer** — pinning, least
privilege, untrusted input, secrets, verification by real invocation, and gates never loosened.
The restatements carry the rationale sentences too, in places word for word: "A tag can be
retroactively repointed at malicious code" appears in both files.

Two governance sentences are also duplicated: the procedure for objecting to a rule change
("name the rule, state concretely what breaks without it, offer the smallest alternative … then
stop and wait") and the carve-out that conventions are not governed. One clause of the first
principle — a major bump is never a move of the current tag — is echoed in the Versioning section.

Principle I is a special case worth stating: the conventions layer enumerating *which* changes
break a caller is not a restatement, because the invariant says only *that* a breaking change
needs a new tag. That split is legitimate and the design preserves it.

**The reference between the two files is a cycle.** The constitution's opening points down at the
conventions file as the owner of the concrete rules; the conventions file's "Changes to these
rules" points back up. Neither is readable first, which is the structural reason the duplication
was survivable: an agent that reads either file alone gets a complete answer, at the cost of two
copies of it.

**The root cause is that the invariants are never loaded.** Nothing imports the constitution, so
an agent sees it only if it goes looking. Restating it in the imported file was the rational
response. Removing the restatement without importing the constitution would lose the rules from
context, so the two changes are one change.

**The user-level file contradicts this repository, and concatenation means both are present.** It
permits a third-party action pinned to "full SHA or explicit tag" and permits `@main` for
in-house references; this repository forbids both. It also restates four working-style bullets
that the conventions layer states again in its own words. That file is out of scope to edit, so
the conventions layer has to name the override.

**The conventions layer already forbids what it does.** It says: "State the rule, not the incident
that taught it. No war stories, no version archaeology, no reasoning left in prose where a test can
hold it." It then names individual test functions, an upstream issue number, a REST endpoint and
its status code, and two internal test-module symbols — much of it a second copy of a comment that
already sits in the test.

## 3. What a check can assert precisely

The spec assumed prose analysis and a tolerance for false positives. That turned out to be
unnecessary for everything that matters, because the repository already contains the pattern.

`tests/test_action_pins.py` holds `PROSE_DOCS` and
`test_no_prose_document_names_a_concrete_major`: every prose document except `README.md` is
scanned for a literal major version, because README owns that value and every other document is
told to cite it. **That is exactly this feature's check, applied to one fact.** The work is to
generalise it to a declared table of owned facts, in the same idiom as `WORKFLOW_CONTRACTS` and
`REQUIRED_CHECKS` — a table in the test, validated against the tree, offline.

Three of the four checks need no similarity heuristic at all, because their forbidden vocabulary
is derivable from the tree:

| Check | Derived from | Precision |
| --- | --- | --- |
| No mechanism identifier above the concrete layer | test function names parsed from `tests/*.py`; `[tools]` and `[tasks]` keys from `mise.toml`; module-level constant names from the test package | exact string match, no tuning |
| No reference against the direction | the layer table: which artefacts each layer may name | exact, path-based |
| No upstream issue reference above the concrete layer | pattern `owner/repo#N` | exact |
| No owned fact restated outside its owner | a declared table of `(fact, owner, pattern)` | exact per row, and the table is the statement of ownership |

The fourth is the one that cannot be derived, and the decision is to **declare rather than
detect**: rows are added to the table as facts gain a second potential home, exactly as
`REQUIRED_CHECKS` grew. A general "same rule stated twice" detector was considered and rejected —
it needs a tuned threshold and an allowlist, which is a gate with a dial on it, and the failure it
would catch beyond the table is a rule nobody has yet noticed is shared.

## 4. Shape decision

The spec deferred this. Four candidates, the winner first.

### Fix ownership and direction in place (SELECTED)

Same four artefacts. Assign every fact one owner, delete the restatements, import the constitution
so its rules are in context without being copied, push mechanism identifiers down into the tests
that own them, and turn `CLAUDE.md` from a one-line import into the navigation layer.

- Adopted because: it is the only candidate that adds no file and satisfies the spec's stated
  criterion — no topic was found for which a single owner cannot be named.
- Adopted because: the canonical text stays one file, so the pointer any other tool follows keeps
  working and adding a third tool stays a pointer rather than a copy.
- Adopted because: the enforcement pattern already exists in this repository and generalises.
- Adopted because: the always-loaded set gets smaller, not larger — roughly a hundred lines of
  restatement and archaeology out, seventy-four lines of invariants in.
- Adopted despite: the conventions file stays a single 190-line document rather than becoming
  navigable modules, so finding a rule is still a search within one file.
- Adopted despite: importing the constitution makes it always-loaded, which is a context cost
  paid deliberately to buy single ownership.
- Adopted despite: it leaves the user-level file's contradiction resolved only by a prose
  sentence, because nothing else can resolve it.

### Split the conventions into topic modules

- Rejected because: it adds files without removing a fact from any layer, and the spec's criterion
  admits a split only where a single owner cannot otherwise be named. None was found.
- Rejected because: imports are eager, so modules cost the same context and buy no containment.
- Rejected despite: it would genuinely make a rule easier to locate, and remains available later
  if the file grows past the documented target again.

### Move mechanics into on-demand skills

- Rejected because: containment is real here, but what would move is reference material an agent
  needs while writing a workflow, not a procedure it invokes. A rule that loads only when asked
  for is a rule that is not applied when nobody asks.
- Rejected because: only Claude Code reads skills, so the conventions would stop being readable by
  the other tool this repository documents.
- Rejected despite: it is the only candidate that would cut the always-loaded set substantially,
  and it is the right home for the release procedure if that ever moves out of `CONTRIBUTING.md`.

### Path-scoped rules under `.claude/rules/`

- Rejected because: it fragments the canonical text into files no other tool can reach, which
  breaks the pointer contract.
- Rejected because: the two candidate sections — workflow conventions and Python conventions — are
  the ones an agent most needs before it opens a file, not after.
- Rejected despite: it is the closest documented mechanism to the containment the request asks
  for, and is the first thing to revisit if this repository ever stops documenting a second tool.

## 5. Open risks

- **Deleting a restatement can delete a rule.** The mitigation is a before-and-after inventory that
  reconciles, and it is a task rather than a hope.
- **Editing the constitution is editing the governance layer.** The planned edits remove its
  downward pointers and nothing else; no principle's substance changes. Stated here because an
  incidental erosion has to be reported even when it is not intended.
- **The ownership table can be gamed by not adding a row.** So can `REQUIRED_CHECKS`. The answer is
  the same: the table is the statement of the contract, and adding to it is part of the change that
  creates the shared fact.
