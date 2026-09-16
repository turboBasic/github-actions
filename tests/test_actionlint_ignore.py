import re
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

from capabilities import REPO, WORKFLOW_DIR

CONFIG = REPO / ".github" / "actionlint.yaml"

DEBT = "docs/technical-debt.md"

# The two same-repository forms GitHub documents and zizmor's self-repository audit demands, each of
# which actionlint still refuses. One per silenced message.
PROBES = {
    "a reusable workflow call": """
name: probe
on:
  pull_request:
permissions: {}
jobs:
  probe:
    permissions: {}
    uses: $/.github/workflows/target.yml
""",
    "an action reference": """
name: probe
on:
  pull_request:
permissions: {}
jobs:
  probe:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    permissions: {}
    steps:
      - uses: $/actions/target
""",
}


def silenced() -> list[str]:
    declared = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    glob = f"{WORKFLOW_DIR.relative_to(REPO)}/**/*.yml"
    return [str(pattern) for pattern in declared["paths"][glob]["ignore"]]


def verdicts(workflow: str, tmp_path: Path) -> str:
    assert shutil.which("actionlint"), (
        "actionlint is not on PATH, so this gate cannot ask whether it still refuses the `$/` form and "
        "the ignore's reason is unchecked. Run the suite as `mise run test`"
    )
    planted = tmp_path / ".github" / "workflows"
    planted.mkdir(parents=True, exist_ok=True)
    (planted / "probe.yml").write_text(workflow, encoding="utf-8")
    # Run from the planted tree, so this repository's own configuration — the very ignore under test —
    # cannot suppress the verdict being looked for.
    return subprocess.run(
        ["actionlint", "-no-color", ".github/workflows/probe.yml"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    ).stdout


def test_the_config_silences_one_message_per_probe() -> None:
    patterns = silenced()
    assert len(patterns) == len(PROBES), (
        f"{CONFIG.name} silences {patterns} — {len(patterns)} messages, and this gate plants "
        f"{len(PROBES)} probes. Every silenced message is held to its reason or one of them is outliving it"
    )


@pytest.mark.parametrize("what", sorted(PROBES))
def test_every_silenced_message_is_still_the_wrong_verdict(what: str, tmp_path: Path) -> None:
    # This gate fails when the outside world improves, which is the only way an expiry works. The ignore
    # exists because two tools contradict each other; nothing else announces the day that ends.
    output = verdicts(PROBES[what], tmp_path)
    matched = [pattern for pattern in silenced() if re.search(pattern, output)]
    assert matched, (
        f"actionlint no longer refuses {what} written as `$/`, so the ignore in {CONFIG.name} has "
        f"outlived its reason: two gates no longer contradict each other. Delete the `paths:` entry — "
        f"and the file, once both are gone — and remove the row from {DEBT}. actionlint said:\n{output}"
    )
