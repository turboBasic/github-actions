import os
import re
import tomllib
from collections.abc import Iterable
from fnmatch import fnmatch
from typing import Any, NamedTuple, cast

from . import ERROR, NOTICE, annotate, emit, read_text, repository, repository_directory
from .repository import RECORD
from .version import (
    UNRELEASED,
    Version,
    compatibility_line,
    format_version,
    increment,
    moving_ref,
    parse_version,
    released_versions,
)

# A break is `type!:` in the subject or a BREAKING CHANGE footer in the body — both are Conventional
# Commits' own spellings, and reading only the subject would miss a break its author declared properly.
BREAKING_SUBJECT = re.compile(r"^[a-zA-Z]+(\([^)]*\))?!:")
BREAKING_FOOTER = re.compile(r"^BREAKING[ -]CHANGE:", re.MULTILINE)
FEATURE_SUBJECT = re.compile(r"^feat(\([^)]*\))?!?:")

# How the run was reached. The already-released condition means something different for each, which is
# why it is an occasion rather than a boolean.
ROUTINE = "routine"
DRY_RUN = "dry-run"
DELIBERATE = "deliberate"

OFF_DEFAULT_BRANCH = "off-default-branch"
MALFORMED_VERSION = "malformed-version"
ALREADY_RELEASED = "already-released"
NO_NOTES = "no-notes"
BREAKS_A_RELEASED_LINE = "breaks-a-released-line"
BAD_SURFACE = "bad-surface-declaration"

SURFACE_KEYS = ("exclude", "include")

MOVING_REF = "moving-ref"
NEXT_VERSION = "next-version"
RELEASE_VERDICT = "release-verdict"
PROPOSAL_VERSION = "proposal-version"
DECISIONS = (MOVING_REF, NEXT_VERSION, RELEASE_VERDICT, PROPOSAL_VERSION)


class Refusal(NamedTuple):
    key: str
    message: str


class Surface(NamedTuple):
    include: tuple[str, ...]
    exclude: tuple[str, ...]
    declared: bool


class Verdict(NamedTuple):
    proceed: bool
    severity: str
    message: str


class Request(NamedTuple):
    version_text: str
    branch: str
    default_branch: str
    occasion: str
    existing: tuple[Version, ...]
    notes: str
    breaking: bool
    feature: bool
    changed_paths: tuple[str, ...]
    surface: Surface


def find_last_computed(messages: Iterable[str]) -> str:
    # Newest first, past however many of a person's edits sit on top. Reading only the tip finds no
    # trailer the moment their commit becomes the tip, which is the ordinary shape of an override.
    for message in messages:
        for line in message.splitlines():
            if line.startswith("Computed-Version: "):
                return line.removeprefix("Computed-Version: ")
    return ""


def settle_proposal_version(computed: str, on_branch: str, last_computed: str) -> tuple[str, bool]:
    # The branch's version differs from the last computed one only because a person edited it. The
    # comparison is against a stored computation read off the branch, so it survives every rewrite of the
    # branch and every replacement of the pull request body.
    #
    # A missing trailer is not evidence of an override: a branch this workflow never wrote to has nothing
    # to compare against. Treating that absence as a difference would freeze the branch forever.
    if on_branch and last_computed and parse_version(on_branch) and on_branch != last_computed:
        return on_branch, True
    return computed, False


def range_verdicts(messages: Iterable[str]) -> tuple[bool, bool]:
    # The two verdicts the increment and the last refusal both read. Getting either wrong puts a release
    # on the wrong compatibility line, and a version tag cannot be withdrawn.
    breaking = False
    feature = False
    for message in messages:
        subject = message.partition("\n")[0]
        breaking = breaking or bool(
            BREAKING_SUBJECT.match(subject) or BREAKING_FOOTER.search(message)
        )
        feature = feature or bool(FEATURE_SUBJECT.match(subject))
    return breaking, feature


def unusable_path(path: str) -> bool:
    return not path or any(char.isspace() for char in path) or path.startswith("-")


def read_surface(table: object) -> Surface | Refusal:
    if table is None:
        return Surface(include=(), exclude=(), declared=False)
    if not isinstance(table, dict):
        return Refusal(
            BAD_SURFACE,
            f"the surface declaration is a {type(table).__name__} rather than a table of "
            f"{list(SURFACE_KEYS)} path lists",
        )
    entries = cast(dict[object, object], table)
    unknown = sorted(str(key) for key in entries if key not in SURFACE_KEYS)
    if unknown:
        return Refusal(
            BAD_SURFACE,
            f"the surface declaration names {unknown} and only {list(SURFACE_KEYS)} are read. A "
            "misspelled key would read as an absent declaration, which widens the surface to every "
            "path while looking configured",
        )
    lists: dict[str, tuple[str, ...]] = {}
    for key in SURFACE_KEYS:
        value = entries.get(key, [])
        if not isinstance(value, list):
            return Refusal(
                BAD_SURFACE,
                f"the surface declaration's {key} is a {type(value).__name__} rather than a list. "
                "Iterating a string yields characters, so every letter would become a path and the "
                "filter would match nothing while looking configured",
            )
        paths = tuple(str(entry) for entry in cast(list[object], value))
        offending = [path for path in paths if unusable_path(path)]
        if offending:
            return Refusal(
                BAD_SURFACE,
                f"the surface declaration's {key} holds {offending!r}. A path is non-empty, holds no "
                "whitespace, and does not begin with a hyphen",
            )
        lists[key] = paths
    return Surface(include=lists["include"], exclude=lists["exclude"], declared=True)


def surface_notice(surface: Surface) -> str | None:
    if surface.declared:
        return None
    return (
        "no surface declaration was found, so every changed path counts towards a break. That "
        "refuses more often rather than less, which is the safe direction — declare include and "
        "exclude path lists to narrow it"
    )


def matches(path: str, patterns: tuple[str, ...]) -> bool:
    return any(
        fnmatch(path, pattern) or fnmatch(path, f"{pattern.rstrip('/')}/*") for pattern in patterns
    )


def touches_surface(surface: Surface, paths: Iterable[str]) -> bool:
    for path in paths:
        if surface.include and not matches(path, surface.include):
            continue
        if matches(path, surface.exclude):
            continue
        return True
    return False


def refusals(request: Request) -> list[Refusal]:
    # The order is the invariant principle V turns on: every refusal is evaluated before any ref
    # exists, because a version tag is immutable and a refusal after one is not a refusal.
    found: list[Refusal] = []
    if request.branch != request.default_branch:
        found.append(
            Refusal(
                OFF_DEFAULT_BRANCH,
                f"the run is on {request.branch!r} and a release is cut only from "
                f"{request.default_branch!r}, which is read from the run rather than compared "
                "against a literal name",
            )
        )
    version = parse_version(request.version_text)
    if version is None:
        found.append(
            Refusal(
                MALFORMED_VERSION,
                f"the declared version {request.version_text!r} is not a plain N.N.N — no leading "
                "v, no leading zero, no pre-release, no build metadata",
            )
        )
        # Nothing below can be decided without a version, and a refusal derived from one that was
        # never read would name a comparison nobody made.
        return found
    highest = max(request.existing, default=UNRELEASED)
    if version <= highest:
        if request.existing:
            behind = (
                f"the declared version {format_version(version)} is not ahead of "
                f"{format_version(highest)}, the highest release across every compatibility line. A "
                "frozen line is left where it is rather than backported"
            )
        else:
            behind = (
                f"nothing has been released and the declared version is {format_version(version)}, "
                f"which is not ahead of {format_version(UNRELEASED)} — the version that means "
                "unreleased. Bump it when the first release is ready"
            )
        found.append(Refusal(ALREADY_RELEASED, behind))
    if not request.notes.strip():
        found.append(
            Refusal(NO_NOTES, "the range renders no notes, so there is nothing to publish")
        )
    if (
        request.breaking
        and touches_surface(request.surface, request.changed_paths)
        and compatibility_line(version) in {compatibility_line(o) for o in request.existing}
    ):
        found.append(
            Refusal(
                BREAKS_A_RELEASED_LINE,
                f"the range breaks the consumer surface while {format_version(version)} stays on "
                f"{moving_ref(version)}, which already has a release. A break starts the next line",
            )
        )
    return found


def decide(request: Request) -> Verdict:
    found = refusals(request)
    reported = "; ".join(refusal.message for refusal in found)
    # `proceed` is not permission to create a ref. A dry run proceeds and creates nothing, so the
    # caller gates every ref-creating step on the dry-run switch as well as on this.
    if request.occasion == DRY_RUN:
        return Verdict(
            True,
            NOTICE,
            f"a dry run creates nothing. It would have refused: {reported}"
            if found
            else "a dry run creates nothing, and every refusal passed",
        )
    if not found:
        return Verdict(True, NOTICE, f"every refusal passed for {request.version_text}")
    if request.occasion == ROUTINE and ALREADY_RELEASED in [r.key for r in found]:
        # A version not ahead of the highest release has not been bumped yet. It is provisional, so
        # nothing below it can be assessed, and a break "on a released line" only says the bump has not
        # happened. A default branch must not redden for that.
        #
        # Softened only while the version is behind. A version that is ahead was asserted by a merged
        # change, so anything wrong with it stays an error however the run was reached.
        return Verdict(False, NOTICE, reported)
    return Verdict(False, ERROR, reported)


def read_records(name: str) -> tuple[str, ...]:
    return tuple(record.strip() for record in read_text(name).split(RECORD) if record.strip())


def read_lines(name: str) -> tuple[str, ...]:
    return tuple(line.strip() for line in read_text(name).splitlines() if line.strip())


def read_released_versions(name: str) -> tuple[Version, ...]:
    return released_versions(read_lines(name))


def surface_from_manifest(path: str) -> Surface | Refusal:
    if not path or not os.path.exists(path):
        return read_surface(None)
    with open(path, "rb") as handle:
        manifest: dict[str, Any] = tomllib.load(handle)
    tool: object = manifest.get("tool")
    if not isinstance(tool, dict):
        return read_surface(None)
    return read_surface(cast(dict[str, object], tool).get("turbobasic-release"))


def declared_version() -> Version | None:
    return parse_version(read_text("VERSION").strip())


def answer_moving_ref() -> int:
    version = declared_version()
    if version is None:
        annotate(ERROR, f"release-decisions cannot name a ref for {read_text('VERSION')!r}")
        return 1
    emit(ref=moving_ref(version))
    return 0


def answer_next_version() -> int:
    where = repository_directory()
    manifest = read_text("MANIFEST") or "pyproject.toml"
    declared = repository.declared_version(where, manifest)
    version = parse_version(declared)
    if version is None:
        annotate(ERROR, f"release-decisions cannot increment {declared!r}, read from {manifest}")
        return 1
    # Rendered here rather than by a `run:` block, so whether the range is empty and what the increment
    # is are read from one pass over the same range.
    notes_path = read_text("NOTES_PATH") or f"{where}/release-notes.md"
    repository.render_notes(where, read_text("CLIFF_CONFIG") or "cliff.toml", notes_path)
    breaking, feature = range_verdicts(repository.commit_messages(where))
    nxt = increment(version, breaking=breaking, feature=feature)
    emit(
        version=format_version(nxt),
        ref=moving_ref(nxt),
        **{"notes-path": notes_path},
    )
    return 0


def answer_release_verdict() -> int:
    # Everything the refusals read comes from the repository itself, so nothing about the range travels
    # through an output and back. Only the occasion and the branch are the run's to state.
    where = repository_directory()
    manifest = read_text("MANIFEST") or "pyproject.toml"
    surface = surface_from_manifest(f"{where}/{manifest}")
    if isinstance(surface, Refusal):
        # A malformed declaration is refused before any ref exists rather than read as an absent one.
        emit(proceed="false", severity=ERROR, message=surface.message, ref="", **{"notes-path": ""})
        annotate(ERROR, surface.message)
        return 1
    notice = surface_notice(surface)
    if notice:
        annotate(NOTICE, notice)
    notes_path = read_text("NOTES_PATH") or f"{where}/release-notes.md"
    notes = repository.render_notes(where, read_text("CLIFF_CONFIG") or "cliff.toml", notes_path)
    breaking, feature = range_verdicts(repository.commit_messages(where))
    version_text = repository.declared_version(where, manifest)
    request = Request(
        version_text=version_text,
        branch=read_text("BRANCH").strip(),
        default_branch=read_text("DEFAULT_BRANCH").strip(),
        occasion=read_text("OCCASION").strip() or DELIBERATE,
        existing=released_versions(repository.release_tags(where)),
        notes=notes,
        breaking=breaking,
        feature=feature,
        changed_paths=repository.changed_paths(where),
        surface=surface,
    )
    verdict = decide(request)
    version = parse_version(request.version_text)
    emit(
        proceed="true" if verdict.proceed else "false",
        severity=verdict.severity,
        message=verdict.message,
        ref=moving_ref(version) if version else "",
        # What the tag is named after. Read from the manifest here rather than passed in, so the version
        # tagged and the version judged cannot differ.
        version=version_text,
        **{"notes-path": notes_path},
    )
    annotate(verdict.severity, verdict.message)
    # A decline is not a failure: a default branch must not redden for a merge that did nothing wrong.
    return 1 if verdict.severity == ERROR else 0


def answer_proposal_version() -> int:
    # The branch, never a pull request body: a template change, a hand edit or a reopen cannot lose what
    # is stored here. Every commit unique to the branch, not only its tip.
    where = repository_directory()
    proposal_ref = read_text("PROPOSAL_REF").strip()
    base = read_text("BASE_COMMIT").strip()
    manifest = read_text("MANIFEST") or "pyproject.toml"
    on_branch = repository.version_on_ref(where, proposal_ref, manifest)
    last_computed = find_last_computed(repository.messages_between(where, base, proposal_ref))
    version, overridden = settle_proposal_version(
        computed=read_text("COMPUTED").strip(),
        on_branch=on_branch.strip(),
        last_computed=last_computed,
    )
    if overridden:
        annotate(
            NOTICE, f"keeping {version} from the proposal branch — a person has already decided"
        )
    emit(version=version)
    return 0


def run(decision: str) -> int:
    if decision == MOVING_REF:
        return answer_moving_ref()
    if decision == NEXT_VERSION:
        return answer_next_version()
    if decision == RELEASE_VERDICT:
        return answer_release_verdict()
    if decision == PROPOSAL_VERSION:
        return answer_proposal_version()
    annotate(
        ERROR, f"release-decisions was asked for {decision!r} and answers only {list(DECISIONS)}"
    )
    return 1
