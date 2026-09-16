import difflib
import json
import os
from typing import Any, NamedTuple, cast

from . import ERROR, NOTICE, annotate, emit, output, read_text, repository_directory

Doc = dict[str, Any]

# The six fields a write to the rulesets API accepts. Everything else a read returns is rejected on a
# write, so the committed file holds these and comparison is over these alone.
WRITABLE_FIELDS = frozenset(
    {"name", "target", "enforcement", "conditions", "rules", "bypass_actors"}
)

# A branch ruleset gates what may reach a ref; a tag one protects the ref itself. Nothing else is
# managed from the tree, so anything else is a mistake rather than a shape to support.
TARGETS = frozenset({"branch", "tag"})

NOTHING = "nothing"
CREATE = "create"
UPDATE = "update"
REFUSE = "refuse"


class Verdict(NamedTuple):
    verdict: str
    ruleset_id: str
    difference: str
    body: Doc | None
    message: str


def shape_problem(committed: Doc) -> str | None:
    unknown = sorted(set(committed) - WRITABLE_FIELDS)
    if unknown:
        return (
            f"the committed ruleset names {unknown}, and a write accepts only "
            f"{sorted(WRITABLE_FIELDS)}. A misspelled field reads as an absent one — fix the key"
        )
    missing = sorted(WRITABLE_FIELDS - set(committed))
    if missing:
        return f"the committed ruleset omits {missing}, which a write requires"
    target = committed.get("target")
    if target not in TARGETS:
        return f"the committed ruleset's target is {target!r}; only {sorted(TARGETS)} are in scope"
    rules = cast(list[Doc], committed["rules"])
    rule_types = [str(rule.get("type")) for rule in rules]
    if not rules:
        return (
            "the committed ruleset carries no rules, and a ruleset requiring nothing gates nothing"
        )
    # Only a branch ruleset gates on checks. A tag one protects the ref itself, so demanding a
    # status-checks rule there would refuse the very shape that makes a release tag immutable.
    if target != "branch":
        return None
    checks_rules = [rule for rule in rules if rule.get("type") == "required_status_checks"]
    if len(checks_rules) != 1:
        return (
            f"the committed ruleset's rule types are {rule_types}, and exactly one must be "
            "'required_status_checks' — a branch ruleset requiring nothing gates nothing"
        )
    contexts = cast(
        list[Doc], checks_rules[0].get("parameters", {}).get("required_status_checks", [])
    )
    if not contexts or any(not check.get("context") for check in contexts):
        return (
            "the committed ruleset's required-status-checks list is empty or carries an empty "
            "context; the context gate would pass on an empty set"
        )
    return None


def normalize(doc: Doc) -> Doc:
    # R4. A read orders lists as it pleases and fills defaults the file omits. Both sides are sorted the
    # same way and only the six writable fields compared, or a dispatch reports drift it did not cause.
    projected: Doc = {field: doc.get(field) for field in WRITABLE_FIELDS}

    rules = sorted(
        cast(list[Doc], projected.get("rules") or []), key=lambda rule: str(rule.get("type"))
    )
    normalized_rules: list[Doc] = []
    for rule in rules:
        rule = dict(rule)
        if rule.get("type") == "required_status_checks":
            params = dict(cast(Doc, rule.get("parameters") or {}))
            params["required_status_checks"] = sorted(
                cast(list[Doc], params.get("required_status_checks") or []),
                key=lambda check: str(check.get("context")),
            )
            rule["parameters"] = params
        normalized_rules.append(rule)
    projected["rules"] = normalized_rules

    projected["bypass_actors"] = sorted(
        cast(list[Doc], projected.get("bypass_actors") or []),
        key=lambda actor: (str(actor.get("actor_type")), actor.get("actor_id")),
    )

    conditions = dict(cast(Doc, projected.get("conditions") or {}))
    ref_name = dict(cast(Doc, conditions.get("ref_name") or {}))
    ref_name["include"] = sorted(
        str(name) for name in cast(list[Any], ref_name.get("include") or [])
    )
    ref_name["exclude"] = sorted(
        str(name) for name in cast(list[Any], ref_name.get("exclude") or [])
    )
    conditions["ref_name"] = ref_name
    projected["conditions"] = conditions

    return projected


def render_difference(committed: Doc, live: Doc) -> str:
    # A diff of the two documents, not a summary of which fields moved. This is the last thing read
    # before a write with no revert, and a per-field summary puts a whole `rules` array on one line.
    def rendered(doc: Doc) -> list[str]:
        projected = {field: doc.get(field) for field in sorted(WRITABLE_FIELDS)}
        return json.dumps(projected, indent=2, sort_keys=True).splitlines()

    # Live first, so `-` is what GitHub holds now and `+` is what the write would leave.
    return "\n".join(
        difflib.unified_diff(rendered(live), rendered(committed), "live", "committed", lineterm="")
    )


def decide(committed: Doc, live: list[Doc]) -> Verdict:
    # `live` holds details, not list-endpoint summaries: a summary carries no rules, conditions or
    # bypass_actors, and comparing against absent fields reports drift that is not there.
    problem = shape_problem(committed)
    if problem:
        return Verdict(REFUSE, "", "", None, problem)

    name = str(committed["name"])
    matches = [
        ruleset
        for ruleset in live
        if ruleset.get("source_type") == "Repository" and ruleset.get("name") == name
    ]

    if len(matches) > 1:
        ids = [str(ruleset.get("id")) for ruleset in matches]
        return Verdict(
            REFUSE,
            "",
            "",
            None,
            f"{len(matches)} rulesets named {name!r} exist on this repository, ids {ids} — the API "
            "does not make names unique. Resolve which one is meant before applying",
        )

    if not matches:
        body = {field: committed[field] for field in WRITABLE_FIELDS}
        return Verdict(
            CREATE,
            "",
            "",
            body,
            f"no ruleset named {name!r} exists on this repository; the committed file becomes a new one",
        )

    live_id = str(matches[0].get("id", ""))
    committed_norm = normalize(committed)
    live_norm = normalize(matches[0])
    if committed_norm == live_norm:
        return Verdict(
            NOTHING,
            live_id,
            "",
            None,
            f"{name!r} already matches the committed file; nothing to change",
        )

    body = {field: committed[field] for field in WRITABLE_FIELDS}
    difference = render_difference(committed_norm, live_norm)
    return Verdict(
        UPDATE,
        live_id,
        difference,
        body,
        f"{name!r} (id {live_id}) differs from the committed file; see the printed difference",
    )


def read_doc(path: str) -> Doc:
    with open(path, encoding="utf-8") as handle:
        return cast(Doc, json.load(handle))


def read_list(path: str) -> list[Doc]:
    with open(path, encoding="utf-8") as handle:
        return cast(list[Doc], json.load(handle))


def run() -> int:
    committed_path = read_text("COMMITTED")
    if not os.path.isfile(committed_path):
        annotate(ERROR, f"no committed ruleset at {committed_path!r} — check the dispatch's name")
        return 1

    verdict = decide(read_doc(committed_path), read_list(read_text("LIVE")))

    body_path = read_text("BODY_PATH")
    if verdict.body is not None and body_path:
        with open(body_path, "w", encoding="utf-8") as handle:
            json.dump(verdict.body, handle, indent=2)

    # Unpacked rather than passed as keywords: `ruleset-id` is the output name a caller reads, and a
    # hyphen is not an identifier.
    emit(
        **{
            "verdict": verdict.verdict,
            "ruleset-id": verdict.ruleset_id,
            "difference": verdict.difference,
            "body": body_path if verdict.body is not None else "",
            "message": verdict.message,
        }
    )
    annotate(ERROR if verdict.verdict == REFUSE else NOTICE, verdict.message)
    return 1 if verdict.verdict == REFUSE else 0


def committed_names(directory: str) -> list[str]:
    return sorted(name[: -len(".json")] for name in os.listdir(directory) if name.endswith(".json"))


def run_list() -> int:
    where = repository_directory()
    directory = os.path.join(where, read_text("RULESET_DIR") or ".github/rulesets")
    named = read_text("NAMED").strip()
    if named:
        emit(rulesets=json.dumps([named]))
        return 0
    if not os.path.isdir(directory):
        annotate(ERROR, f"no committed ruleset to read under {directory}")
        return 1
    names = committed_names(directory)
    if not names:
        # An empty matrix skips the job below, and a skipped job reports success — so a scheduled run
        # that listed nothing would be a green check that read no ruleset at all.
        annotate(ERROR, f"no committed ruleset to read under {directory}")
        return 1
    emit(rulesets=json.dumps(names))
    return 0


def run_read() -> int:
    # In full: a list-endpoint summary carries no rules, conditions or bypass_actors, so there would be
    # nothing to compare. `includes_parents=false` excludes an organisation's, which this cannot write.
    repository = read_text("GH_REPO").strip()
    destination = read_text("LIVE_PATH").strip()
    if not repository or not destination:
        annotate(ERROR, "reading the live rulesets needs both GH_REPO and LIVE_PATH")
        return 1
    listed = output(
        ("gh", "api", f"repos/{repository}/rulesets?includes_parents=false", "--jq", ".[].id")
    )
    live: list[Doc] = []
    for identifier in (line.strip() for line in listed.splitlines()):
        if not identifier:
            continue
        live.append(
            cast(
                Doc,
                json.loads(output(("gh", "api", f"repos/{repository}/rulesets/{identifier}"))),
            )
        )
    with open(destination, "w", encoding="utf-8") as handle:
        json.dump(live, handle)
    return 0


def run_apply() -> int:
    repository = read_text("GH_REPO").strip()
    verdict = read_text("VERDICT").strip()
    body = read_text("BODY").strip()
    identifier = read_text("RULESET_ID").strip()
    if not repository or not body or verdict not in {CREATE, UPDATE}:
        annotate(ERROR, f"applying a ruleset needs a body and a {CREATE} or {UPDATE} verdict")
        return 1
    if verdict == CREATE:
        output(("gh", "api", f"repos/{repository}/rulesets", "--input", body))
    else:
        if not identifier:
            annotate(ERROR, f"an {UPDATE} needs the live ruleset's id, and none was given")
            return 1
        output(
            ("gh", "api", "-X", "PUT", f"repos/{repository}/rulesets/{identifier}", "--input", body)
        )
    return 0
