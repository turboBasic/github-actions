# Consumer features

The product boundary this repository is aiming at. It describes the **target**; `README.md` describes
what currently ships. Where the two differ, the README is right about today and this document is right
about the intent. This document owns why a capability belongs; the README and the workflow files own
usage and current detail.

## Purpose

This repository exists so that a handful of repositories under one owner can keep a standard none of
them would keep alone. Its consumers are that owner's own repositories, in several languages, at least
one of them pinned by somebody further downstream. Each reaches for the same few results: a version
number nobody had to choose, a change described the same way it would be described anywhere else, its
own checks reaching a verdict it can reproduce, and a warning before it starts depending on something
with a known vulnerability. Without somewhere central to keep them, those results are not rebuilt per
repository — they are dropped. None of this is hard. A standard nobody has to re-implement is a
standard that survives.

## Feature catalogue

### Versions and releases that decide themselves

- **Need:** A maintainer picks a version number by hand and cuts the release around it, and both are
  easy to get wrong in ways nobody can undo afterwards.
- **Use case:** When a change is ready to go out, the maintainer uses this to have the next number
  worked out from what actually changed, and the release published from the same evidence.
- **Success:** A release exists carrying a number that matches what changed, and nobody typed the
  number.
- **Not included:** Putting whatever the project builds anywhere. The release is published; uploading
  an artefact is deliberately outside it.

### One grammar for describing changes, across every repository

- **Need:** Each repository invents its own habits for describing a change, so the same word means
  different things in different places and the record of what changed cannot be relied on.
- **Use case:** When a change is proposed, the maintainer uses this to have its description judged
  against one grammar they wrote once and reuse everywhere.
- **Success:** A proposal whose description breaks the grammar is stopped before it merges, and the
  verdict matches the one the maintainer's own machine gives.
- **Not included:** Judging whether a description is *accurate* or well written. Only its form is
  checked.

### A verdict on my own rules that I can reproduce

- **Need:** A maintainer's own checks either do not run before a merge or run differently there than on
  their own machine, so a red result cannot be reproduced and a green one cannot be trusted.
- **Use case:** When a change is proposed, the maintainer uses this to have their own checks reach a
  verdict they could have reached themselves.
- **Success:** The verdict on a change is the verdict the maintainer gets on the same change locally.
- **Not included:** Supplying the rules. The checks stay the maintainer's own; this runs them and never
  decides what they should be.

Only a Python project can take this one. The other three features are language-neutral, and nothing
here commits to answering this one for other languages.

### No new dependency carrying a known advisory

- **Need:** A change can quietly start depending on something with a publicly known vulnerability, and
  by the time anyone hears, it has merged.
- **Use case:** When a change adds or moves a dependency, the maintainer uses this to have it stopped
  before merge if what it now depends on carries a known advisory of consequence.
- **Success:** A proposal that would introduce a known advisory is stopped; one that would not passes
  without comment.
- **Not included:** Refusing a dependency over its licence, or judging anything already depended on.
  Only what the change newly introduces is judged.

## Non-features

Each must stay true. None is a reason anyone adopts this repository.

- **A tool version a consumer must control is never pinned centrally.** It is the only reason a local
  verdict and a published one agree.
- **A published reference is never withdrawn or moved across a break.** What a consumer pins keeps
  meaning what it meant.
- **A check a consumer is told to require never reports success without judging.** A green result
  nobody investigates is worse than a red one.

## Remove, narrow, close

The only section carrying internal names, because traceability needs them.

| Current offer | Direction | Reason |
| --- | --- | --- |
| `pr-description` | remove | No feature names it. It produces content rather than a verdict, and the half of a pull request body worth having — why the change was made — cannot be derived from the commits. |
| `prek-advisory`, and the changed-files lint it compensates for | remove and narrow together | Judging only the files a change touched is the one thing making a published verdict differ from the maintainer's own full run. Judging the whole tree removes the gap, the second capability, and four inputs. |
| `apply-ruleset` | leave alone | Not a consumer feature. It stays as something the repository does for itself. |

## Test direction

**Retain.** Coverage of each feature's success statement, and of every constraint above. Three groups
earn their place: the fixture recording each capability's published surface, because a renamed input or
check name is the one break a consumer cannot absorb; the coverage of the version decision, because its
refusals are all that stand between a mistake and an immutable tag somebody else pinned; and the tests
that prove the other checks are not inert, because a check reading nothing reports success.

**Reduce.** Three tests, each going with the capability it covers rather than ahead of it. Nothing else
in the suite documents how the code happens to work.

**Reclassify rather than cut.** Coverage of the settings work protects an internal safeguard rather
than a consumer promise. That is not excess.

## Open decisions

None block simplification.
