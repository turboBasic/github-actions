import shutil
from collections.abc import Iterable

from . import ERROR, annotate, read_text


def absent(tools: Iterable[str]) -> list[str]:
    return [tool for tool in tools if shutil.which(tool) is None]


def run() -> int:
    capability = read_text("CAPABILITY").strip() or "this capability"
    tools = read_text("TOOLS").split()
    if not tools:
        annotate(
            ERROR,
            f"preflight was asked to check nothing on behalf of {capability}, so it would report "
            "success whatever the runner is missing. Name the tools in the `tools` input, or drop the "
            "step and the prerequisite together",
        )
        return 1
    missing = absent(tools)
    if not missing:
        return 0
    # Names the tool, the capability, and where to declare it. `command not found` is not a contract.
    annotate(
        ERROR,
        f"{capability} looked for {', '.join(missing)} on PATH after installing this repository's "
        f"pinned tools, and did not find {'them' if len(missing) > 1 else 'it'}. Add "
        f"{', '.join(missing)} to the [tools] table in mise.toml and commit the change; {capability} "
        "never pins a version the repository being released does not control",
    )
    return 1
