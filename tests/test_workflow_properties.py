import re
import tomllib
from itertools import pairwise
from typing import Any, cast

from capabilities import (
    CONVENTIONAL_COMMITS,
    INPUT_REF,
    REPO,
    WORKFLOW_DIR,
    Doc,
    action_paths,
    declared_input_specs,
    declared_inputs,
    fixture,
    is_capability,
    jobs,
    load,
    triggers,
    workflow_docs,
    workflow_paths,
)

# A job gated on which event reached it. A skipped job reports success, so a required check reached
# from an event it does not handle passes without reading anything — and where a red check gets
# investigated, a green one does not.
EVENT_CONDITIONAL = re.compile(r"github\.event_name")

# The permission and its reason on one line. FR-004 makes the `permissions:` block its own
# documentation, which only works while the reason cannot drift from the demand it explains — so it
# sits beside it rather than a line above or a file away.
PERMISSION = re.compile(r"^\s*[a-z][a-z-]*:\s*(?:read|write|none)\s*(?:#(?P<reason>.*))?$")

TABLE_DELIMITER = re.compile(r"^\|[\s:|-]+\|$")
NAMES_A_DEFAULT = re.compile(r"default", re.IGNORECASE)

GOVERNS_A_CACHE = re.compile(r"cache", re.IGNORECASE)

# The steps of `project-ci` that judge the tree, which are also the tasks it invokes: the stage id, its
# switch and the task behind it are one word.
STAGES = ("lint", "build", "typecheck", "test")


def skipping_jobs(doc: Doc) -> set[str]:
    return {
        str(job_id)
        for job_id, job in jobs(doc).items()
        if EVENT_CONDITIONAL.search(str(job.get("if", "")))
    }


def test_every_event_conditional_job_appears_in_the_skip_table_with_a_reason() -> None:
    committed = fixture()
    for path in workflow_paths():
        doc = load(path)
        if not is_capability(doc):
            continue
        registered: set[str] = set()
        # A capability with no fixture row at all is the surface gate's failure to report, not this
        # one's; registering nothing here still fails below if it has a job that skips.
        for skip in committed.get(path.stem, {}).get("skips_under", []):
            assert skip["jobs"], f"{path.stem}: a skip entry naming no job asserts nothing"
            assert str(skip["event"]).strip(), f"{path.stem}: a skip entry naming no event"
            assert str(skip["reason"]).strip(), (
                f"{path.stem}: {skip['jobs']} skips under {skip['event']} with no reason. "
                "An exemption list without reasons is a dial on the gate"
            )
            registered |= {str(job) for job in skip["jobs"]}
        assert registered <= set(jobs(doc)), (
            f"{path.stem}: the skip table names {sorted(registered - set(jobs(doc)))}, "
            "which is not a job in the workflow"
        )
        assert registered == skipping_jobs(doc), (
            f"{path.stem}: jobs skipping on an event are {sorted(skipping_jobs(doc))}, "
            f"the skip table registers {sorted(registered)}. Every skip carries its reason or the "
            "gate reports green without judging"
        )


def test_every_permission_carries_its_reason_beside_it() -> None:
    unexplained: list[str] = []
    for path in workflow_paths() + action_paths():
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            match = PERMISSION.match(line)
            if match and not (match.group("reason") or "").strip():
                unexplained.append(f"{path.relative_to(REPO)}:{number}: {line.strip()}")
    assert unexplained == [], (
        "permission demanded with no reason beside it: "
        + "; ".join(unexplained)
        + ". A shortfall fails the run before any job exists, so the block is the only place a "
        "consumer can read what it is for"
    )


def test_the_permission_reader_tells_an_explained_grant_from_a_bare_one() -> None:
    # Pre-flight the matcher. Its steady state is an empty result, so a pattern that stopped matching
    # would report green over a tree of permissions nobody explained.
    explained = PERMISSION.match("      contents: read # the range check checks this tree out")
    assert explained is not None and (explained.group("reason") or "").strip()
    bare = PERMISSION.match("      contents: read")
    assert bare is not None and not (bare.group("reason") or "").strip()
    assert PERMISSION.match("    timeout-minutes: 5") is None


def steps_of(name: str, job_id: str) -> list[Doc]:
    return list(jobs(load(WORKFLOW_DIR / f"{name}.yml"))[job_id]["steps"])


def uses_slugs(steps: list[Doc]) -> set[str]:
    # The slug is the part before `@`. The digest is deliberately not read here: the workflow owns
    # the pin and test_action_pins.py owns whether it is a full SHA, so a bump stays a one-file edit.
    return {str(step["uses"]).partition("@")[0] for step in steps if "uses" in step}


def test_dependency_review_uses_only_the_pinned_action() -> None:
    # FR-002, FR-015: no checkout and no task-runner step. The action reads the difference from the
    # API, so a checkout beside it would be this capability reading a tree it has no reason to have.
    slugs = uses_slugs(steps_of("dependency-review", "dependency-review"))
    assert slugs == {"actions/dependency-review-action"}, (
        f"dependency-review's job uses {sorted(slugs)}, expected exactly "
        "{'actions/dependency-review-action'}. A checkout or a task-runner step here is what "
        "FR-002/FR-015 forbid"
    )


def test_the_uses_slug_reader_refuses_a_checkout_beside_the_real_step() -> None:
    # Pre-flight the reader (FR-022): its steady state is a one-element set, so a change that stopped
    # it finding anything would report green over a capability that checks the caller's tree out.
    slugs = uses_slugs(
        [
            {"uses": "actions/checkout@abc123"},
            {"uses": "actions/dependency-review-action@a1d282b"},
        ]
    )
    assert slugs == {"actions/checkout", "actions/dependency-review-action"}


# The one key this capability passes the action. Every other key the action declares — the pull
# request comment, a licence list, an override — stays unset, so the action's defaults are the policy.
ALLOWED_REVIEW_INPUT = "fail-on-severity"


def review_with_keys(steps: list[Doc]) -> set[str]:
    step = next(step for step in steps if step.get("id") == "review")
    return {str(key) for key in cast(Doc, step.get("with") or {})}


def test_dependency_review_passes_the_action_only_its_one_input() -> None:
    keys = review_with_keys(steps_of("dependency-review", "dependency-review"))
    assert keys == {ALLOWED_REVIEW_INPUT}, (
        f"dependency-review's review step passes {sorted(keys)}, the one key this capability allows "
        f"is {ALLOWED_REVIEW_INPUT!r}. comment-summary-in-pr at always or on-failure demands "
        "pull-requests: write, which every caller would then have to grant before any job exists"
    )


def test_the_with_key_reader_finds_the_extra_key_beside_the_allowed_one() -> None:
    # Pre-flight the reader. Its steady state is a one-element set, so a reader that stopped finding
    # the `with:` block would report green over a capability demanding pull-requests: write.
    keys = review_with_keys(
        [{"id": "review", "with": {"fail-on-severity": "low", "comment-summary-in-pr": "always"}}]
    )
    assert keys == {ALLOWED_REVIEW_INPUT, "comment-summary-in-pr"}


def undocumented_inputs(name: str, specs: dict[str, Doc]) -> list[str]:
    complaints: list[str] = []
    for input_name, spec in specs.items():
        if not str(spec.get("description", "")).strip():
            complaints.append(f"{name}: input {input_name!r} has no description")
        if "default" not in spec:
            complaints.append(f"{name}: input {input_name!r} has no default")
    return complaints


def test_every_published_workflow_input_documents_itself() -> None:
    # FR-004.
    committed = fixture()
    missing: list[str] = []
    for name, doc in workflow_docs().items():
        row = committed.get(name, {})
        if not (row.get("kind") == "workflow" and row.get("published")):
            continue
        missing += undocumented_inputs(name, declared_input_specs(doc))
    assert missing == [], (
        "; ".join(missing) + ". An input whose behaviour when unset is unwritten is a promise with "
        "nothing behind it: give it a description and an explicit default in the workflow that "
        "declares it"
    )


def test_the_input_spec_check_names_the_key_each_input_is_missing() -> None:
    # Pre-flight the check. Its steady state is an empty list, so a check that stopped reading a spec
    # would report green over a published input nobody documented.
    complaints = undocumented_inputs(
        "synthetic",
        {
            "no-description": {"type": "string", "default": "low"},
            "no-default": {"type": "string", "description": "the floor a finding fails at"},
        },
    )
    assert complaints == [
        "synthetic: input 'no-description' has no description",
        "synthetic: input 'no-default' has no default",
    ]


def find_graph_off_step(steps: list[Doc]) -> Doc | None:
    # Found by id, never by retyping the condition — a reworded condition would then match nothing
    # and this would report green over a missing diagnostic.
    matches = [step for step in steps if step.get("id") == "graph-off"]
    assert len(matches) <= 1, f"more than one step id 'graph-off': {matches}"
    return matches[0] if matches else None


def test_dependency_review_names_the_setting_it_cannot_switch_on() -> None:
    # FR-011, FR-024.
    step = find_graph_off_step(steps_of("dependency-review", "dependency-review"))
    assert step is not None, (
        "dependency-review names no step id 'graph-off'. Add one, gated on `failure() && "
        "steps.review.outputs.dependency-changes == ''`, whose run: names the dependency-graph "
        "setting and says this capability cannot switch it on for the caller"
    )
    condition = str(step.get("if", ""))
    assert "failure()" in condition, (
        f"graph-off runs under `if: {condition}`, which does not check failure() — it could fire on a "
        "run that judged a real advisory"
    )
    assert "steps.review.outputs.dependency-changes" in condition, (
        f"graph-off runs under `if: {condition}`, which does not read dependency-changes, the "
        "discriminator between a run that read the comparison and one that judged nothing"
    )
    script = str(step.get("run", ""))
    assert "security_analysis" in script, (
        f"graph-off's run: {script!r} does not name the dependency-graph setting"
    )
    assert "cannot" in script.lower(), (
        f"graph-off's run: {script!r} does not say this capability cannot switch the setting on"
    )


def test_the_graph_off_finder_reports_the_absence_rather_than_passing() -> None:
    # Pre-flight the finder with a synthetic step list carrying no `graph-off` id.
    assert find_graph_off_step([{"id": "review"}]) is None


def exclude_disagreement(excluded: set[str], callers: set[str]) -> tuple[set[str], set[str]]:
    # The two directions separately: callers no exclude entry names, then entries naming a workflow
    # that is a capability now. A bare `==` would name neither in the failure.
    return callers - excluded, excluded - callers


def test_the_release_exclude_list_names_exactly_the_non_capability_workflows() -> None:
    # FR-018. Read at release time and nowhere else, so a caller missing here has no symptom until it
    # skews a version decision — the failure mode is silence, which is why this is a gate.
    config = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))
    excluded = {
        str(entry)
        for entry in config["tool"]["turbobasic-release"]["exclude"]
        if str(entry).startswith(".github/workflows/")
    }
    callers = {
        f".github/workflows/{name}.yml"
        for name, doc in workflow_docs().items()
        if not is_capability(doc)
    }
    # Two empty sets agree, which is the one state this gate passes without reading the tree.
    assert callers, (
        "no workflow in the tree reads as a caller, so the comparison below would agree over nothing. "
        "is_capability or workflow_docs has stopped reading the tree — fix the reader, not this gate"
    )
    unlisted, stale = exclude_disagreement(excluded, callers)
    assert not unlisted and not stale, (
        f"[tool.turbobasic-release].exclude does not name {sorted(unlisted)}, and names "
        f"{sorted(stale)} which are capabilities. A caller missing from exclude makes a later edit to "
        "this repository's own call site count towards a break; an entry naming a workflow that has "
        "since become a capability keeps consumer surface out of the range a release reads"
    )


def test_the_exclude_comparison_names_both_directions_it_claims_to_catch() -> None:
    # Pre-flight the comparison. Set equality alone would report a disagreement without saying which
    # side, and the gate's message promises both.
    unlisted, stale = exclude_disagreement(
        {".github/workflows/ci.yml", ".github/workflows/release.yml"},
        {".github/workflows/ci.yml", ".github/workflows/propose-on-merge.yml"},
    )
    assert unlisted == {".github/workflows/propose-on-merge.yml"}
    assert stale == {".github/workflows/release.yml"}


def test_no_capability_takes_an_input_governing_the_cache() -> None:
    # Hook environments are cached unconditionally. An input that silently did nothing unless a
    # second one was also set was worse than no input at all, and removing one is a break.
    for name, doc in workflow_docs().items():
        if not is_capability(doc):
            continue
        governing = sorted(
            input_ for input_ in declared_inputs(doc) if GOVERNS_A_CACHE.search(input_)
        )
        assert governing == [], (
            f"{name}: declares {governing}, but caching is not a call site's choice"
        )


def test_the_cache_input_matcher_reads_a_name_it_is_given() -> None:
    # Pre-flight the matcher, or a capability could declare a caching input and this gate would not see
    # it. No capability declares one today, so the gate has nothing else to prove it works.
    assert GOVERNS_A_CACHE.search("cache-key")
    assert GOVERNS_A_CACHE.search("restore-cache")
    assert not GOVERNS_A_CACHE.search("lint-task")


# An input is worth its place only where the caller knows something the callee cannot. A timeout is that
# where the runtime is a function of the caller's tree, and nowhere else — every other knob on a
# published surface is a promise with nothing behind it.
TIMEOUT_INPUT = "timeout-minutes"

MAY_TAKE_A_TIMEOUT = {
    "project-ci": "runs the caller's own tasks and cannot know how long they take",
}


def test_a_timeout_input_exists_only_where_the_caller_knows_the_runtime() -> None:
    # Set equality, not a subset: a capability joining the set fails, and one leaving it fails too, so
    # the justification above and the tree cannot part company in either direction.
    declaring = {
        name
        for name, doc in workflow_docs().items()
        if is_capability(doc) and TIMEOUT_INPUT in declared_inputs(doc)
    }
    assert declaring == set(MAY_TAKE_A_TIMEOUT), (
        f"capabilities declaring {TIMEOUT_INPUT} are {sorted(declaring)}; the ones a caller can time "
        f"better than the callee are {sorted(MAY_TAKE_A_TIMEOUT)}. "
        + "; ".join(f"{name} {why}" for name, why in sorted(MAY_TAKE_A_TIMEOUT.items()))
        + ". A capability whose runtime is its own fixes its timeout in its jobs; adding or removing this "
        "input changes the published surface, so the fixture moves in the same change"
    )


def test_every_job_of_a_capability_without_the_input_fixes_its_own_timeout() -> None:
    # An input removed leaves nothing behind: the schema hook refuses a job with no timeout at all, and
    # this says the same thing where the removal happened, so the two are not one hook away from silence.
    unbounded: list[str] = []
    for name, doc in workflow_docs().items():
        if not is_capability(doc) or name in MAY_TAKE_A_TIMEOUT:
            continue
        for job_id, job in jobs(doc).items():
            if TIMEOUT_INPUT not in job:
                unbounded.append(f"{name}: job {job_id}")
    assert unbounded == [], (
        f"jobs with no {TIMEOUT_INPUT} of their own: {unbounded}. Their capability takes no timeout "
        "input, so nothing else would bound them"
    )


def test_project_ci_invokes_the_fixed_contract_and_prepares_nothing() -> None:
    commands = {
        str(step.get("id", "")): str(step.get("run", "")).strip()
        for step in steps_of("project-ci", "project-ci")
        if "run" in step
    }
    expected = {stage: f"mise run {stage}" for stage in STAGES}
    assert {name: run for name, run in commands.items() if name in expected} == expected, (
        f"project-ci runs {commands}. Each stage invokes the task of its own name: a task name is never "
        "an input, because caller-chosen text on a command line is what principle VI forbids"
    )
    elsewhere = {
        name: step.get("working-directory")
        for step in steps_of("project-ci", "project-ci")
        if (name := str(step.get("id", ""))) in expected
        and step.get("working-directory") != "${{ inputs.working-directory }}"
    }
    assert elsewhere == {}, (
        f"project-ci stages not running in the component's directory: {elsewhere}. A stage left at the "
        "root reports on a component the check name does not say"
    )
    assert set(commands) - set(expected) == {"stages"}, (
        f"project-ci runs {sorted(set(commands) - set(expected))} besides its stages and the refusal. A "
        "lockfile install or a module download here is a preparation belonging to the task that needs it"
    )


def test_the_refusal_fires_when_every_stage_is_off_and_not_before() -> None:
    refusal = next(
        step for step in steps_of("project-ci", "project-ci") if step.get("id") == "stages"
    )
    condition = " ".join(str(refusal.get("if", "")).split())
    assert condition == " && ".join(f"!inputs.run-{stage}" for stage in STAGES), (
        f"project-ci's refusal runs under `if: {condition}`. Every stage joins it: a narrower condition "
        "lets a call judging nothing report success, a wider one refuses a call that would have judged"
    )


def test_each_stage_of_project_ci_is_gated_on_its_own_switch_and_nothing_else() -> None:
    # An input named for a stage governs that stage entirely, so a second clause is either an input
    # that half-works or a stage that goes quiet under some event while its switch still reads on.
    for step in steps_of("project-ci", "project-ci"):
        stage = str(step.get("id", ""))
        if stage not in STAGES:
            continue
        condition = str(step.get("if", ""))
        consulted = sorted(set(INPUT_REF.findall(condition)))
        expected = f"run-{stage}"
        assert consulted == [expected], (
            f"project-ci's {stage} stage runs under `if: {condition}`, consulting {consulted}. Its own "
            f"switch is {expected} and nothing else belongs there: an input named for a stage governs "
            "that stage entirely or it is misnamed"
        )
        assert not EVENT_CONDITIONAL.search(condition), (
            f"project-ci's {stage} stage runs under `if: {condition}`, which reads the event. A stage "
            "that judges nothing under some events reports success on those events while its switch "
            "still says it is on"
        )


# The writes a step may perform. Three steps, not one invocation: the ordering and the conditions below
# are principle V's protection, and collapsing them takes every gate here to nothing found.
CREATES_A_REF = ("create-tag", "publish-release", "move-ref")


def ref_writes(step: Doc) -> str:
    # `run:` is read as well as the action, so a step reverting to bare `gh` cannot pass unread.
    named = str(cast(dict[str, Any], step.get("with", {})).get("command", ""))
    if named in CREATES_A_REF:
        return named
    script = str(step.get("run", ""))
    return next(
        (marker for marker in ("git/refs", "git/tags", "gh release create") if marker in script), ""
    )


# Writing a version means authoring a commit. The release path tags what a merged change already
# decided, so it never authors one — the proposal path is where a version is written. The write action
# answers `write-proposal`, which authors one, so the `command:` a step names counts as much as its shell.
WRITES_A_VERSION = ("git commit", "cz bump", "sed -i", "bump-my-version")
AUTHORS_A_COMMIT = ("write-proposal",)


def release_steps() -> list[Doc]:
    return steps_of("release", "tag-and-publish")


def test_no_ref_creating_step_precedes_the_refusals() -> None:
    # Principle V's structural gate. A refusal after a tag exists is not a refusal, because a version
    # tag is immutable and cannot be withdrawn — so ordering is the whole protection.
    steps = release_steps()
    decided = next(index for index, step in enumerate(steps) if step.get("id") == "decide")
    for index, step in enumerate(steps):
        if ref_writes(step):
            assert index > decided, (
                f"release step {step.get('id')!r} creates a ref at position {index}, before the "
                f"refusals at {decided}. Every refusal runs before any ref exists or none of them mean "
                "anything"
            )


def _job_calling(doc: Doc, capability: str) -> str | None:
    target = f"$/.github/workflows/{capability}.yml"
    for job_id, job in jobs(doc).items():
        if not isinstance(job, dict):
            continue
        if str(cast(Doc, job).get("uses", "")) == target:
            return str(job_id)
    return None


def _needs_of(job: Doc) -> list[str]:
    needs: Any = job.get("needs") or []
    return (
        [str(needs)] if isinstance(needs, str) else [str(need) for need in cast(list[Any], needs)]
    )


def _depends_on(doc: Doc, job_id: str, target: str) -> bool:
    frontier = [job_id]
    seen: set[str] = set()
    while frontier:
        current = frontier.pop()
        job = jobs(doc).get(current)
        if not isinstance(job, dict):
            continue
        for need in _needs_of(cast(Doc, job)):
            if need == target:
                return True
            if need not in seen:
                seen.add(need)
                frontier.append(need)
    return False


def _pushes_to_main(doc: Doc) -> bool:
    push = triggers(doc).get("push")
    return isinstance(push, dict) and "main" in (cast(Doc, push).get("branches") or [])


def test_release_and_release_proposal_never_reach_one_push_unordered() -> None:
    # release-proposal reads the tag list at checkout. Called beside release on the same push rather than
    # behind it, it measures against a tag that does not exist yet, on every release merge — the loser is
    # whichever side does less work, which is always release-proposal.
    release_site: tuple[str, str] | None = None
    proposal_site: tuple[str, Doc, str] | None = None
    for name, doc in workflow_docs().items():
        if is_capability(doc) or not _pushes_to_main(doc):
            continue
        release_job = _job_calling(doc, "release")
        if release_job:
            release_site = (name, release_job)
        proposal_job = _job_calling(doc, "release-proposal")
        if proposal_job:
            proposal_site = (name, doc, proposal_job)

    assert release_site is not None and proposal_site is not None, (
        "no caller on push: branches: [main] calls both release and release-proposal. Either this "
        "repository stopped calling one of them, or the readers above have stopped finding it — check "
        "that before reading this as the race being fixed"
    )

    release_name, release_job_id = release_site
    proposal_name, proposal_doc, proposal_job_id = proposal_site

    assert release_name == proposal_name, (
        f"release is called from {release_name}.yml and release-proposal from {proposal_name}.yml, two "
        "separate workflow files that both fire on push: branches: [main]. needs: cannot order jobs "
        "across workflow files, so nothing stops release-proposal from reading the tag list before the "
        "same push's release job has written to it. Fold both calls into one workflow file"
    )
    assert _depends_on(proposal_doc, proposal_job_id, release_job_id), (
        f"{proposal_name}.yml's {proposal_job_id!r} job calls release-proposal without depending on "
        f"{release_job_id!r}, which calls release. release-proposal reads the tag list at checkout, so "
        f"without `needs: {release_job_id}` it can run before a same-push release has tagged anything. "
        f"Add `needs: {release_job_id}` to the {proposal_job_id!r} job in "
        f".github/workflows/{proposal_name}.yml"
    )


def test_the_ordering_readers_find_the_calls_and_the_dependency_they_are_given() -> None:
    # Pre-flight the three readers above. Their steady state here is "found and ordered", so a reader
    # that stopped matching a `uses:` or a `needs:` would report green over the race itself.
    given: Doc = {
        "on": {"push": {"branches": ["main"]}},
        "jobs": {
            "release": {"uses": "$/.github/workflows/release.yml"},
            "gate": {"needs": "release"},
            "proposal": {"needs": ["gate"], "uses": "$/.github/workflows/release-proposal.yml"},
        },
    }
    assert _pushes_to_main(given)
    assert not _pushes_to_main({"on": {"push": {"branches": ["staging"]}}})
    assert _job_calling(given, "release") == "release"
    assert _job_calling(given, "release-proposal") == "proposal"
    assert _depends_on(given, "proposal", "release")
    assert not _depends_on(given, "release", "proposal")


GUARD_OUTPUT = "steps.guard.outputs.already-released"

# The one step between `guard` and `close` that must stay unconditional, with why: `close` still needs
# a token to shut a stale open proposal even on a run the guard has already declined.
RUNS_REGARDLESS_OF_THE_GUARD = {"token"}


def test_every_step_between_the_guard_and_the_close_is_gated_on_it() -> None:
    # release-proposal's backstop. A run landing on a commit a release already tagged must skip every
    # step that would read a stale tag list or write a wrong proposal, not only the writes at the end —
    # `close` already gates those on an empty range.
    steps = steps_of("release-proposal", "propose")
    ids = [str(step.get("id", "")) for step in steps]
    assert "guard" in ids and "close" in ids, (
        "release-proposal names no step id 'guard' or no step id 'close', so this gate places nothing"
    )
    start, end = ids.index("guard") + 1, ids.index("close")
    assert start < end, "release-proposal's 'guard' step does not precede its 'close' step"
    not_gated = [
        step.get("id") or step.get("name")
        for step in steps[start:end]
        if step.get("id") not in RUNS_REGARDLESS_OF_THE_GUARD
        and GUARD_OUTPUT not in str(step.get("if", ""))
    ]
    assert not_gated == [], (
        f"release-proposal steps {not_gated} run between 'guard' and 'close' with no `if:` reading "
        f"{GUARD_OUTPUT} — a run that already declined still pays for them"
    )


def test_the_step_range_finder_reports_the_step_nothing_gates() -> None:
    # Pre-flight the slice above with a synthetic step list, or a rename of either id would report
    # green over a step nothing gates.
    steps: list[Doc] = [
        {"id": "guard"},
        {"id": "loud", "if": f"{GUARD_OUTPUT} != 'true'"},
        {"id": "token"},
        {"name": "quiet"},
        {"id": "close"},
    ]
    ids = [str(step.get("id", "")) for step in steps]
    start, end = ids.index("guard") + 1, ids.index("close")
    not_gated = [
        step.get("id") or step.get("name")
        for step in steps[start:end]
        if step.get("id") not in RUNS_REGARDLESS_OF_THE_GUARD
        and GUARD_OUTPUT not in str(step.get("if", ""))
    ]
    assert not_gated == ["quiet"]


def test_every_ref_creating_step_is_gated_on_the_verdict_and_on_the_dry_run() -> None:
    # `proceed` is not permission to create a ref: a dry run proceeds and creates nothing. Both gates
    # or a dry run tags for real.
    found = 0
    for step in release_steps():
        if not ref_writes(step):
            continue
        found += 1
        condition = str(step.get("if", ""))
        assert "steps.decide.outputs.proceed" in condition, (
            f"release step {step.get('id')!r} creates a ref under `if: {condition}`, which does not "
            "read the verdict"
        )
        assert "inputs.dry-run" in condition, (
            f"release step {step.get('id')!r} creates a ref under `if: {condition}`, which does not "
            "exclude a dry run. A dry run that tags is not a dry run"
        )
    assert found >= 3, (
        f"only {found} ref-creating steps found in release.yml, so this gate is reading the wrong "
        "thing — the tag, the release and the moving ref are three"
    )


def test_no_step_in_the_release_path_writes_a_version() -> None:
    # The version released is what a merged change decided, and this capability only tags it. The
    # proposal path writes versions; this one is gated against ever doing so.
    offending: list[str] = []
    for step in release_steps():
        script = str(step.get("run", ""))
        offending += [
            f"{step.get('id')}: {marker}" for marker in WRITES_A_VERSION if marker in script
        ]
        named = str(cast(dict[str, Any], step.get("with", {})).get("command", ""))
        offending += [
            f"{step.get('id')}: {named}" for marker in AUTHORS_A_COMMIT if named == marker
        ]
    assert offending == [], (
        f"release.yml authors a change: {offending}. It tags what was already decided, and a version "
        "it wrote itself would be a version no review ever saw"
    )


def test_the_three_writes_happen_in_the_order_the_last_one_depends_on() -> None:
    # The moving ref goes last, once the release exists. A failure before it leaves consumers on the
    # previous release rather than on a ref naming an unpublished one.
    performed = [write for step in release_steps() if (write := ref_writes(step))]
    assert performed == ["create-tag", "publish-release", "move-ref"], (
        f"release.yml performs its writes as {performed}. The tag is created before the release that "
        "verifies it, and the compatibility ref moves only once that release exists — none of the three "
        "can be withdrawn, so the order is the whole protection"
    )


def test_the_write_reader_finds_both_the_action_and_a_bare_call() -> None:
    # Pre-flight both shapes. Every write goes through the action today, so the `run:` half is otherwise
    # never exercised.
    assert ref_writes({"with": {"command": "move-ref"}}) == "move-ref"
    assert ref_writes({"with": {"command": "preflight"}}) == ""
    assert ref_writes({"run": 'gh api "repos/$GH_REPO/git/tags" -f tag=v1'}) == "git/tags"
    assert ref_writes({"run": "gh release create v1"}) == "gh release create"
    assert ref_writes({"run": "echo nothing"}) == ""


def test_the_version_writing_markers_match_a_step_that_authors_one() -> None:
    # Pre-flight the markers. No step in the release path writes a version, which is the point, so the
    # gate above can never demonstrate that its tuple still matches anything.
    assert any(marker in 'git commit -m "chore: release v1.2.3"' for marker in WRITES_A_VERSION)
    assert any(marker in "uv run cz bump --yes" for marker in WRITES_A_VERSION)
    assert not any(
        marker in "gh release create v1.2.3 --notes-file notes.md" for marker in WRITES_A_VERSION
    )
    # And the shape the shell markers cannot see: an action asked to author one.
    assert "write-proposal" in AUTHORS_A_COMMIT
    assert "create-tag" not in AUTHORS_A_COMMIT


# Only a write sends a body, which is what separates it from the read above it. Both the action and the
# `--input` a bare call would use are read.
RULESET_WRITE = "$/actions/ruleset-write"
SENDS_A_BODY = "--input"


def sends_a_body(step: Doc) -> bool:
    return str(step.get("uses", "")) == RULESET_WRITE or SENDS_A_BODY in str(step.get("run", ""))


def apply_steps() -> list[Doc]:
    return steps_of("apply-ruleset", "apply")


def test_the_applier_is_reachable_by_dispatch_and_a_schedule_alone() -> None:
    # FR-003. A push or a merge trigger would apply whatever the tree said at that commit, before
    # anyone had read the difference, and a ruleset write has no revert.
    reached_by = set(triggers(load(WORKFLOW_DIR / "apply-ruleset.yml")))
    assert reached_by == {"workflow_dispatch", "schedule"}, (
        f"apply-ruleset is reachable from {sorted(reached_by)}. Applying is a human act, and the "
        "schedule is the read that never writes"
    )


def test_every_ruleset_writing_step_is_gated_on_the_event_the_dry_run_and_the_verdict() -> None:
    # The dispatch-only half of FR-003, which the trigger set alone no longer holds. Deleting any one
    # of the three clauses gives a cron that writes, a dry run that writes, or a write over a refusal.
    found = 0
    for step in apply_steps():
        if not sends_a_body(step):
            continue
        found += 1
        condition = str(step.get("if", ""))
        assert "github.event_name == 'workflow_dispatch'" in condition, (
            f"apply-ruleset step {step.get('name')!r} writes under `if: {condition}`, which does not "
            "pin the event. `inputs.dry-run` is absent on a schedule and an absent input compares "
            "equal to false, so the cron would write"
        )
        assert "inputs.dry-run" in condition, (
            f"apply-ruleset step {step.get('name')!r} writes under `if: {condition}`, which does not "
            "exclude a dry run. A dry run that writes is not a dry run"
        )
        assert "steps.decide.outputs.verdict" in condition, (
            f"apply-ruleset step {step.get('name')!r} writes under `if: {condition}`, which does not "
            "read the verdict, so it would write over a refusal"
        )
    assert found == 1, (
        f"{found} ruleset-writing steps found in apply-ruleset.yml, expected exactly one — this gate "
        "is reading the wrong thing, or a second write appeared beside the gated one"
    )


def test_the_body_sending_reader_finds_both_the_action_and_a_bare_call() -> None:
    # Pre-flight both shapes. The write goes through the action today, so the `run:` half is otherwise
    # never exercised.
    assert sends_a_body({"uses": RULESET_WRITE})
    assert sends_a_body({"run": 'gh api "repos/$GH_REPO/rulesets" --input "$BODY"'})
    assert not sends_a_body({"uses": "$/actions/ruleset-state"})
    assert not sends_a_body({"run": 'gh api "repos/$GH_REPO/rulesets" --jq .id'})


def test_the_scheduled_read_fails_on_any_verdict_but_nothing() -> None:
    # A condition that stops matching leaves a scheduled run reporting success over a live ruleset
    # nobody is applying.
    alarm = [step for step in apply_steps() if step.get("id") == "drift"]
    assert len(alarm) == 1, (
        "apply-ruleset names no step `drift`, so nothing reports that the live ruleset stopped "
        "matching the tree and every scheduled run is a green check that read nothing"
    )
    condition = str(alarm[0].get("if", ""))
    assert "github.event_name == 'schedule'" in condition, (
        f"the drift alarm runs under `if: {condition}`, which does not pin the schedule. A dispatch "
        "exits successfully on a difference, because a difference is the reason to dispatch"
    )
    assert "verdict != 'nothing'" in condition, (
        f"the drift alarm runs under `if: {condition}`, which does not read the verdict, so drift "
        "either never fails or every run does"
    )


def test_no_workflow_anywhere_triggers_on_pull_request_target() -> None:
    # It runs with this repository's own token while the pull request's text is a fork's to choose,
    # so a trigger added here hands that token whatever the fork wrote.
    offending = [
        str(path.stem) for path in workflow_paths() if "pull_request_target" in triggers(load(path))
    ]
    assert offending == [], f"{offending} trigger on pull_request_target"


def test_both_grammar_jobs_pin_the_event_they_can_judge() -> None:
    # Pinning the event is also what puts `pull_request_target` structurally out of reach: neither job
    # runs under any event but the one it reads a title and a range from.
    doc = load(CONVENTIONAL_COMMITS)
    found = jobs(doc)
    # Without this the loop below passes over an empty map, so a reader that stopped finding jobs would
    # report green while neither grammar check pinned its event.
    assert len(found) == 2, (
        f"conventional-commits declares jobs {sorted(found)}; this gate judges the two grammar jobs. "
        "Reading a different number means it is looking at the wrong workflow, or a job appeared that "
        "nothing here holds to an event"
    )
    for job_id, job in found.items():
        condition = str(job.get("if", ""))
        assert "github.event_name == 'pull_request'" in condition, (
            f"conventional-commits job {job_id} runs under `if: {condition}`, which does not pin the "
            "event to pull_request. There is no title and no range to judge under any other"
        )


def table_headers(text: str) -> list[list[str]]:
    lines = text.splitlines()
    return [
        [cell.strip() for cell in line.strip().strip("|").split("|")]
        for line, following in pairwise(lines)
        if line.lstrip().startswith("|") and TABLE_DELIMITER.match(following.strip())
    ]


def test_no_readme_table_names_a_default() -> None:
    # An input's default is owned by the capability YAML. A README column headed `Default` is a
    # second owner, and the two drift into shipping a promise the workflow does not keep.
    offending = [
        cell
        for header in table_headers((REPO / "README.md").read_text(encoding="utf-8"))
        for cell in header
        if NAMES_A_DEFAULT.search(cell)
    ]
    assert offending == [], (
        f"README.md has a table column headed {offending}. Defaults live in the capability YAML, "
        "which cannot drift from itself; the README carries a call site and prose"
    )


def test_the_table_reader_finds_a_table_it_is_given() -> None:
    # Pre-flight the reader, or a change that stops it matching anything reports green over a README
    # full of input tables.
    headers = table_headers("| Input | Default |\n| --- | --- |\n| a | b |\n")
    assert headers == [["Input", "Default"]]
    assert table_headers("| Input | Default |\nnot a table\n") == []


# Absent is not false: a run the guard declined never reaches the decision, so a condition testing
# against `true` would read an unmeasured range as one worth proposing.
EMPTY_VERDICT = "steps.next.outputs.empty"
CLOSES_A_STALE_PROPOSAL = f"{EMPTY_VERDICT} != 'false'"
ACTS_ON_A_MEASURED_RANGE = f"{EMPTY_VERDICT} == 'false'"


def proposal_steps() -> list[Doc]:
    return steps_of("release-proposal", "propose")


def test_nothing_writes_a_proposal_for_a_range_no_decision_measured() -> None:
    steps = proposal_steps()
    ids = [str(step.get("id", "")) for step in steps]
    assert "close" in ids, "release-proposal names no step id 'close', so this gate places nothing"
    after = steps[ids.index("close") + 1 :]
    assert after, "no step follows 'close', so this gate holds nothing"
    wrong = [
        f"{step.get('id') or step.get('name')!r} under `if: {step.get('if', '')}`"
        for step in after
        if ACTS_ON_A_MEASURED_RANGE not in str(step.get("if", ""))
    ]
    assert wrong == [], (
        f"steps after 'close' that do not require a measured range: {wrong}. The verdict is absent on a "
        f"run the guard declined, so the condition is `{ACTS_ON_A_MEASURED_RANGE}` and never a test "
        "against 'true'"
    )


def test_the_stale_proposal_is_closed_on_an_absent_verdict_too() -> None:
    # A run landing on a commit a release already tagged reaches `close` with no verdict at all.
    close = next(step for step in proposal_steps() if step.get("id") == "close")
    condition = str(close.get("if", ""))
    assert condition == CLOSES_A_STALE_PROPOSAL, (
        f"release-proposal's 'close' runs under `if: {condition}`. It has to fire on an absent verdict as "
        f"well as on 'true', which is `{CLOSES_A_STALE_PROPOSAL}`"
    )


def test_no_step_in_the_proposal_path_re_derives_the_verdict() -> None:
    # A shell condition inspecting the rendered file would be a second owner of the verdict.
    inspecting = [
        step.get("id") or step.get("name")
        for step in proposal_steps()
        if "notes-path" in str(step.get("run", "")) or "tr -d" in str(step.get("run", ""))
    ]
    assert inspecting == [], (
        f"{inspecting} decides in shell what the decision already emits. `next-version` reads the range "
        "once and says whether it renders anything"
    )
