import re
from collections.abc import Iterable

Version = tuple[int, int, int]

# The compatibility boundary, stated once. `compatibility_line` is its only reader, and a test holds
# that. Below this version the minor signals a break, so reading the boundary off the major is wrong —
# and wrong permissively, which lets a break move a ref consumers pin.
FIRST_STABLE: Version = (1, 0, 0)

# The baseline for a repository with no releases. It is not ahead of itself, so every merge declines
# while it stands, and a repository may sit here indefinitely.
UNRELEASED: Version = (0, 0, 0)

# No leading zero, no pre-release, no build metadata, no leading `v`.
VERSION = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")


def parse_version(text: str) -> Version | None:
    found = VERSION.match(text)
    return (int(found[1]), int(found[2]), int(found[3])) if found else None


def format_version(version: Version) -> str:
    return ".".join(str(part) for part in version)


def is_release_tag(tag: str) -> bool:
    # A git glob cannot anchor, so `v[0-9]*.[0-9]*.[0-9]*` admits `v1.2.3-rc1` and `v1.2.3.4`. This is
    # what decides a release tag, and every reader of one goes through it.
    return tag.startswith("v") and VERSION.match(tag.removeprefix("v")) is not None


def released_versions(tags: Iterable[str]) -> tuple[Version, ...]:
    # A tag that is not a plain version is not a release of any line here — a moving ref is one, and a
    # repository is allowed to carry tags this scheme never made — so it is skipped, not refused.
    parsed = (parse_version(tag.removeprefix("v")) for tag in tags)
    return tuple(version for version in parsed if version is not None)


def compatibility_line(version: Version) -> tuple[int, ...]:
    return version[:1] if version >= FIRST_STABLE else version[:2]


def moving_ref(version: Version) -> str:
    return "v" + ".".join(str(part) for part in compatibility_line(version))


def increment(version: Version, breaking: bool, feature: bool) -> Version:
    major, minor, patch = version
    # Which component the line owns is read from the line, never from the version, so the boundary
    # keeps its single owner. A feature may only advance a component the line does not own.
    line_owns_the_major = len(compatibility_line(version)) == 1
    if breaking:
        return (major + 1, 0, 0) if line_owns_the_major else (major, minor + 1, 0)
    if feature and line_owns_the_major:
        return (major, minor + 1, 0)
    return (major, minor, patch + 1)
