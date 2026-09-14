import json
import re
import tomllib
from collections.abc import Iterator
from pathlib import Path
from typing import Any, NamedTuple, cast

import yaml

REPO = Path(__file__).resolve().parent.parent
WORKFLOW_DIR = REPO / ".github" / "workflows"
ACTION_DIR = REPO / "actions"
RULESET_DIR = REPO / ".github" / "rulesets"
CONVENTIONAL_COMMITS = WORKFLOW_DIR / "conventional-commits.yml"
FIXTURE = Path(__file__).parent / "published_surface.toml"

Doc = dict[Any, Any]

# The inputs a job's `if:` consults, which are the ones a caller can switch it off with.
INPUT_REF = re.compile(r"inputs\.([A-Za-z0-9_-]+)")

# A workflow's `on:` key is YAML 1.1's `true`, so a parser hands it back as the boolean and every
# lookup by the string finds nothing. Both spellings are read, because which one arrives depends on
# the parser rather than on the file.
ON_KEYS: tuple[Any, ...] = (True, "on")

LEVELS = {"none": 0, "read": 1, "write": 2}


def load(path: Path) -> Doc:
    return cast(Doc, yaml.safe_load(path.read_text(encoding="utf-8")))


def workflow_docs() -> dict[str, Doc]:
    return {path.stem: load(path) for path in sorted(WORKFLOW_DIR.glob("*.yml"))}


def action_docs() -> dict[str, Doc]:
    return {path.parent.name: load(path) for path in sorted(ACTION_DIR.glob("*/action.yml"))}


def ruleset_docs() -> dict[str, Doc]:
    return {
        path.stem: cast(Doc, json.loads(path.read_text(encoding="utf-8")))
        for path in sorted(RULESET_DIR.glob("*.json"))
    }


def required_contexts(doc: Doc) -> list[str]:
    for rule in cast(list[Doc], doc.get("rules", [])):
        if rule.get("type") == "required_status_checks":
            checks = cast(list[Doc], rule.get("parameters", {}).get("required_status_checks", []))
            return [str(check["context"]) for check in checks]
    return []


def workflow_paths() -> list[Path]:
    return sorted(WORKFLOW_DIR.glob("*.yml"))


def action_paths() -> list[Path]:
    return sorted(ACTION_DIR.glob("*/action.yml"))


def fixture() -> dict[str, Doc]:
    return cast(dict[str, Doc], tomllib.loads(FIXTURE.read_text(encoding="utf-8")))


def triggers(doc: Doc) -> Doc:
    for key in ON_KEYS:
        if key in doc:
            found: Any = doc[key]
            if isinstance(found, str):
                return {found: None}
            if isinstance(found, list):
                return dict.fromkeys(cast(list[Any], found))
            return cast(Doc, found)
    return {}


def is_capability(doc: Doc) -> bool:
    return "workflow_call" in triggers(doc)


def is_call_only(doc: Doc) -> bool:
    # A workflow reachable only by a call never has a run of its own, so its entry in the Actions
    # sidebar is permanently empty. Read from the trigger set, so a workflow gaining a trigger stops
    # being one of these without a list needing to be edited.
    return set(triggers(doc)) == {"workflow_call"}


def jobs(doc: Doc) -> Doc:
    return cast(Doc, doc.get("jobs", {}))


def job_names(doc: Doc) -> dict[str, str]:
    # Where a job declares no name GitHub falls back to its id, so the id is what a consumer would
    # have to require. This is the one place that fallback is written.
    return {str(job_id): str(job.get("name", job_id)) for job_id, job in jobs(doc).items()}


def check_names(doc: Doc) -> list[str]:
    # A consumer's required context is its own job id, then the called job's name.
    return sorted(job_names(doc).values())


class ComposedContext(NamedTuple):
    context: str
    workflow: str
    job: str
    calls: str | None
    cannot_judge: str | None


def _called_capability(uses: str) -> str | None:
    # Only a job-level `uses:` reaching this repository's own workflows composes a context beyond
    # its own name — the only place `$/.github/workflows/<name>.yml` can point.
    prefix = "$/.github/workflows/"
    if not uses.startswith(prefix):
        return None
    return uses.removeprefix(prefix).removesuffix(".yml")


def _cannot_judge(job: Doc, wf_triggers: Doc, capability: str | None) -> str | None:
    if capability is not None and fixture().get(capability, {}).get("judges", True) is False:
        return f"{capability} never judges what it names; the run may report success without checking anything"
    if "if" in job:
        return str(job["if"])
    if "pull_request" not in wf_triggers:
        events = ", ".join(str(event) for event in wf_triggers) or "no events"
        return f"the workflow declares no pull_request trigger, only {events}"
    return None


def switched_off(job: Doc, capability: str | None, called_job: str) -> str | None:
    # A switched-off check skips its job, and a skipped job reports success. Anything but the default or
    # a literal `true` is refused, an expression included: it cannot be resolved offline, so it is not
    # provably on.
    if capability is None:
        return None
    doc = workflow_docs().get(capability)
    if doc is None:
        return None
    given = cast(Doc, job.get("with") or {})
    for job_id, called in jobs(doc).items():
        if not isinstance(called, dict) or str(cast(Doc, called).get("name", job_id)) != called_job:
            continue
        for name in INPUT_REF.findall(str(cast(Doc, called).get("if", ""))):
            if name in given and given[name] is not True:
                return (
                    f"the call passes {name}: {given[name]!r}, and {capability}'s {called_job} job is "
                    f"gated on inputs.{name} — a skipped job reports success"
                )
    return None


def composed_contexts() -> list[ComposedContext]:
    # Reads only caller workflows — a capability's own jobs are not what a ruleset can require.
    out: list[ComposedContext] = []
    for wf_name, doc in workflow_docs().items():
        if is_capability(doc):
            continue
        wf_triggers = triggers(doc)
        for job_id, job in jobs(doc).items():
            if not isinstance(job, dict):
                continue
            job = cast(Doc, job)
            calling_half = str(job.get("name", job_id))
            capability = _called_capability(str(job["uses"])) if "uses" in job else None
            called_names = fixture().get(capability, {}).get("check_name") if capability else None
            cannot_judge = _cannot_judge(job, wf_triggers, capability)
            if called_names:
                for called_job in cast(list[str], called_names):
                    out.append(
                        ComposedContext(
                            context=f"{calling_half} / {called_job}",
                            workflow=wf_name,
                            job=job_id,
                            calls=capability,
                            cannot_judge=cannot_judge or switched_off(job, capability, called_job),
                        )
                    )
            else:
                out.append(
                    ComposedContext(
                        context=calling_half,
                        workflow=wf_name,
                        job=job_id,
                        calls=capability,
                        cannot_judge=cannot_judge,
                    )
                )
    return out


def allowed_commit_types() -> list[str]:
    # The grammar both required checks judge against, declared once as that capability's own default.
    # Read here rather than restated, so the notes gate and the grammar gate cannot disagree about
    # which types exist.
    call: Any = triggers(load(CONVENTIONAL_COMMITS)).get("workflow_call") or {}
    inputs = cast(Doc, cast(Doc, call).get("inputs", {}))
    default = cast(Doc, inputs.get("types", {})).get("default", "")
    return [line.strip() for line in str(default).splitlines() if line.strip()]


def declared_inputs(doc: Doc) -> set[str]:
    call: Any = triggers(doc).get("workflow_call") or {}
    return {str(name) for name in cast(Doc, call).get("inputs", {})}


def declared_input_specs(doc: Doc) -> dict[str, Doc]:
    # Each input's own mapping, so a caller can check for `description` and `default` without a
    # second YAML walk.
    call: Any = triggers(doc).get("workflow_call") or {}
    return {str(name): cast(Doc, spec) for name, spec in cast(Doc, call).get("inputs", {}).items()}


def declared_secrets(doc: Doc) -> set[str]:
    # A required secret a caller does not pass fails the run before any job exists, exactly as a
    # permission shortfall does, so the names are surface rather than documentation.
    call: Any = triggers(doc).get("workflow_call") or {}
    return {str(name) for name in cast(Doc, call).get("secrets", {})}


def action_inputs(doc: Doc) -> set[str]:
    return {str(name) for name in cast(Doc, doc.get("inputs", {}))}


def permission_blocks(doc: Doc) -> Iterator[tuple[str, Any]]:
    if "permissions" in doc:
        yield "workflow", doc["permissions"]
    for job_id, job in jobs(doc).items():
        if isinstance(job, dict) and "permissions" in cast(Doc, job):
            yield str(job_id), cast(Doc, job)["permissions"]


def blanket_permissions(doc: Doc) -> list[str]:
    # `permissions: read-all` names no scope, so it would compare equal to a capability demanding
    # nothing and pass the surface gate while granting the run everything.
    return [where for where, block in permission_blocks(doc) if not isinstance(block, dict)]


def permission_demand(doc: Doc) -> dict[str, str]:
    # What a caller must grant for the run to start: the highest level any block asks for. A called
    # job cannot exceed its caller, so the union is the demand rather than any single block.
    demand: dict[str, str] = {}
    for _, block in permission_blocks(doc):
        if not isinstance(block, dict):
            continue
        for scope, level in cast(Doc, block).items():
            if LEVELS.get(str(level), -1) > LEVELS.get(demand.get(str(scope), "none"), 0):
                demand[str(scope)] = str(level)
    return {scope: level for scope, level in demand.items() if level != "none"}


def values_at(node: Any, key: str, path: str = "") -> Iterator[tuple[str, str]]:
    # One walker for both the interpolation gate and the pin gate: naming the key rather than the
    # place it may appear means a value nested somewhere new is still read.
    if isinstance(node, dict):
        for k, value in cast(Doc, node).items():
            here = f"{path}.{k}" if path else str(k)
            if k == key and isinstance(value, str):
                yield here, value
            else:
                yield from values_at(value, key, here)
    elif isinstance(node, list):
        for index, value in enumerate(cast(list[Any], node)):
            yield from values_at(value, key, f"{path}[{index}]")


def every_yaml() -> Iterator[tuple[str, Doc]]:
    for path in workflow_paths() + action_paths():
        yield str(path.relative_to(REPO)), load(path)
