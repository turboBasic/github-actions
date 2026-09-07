# Contract: Owned Facts

Normative. One row per fact with more than one plausible home. The **anchor** is a distinctive
phrase from the owner's own text, and the check makes two assertions per row:

1. The anchor still appears in the owner. A row matching nothing is a row that has rotted, so
   rewriting the owner fails loudly and the table is updated in the same change.
2. The anchor appears nowhere else outside the declared exemptions.

Anchors catch the copy and the drift that follows it. A deliberate paraphrase is a new statement and
a reviewer's problem, not a check's — the same bargain `test_no_prose_document_names_a_concrete_major`
already makes.

## Rows

| Fact | Owner | Anchor |
| --- | --- | --- |
| A breaking change is a new tag, and released tags do not move | constitution I | `Patch tags are immutable` |
| Why a third-party tag cannot be trusted | constitution II | `retroactively repointed at malicious code` |
| Permissions reduce down a call chain and never rise | constitution III | `only ever reduce down a call chain` |
| Untrusted input reaches a shell as data | constitution IV | `never through inline` |
| Secrets are never written anywhere | constitution V | `written to a file, a log, an artifact` |
| Lint is not verification | constitution VI | `Lint does not verify a workflow` |
| No gate is loosened to make a run pass | constitution VII | `no rule disabled to` |
| How to object to a rule change | constitution Governance | `smallest alternative that meets the underlying need` |
| Conventions are not governed by the constitution | constitution Governance | `Conventions are not governed here` |
| What qualifies a rule as an invariant | constitution Governance | `expensive to reverse and cheap to commit by accident` |
| Which major is current | `README.md` Versioning | pattern `@?\bv\d`, already asserted |
| The label set and its axes | `CONTRIBUTING.md` Labels | `This table is the label set` |
| Where the version is decided | `CONTRIBUTING.md` Releasing | `the only place the version is decided` |
| How a release is cut and what it refuses | `CONTRIBUTING.md` Releasing | `approve a proposal` |
| How a workflow change is verified before the tag moves | `CONTRIBUTING.md` Verifying | `Run every workflow you change` |
| The allowed commit types | `conventional-commits.yml` default | already asserted against commitizen |
| The frozen input and permission surface | `tests/test_action_pins.py` | already the table |

The last two rows carry no anchor because a gate already holds them; they are listed so the
inventory is complete and so nobody adds a third copy of either into prose.

## What layer 2 keeps

The conventions layer keeps what it alone owns, and cites the rest by principle number. What
survives, by current section:

| Section | Disposition |
| --- | --- |
| Working style | keeps; adds the paragraph on overriding the user-level layer |
| Changes to these rules | shrinks to a citation of Governance plus the sentence about not objecting over conventions being *this* layer's business |
| Specs | keeps the size table; drops the vendoring mechanics to layer 3 |
| Tooling hierarchy | keeps the order **and the tool and task names** — naming `prek` or the lint task is the rule's content, not a mechanism behind it |
| Dependencies | keeps; drops the config filenames, which navigation owns |
| Workflows and actions | keeps naming, placement, input and permission conventions, and which changes break a caller; drops six restated principles, every test name, and the archaeology |
| Python | keeps in full — it is convention and names nothing below |
| Comments and docs | keeps in full |
| Quality gates | keeps the entry-point rule with its runner named, and "enforced by test" as a fact; drops every *test's* name and the reasoning behind a specific gate |
| Versioning | keeps what the number describes; drops the tag-immutability clause and the procedure |
| Git | keeps; drops "never commit a secret" as a citation of principle V |
| CI | keeps the self-call rule; drops the upstream issue number and the ignore's archaeology |

Every dropped item lands somewhere named, or is recorded as deliberately dropped. Nothing is
deleted without a destination — that is what the inventory task reconciles.

Layer 2 also **gains** one thing it does not have today: the layering rule itself. Rules about rules
are layer 2's business — that is what "Changes to these rules" already is — so the rule that each
fact has one owner and that references run one way is stated there, in a short paragraph, and owned
there. `docs/instruction-layers.md` explains the pattern for another repository to adopt; it is not
where this repository's copy of the rule lives, because layer 2 may not cite layer 3.
