# The instruction layers

A repository that instructs an AI coding tool accumulates rules faster than it accumulates places to
keep them. The failure always has the same shape: one rule ends up stated in two files, the copies
drift apart, and a reader — human or agent — gets two answers with nothing to say which is current.

Four layers give every fact exactly one home, and a direction rule keeps the layers from pointing at
each other in a circle.

This document is explanatory. It describes a shape another repository can adopt; the rules binding
*this* repository are stated in its own conventions layer, not here.

## The four layers

| # | Layer | Holds | Changes |
| --- | --- | --- | --- |
| 1 | Invariants | what may never be violated, as a short numbered list | rarely, by amendment, carrying a version of its own |
| 2 | Conventions | how work is done here | as practice settles |
| 3 | Mechanics | the procedures, the gates, and every tool setting | with the code |
| 4 | Navigation | where each fact lives | when an artefact moves |

The numbering is not seniority. It is abstraction: layer 1 is the most abstract and the least
frequently touched, layer 3 the most concrete and the one that moves constantly.

## What belongs in each

**Layer 1** is short, and deliberately expensive to change. A rule earns a place in it only when
breaking it would cost far more to undo than to prevent, *and* when it could be broken without
anyone noticing at the time. Anything a reviewer would catch and a revert would repair is a
convention instead. Each entry reads as a gate: a proposal can be held against it and fail.

**Layer 2** is where most rules live — naming, file placement, how a test is organised, which
library gets reached for first. These settle over time and are edited without ceremony. A request to
change one of them is just a request, and treating it as graver than that is the layer overreaching.

**Layer 3** is everything a machine reads or a procedure needs: the tests, the linter settings, the
task definitions, the contributor guide, the reference a caller reads. It moves with the code
because it *is* the code's description of itself.

**Layer 4** is a map. It names every artefact and says, in one line each, what that artefact
answers.

## The direction rule

Every fact has exactly one owning layer. A layer needing a fact it does not own cites the owner
instead of restating it, and a citation only ever runs from the concrete toward the abstract.

So layer 2 may cite a layer 1 principle by number. Layer 1 cites nothing at all — it names no
artefact, because naming one would fix a filename inside the most stable document in the tree.
Layer 3 may cite layers 1 and 2 by section, and other layer 3 files freely.

The rule reads oddly until you see what it prevents. A downward citation — an abstract document
naming a concrete one — is a promise the abstract document cannot keep. Rename the concrete file and
the stable document is silently wrong. Citations in the other direction cost nothing, because the
abstract end does not move.

Since every citation strictly reduces the layer number, the graph has no cycle by construction.

## Navigation is not a rule layer

Layer 4 is the file the tool loads first, every session, without being asked. That makes it the most
tempting place to put a rule, and the worst.

A rule there has no owner. It is invisible to the layering, it can contradict the layer that should
have held it, and because layer 4 is necessarily exempt from the direction rule — naming every
artefact by path is its entire content — nothing catches the contradiction.

So a navigation file carries the imports, the links, the layer table, and one line per artefact.
Nothing imperative. A sentence in it that tells someone what to do belongs a layer down.

## How a violation is caught

Prose rot is silent, so the layering is held by a test that reads the tree and needs no network.
Four checks cover it:

- **Assignment** — every document in the tree belongs to exactly one layer. A new file assigned to
  none fails, which forces it to be placed deliberately rather than drifting in unnoticed.
- **Direction** — no artefact names one from a higher-numbered layer, layer 4 excepted.
- **Mechanism names** — nothing above layer 3 carries an identifier that layer 3 alone owns: a test
  function's name, a constant from a test module, an upstream issue reference, an API route, a bare
  status code. These are derived from the tree at check time rather than listed, so the list cannot
  go stale.
- **Owned facts** — a table of the facts with more than one plausible home, each with a distinctive
  phrase taken from its owner's own text. Every row is asserted twice: the phrase is still in its
  owner, and it appears nowhere else. The first assertion is what stops a row rotting into a pattern
  that matches nothing.

Two details decide whether the checks are usable rather than merely present.

**A phrase is matched with whitespace collapsed.** A distinctive phrase long enough to be
distinctive is long enough to wrap, and a line-based search finds none of the ones that do.

**Tool and task names are deliberately not mechanism names.** They are the content of a rule rather
than a mechanism behind it — a hierarchy saying "the project's own task first, then the hook runner"
without naming either is not a rule anyone can follow. They also do not rot quietly: rename a task
and every invocation of it breaks at once, loudly, for humans first.

## Adopting the shape

The order matters, because the middle step destroys information.

1. Inventory what is in force today: one row per rule, with the file and line stating it. A rule
   missed here is a rule that can be lost without trace.
2. Write the navigation file, and make it load the two rule layers eagerly. Confirm mechanically
   that they load before deleting anything, because a copy deleted while the original is out of
   context takes the rule with it.
3. Delete each restatement, leaving a citation of the owner behind.
4. Rebuild the inventory and reconcile it against the first one. Every rule present before is
   present after, in exactly one layer; a deliberate drop is recorded as one.
5. Add the checks last. Written against an uncleaned tree they fail on work in progress; written
   against a cleaned one they hold the cleaning in place.

Exemptions are unavoidable — vendored trees get rewritten wholesale, and frozen work logs are never
edited again — but each one carries its reason next to it, asserted present. An exemption list
without reasons becomes a dial on the gate.
