import os
import sys
import uuid

NOTICE = "notice"
ERROR = "error"


def read_text(name: str) -> str:
    return os.environ.get(name, "")


def emit(**values: str) -> None:
    path = read_text("GITHUB_OUTPUT")
    if not path:
        return
    with open(path, "a", encoding="utf-8") as handle:
        for name, value in values.items():
            # A value may hold newlines — rendered notes and a rendered difference both do — so every
            # output uses the delimiter form, and the delimiter is random per value. A fixed one
            # appearing inside the value would close the block early and let the remainder be read as
            # further outputs; the values here are rendered from commit messages and API responses, so a
            # commit or a ruleset quoting the delimiter is all it would take.
            delimiter = f"delimiter{uuid.uuid4().hex}"
            handle.write(f"{name}<<{delimiter}\n{value}\n{delimiter}\n")


def annotate(severity: str, message: str) -> None:
    print(f"::{severity}::{message}", file=sys.stderr if severity == ERROR else sys.stdout)
