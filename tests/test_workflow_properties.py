import re
import tomllib
from itertools import pairwise
from typing import cast

from capabilities import (
    CONVENTIONAL_COMMITS,
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

# The steps of `python-ci` that judge the tree. Named by id rather than by the shape of their `run:`
# line, so the gate holds whatever the lines become.
STAGES = ("lint", "lint-changed", "typecheck", "tests")


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
        {".github/workflows/ci.yml", ".github/workflows/advisory.yml"},
    )
    assert unlisted == {".github/workflows/advisory.yml"}
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
    assert not GOVERNS_A_CACHE.search("hook-stage")


# An input is worth its place only where the caller knows something the callee cannot. A timeout is that
# where the runtime is a function of the caller's tree, and nowhere else — every other knob on a
# published surface is a promise with nothing behind it.
TIMEOUT_INPUT = "timeout-minutes"

MAY_TAKE_A_TIMEOUT = {
    "python-ci": "runs the caller's own tasks and cannot know how long they take",
    "prek-advisory": "reads the caller's whole tree and cannot know how large it is",
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


def test_the_lockfile_check_precedes_every_stage_of_python_ci() -> None:
    ids = [str(step.get("id", "")) for step in steps_of("python-ci", "python-ci")]
    missing = [step_id for step_id in ("lockfile", *STAGES) if step_id not in ids]
    assert missing == [], f"python-ci names no step {missing}, so this gate places nothing"
    assert ids.index("lockfile") < min(ids.index(stage) for stage in STAGES), (
        "python-ci runs a stage before installing from the lockfile. A lockfile disagreeing with "
        "its manifest makes every stage a verdict about a tree the maintainer does not have"
    )


def test_the_changed_files_lint_is_gated_on_the_lint_stage_switch() -> None:
    condition = next(
        str(step.get("if", ""))
        for step in steps_of("python-ci", "python-ci")
        if step.get("id") == "lint-changed"
    )
    assert "inputs.run-lint" in condition, (
        f"python-ci lints the changed set under `if: {condition}`, which does not consult "
        "run-lint. An input named for a stage governs that stage entirely or it is misnamed"
    )


# A whole-tree lint, read from the command rather than from which branch of the `if` it sits in, so a
# third path is covered the moment it is written.
WHOLE_TREE_LINT = re.compile(r"prek run .*--all-files.*")
SHOWS_THE_DIFF = "--show-diff-on-failure"


def whole_tree_lints() -> list[str]:
    run = next(
        str(step.get("run", ""))
        for step in steps_of("prek-advisory", "prek-advisory")
        if step.get("id") == "lint"
    )
    return WHOLE_TREE_LINT.findall(run)


def test_every_whole_tree_lint_reports_the_diff_that_would_fix_it() -> None:
    found = whole_tree_lints()
    assert len(found) >= 2, (
        f"prek-advisory's lint step holds {len(found)} whole-tree invocations, and it has a staged "
        "path and a default-stage one. This gate is reading the wrong step"
    )
    silent = [line for line in found if SHOWS_THE_DIFF not in line]
    assert silent == [], (
        f"whole-tree lints running without {SHOWS_THE_DIFF}: {silent}. A hook that rewrites a file "
        "then reports only its own name, so the comment says which hook failed and not the change "
        "that satisfies it"
    )


def test_the_whole_tree_lint_reader_finds_a_line_the_flag_is_gone_from() -> None:
    # Pre-flight: every line above carries the flag, so the gate can never show that it reads a line
    # by the invocation rather than by the flag it is looking for.
    stripped = [line.replace(f"{SHOWS_THE_DIFF} ", "") for line in whole_tree_lints()]
    assert stripped
    for line in stripped:
        assert WHOLE_TREE_LINT.fullmatch(line), line
        assert SHOWS_THE_DIFF not in line


# What a step does, read from the command it runs rather than from a list this test also keeps. A step
# creating a ref names one of these; nothing else in the release path does.
CREATES_A_REF = ("git/refs", "git/tags", "gh release create")

# Writing a version means authoring a commit. The release path tags what a merged change already
# decided, so it never authors one — the proposal path is where a version is written.
WRITES_A_VERSION = ("git commit", "cz bump", "sed -i", "bump-my-version")


def release_steps() -> list[Doc]:
    return steps_of("release", "tag-and-publish")


def test_no_ref_creating_step_precedes_the_refusals() -> None:
    # Principle V's structural gate. A refusal after a tag exists is not a refusal, because a version
    # tag is immutable and cannot be withdrawn — so ordering is the whole protection.
    steps = release_steps()
    decided = next(index for index, step in enumerate(steps) if step.get("id") == "decide")
    for index, step in enumerate(steps):
        if any(marker in str(step.get("run", "")) for marker in CREATES_A_REF):
            assert index > decided, (
                f"release step {step.get('id')!r} creates a ref at position {index}, before the "
                f"refusals at {decided}. Every refusal runs before any ref exists or none of them mean "
                "anything"
            )


def test_every_ref_creating_step_is_gated_on_the_verdict_and_on_the_dry_run() -> None:
    # `proceed` is not permission to create a ref: a dry run proceeds and creates nothing. Both gates
    # or a dry run tags for real.
    found = 0
    for step in release_steps():
        if not any(marker in str(step.get("run", "")) for marker in CREATES_A_REF):
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
    assert offending == [], (
        f"release.yml authors a change: {offending}. It tags what was already decided, and a version "
        "it wrote itself would be a version no review ever saw"
    )


def test_the_version_writing_markers_match_a_step_that_authors_one() -> None:
    # Pre-flight the markers. No step in the release path writes a version, which is the point, so the
    # gate above can never demonstrate that its tuple still matches anything.
    assert any(marker in 'git commit -m "chore: release v1.2.3"' for marker in WRITES_A_VERSION)
    assert any(marker in "uv run cz bump --yes" for marker in WRITES_A_VERSION)
    assert not any(
        marker in "gh release create v1.2.3 --notes-file notes.md" for marker in WRITES_A_VERSION
    )


# A ruleset write, read from the command rather than from a list this test also keeps. Only a write
# sends a body, so `--input` is what separates the two calls in this workflow from the read above them.
SENDS_A_BODY = "--input"


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
        if SENDS_A_BODY not in str(step.get("run", "")):
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
