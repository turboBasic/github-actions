import os
import subprocess
import sys
import uuid
from collections.abc import Sequence

NOTICE = "notice"
ERROR = "error"


def read_text(name: str) -> str:
    return os.environ.get(name, "")


def repository_directory() -> str:
    # The tree to read: the caller's checkout on a runner, the working directory locally. Never the
    # module's own location — a composite action's files arrive as an export with no `.git`.
    return read_text("REPO_DIR") or read_text("GITHUB_WORKSPACE") or os.getcwd()


def output(argv: Sequence[str], cwd: str | None = None) -> str:
    # `shell=False`, every value its own argument. A ref, a path and a version are text from outside.
    finished = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, check=False)
    if finished.returncode != 0:
        raise RuntimeError(
            f"{' '.join(argv)} exited {finished.returncode}: {finished.stderr.strip()}"
        )
    return finished.stdout


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
