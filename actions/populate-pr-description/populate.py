import os
import subprocess
from pathlib import Path
from textwrap import indent

from jinja2 import Template

base_sha = os.environ["BASE_SHA"]
head_sha = os.environ["HEAD_SHA"]
pr_number = os.environ["PR_NUMBER"]
repo = os.environ["REPO"]
template_path = Path(os.environ.get("TEMPLATE_PATH") or ".github/PULL_REQUEST_TEMPLATE.md")

# Each commit message is separated by a NUL byte to handle multi-line bodies.
result = subprocess.run(
    ["git", "log", "--format=%B%x00", f"{base_sha}..{head_sha}"],
    capture_output=True,
    text=True,
    check=True,
)
commits = [c.strip() for c in result.stdout.split("\x00") if c.strip()]

subjects: list[str] = []
change_items: list[str] = []
for commit in commits:
    lines = commit.splitlines()
    subject = lines[0] if lines else ""
    subjects.append(subject)
    # Blank lines are what separate the body's paragraphs, so they survive; indenting
    # keeps each paragraph inside the list item. Joining every line with a blank line
    # instead would render a wrapped paragraph as one paragraph per source line.
    body = "\n".join(ln.rstrip() for ln in lines[1:]).strip()
    if body:
        change_items.append(f"- **{subject}**\n\n{indent(body, '  ')}")
    else:
        change_items.append(f"- {subject}")

description = (
    "\n".join(f"- {s}" for s in subjects)
    if subjects
    else "<!-- Briefly describe what this PR does and why. -->"
)
changes = "\n\n".join(change_items) if change_items else "<!-- List the main changes. -->"

body = Template(template_path.read_text()).render(description=description, changes=changes)

subprocess.run(
    [
        "gh",
        "api",
        f"repos/{repo}/pulls/{pr_number}",
        "--method",
        "PATCH",
        "--field",
        f"body={body}",
    ],
    check=True,
)
