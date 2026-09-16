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
            # Random per value. A fixed delimiter appearing inside a value closes the block early, and
            # the remainder is then read as further outputs.
            delimiter = f"delimiter{uuid.uuid4().hex}"
            handle.write(f"{name}<<{delimiter}\n{value}\n{delimiter}\n")


def annotate(severity: str, message: str) -> None:
    print(f"::{severity}::{message}", file=sys.stderr if severity == ERROR else sys.stdout)
